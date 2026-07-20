import logging
from celery import shared_task
from django.utils import timezone
from shop.models import Coupon
from shop.utils.task_logger import log_task_execution

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=300, soft_time_limit=180)
@log_task_execution("Expired Coupon Cleanup")
def disable_expired_coupons_task(self):
    """
    Daily task to disable expired coupons without deleting them 
    (to preserve historical usage).
    """
    now = timezone.now()
    
    # We update in bulk to be efficient
    expired_active_coupons = Coupon.objects.filter(is_active=True, expires_at__lt=now)
    
    updated_count = expired_active_coupons.update(is_active=False)
    
    logger.info(f"Disabled {updated_count} expired coupons.")
    return {"status": "success", "disabled_count": updated_count}
