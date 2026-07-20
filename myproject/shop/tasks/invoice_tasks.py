import logging
from celery import shared_task
from shop.models import Order
from shop.utils.task_logger import log_task_execution

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=300)
@log_task_execution("Generate Invoice")
def generate_invoice_task(self, order_id):
    """
    Triggered after successful payment. 
    Generates an invoice PDF, stores it, and emails the invoice.
    """
    from shop.services.invoice_service import InvoiceService
    try:
        logger.info(f"Generating invoice for order {order_id}")
        order = Order.objects.get(id=order_id)
        
        # This service internally creates the Invoice object and the PDF
        invoice = InvoiceService.generate_invoice(order)
        
        if invoice:
            # We can dispatch the email task from here so they run sequentially
            from shop.tasks.email_tasks import send_order_confirmation_email_task
            send_order_confirmation_email_task.delay(order_id)
            
        return {"status": "success", "order_id": order_id}
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found for invoice generation.")
        # Do not retry for DoesNotExist
        return {"status": "failed", "reason": "Order not found"}
    except Exception as exc:
        logger.error(f"Failed to generate invoice for order {order_id}: {exc}")
        raise self.retry(exc=exc)
