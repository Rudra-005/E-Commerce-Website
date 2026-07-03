from django.apps import AppConfig


class ShopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shop'

    def ready(self):
        import os
        # Prevent scheduler from running twice in development with auto-reloader
        if os.environ.get('RUN_MAIN', None) == 'true' or not os.environ.get('RUN_MAIN'):
            from .idle_timeout_task import start_scheduler
            start_scheduler()
