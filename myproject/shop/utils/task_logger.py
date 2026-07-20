import logging
import time
from functools import wraps
from django.utils import timezone
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

def log_task_execution(task_name):
    """
    Decorator to log task execution details into the TaskExecutionLog table.
    Captures START, SUCCESS, FAILURE, and RETRY information.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from shop.models import TaskExecutionLog
            
            # Celery injects 'self' as the first argument when bind=True
            task_instance = args[0] if args else None
            
            queue_name = 'default'
            if task_instance and hasattr(task_instance, 'app'):
                queue_name = getattr(task_instance.app.conf, 'task_routes', {}).get(
                    task_instance.name, {}
                ).get('queue', 'default')

            log = TaskExecutionLog.objects.create(
                task_name=task_name,
                queue_name=queue_name,
                status='STARTED',
                started_at=timezone.now(),
                payload=kwargs
            )
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                log.status = 'COMPLETED'
                return result
            except Exception as e:
                # Check if it's a Celery Retry exception
                from celery.exceptions import Retry
                if isinstance(e, Retry):
                    log.status = 'RETRYING'
                    log.retry_count += 1
                    logger.warning(f"Task {task_name} retrying: {e}")
                else:
                    log.status = 'FAILED'
                    logger.error(f"Task {task_name} failed: {e}", exc_info=True)
                
                log.exception = str(e)
                raise
            finally:
                log.finished_at = timezone.now()
                log.execution_time = time.time() - start_time
                log.save()
        return wrapper
    return decorator
