import os
# ML Libraries imported locally inside methods to save RAM
import logging
from django.conf import settings
from django.db.models import Count, Avg, Case, When
from shop.models import Product, UserInteraction

logger = logging.getLogger(__name__)

class RecommendationEngine:
    """
    Generates personalized product recommendations based on user interaction history and FAISS embeddings.
    """
    
    _product_faiss_index = None
    _product_ids = None
    _user_embeddings = None
    _user_ids = None
    _is_loaded = False

    @classmethod
    def load_faiss_indexes(cls):
        """Loads FAISS indexes for products and user embeddings."""
        if cls._is_loaded:
            return

        try:
            import faiss
            import numpy as np
            
            base_dir = settings.BASE_DIR
            emb_dir = os.path.join(base_dir, 'ml_data', 'embeddings')
            p_emb_path = os.path.join(emb_dir, 'product_embeddings.npy')
            p_id_path = os.path.join(emb_dir, 'product_ids.npy')
            u_emb_path = os.path.join(emb_dir, 'user_embeddings.npy')
            u_id_path = os.path.join(emb_dir, 'user_ids.npy')
            
            if not all(os.path.exists(p) for p in [p_emb_path, p_id_path, u_emb_path, u_id_path]):
                logger.warning("Embedding files missing. ML Recommendations disabled.")
                cls._is_loaded = True
                return

            # Load Product Embeddings and Build Index
            p_embeddings = np.load(p_emb_path).astype('float32')
            cls._product_ids = np.load(p_id_path, allow_pickle=True)
            faiss.normalize_L2(p_embeddings) # For inner product -> cosine similarity

            
            dimension = p_embeddings.shape[1]
            cls._product_faiss_index = faiss.IndexFlatIP(dimension)
            cls._product_faiss_index.add(p_embeddings)
            
            # Load User Embeddings into memory (dict for O(1) lookup)
            u_embeddings = np.load(u_emb_path).astype('float32')
            faiss.normalize_L2(u_embeddings) # Normalize user vectors as well
            u_ids = np.load(u_id_path, allow_pickle=True)
            
            cls._user_embeddings = {str(uid): vec for uid, vec in zip(u_ids, u_embeddings)}
            
            cls._is_loaded = True
            logger.info("Successfully loaded Two-Tower FAISS indexes.")
            
        except Exception as e:
            logger.error(f"Failed to load FAISS embeddings: {e}")
            cls._is_loaded = True # Prevent continuous retries

    @classmethod
    def get_recommendations(cls, user, limit=10, context_type='general', target_id=None, cart_ids=None):
        """Main routing method called by RecommendationAPIView."""
        cls.load_faiss_indexes()
        
        if context_type == 'similar' and target_id:
            return cls.get_related_products(target_id, limit)
        elif context_type == 'also_viewed' and target_id:
            return cls.get_customers_also_viewed(target_id, limit)
        elif context_type == 'bought_together' and cart_ids:
            return cls._get_bought_together(cart_ids, limit)
        
        # Default 'general' Recommended For You
        return cls.get_user_recommendations(user, limit)

    @classmethod
    def get_related_products(cls, product_id, limit=10):
        """Finds related products using the Product FAISS index and enforces category matching."""
        if not cls._product_faiss_index or cls._product_ids is None:
            return cls._get_fallback_similar_products(product_id, limit)
            
        try:
            target = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return []
            
        product_id_str = str(product_id)
        
        try:
            import numpy as np
            idx = np.where(cls._product_ids == product_id_str)[0][0]
            query_vector = cls._product_faiss_index.reconstruct(int(idx)).reshape(1, -1)
        except (IndexError, RuntimeError, Exception, ImportError):
            return cls._get_fallback_similar_products(product_id, limit)
            
        # Search FAISS for more items (since we will filter out wrong categories)
        search_k = limit * 5
        distances, indices = cls._product_faiss_index.search(query_vector, search_k)
        
        raw_related_ids = []
        for i in range(search_k):
            if i >= len(indices[0]): break
            match_idx = indices[0][i]
            if match_idx < 0: continue
            match_id = str(cls._product_ids[match_idx])
            
            if match_id != product_id_str:
                raw_related_ids.append(match_id)
                
        if not raw_related_ids:
            return cls._get_fallback_similar_products(product_id, limit)
            
        # Enforce category match
        matching_products = Product.objects.filter(id__in=raw_related_ids)
        if target.category_fk_id:
            matching_products = matching_products.filter(category_fk_id=target.category_fk_id)
            
        # Keep FAISS order
        product_dict = {str(p.id): p for p in matching_products}
        
        final_products = []
        for rid in raw_related_ids:
            if rid in product_dict:
                final_products.append(product_dict[rid])
            if len(final_products) == limit:
                break
                
        # If FAISS didn't have enough same-category items, pad with fallback
        if len(final_products) < limit:
            needed = limit - len(final_products)
            exclude_ids = [target.id] + [p.id for p in final_products]
            fallback = cls._get_fallback_similar_products(product_id, needed)
            
            # Since _get_fallback_similar_products could return overlapping items if not careful,
            # we manually ensure no duplicates
            for f in fallback:
                if f.id not in exclude_ids:
                    final_products.append(f)
                    exclude_ids.append(f.id)
                if len(final_products) == limit:
                    break
                    
        return final_products

    @classmethod
    def get_user_recommendations(cls, user, limit=10):
        """Finds personalized recommendations using User Embeddings via FAISS."""
        if not user.is_authenticated:
            return cls._get_fallback_general_recommendations(limit)
            
        if not cls._product_faiss_index or not cls._user_embeddings:
            return cls._get_fallback_general_recommendations(limit)
            
        user_id_str = str(user.id)
        user_vector = cls._user_embeddings.get(user_id_str)
        
        if user_vector is None:
            return cls._get_fallback_general_recommendations(limit)
            
        # Reshape for FAISS
        query_vector = user_vector.reshape(1, -1)
        
        # We need to exclude products the user has already bought.
        purchased_ids = set(UserInteraction.objects.filter(
            user=user, interaction_type='purchase'
        ).values_list('product_id', flat=True))
        
        # Search FAISS (fetch more to account for purchased items)
        search_limit = limit + len(purchased_ids) + 5
        distances, indices = cls._product_faiss_index.search(query_vector, search_limit)
        
        recommended_ids = []
        for i in range(search_limit):
            if i >= len(indices[0]): break
            match_idx = indices[0][i]
            if match_idx < 0: continue
            match_id = str(cls._product_ids[match_idx])
            
            if int(match_id) not in purchased_ids:
                recommended_ids.append(match_id)
                if len(recommended_ids) == limit:
                    break
                    
        if not recommended_ids:
            return cls._get_fallback_general_recommendations(limit)
            
        return cls._fetch_ordered_products(recommended_ids)

    @classmethod
    def get_customers_also_viewed(cls, product_id, limit=10):
        """Uses interaction co-occurrence (Collaborative Filtering via Django ORM)."""
        # Find up to 100 recent users who viewed this exact product
        user_ids = list(UserInteraction.objects.filter(
            product_id=product_id, interaction_type='view'
        ).values_list('user_id', flat=True).distinct()[:100])
        
        if not user_ids:
            return cls.get_related_products(product_id, limit)
            
        # Find other products those same users interacted with
        also_viewed_ids = UserInteraction.objects.filter(
            user_id__in=user_ids
        ).exclude(
            product_id=product_id
        ).values('product_id').annotate(
            interactions=Count('id')
        ).order_by('-interactions')[:limit]
        
        product_ids = [item['product_id'] for item in also_viewed_ids]
        
        if not product_ids:
            return cls.get_related_products(product_id, limit)
            
        products = Product.objects.filter(id__in=product_ids)
        product_dict = {str(p.id): p for p in products}
        result = [product_dict[str(pid)] for pid in product_ids if str(pid) in product_dict]
        
        if len(result) < limit:
            needed = limit - len(result)
            exclude_ids = [product_id] + [p.id for p in result]
            result.extend(cls._get_fallback_general_recommendations(needed, exclude_ids=exclude_ids))
            
        return result[:limit]

    # ==========================
    # HELPERS & FALLBACKS
    # ==========================
    
    @classmethod
    def _fetch_ordered_products(cls, string_id_list):
        """Fetches Django Products maintaining the exact order of the provided string IDs."""
        preserved_order = Case(*[When(pk=int(pk), then=pos) for pos, pk in enumerate(string_id_list)])
        return list(Product.objects.filter(id__in=string_id_list).order_by(preserved_order))

    @classmethod
    def _get_bought_together(cls, cart_ids, limit):
        """Helper for Cart page bought together recommendations."""
        if not cart_ids:
            return cls._get_fallback_general_recommendations(limit)
            
        cart_ids_list = [int(i) for i in cart_ids.split(',') if i.isdigit()]
        if not cart_ids_list:
            return cls._get_fallback_general_recommendations(limit)
            
        # Use FAISS related for the first item in cart as a quick robust bought-together
        return cls.get_related_products(cart_ids_list[0], limit)

    @classmethod
    def _get_fallback_similar_products(cls, target_id, limit):
        try:
            target = Product.objects.get(id=target_id)
            if not target.category_fk_id:
                return cls._get_fallback_general_recommendations(limit)
                
            similars = Product.objects.filter(
                category_fk_id=target.category_fk_id
            ).exclude(id=target_id).annotate(
                avg_rating=Avg('reviews__rating'),
                review_count=Count('reviews')
            ).order_by('-avg_rating', '-review_count')[:limit]
            
            similars_list = list(similars)
            if len(similars_list) < limit:
                needed = limit - len(similars_list)
                exclude_ids = [target_id] + [p.id for p in similars_list]
                similars_list.extend(cls._get_fallback_general_recommendations(needed, exclude_ids=exclude_ids))
                
            return similars_list[:limit]
        except Product.DoesNotExist:
            return cls._get_fallback_general_recommendations(limit)

    @classmethod
    def _get_fallback_general_recommendations(cls, limit, exclude_ids=None):
        qs = Product.objects.all()
        if exclude_ids:
            qs = qs.exclude(id__in=exclude_ids)
            
        return list(qs.annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        ).order_by('-avg_rating', '-review_count')[:limit])
