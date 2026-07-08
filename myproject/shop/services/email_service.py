import logging
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def send_welcome_email(user_id):
        """
        Renders and sends a personalized welcome email to a new user.
        Catches exceptions gracefully and logs the outcome.
        """
        try:
            user = User.objects.get(id=user_id)
            if not user.email:
                logger.warning(f"Cannot send welcome email. User {user_id} has no email address configured.")
                return False

            # Compile context variables
            user_name = user.first_name if user.first_name else user.username
            app_name = getattr(settings, "SITE_NAME", "Velora")
            dashboard_url = getattr(settings, "SITE_URL", "http://localhost:8000")
            support_email = getattr(settings, "SUPPORT_EMAIL", settings.EMAIL_HOST_USER)
            current_year = timezone.now().year

            context = {
                "user_name": user_name,
                "username": user.username,
                "app_name": app_name,
                "dashboard_url": dashboard_url,
                "support_email": support_email,
                "current_year": current_year,
            }

            # Render HTML and Text versions
            html_content = render_to_string("emails/welcome_email.html", context)
            text_content = render_to_string("emails/welcome_email.txt", context)

            subject = f"Welcome to {app_name}! 🎉"
            from_email = settings.DEFAULT_FROM_EMAIL

            # Build and send email
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[user.email]
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=False)

            logger.info(f"Successfully sent welcome email to user {user_id} ({user.email})")
            return True

        except User.DoesNotExist:
            logger.error(f"Failed to send welcome email. User with ID {user_id} does not exist.")
            return False
        except Exception as e:
            logger.error(f"Failed to send welcome email to user {user_id}: {e}", exc_info=True)
            return False
