"""
Vector search service using pgvector.
Implements filtered semantic search: extract filters → SQL filter → vector search.
"""

import re
import logging
from django.db.models import Q

logger = logging.getLogger(__name__)


def extract_filters(query):
    """
    Extract structured filters from a natural language query.
    Returns dict: {category, max_price, min_price, use_case}
    """
    query_lower = query.lower().strip()
    filters = {}

    # ── Price Extraction ──
    # "under 50000", "below 5000", "less than 10000"
    price_patterns = [
        r'(?:under|below|less\s+than|max|upto|up\s+to|within|budget\s+of)\s*(?:₹|rs\.?|inr)?\s*(\d[\d,]*)',
        r'(?:₹|rs\.?|inr)\s*(\d[\d,]*)\s*(?:or\s+less|max|budget)',
        r'(\d[\d,]*)\s*(?:rupees?|rs\.?)\s*(?:or\s+less|max|budget)',
    ]
    for pattern in price_patterns:
        match = re.search(pattern, query_lower)
        if match:
            price_str = match.group(1).replace(',', '')
            filters['max_price'] = int(price_str)
            break

    # "above 10000", "more than 5000", "over 2000"
    above_patterns = [
        r'(?:above|over|more\s+than|min|starting|from)\s*(?:₹|rs\.?|inr)?\s*(\d[\d,]*)',
    ]
    for pattern in above_patterns:
        match = re.search(pattern, query_lower)
        if match:
            price_str = match.group(1).replace(',', '')
            filters['min_price'] = int(price_str)
            break

    # "between 5000 and 10000"
    between_match = re.search(
        r'between\s*(?:₹|rs\.?|inr)?\s*(\d[\d,]*)\s*(?:and|to|-)\s*(?:₹|rs\.?|inr)?\s*(\d[\d,]*)',
        query_lower
    )
    if between_match:
        filters['min_price'] = int(between_match.group(1).replace(',', ''))
        filters['max_price'] = int(between_match.group(2).replace(',', ''))

    # ── Category Detection ──
    category_keywords = {
        'laptop': ['laptop', 'laptops', 'notebook', 'chromebook', 'macbook'],
        'phone': ['phone', 'phones', 'mobile', 'mobiles', 'smartphone', 'iphone', 'android'],
        'headphone': ['headphone', 'headphones', 'earphone', 'earphones', 'earbuds', 'airpods', 'headset'],
        'watch': ['watch', 'watches', 'smartwatch', 'smartwatches', 'fitness band'],
        'shoe': ['shoe', 'shoes', 'sneaker', 'sneakers', 'running shoe', 'footwear', 'boots'],
        'camera': ['camera', 'cameras', 'dslr', 'mirrorless'],
        'tv': ['tv', 'television', 'smart tv', 'monitor', 'display'],
        'tablet': ['tablet', 'tablets', 'ipad'],
        'speaker': ['speaker', 'speakers', 'bluetooth speaker', 'soundbar'],
        'keyboard': ['keyboard', 'keyboards', 'mechanical keyboard'],
        'mouse': ['mouse', 'mice', 'gaming mouse', 'wireless mouse'],
        'clothing': ['shirt', 'tshirt', 't-shirt', 'jeans', 'jacket', 'dress', 'clothing', 'clothes'],
        'bag': ['bag', 'bags', 'backpack', 'backpacks', 'handbag', 'luggage'],
    }

    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in query_lower:
                filters['category'] = category
                break
        if 'category' in filters:
            break

    # ── Use Case Detection ──
    use_case_keywords = {
        'gaming': ['gaming', 'gamer', 'game', 'fps', 'esports'],
        'student': ['student', 'students', 'college', 'study', 'school', 'education'],
        'office': ['office', 'work', 'professional', 'business', 'productivity'],
        'running': ['running', 'jogging', 'marathon', 'athletic'],
        'sports': ['sports', 'gym', 'fitness', 'workout', 'exercise', 'training'],
        'travel': ['travel', 'traveling', 'trip', 'portable', 'lightweight'],
        'photography': ['photography', 'photo', 'camera', 'photographer'],
        'music': ['music', 'audio', 'bass', 'sound', 'listening'],
        'gift': ['gift', 'gifts', 'gifting', 'present', 'birthday'],
    }

    for use_case, keywords in use_case_keywords.items():
        for keyword in keywords:
            if keyword in query_lower:
                filters['use_case'] = use_case
                break
        if 'use_case' in filters:
            break

    return filters


def search_products(query, top_k=8):
    """
    Perform filtered semantic search.

    Steps:
    1. Extract filters from query
    2. Apply database-level filters (price, category)
    3. Calculate vector similarity in memory on the filtered set using NumPy
    4. Return top products with scores
    """
    from shop.models import Product
    from chatbot.models import ProductEmbedding
    from chatbot.services.embedding_service import generate_embedding
    import numpy as np
    import json

    filters = extract_filters(query)
    logger.info(f"Extracted filters: {filters}")

    # ── Step 1: Build base queryset with SQL filters ──
    product_qs = Product.objects.all()

    if 'max_price' in filters:
        product_qs = product_qs.filter(price__lte=filters['max_price'])

    if 'min_price' in filters:
        product_qs = product_qs.filter(price__gte=filters['min_price'])

    if 'category' in filters:
        cat = filters['category']
        product_qs = product_qs.filter(
            Q(category__icontains=cat) |
            Q(name__icontains=cat) |
            Q(category_fk__name__icontains=cat)
        )

    filtered_product_ids = set(product_qs.values_list('id', flat=True))

    # If filtering gave us nothing, we should not fall back (it ignores user filters)
    if len(filtered_product_ids) == 0:
        logger.info("No products matched filters, returning empty list.")
        return [], filters

    # ── Step 2: Generate query embedding ──
    try:
        query_embedding = generate_embedding(query)
        query_vector = np.array(query_embedding, dtype=np.float32)
    except Exception as e:
        logger.error(f"Failed to generate embedding (is sentence_transformers installed?): {e}")
        # If embedding fails, return empty products so chat doesn't crash
        return [], filters

    # Normalize query vector
    norm_query = np.linalg.norm(query_vector)
    if norm_query > 0:
        query_vector = query_vector / norm_query

    # ── Step 3: Fetch embeddings and compute similarity in memory ──
    embeddings_qs = ProductEmbedding.objects.all()
    if filtered_product_ids is not None:
        embeddings_qs = embeddings_qs.filter(product_id__in=filtered_product_ids)

    # Load all relevant embeddings from database
    embeddings_data = list(embeddings_qs.select_related('product', 'product__category_fk'))
    
    if not embeddings_data:
        logger.info("No product embeddings found in the database.")
        return [], filters

    product_vectors = []
    for emb in embeddings_data:
        vec = emb.embedding
        if isinstance(vec, str):
            vec = json.loads(vec)
        product_vectors.append(vec)

    product_vectors = np.array(product_vectors, dtype=np.float32)  # shape: (N, 384)

    # Normalize product vectors
    norms = np.linalg.norm(product_vectors, axis=1)
    norms[norms == 0] = 1.0
    product_vectors_norm = product_vectors / norms[:, np.newaxis]

    # Calculate cosine similarity using dot product of normalized vectors
    similarities = np.dot(product_vectors_norm, query_vector)

    # Get top K indices sorted by similarity descending
    top_indices = np.argsort(similarities)[::-1][:top_k]

    # ── Step 4: Build result list ──
    products = []
    for idx in top_indices:
        result = embeddings_data[idx]
        product = result.product
        similarity = float(similarities[idx])

        # Skip products with similarity score lower than 0.38 (prevents off-topic matches)
        if similarity < 0.38:
            continue

        products.append({
            'id': product.id,
            'name': product.name,
            'price': str(product.price),
            'image': product.image,
            'description': product.description[:200],
            'category': product.category_fk.name if product.category_fk else product.category,
            'rating': product.average_rating,
            'stock': product.stock,
            'url': f'/product/{product.id}/',
            'similarity': round(similarity, 3),
        })

    logger.info(f"Memory vector search returned {len(products)} products")
    return products, filters
