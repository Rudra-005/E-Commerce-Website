from django.apps import AppConfig


class ShopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shop'

    def ready(self):
        import sys
        import os

        # Detect if running as Flower or Celery Beat - skip scheduler in these
        # Flower uses Tornado's event loop and APScheduler blocks it
        argv_str = ' '.join(sys.argv)
        is_flower = 'flower' in argv_str
        is_beat = 'celery' in argv_str and 'beat' in argv_str

        if is_flower or is_beat:
            return

        # Prevent scheduler from running twice in development with auto-reloader
        if os.environ.get('RUN_MAIN', None) == 'true' or not os.environ.get('RUN_MAIN'):
            from .idle_timeout_task import start_scheduler
            start_scheduler()

