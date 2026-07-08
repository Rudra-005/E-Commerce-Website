from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

@receiver(pre_save, sender=User)
def check_unique_email(sender, instance, **kwargs):
    if instance.email:
        email = instance.email.lower()
        exists = User.objects.filter(email__iexact=email).exclude(pk=instance.pk).exists()
        if exists:
            raise ValidationError("An account with this email already exists.")

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        from shop.models import UserProfile
        UserProfile.objects.get_or_create(user=instance)


import logging
import threading

logger = logging.getLogger(__name__)

def _send_welcome_email_fallback(user_id):
    """
    Fallback welcome email dispatcher running in a background thread if Celery enqueuing fails.
    """
    try:
        from shop.services.email_service import EmailService
        EmailService.send_welcome_email(user_id)
    except Exception as e:
        logger.error(f"Fallback welcome email thread failed for user {user_id}: {e}", exc_info=True)


@receiver(post_save, sender=User)
def send_welcome_email_on_signup(sender, instance, created, **kwargs):
    """
    Trigger welcome email via Celery task when a user account is successfully created.
    If Celery or Redis is down, fall back to a background thread to prevent blocking registration.
    """
    if created:
        if not instance.email:
            logger.warning(f"User {instance.id} created without email. Welcome email skipped.")
            return

        from shop.tasks import send_welcome_email_task
        try:
            send_welcome_email_task.delay(instance.id)
            logger.info(f"Welcome email task queued in Celery for user {instance.id}")
        except Exception as e:
            logger.warning(f"Failed to queue welcome email task in Celery for user {instance.id}: {e}. Falling back to daemon thread.")
            thread = threading.Thread(target=_send_welcome_email_fallback, args=(instance.id,))
            thread.daemon = True
            thread.start()

