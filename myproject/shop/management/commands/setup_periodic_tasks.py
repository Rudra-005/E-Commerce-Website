"""
Management command to set up Celery Beat periodic tasks.
Run: python manage.py setup_periodic_tasks
"""
import json
import sys
import io
from django.core.management.base import BaseCommand
from django_celery_beat.models import (
    PeriodicTask,
    IntervalSchedule,
    CrontabSchedule,
)


class Command(BaseCommand):
    help = 'Setup all periodic (cron) tasks for the E-Commerce platform'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Force UTF-8 output on Windows
        if sys.platform == 'win32':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing periodic tasks before creating new ones',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all registered periodic tasks',
        )
        parser.add_argument(
            '--disable-all',
            action='store_true',
            help='Disable all periodic tasks',
        )
        parser.add_argument(
            '--enable-all',
            action='store_true',
            help='Enable all periodic tasks',
        )

    def _write(self, msg, style=None):
        """Write with UTF-8 encoding support for Windows"""
        try:
            if style:
                msg = style(msg)
            self.stdout.write(msg)
        except UnicodeEncodeError:
            # Fallback: strip non-ASCII characters
            clean = msg.encode('ascii', 'replace').decode('ascii')
            self.stdout.write(clean)

    def handle(self, *args, **options):
        if options['list']:
            self._list_tasks()
            return

        if options['disable_all']:
            count = PeriodicTask.objects.exclude(
                name__startswith='celery.'
            ).update(enabled=False)
            self._write(f'[PAUSED] Disabled {count} tasks', self.style.WARNING)
            return

        if options['enable_all']:
            count = PeriodicTask.objects.exclude(
                name__startswith='celery.'
            ).update(enabled=True)
            self._write(f'[PLAY] Enabled {count} tasks', self.style.SUCCESS)
            return

        if options['clear']:
            deleted, _ = PeriodicTask.objects.exclude(
                name__startswith='celery.'
            ).delete()
            self._write(f'[CLEAR] Deleted {deleted} existing tasks', self.style.WARNING)

        self._create_schedules()
        self._create_tasks()
        self._list_tasks()

    def _create_schedules(self):
        """Create all the interval and crontab schedules"""
        self._write('\n[SCHEDULES] Creating schedules...', self.style.HTTP_INFO)

        # -- Interval Schedules --
        self.every_30_sec, _ = IntervalSchedule.objects.get_or_create(
            every=30, period=IntervalSchedule.SECONDS
        )
        self.every_1_min, _ = IntervalSchedule.objects.get_or_create(
            every=1, period=IntervalSchedule.MINUTES
        )
        self.every_5_min, _ = IntervalSchedule.objects.get_or_create(
            every=5, period=IntervalSchedule.MINUTES
        )
        self.every_15_min, _ = IntervalSchedule.objects.get_or_create(
            every=15, period=IntervalSchedule.MINUTES
        )
        self.every_1_hour, _ = IntervalSchedule.objects.get_or_create(
            every=1, period=IntervalSchedule.HOURS
        )

        # -- Crontab Schedules --
        # Every day at midnight IST (18:30 UTC previous day)
        self.daily_midnight, _ = CrontabSchedule.objects.get_or_create(
            minute='30', hour='18', day_of_week='*',
            day_of_month='*', month_of_year='*',
        )
        # Every day at 6 AM IST (00:30 UTC)
        self.daily_6am, _ = CrontabSchedule.objects.get_or_create(
            minute='30', hour='0', day_of_week='*',
            day_of_month='*', month_of_year='*',
        )
        # Every Sunday at 2 AM IST (Saturday 20:30 UTC)
        self.weekly_sunday, _ = CrontabSchedule.objects.get_or_create(
            minute='30', hour='20', day_of_week='6',
            day_of_month='*', month_of_year='*',
        )

        self._write('  [OK] Schedules created', self.style.SUCCESS)

    def _create_tasks(self):
        """Create all periodic tasks"""
        self._write('\n[TASKS] Creating periodic tasks...\n', self.style.HTTP_INFO)

        tasks = [
            # -- ANALYTICS TASKS --
            {
                'name': 'Generate Business Insights (Every 1 Hour)',
                'task': 'shop.tasks.generate_business_insights_task',
                'interval': self.every_1_hour,
                'queue': 'analytics',
                'description': 'Generates business analytics, revenue reports, trending products',
            },

            # -- INVENTORY TASKS --
            {
                'name': 'Sync Inventory (Every 15 Minutes)',
                'task': 'shop.tasks.sync_inventory_task',
                'interval': self.every_15_min,
                'queue': 'default',
                'description': 'Syncs product inventory levels, updates stock status',
            },

            # -- FLASH SALE TASKS --
            {
                'name': 'Expire Flash Sales (Every 5 Minutes)',
                'task': 'shop.tasks.expire_flash_sales_task',
                'interval': self.every_5_min,
                'queue': 'default',
                'description': 'Checks and expires flash sales that have ended',
            },

            # -- RECOMMENDATION TASKS --
            {
                'name': 'Rebuild Recommendation Cache (Daily 6 AM)',
                'task': 'shop.tasks.update_recommendation_cache_task',
                'crontab': self.daily_6am,
                'queue': 'recommendation',
                'description': 'Rebuilds FAISS indexes for product recommendations',
                'kwargs': json.dumps({'product_id': None}),
            },

            # -- DEBUG / HEALTH CHECK --
            {
                'name': 'Health Check Ping (Every 1 Minute)',
                'task': 'myproject.celery.debug_task',
                'interval': self.every_1_min,
                'queue': 'default',
                'description': 'Simple heartbeat to verify Celery workers are alive',
            },

            # -- AI EMAIL CAMPAIGN TASKS --
            {
                'name': 'Send AI Email Campaign (Every 1 Minute)',
                'task': 'shop.tasks.send_ai_email_campaign_task',
                'interval': self.every_1_min,
                'queue': 'email',
                'description': 'Automatically generates and sends AI email campaigns in rotating languages',
            },
        ]

        for task_config in tasks:
            name = task_config['name']
            defaults = {
                'task': task_config['task'],
                'enabled': True,
                'queue': task_config.get('queue', 'default'),
                'description': task_config.get('description', ''),
            }

            if 'interval' in task_config:
                defaults['interval'] = task_config['interval']
                defaults['crontab'] = None
            elif 'crontab' in task_config:
                defaults['crontab'] = task_config['crontab']
                defaults['interval'] = None

            if 'kwargs' in task_config:
                defaults['kwargs'] = task_config['kwargs']

            task, created = PeriodicTask.objects.update_or_create(
                name=name,
                defaults=defaults,
            )
            status = '[NEW]' if created else '[UPDATED]'
            self._write(f'  {status}: {name}')
            self._write(f'        Task: {task_config["task"]}')
            self._write(f'        Queue: {task_config.get("queue", "default")}')
            self._write('')

    def _list_tasks(self):
        """List all registered periodic tasks"""
        tasks = PeriodicTask.objects.exclude(name__startswith='celery.').order_by('name')

        if not tasks.exists():
            self._write('\n[WARNING] No periodic tasks found! Run without --list to create them.', self.style.WARNING)
            return

        self._write(f'\n[LIST] Registered Periodic Tasks ({tasks.count()}):', self.style.HTTP_INFO)
        self._write('-' * 80)

        for task in tasks:
            status = '[ENABLED]' if task.enabled else '[DISABLED]'
            schedule = task.interval or task.crontab or 'No schedule'
            last_run = task.last_run_at.strftime('%Y-%m-%d %H:%M:%S') if task.last_run_at else 'Never'

            self._write(f'\n  {task.name}')
            self._write(f'    Status:     {status}')
            self._write(f'    Task:       {task.task}')
            self._write(f'    Schedule:   {schedule}')
            self._write(f'    Queue:      {task.queue or "default"}')
            self._write(f'    Last Run:   {last_run}')
            self._write(f'    Total Runs: {task.total_run_count}')

        self._write('\n' + '-' * 80)
        self._write(f'Total: {tasks.count()} tasks', self.style.SUCCESS)
