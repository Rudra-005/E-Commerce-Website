import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from shop.models import Order, OrderItem, Product, Notification
from shop.utils.task_logger import log_task_execution

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=180)
@log_task_execution("Auto Cancel Unpaid COD")
def auto_cancel_unpaid_cod_task(self):
    """
    Finds COD orders that are Pending and unverified for more than 30 minutes.
    Cancels them, releases stock, and notifies the user.
    """
    from datetime import timedelta
    thirty_mins_ago = timezone.now() - timedelta(minutes=30)
    
    pending_cod_orders = Order.objects.filter(
        payment_method='COD',
        status='Pending',
        cod_verified=False,
        created_at__lt=thirty_mins_ago
    )
    
    from shop.services.inventory_service import InventoryService
    
    processed_count = 0
    for order in pending_cod_orders:
        try:
            # Release stock first
            InventoryService.release_stock(
                reference_id=f"ORDER_{order.id}",
                idempotency_key_prefix="COD_CANCEL",
                release_reason="Unpaid COD Cancelled"
            )
            
            with transaction.atomic():
                # Lock order to prevent race conditions during cancellation
                locked_order = Order.objects.select_for_update().get(id=order.id)
                
                if locked_order.status != 'Pending':
                    continue
                
                # Mark items as cancelled
                items = OrderItem.objects.filter(order=locked_order)
                for item in items:
                    item.status = 'Cancelled'
                    item.save(update_fields=['status'])
                
                locked_order.status = 'Cancelled'
                locked_order.save(update_fields=['status'])
                
                if locked_order.user:
                    Notification.objects.create(
                        user=locked_order.user,
                        message=f"Your Cash on Delivery Order #{locked_order.id} was cancelled because it was not verified within 30 minutes."
                    )
                
                processed_count += 1
                logger.info(f"Cancelled unpaid COD Order #{locked_order.id} and released stock.")
        except Exception as e:
            logger.error(f"Failed to cancel unpaid COD Order #{order.id}: {str(e)}")
            
    return {"status": "success", "processed_count": processed_count}
