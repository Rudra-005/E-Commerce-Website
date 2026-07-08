from django.apps import AppConfig


class ChatbotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chatbot'
    verbose_name = 'AI Shopping Assistant'

    def ready(self):
        import sys
        import os
        import threading
        
        # Check if we should skip loading the ML models (e.g. Flower, Celery Beat, or explicit flag)
        argv_str = ' '.join(sys.argv).lower()
        is_flower = 'flower' in argv_str
        is_beat = 'celery' in argv_str and 'beat' in argv_str
        skip_ml = os.environ.get('SKIP_ML_MODELS') == '1'

        if is_flower or is_beat or skip_ml:
            return

        def load_model_in_background():
            try:
                from .services.embedding_service import get_model
                get_model()
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error loading embedding model in background thread: {e}")

        # Start loading the model in a background thread so imports and setup do not block Django startup
        threading.Thread(target=load_model_in_background, daemon=True).start()


