import logging
from celery import shared_task
from django.utils import timezone
from shop.models import Notification
from shop.utils.task_logger import log_task_execution

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=300, soft_time_limit=180)
@log_task_execution("Notification Cleanup")
def archive_old_notifications_task(self):
    """
    Weekly task to archive old notifications.
    Only archives read notifications older than 30 days.
    Never deletes unread notifications.
    """
    from datetime import timedelta
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    # We update in bulk to be efficient
    old_read_notifications = Notification.objects.filter(
        is_read=True, 
        archived=False,
        created_at__lt=thirty_days_ago
    )
    
    archived_count = old_read_notifications.update(archived=True)
    
    logger.info(f"Archived {archived_count} old, read notifications.")
    return {"status": "success", "archived_count": archived_count}
