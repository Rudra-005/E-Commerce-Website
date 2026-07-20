import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from shop.models import Cart, Product, Notification
from shop.utils.task_logger import log_task_execution

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=120)
@log_task_execution("Checkout Expiration")
def expire_checkouts_task(self):
    """
    Finds carts in CHECKOUT status that have expired.
    Restores reserved stock safely using select_for_update, marks carts as EXPIRED.
    """
    from shop.services.inventory_service import InventoryService
    
    expired_carts = Cart.objects.filter(status='CHECKOUT', expires_at__lt=timezone.now())
    
    processed_count = 0
    for cart in expired_carts:
        try:
            # Release stock
            InventoryService.release_stock(
                reference_id=f"CART_{cart.id}",
                idempotency_key_prefix="EXP",
                release_reason="Cart Expired"
            )
            
            with transaction.atomic():
                # Mark cart as expired
                locked_cart = Cart.objects.select_for_update().get(id=cart.id)
                locked_cart.status = 'EXPIRED'
                locked_cart.save(update_fields=['status'])
                
                # Notify User if authenticated
                if locked_cart.user:
                    Notification.objects.create(
                        user=locked_cart.user,
                        message=f"Your checkout for cart {locked_cart.id} has expired. Stock has been released."
                    )
                
                processed_count += 1
                logger.info(f"Expired cart {locked_cart.id}. Released stock.")
        except Exception as e:

            logger.error(f"Failed to expire cart {cart.id}: {str(e)}")
            # We don't raise here, we continue to process other carts, but log the error.
            
    return {"status": "success", "processed_count": processed_count}


@shared_task(bind=True, max_retries=3, default_retry_delay=300, soft_time_limit=300)
@log_task_execution("Delete Guest Carts")
def delete_guest_carts_task(self):
    """
    Deletes guest carts older than 7 days.
    """
    from datetime import timedelta
    seven_days_ago = timezone.now() - timedelta(days=7)
    
    # Guest carts are those with no user and an old created_at date
    guest_carts = Cart.objects.filter(user__isnull=True, created_at__lt=seven_days_ago)
    
    deleted_count, _ = guest_carts.delete()
    
    logger.info(f"Deleted {deleted_count} old guest carts.")
    return {"status": "success", "deleted_count": deleted_count}
