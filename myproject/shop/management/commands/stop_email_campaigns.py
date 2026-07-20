"""
Management command to deactivate all AI email campaigns and remove
any Celery Beat periodic tasks that trigger email-sending.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Deactivates all AI email campaigns and removes related Celery Beat periodic tasks to stop email spam."

    def handle(self, *args, **options):
        # 1. Deactivate all AIEmailCampaign entries
        from shop.models import AIEmailCampaign

        active_campaigns = AIEmailCampaign.objects.filter(is_active=True)
        count = active_campaigns.count()
        active_campaigns.update(is_active=False)
        self.stdout.write(self.style.SUCCESS(f"Deactivated {count} active AI email campaign(s)."))

        # 2. Remove Celery Beat periodic tasks related to email campaigns
        try:
            from django_celery_beat.models import PeriodicTask

            email_tasks = PeriodicTask.objects.filter(
                task__icontains="send_ai_email_campaign"
            )
            email_task_count = email_tasks.count()
            email_tasks.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Deleted {email_task_count} Celery Beat periodic task(s) for email campaigns."
                )
            )

            # Also disable any other email-related periodic tasks
            other_email_tasks = PeriodicTask.objects.filter(
                task__icontains="email"
            )
            other_count = other_email_tasks.count()
            if other_count > 0:
                other_email_tasks.update(enabled=False)
                self.stdout.write(
                    self.style.WARNING(
                        f"Disabled {other_count} other email-related periodic task(s)."
                    )
                )

        except ImportError:
            self.stdout.write(
                self.style.WARNING(
                    "django_celery_beat not installed — skipping periodic task cleanup."
                )
            )

        self.stdout.write(self.style.SUCCESS("\nDone! No more campaign emails will be sent."))
