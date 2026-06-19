from django.apps import AppConfig


class ChatbotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chatbot'
    verbose_name = 'AI Shopping Assistant'

    def ready(self):
        import threading
        
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

