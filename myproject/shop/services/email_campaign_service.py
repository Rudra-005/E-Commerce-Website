import logging
import markdown
import threading
from django.utils import timezone
from shop.models import AIEmailCampaign, AIEmailLog
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from chatbot.services.groq_service import get_client

logger = logging.getLogger(__name__)

class AIEmailCampaignService:
    @staticmethod
    def run_all_active_campaigns():
        """
        Executes all active AI Email Campaigns.
        Generates emails using Groq and sends them to all registered users.
        """
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
            AIEmailCampaignService._run_single_campaign(campaign, client, users)

        return {"status": "success", "campaigns_run": active_campaigns.count()}

    @staticmethod
    def _run_single_campaign(campaign, client, users):
        """
        Runs a single AI Email Campaign.
        """
        # Determine current language
        languages = [l.strip() for l in campaign.languages.split(',')]
        if not languages:
            return
            
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

    @staticmethod
    def run_all_campaigns_async():
        """
        Runs all active campaigns asynchronously in a separate thread.
        This replaces the `.delay()` from Celery.
        """
        def target():
            try:
                AIEmailCampaignService.run_all_active_campaigns()
            finally:
                from django.db import connection
                connection.close()

        thread = threading.Thread(target=target)
        thread.daemon = False
        thread.start()
