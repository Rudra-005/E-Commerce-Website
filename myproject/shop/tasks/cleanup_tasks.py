import logging
import os
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from shop.models import EmailOTP
from shop.utils.task_logger import log_task_execution

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=120)
@log_task_execution("Expired OTP Cleanup")
def cleanup_expired_otp_task(self):
    """
    Hourly task to delete expired OTPs and verification tokens.
    """
    from datetime import timedelta
    # Assuming OTPs are valid for 10 minutes, we'll clean anything older than 1 hour just to be safe
    one_hour_ago = timezone.now() - timedelta(hours=1)
    
    deleted_count, _ = EmailOTP.objects.filter(created_at__lt=one_hour_ago).delete()
    
    logger.info(f"Deleted {deleted_count} expired OTPs.")
    return {"status": "success", "deleted_count": deleted_count}


@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=120)
@log_task_execution("Session Cleanup")
def cleanup_sessions_task(self):
    """
    Daily task to remove expired Django sessions.
    Also handles expired JWT blacklist entries if `rest_framework_simplejwt.token_blacklist` is installed.
    """
    from django.contrib.sessions.models import Session
    
    # Delete expired Django sessions
    deleted_count, _ = Session.objects.filter(expire_date__lt=timezone.now()).delete()
    logger.info(f"Deleted {deleted_count} expired Django sessions.")
    
    # If using rest_framework_simplejwt blacklist
    try:
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
        # Outstanding tokens with an expiration date in the past
        jwt_deleted_count, _ = OutstandingToken.objects.filter(expires_at__lt=timezone.now()).delete()
        logger.info(f"Deleted {jwt_deleted_count} expired JWT outstanding tokens.")
    except ImportError:
        pass
        
    return {"status": "success", "deleted_sessions": deleted_count}


@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=300)
@log_task_execution("Temporary Image Cleanup")
def cleanup_temporary_images_task(self):
    """
    Daily task to delete temporary uploads, failed uploads, orphan images, and unused thumbnails.
    """
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
    
    deleted_files = 0
    if os.path.exists(temp_dir):
        # We'll consider files older than 24 hours as orphaned/temp
        now = time.time()
        for filename in os.listdir(temp_dir):
            filepath = os.path.join(temp_dir, filename)
            if os.path.isfile(filepath):
                # Check modification time
                if os.stat(filepath).st_mtime < now - 86400: # 24 hours
                    try:
                        os.remove(filepath)
                        deleted_files += 1
                    except Exception as e:
                        logger.error(f"Failed to delete temp image {filepath}: {e}")
                        
    logger.info(f"Cleaned up {deleted_files} temporary images.")
    return {"status": "success", "deleted_files": deleted_files}
