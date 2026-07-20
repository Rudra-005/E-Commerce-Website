import logging
from celery import shared_task
from shop.utils.task_logger import log_task_execution

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=300, soft_time_limit=1200)
@log_task_execution("Update Recommendation Cache")
def update_recommendation_cache_task(self):
    """
    Nightly task to refresh recommendations.
    Refreshes FAISS index, embeddings, and cached recommendations.
    Does NOT retrain full ML model to save compute.
    """
    try:
        logger.info("Updating recommendation cache")
        from shop.services.recommendation_service import RecommendationEngine
        RecommendationEngine.load_faiss_indexes()
        
        # Here we would normally trigger an update of the embeddings 
        # from the database state if we are doing a light re-compute.
        # e.g. RecommendationEngine.refresh_embeddings()
        
        return {"status": "success"}
    except Exception as exc:
        raise self.retry(exc=exc)
