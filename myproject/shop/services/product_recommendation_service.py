import os
import faiss
import numpy as np
import logging
from django.conf import settings
from shop.models import Product

logger = logging.getLogger(__name__)

class ProductRecommendationService:
    _faiss_index = None
    _product_ids = None
    _is_loaded = False

    @classmethod
    def load_product_embeddings(cls):
        """Loads embeddings and builds FAISS index once on startup."""
        if cls._is_loaded:
            return

        try:
            base_dir = settings.BASE_DIR
            emb_path = os.path.join(base_dir, 'ml_data', 'embeddings', 'product_embeddings.npy')
            id_path = os.path.join(base_dir, 'ml_data', 'embeddings', 'product_ids.npy')
            
            if not os.path.exists(emb_path) or not os.path.exists(id_path):
                logger.warning(f"Embedding files not found. Recommendations disabled.")
                cls._is_loaded = True
                return

            # Load embeddings
            embeddings = np.load(emb_path).astype('float32')
            cls._product_ids = np.load(id_path, allow_pickle=True)
            
            # Normalize embeddings for Cosine Similarity (IndexFlatIP acts as cosine if normalized)
            faiss.normalize_L2(embeddings)
            
            # Build Index
            dimension = embeddings.shape[1]
            cls._faiss_index = faiss.IndexFlatIP(dimension)
            cls._faiss_index.add(embeddings)
            
            cls._is_loaded = True
            logger.info("Successfully loaded FAISS product embeddings.")
            
        except Exception as e:
            logger.error(f"Failed to load FAISS embeddings: {e}")
            cls._is_loaded = True # Prevent continuous retrying on failure

    @classmethod
    def get_related_products(cls, product_id, top_k=10):
        """Returns a list of related Product objects."""
        cls.load_product_embeddings()
        
        if cls._faiss_index is None or cls._product_ids is None:
            return []
            
        product_id_str = str(product_id)
        
        # Find the index of the queried product
        try:
            idx = np.where(cls._product_ids == product_id_str)[0][0]
        except IndexError:
            return [] # Product not in FAISS index
            
        # Reconstruct the vector from the FAISS index
        try:
            query_vector = cls._faiss_index.reconstruct(int(idx)).reshape(1, -1)
        except Exception as e:
            logger.error(f"FAISS reconstruct failed: {e}")
            return []
            
        # Search for top_k + 1 (since the product itself will be the #1 match)
        distances, indices = cls._faiss_index.search(query_vector, top_k + 1)
        
        related_ids = []
        for i in range(top_k + 1):
            match_idx = indices[0][i]
            match_id = str(cls._product_ids[match_idx])
            
            if match_id != product_id_str:
                related_ids.append(match_id)
                
        # Limit to exactly top_k in case it found more
        related_ids = related_ids[:top_k]
        
        if not related_ids:
            return []
            
        # Fetch Django Products while preserving FAISS ordering
        from django.db.models import Case, When
        preserved_order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(related_ids)])
        products = Product.objects.filter(id__in=related_ids).order_by(preserved_order)
        
        return products

def get_related_products(product_id, top_k=10):
    """Helper wrapper function to expose directly"""
    return ProductRecommendationService.get_related_products(product_id, top_k)
