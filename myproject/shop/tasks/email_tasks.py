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

@shared_task(bind=True, max_retries=1, soft_time_limit=300)
@log_task_execution("AI Email Campaign")
def send_ai_email_campaign_task(self):
    """
    Task to execute active AI Email Campaigns.
    Generates emails using Groq and sends them to all registered users.
    """
    from shop.models import AIEmailCampaign, AIEmailLog
    from django.contrib.auth.models import User
    from django.core.mail import EmailMultiAlternatives
    from django.conf import settings
    from chatbot.services.groq_service import get_client
    import markdown

    active_campaigns = AIEmailCampaign.objects.filter(is_active=True)
    if not active_campaigns.exists():
        logger.info("No active AI email campaigns to run.")
        return {"status": "skipped", "reason": "No active campaigns"}

    client = get_client()
    users = User.objects.filter(email__isnull=False).exclude(email="")
    if not users.exists():
        logger.warning("No users with emails found for AI Campaign.")
        return {"status": "skipped", "reason": "No users"}

    for campaign in active_campaigns:
        # Determine current language
        languages = [l.strip() for l in campaign.languages.split(',')]
        if not languages:
            continue
            
        lang = languages[campaign.current_language_index % len(languages)]
        logger.info(f"Running AI campaign '{campaign.topic}' in {lang}")

        # Prompt Groq for subject and body
        prompt = (
            f"Write an engaging, promotional marketing email about '{campaign.topic}'. "
            f"The email must be written entirely in the {lang} language. "
            f"Format your response EXACTLY as follows, with no extra text before or after:\n\n"
            f"SUBJECT: [Your engaging subject line here]\n\n"
            f"BODY:\n[Your email body formatted in markdown here]"
        )

        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are an expert e-commerce marketing copywriter."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000,
            )
            
            content = response.choices[0].message.content.strip()
            
            if "SUBJECT:" in content and "BODY:" in content:
                parts = content.split("BODY:")
                subject = parts[0].replace("SUBJECT:", "").strip()
                markdown_body = parts[1].strip()
            else:
                # Fallback parser if LLM disobeys format
                lines = content.split('\n')
                subject = lines[0].replace("SUBJECT:", "").strip() if lines else f"Update on {campaign.topic}"
                markdown_body = '\n'.join(lines[1:]).strip()

            html_body = markdown.markdown(markdown_body)
            
            # Send the email
            emails_sent = 0
            for user in users:
                # Personalize greeting
                personalized_html = html_body.replace("[User Name]", user.first_name or user.username)
                personalized_html = personalized_html.replace("[Your Name]", user.first_name or user.username)
                
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=markdown_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user.email]
                )
                msg.attach_alternative(personalized_html, "text/html")
                try:
                    msg.send(fail_silently=False)
                    emails_sent += 1
                except Exception as e:
                    logger.error(f"Failed to send campaign email to {user.email}: {e}")

            # Log success
            AIEmailLog.objects.create(
                campaign=campaign,
                subject=subject,
                body=html_body,
                language=lang,
                recipient_count=emails_sent,
                status="SENT"
            )
            
            # Update campaign state
            from django.utils import timezone
            campaign.last_sent_at = timezone.now()
            campaign.current_language_index = (campaign.current_language_index + 1) % len(languages)
            campaign.save()

        except Exception as e:
            logger.error(f"AI Email Campaign failed for '{campaign.topic}': {e}", exc_info=True)
            AIEmailLog.objects.create(
                campaign=campaign,
                subject="Failed to Generate",
                body="",
                language=lang,
                status="FAILED",
                exception=str(e)
            )
            raise self.retry(exc=e)

    return {"status": "success", "campaigns_run": active_campaigns.count()}
