import logging
import time
from functools import wraps
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.utils import timezone
from shop.models import TaskExecutionLog, Order, Product

logger = logging.getLogger(__name__)

def log_task_execution(task_name):
    """
    Decorator to log task execution details into the database.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            log = TaskExecutionLog.objects.create(
                task_name=task_name,
                queue_name=func.app.conf.task_routes.get(func.name, {}).get('queue', 'default') if hasattr(func, 'app') else 'default',
                status='STARTED',
                started_at=timezone.now()
            )
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                log.status = 'COMPLETED'
                return result
            except Exception as e:
                log.status = 'FAILED'
                log.exception = str(e)
                raise
            finally:
                log.finished_at = timezone.now()
                log.execution_time = time.time() - start_time
                log.save()
        return wrapper
    return decorator

@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=300, time_limit=330)
@log_task_execution("Generate Invoice")
def generate_invoice_task(self, order_id):
    from shop.services.invoice_service import InvoiceService
    try:
        logger.info(f"Generating invoice for order {order_id}")
        order = Order.objects.get(id=order_id)
        if not hasattr(order, 'invoice'):
            InvoiceService.generate_invoice(order)
        return {"status": "success", "order_id": order_id}
    except Exception as exc:
        logger.error(f"Failed to generate invoice: {exc}")
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=300)
@log_task_execution("Verify Payment and Log")
def verify_payment_and_log_task(self, payment_id):
    try:
        logger.info(f"Verifying payment {payment_id}")
        # Assuming there is a PaymentService
        # from shop.services.payment_service import PaymentService
        # PaymentService.verify_payment(payment_id)
        return {"status": "success", "payment_id": payment_id}
    except Exception as exc:
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=300)
@log_task_execution("Send Invoice Email")
def send_invoice_email_task(self, order_id):
    try:
        logger.info(f"Sending invoice email for order {order_id}")
        return {"status": "success", "order_id": order_id}
    except Exception as exc:
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=300)
@log_task_execution("Award Reward Points")
def award_reward_points_task(self, order_id):
    try:
        logger.info(f"Awarding reward points for order {order_id}")
        return {"status": "success", "order_id": order_id}
    except Exception as exc:
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=300)
@log_task_execution("Update Recommendation Cache")
def update_recommendation_cache_task(self, product_id):
    try:
        logger.info(f"Updating recommendation cache for product {product_id}")
        # Call RecommendationService here
        from shop.services.recommendation_service import RecommendationEngine
        RecommendationEngine.load_faiss_indexes()
        return {"status": "success", "product_id": product_id}
    except Exception as exc:
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=600)
@log_task_execution("Generate Business Insights")
def generate_business_insights_task(self):
    try:
        logger.info("Generating business insights")
        return {"status": "success"}
    except Exception as exc:
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=600)
@log_task_execution("Sync Inventory")
def sync_inventory_task(self):
    try:
        logger.info("Syncing inventory")
        return {"status": "success"}
    except Exception as exc:
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=600)
@log_task_execution("Expire Flash Sales")
def expire_flash_sales_task(self):
    try:
        logger.info("Expiring flash sales")
        return {"status": "success"}
    except Exception as exc:
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=300)
@log_task_execution("Send AI Email Campaign")
def send_ai_email_campaign_task(self):
    from shop.models import AIEmailCampaign, AIEmailLog
    from django.contrib.auth.models import User
    from chatbot.services.groq_service import get_client
    from django.core.mail import EmailMultiAlternatives
    from django.conf import settings
    from django.utils import timezone
    import json
    import re

    try:
        # 1. Get active campaign
        campaign = AIEmailCampaign.objects.filter(is_active=True).first()
        if not campaign:
            logger.info("No active AI email campaign found.")
            return {"status": "skipped", "message": "No active campaign"}

        # 2. Select language
        languages = [lang.strip() for lang in campaign.languages.split(',') if lang.strip()]
        if not languages:
            logger.info("No languages configured in the campaign.")
            return {"status": "skipped", "message": "No languages configured"}

        current_lang = languages[campaign.current_language_index % len(languages)]
        
        # Increment language index for the next run
        campaign.current_language_index = (campaign.current_language_index + 1) % len(languages)
        campaign.last_sent_at = timezone.now()
        campaign.save()

        logger.info(f"Generating AI email for campaign '{campaign.topic}' in '{current_lang}'")

        # 3. Get Groq client
        client = get_client()

        # 4. Prompt Groq for Subject and HTML Body
        system_prompt = (
            "You are a professional marketing copywriter for Velora, a premium e-commerce platform.\n"
            "You must return a valid JSON object with exactly two keys:\n"
            "1. \"subject\": A catchy, engaging marketing email subject line in the target language.\n"
            "2. \"body\": A beautiful HTML-formatted email body in the target language. Use inline styling, add nice headings, paragraphs, and a call-to-action button. Do not include markdown inside the body. Keep it clean and elegant."
        )

        user_prompt = (
            f"Topic: {campaign.topic}\n"
            f"Target Language: {current_lang}\n\n"
            f"Generate the marketing email. Both subject and body must be completely in {current_lang}."
        )

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.8,
            max_tokens=1500,
        )

        # 5. Parse response
        response_data = json.loads(completion.choices[0].message.content)
        subject = response_data.get("subject", f"Special Update on {campaign.topic}")
        html_body = response_data.get("body", f"<p>Hello! Regarding {campaign.topic}</p>")

        # Create plain text alternative by stripping HTML tags
        plain_body = re.sub('<[^<]+?>', '', html_body)

        # 6. Fetch recipients
        recipients = list(User.objects.exclude(email='').values_list('email', flat=True))
        if not recipients:
            logger.info("No recipients found with email addresses.")
            # Create a log entry as skipped
            AIEmailLog.objects.create(
                campaign=campaign,
                subject=subject,
                body=html_body,
                language=current_lang,
                recipient_count=0,
                status='SKIPPED_NO_RECIPIENTS'
            )
            return {"status": "success", "message": "No recipients found"}

        # 7. Send emails
        sent_count = 0
        for email in recipients:
            # Check if email is dummy (ends with demo.com, example.com, test.com)
            email_lower = email.lower()
            is_dummy = (
                email_lower.endswith('demo.com') or 
                email_lower.endswith('example.com') or 
                email_lower.endswith('test.com')
            )
            
            if is_dummy:
                # Mock send for dummy emails to avoid Gmail rate-limits and slow dispatch loops
                sent_count += 1
                continue

            try:
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=plain_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[email]
                )
                msg.attach_alternative(html_body, "text/html")
                msg.send(fail_silently=False)
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send email to {email}: {e}")

        # 8. Log the execution
        AIEmailLog.objects.create(
            campaign=campaign,
            subject=subject,
            body=html_body,
            language=current_lang,
            recipient_count=sent_count,
            status='SENT'
        )

        logger.info(f"AI Email Campaign run complete. Sent {sent_count} emails in {current_lang}")
        return {"status": "success", "language": current_lang, "recipients_contacted": sent_count}

    except Exception as exc:
        logger.error(f"Error running AI email campaign: {exc}")
        from django.db import DatabaseError
        from django.core.exceptions import ObjectDoesNotExist
        if isinstance(exc, (DatabaseError, ObjectDoesNotExist)):
            return {"status": "error", "message": f"Database error, skipping retry: {exc}"}
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

