import logging
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
import json

logger = logging.getLogger(__name__)

def setup_periodic_tasks():
    """
    Seed all required Celery Beat schedules into the database.
    This ensures our required background jobs are configured correctly.
    """
    
    # --- Interval Schedules ---
    every_minute, _ = IntervalSchedule.objects.get_or_create(every=1, period=IntervalSchedule.MINUTES)
    every_five_minutes, _ = IntervalSchedule.objects.get_or_create(every=5, period=IntervalSchedule.MINUTES)
    every_thirty_minutes, _ = IntervalSchedule.objects.get_or_create(every=30, period=IntervalSchedule.MINUTES)
    
    # --- Crontab Schedules ---
    hourly, _ = CrontabSchedule.objects.get_or_create(minute='0', hour='*', day_of_week='*', day_of_month='*', month_of_year='*')
    daily_midnight, _ = CrontabSchedule.objects.get_or_create(minute='0', hour='0', day_of_week='*', day_of_month='*', month_of_year='*')
    weekly_sunday, _ = CrontabSchedule.objects.get_or_create(minute='0', hour='0', day_of_week='0', day_of_month='*', month_of_year='*')

    tasks = [
        {
            'name': 'Checkout Expiration (Every 1 min)',
            'task': 'shop.tasks.cart_tasks.expire_checkouts_task',
            'interval': every_minute,
            'crontab': None
        },
        {
            'name': 'Auto Cancel Unpaid COD (Every 30 mins)',
            'task': 'shop.tasks.order_tasks.auto_cancel_unpaid_cod_task',
            'interval': every_thirty_minutes,
            'crontab': None
        },
        {
            'name': 'Failed Email Retry (Every 5 mins)',
            'task': 'shop.tasks.email_tasks.retry_failed_emails_task',
            'interval': every_five_minutes,
            'crontab': None
        },
        {
            'name': 'Expired OTP Cleanup (Hourly)',
            'task': 'shop.tasks.cleanup_tasks.cleanup_expired_otp_task',
            'interval': None,
            'crontab': hourly
        },
        {
            'name': 'Product Popularity Score (Hourly)',
            'task': 'shop.tasks.analytics_tasks.update_product_popularity_score_task',
            'interval': None,
            'crontab': hourly
        },
        {
            'name': 'Delete Guest Carts (Daily)',
            'task': 'shop.tasks.cart_tasks.delete_guest_carts_task',
            'interval': None,
            'crontab': daily_midnight
        },
        {
            'name': 'Session Cleanup (Daily)',
            'task': 'shop.tasks.cleanup_tasks.cleanup_sessions_task',
            'interval': None,
            'crontab': daily_midnight
        },
        {
            'name': 'Temporary Image Cleanup (Daily)',
            'task': 'shop.tasks.cleanup_tasks.cleanup_temporary_images_task',
            'interval': None,
            'crontab': daily_midnight
        },
        {
            'name': 'Expired Coupon Cleanup (Daily)',
            'task': 'shop.tasks.coupon_tasks.disable_expired_coupons_task',
            'interval': None,
            'crontab': daily_midnight
        },
        {
            'name': 'Recommendation Refresh (Nightly)',
            'task': 'shop.tasks.recommendation_tasks.update_recommendation_cache_task',
            'interval': None,
            'crontab': daily_midnight
        },
        {
            'name': 'Analytics Reports (Nightly)',
            'task': 'shop.tasks.analytics_tasks.generate_business_insights_task',
            'interval': None,
            'crontab': daily_midnight
        },
        {
            'name': 'Search Index Rebuild (Nightly)',
            'task': 'shop.tasks.search_tasks.rebuild_search_index_task',
            'interval': None,
            'crontab': daily_midnight
        },
        {
            'name': 'Database Backup (Nightly)',
            'task': 'shop.tasks.backup_tasks.backup_database_task',
            'interval': None,
            'crontab': daily_midnight
        },
        {
            'name': 'Notification Cleanup (Weekly)',
            'task': 'shop.tasks.notification_tasks.archive_old_notifications_task',
            'interval': None,
            'crontab': weekly_sunday
        }
    ]

    for t in tasks:
        PeriodicTask.objects.update_or_create(
            name=t['name'],
            defaults={
                'task': t['task'],
                'interval': t['interval'],
                'crontab': t['crontab'],
                'args': json.dumps([]),
                'kwargs': json.dumps({}),
                'enabled': True
            }
        )
        logger.info(f"Configured periodic task: {t['name']}")
