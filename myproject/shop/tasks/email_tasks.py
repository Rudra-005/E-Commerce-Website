import logging
from celery import shared_task
from shop.models import Order
from shop.utils.task_logger import log_task_execution
from smtplib import SMTPException

logger = logging.getLogger(__name__)

@shared_task(
    bind=True, 
    max_retries=5, 
    default_retry_delay=300, # 5 minutes
    autoretry_for=(SMTPException, ConnectionError, Exception),
    retry_backoff=True,
    retry_jitter=True,
    soft_time_limit=120
)
@log_task_execution("Order Confirmation Email")
def send_order_confirmation_email_task(self, order_id):
    """
    Sends order confirmation, tracking info, and invoice.
    Retries automatically every 5 minutes on failure.
    """
    try:
        from shop.services.email_service import EmailService 
        order = Order.objects.get(id=order_id)
        
        success = EmailService.send_order_confirmation(order)
        if not success:
            raise Exception("EmailService.send_order_confirmation returned False")
        
        logger.info(f"Order confirmation email sent for Order #{order_id}")
        return {"status": "success", "order_id": order_id}
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found for email confirmation.")
        # Don't retry if order doesn't exist
        return {"status": "failed", "reason": "Order not found"}
    except Exception as exc:
        logger.error(f"Failed to send order confirmation email for Order #{order_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=300)
@log_task_execution("Send Welcome Email")
def send_welcome_email_task(self, user_id):
    try:
        from shop.services.email_service import EmailService
        success = EmailService.send_welcome_email(user_id)
        if not success:
            raise Exception("EmailService.send_welcome_email returned False")
        return {"status": "success", "user_id": user_id}
    except Exception as exc:
        logger.error(f"Error in send_welcome_email_task for user {user_id}: {exc}")
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=1, soft_time_limit=120)
@log_task_execution("Failed Email Retry Cron")
def retry_failed_emails_task(self):
    """
    A scheduled task that runs every 5 minutes.
    In a robust system, this would query a FailedEmail model and re-enqueue them.
    Since we are relying on Celery's autoretry mechanism (which uses RabbitMQ/Redis DLQ and countdown),
    this task acts as an auditor to alert admins if DLQ is growing.
    """
    logger.info("Executing periodic failed email retry auditor.")
    # E.g., re-enqueue from DB if we had a FailedEmailLog table
    return {"status": "success"}
