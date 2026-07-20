import logging
from celery import shared_task
from django.utils import timezone
from django.db.models import Count, Avg, F
from django.db import transaction
from shop.models import Product, UserInteraction, Order
from shop.utils.task_logger import log_task_execution

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=300, soft_time_limit=600)
@log_task_execution("Product Popularity Score")
def update_product_popularity_score_task(self):
    """
    Runs hourly to calculate and update the popularity_score of all products.
    Weights: 
    - Purchases (0.4)
    - Cart additions (0.3)
    - Views (0.1)
    - Wishlist (0.1)
    - Ratings/Reviews (0.1)
    """
    logger.info("Starting product popularity score calculation.")
    
    # Process in batches using iterator() for performance
    products = Product.objects.all().iterator(chunk_size=100)
    
    updated_products = []
    
    for product in products:
        # Fetch interactions
        interactions = UserInteraction.objects.filter(product=product).values('interaction_type').annotate(count=Count('id'))
        
        counts = {item['interaction_type']: item['count'] for item in interactions}
        views = counts.get('view', 0)
        cart_adds = counts.get('cart', 0)
        purchases = counts.get('purchase', 0)
        wishlist_adds = counts.get('wishlist', 0)
        
        # Ratings
        avg_rating = product.average_rating
        review_count = product.total_reviews
        
        # Calculate score
        score = (purchases * 4.0) + (cart_adds * 3.0) + (wishlist_adds * 1.0) + (views * 0.1)
        score += (avg_rating * 2.0) + (review_count * 0.5)
        
        product.popularity_score = round(score, 2)
        updated_products.append(product)
        
        # Bulk update in chunks to avoid memory bloat
        if len(updated_products) >= 100:
            with transaction.atomic():
                Product.objects.bulk_update(updated_products, ['popularity_score'])
            updated_products = []

    # Update remaining
    if updated_products:
        with transaction.atomic():
            Product.objects.bulk_update(updated_products, ['popularity_score'])

    logger.info("Completed product popularity score calculation.")
    return {"status": "success"}


@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=600)
@log_task_execution("Generate Business Insights")
def generate_business_insights_task(self):
    """
    Nightly analytics reports.
    Generates Sales, Revenue, Orders, Top Products, etc.
    """
    logger.info("Generating nightly business insights and analytics reports.")
    # In a full implementation, this would aggregate data and store it in an AnalyticsReport model.
    # We mock the aggregation here to demonstrate structure.
    
    total_orders = Order.objects.count()
    # Mocking storage logic...
    
    return {"status": "success", "total_orders": total_orders}
