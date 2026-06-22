"""
Embedding service using BAAI/bge-small-en-v1.5.
Generates and stores product embeddings in PostgreSQL via pgvector.
"""

import logging
import threading
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Lazy-loaded singleton model instance
_model = None
_model_lock = threading.Lock()


def get_model():
    """Load the embedding model (singleton, loaded once)."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                logger.info("Loading BAAI/bge-small-en-v1.5 embedding model...")
                try:
                    # Load from local cache, avoiding network checks and potential hangs
                    _model = SentenceTransformer('BAAI/bge-small-en-v1.5', local_files_only=True, device='cpu')
                except Exception as e:
                    logger.warning(f"Could not load model locally from cache, falling back to online load: {e}")
                    _model = SentenceTransformer('BAAI/bge-small-en-v1.5', device='cpu')
                logger.info("Embedding model loaded successfully.")
    return _model


def build_product_text(product):
    """
    Build the text representation of a product for embedding.
    Combines name, category, description, and price range.
    """
    # Determine price range bucket
    price = float(product.price)
    if price < 1000:
        price_range = "very budget, under 1000"
    elif price < 5000:
        price_range = "budget, under 5000"
    elif price < 15000:
        price_range = "mid-range, under 15000"
    elif price < 50000:
        price_range = "premium, under 50000"
    else:
        price_range = "luxury, above 50000"

    # Get category name
    category_name = product.category or ""
    if product.category_fk:
        category_name = product.category_fk.name

    parts = [
        f"Product: {product.name}.",
        f"Category: {category_name}.",
        f"Price: ₹{price:.0f} ({price_range}).",
        f"Description: {product.description}.",
    ]

    return " ".join(parts)


def generate_embedding(text):
    """Generate embedding vector for a single text string."""
    model = get_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def generate_product_embedding(product):
    """Generate and store embedding for a single product."""
    from chatbot.models import ProductEmbedding

    text = build_product_text(product)
    vector = generate_embedding(text)

    embedding_obj, created = ProductEmbedding.objects.update_or_create(
        product=product,
        defaults={
            'embedding': vector,
            'text_content': text,
        }
    )
    return embedding_obj, created


def generate_all_embeddings(batch_size=50):
    """
    Generate embeddings for all products that don't have one yet.
    Returns (created_count, skipped_count).
    """
    from shop.models import Product
    from chatbot.models import ProductEmbedding

    # Get product IDs that already have embeddings
    existing_ids = set(
        ProductEmbedding.objects.values_list('product_id', flat=True)
    )

    products = Product.objects.all()
    total = products.count()
    created_count = 0
    skipped_count = 0

    model = get_model()

    # Process in batches
    batch_texts = []
    batch_products = []

    for i, product in enumerate(products.iterator()):
        if product.id in existing_ids:
            skipped_count += 1
            continue

        text = build_product_text(product)
        batch_texts.append(text)
        batch_products.append(product)

        if len(batch_texts) >= batch_size:
            _store_batch(model, batch_products, batch_texts)
            created_count += len(batch_texts)
            logger.info(f"Progress: {created_count + skipped_count}/{total}")
            batch_texts = []
            batch_products = []

    # Store remaining
    if batch_texts:
        _store_batch(model, batch_products, batch_texts)
        created_count += len(batch_texts)

    logger.info(f"Done. Created: {created_count}, Skipped: {skipped_count}")
    return created_count, skipped_count


def regenerate_all_embeddings(batch_size=50):
    """
    Regenerate embeddings for ALL products (including existing ones).
    Returns total count processed.
    """
    from shop.models import Product
    from chatbot.models import ProductEmbedding

    products = Product.objects.all()
    total = products.count()
    processed = 0

    model = get_model()

    batch_texts = []
    batch_products = []

    for product in products.iterator():
        text = build_product_text(product)
        batch_texts.append(text)
        batch_products.append(product)

        if len(batch_texts) >= batch_size:
            _store_batch(model, batch_products, batch_texts)
            processed += len(batch_texts)
            logger.info(f"Progress: {processed}/{total}")
            batch_texts = []
            batch_products = []

    if batch_texts:
        _store_batch(model, batch_products, batch_texts)
        processed += len(batch_texts)

    logger.info(f"Regenerated {processed} embeddings.")
    return processed


def _store_batch(model, products, texts):
    """Encode a batch of texts and store them."""
    from chatbot.models import ProductEmbedding

    embeddings = model.encode(texts, normalize_embeddings=True, batch_size=len(texts))

    for product, text, emb in zip(products, texts, embeddings):
        ProductEmbedding.objects.update_or_create(
            product=product,
            defaults={
                'embedding': emb.tolist(),
                'text_content': text,
            }
        )
