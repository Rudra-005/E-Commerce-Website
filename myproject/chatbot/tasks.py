import logging
import time
from functools import wraps
from celery import shared_task
from django.utils import timezone
from shop.models import TaskExecutionLog

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

@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=300)
@log_task_execution("Process Human Handoff")
def process_human_handoff_task(self, session_id):
    try:
        logger.info(f"Processing human handoff for session {session_id}")
        return {"status": "success", "session_id": session_id}
    except Exception as exc:
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=300)
@log_task_execution("Generate Conversation Summary")
def generate_conversation_summary_task(self, session_id):
    try:
        logger.info(f"Generating conversation summary for session {session_id}")
        # Will call LangGraph/Groq service here
        return {"status": "success", "session_id": session_id}
    except Exception as exc:
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=300)
@log_task_execution("Classify Issue")
def classify_issue_task(self, session_id):
    try:
        logger.info(f"Classifying issue for session {session_id}")
        return {"status": "success", "session_id": session_id}
    except Exception as exc:
        raise self.retry(exc=exc)
