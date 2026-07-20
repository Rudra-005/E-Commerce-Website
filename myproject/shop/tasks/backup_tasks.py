import logging
import os
import subprocess
from datetime import datetime, timedelta
from celery import shared_task
from django.conf import settings
from shop.utils.task_logger import log_task_execution

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=300, soft_time_limit=1800)
@log_task_execution("Database Backup")
def backup_database_task(self):
    """
    Nightly task to backup PostgreSQL database, compress it, and enforce a 7-day retention policy.
    Requires pg_dump in the environment PATH.
    """
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        
    db_settings = settings.DATABASES['default']
    db_name = db_settings.get('NAME')
    db_user = db_settings.get('USER')
    db_password = db_settings.get('PASSWORD')
    db_host = db_settings.get('HOST', 'localhost')
    db_port = db_settings.get('PORT', '5432')
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{db_name}_{timestamp}.sql.gz"
    backup_filepath = os.path.join(backup_dir, backup_filename)
    
    # 1. Perform Backup and Compress
    try:
        logger.info(f"Starting database backup: {backup_filename}")
        
        # pg_dump -h host -p port -U user dbname | gzip > backup.sql.gz
        env = os.environ.copy()
        if db_password:
            env['PGPASSWORD'] = db_password
            
        pg_dump_cmd = ['pg_dump', '-h', str(db_host), '-p', str(db_port), '-U', db_user, db_name]
        
        with open(backup_filepath, 'wb') as f_out:
            pg_dump_process = subprocess.Popen(pg_dump_cmd, stdout=subprocess.PIPE, env=env)
            gzip_process = subprocess.Popen(['gzip'], stdin=pg_dump_process.stdout, stdout=f_out, env=env)
            pg_dump_process.stdout.close()  # Allow pg_dump_process to receive a SIGPIPE if gzip_process exits
            gzip_process.communicate()
            
        if gzip_process.returncode != 0:
            raise Exception(f"pg_dump or gzip failed with return code {gzip_process.returncode}")
            
        logger.info(f"Backup completed successfully: {backup_filepath}")
        
    except Exception as exc:
        logger.error(f"Backup failed: {exc}")
        if os.path.exists(backup_filepath):
            os.remove(backup_filepath)
        raise self.retry(exc=exc)
        
    # 2. Enforce 7-Day Retention Policy
    try:
        retention_days = 7
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        deleted_count = 0
        
        for filename in os.listdir(backup_dir):
            if filename.startswith('backup_') and filename.endswith('.sql.gz'):
                filepath = os.path.join(backup_dir, filename)
                file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                
                if file_mtime < cutoff_date:
                    os.remove(filepath)
                    deleted_count += 1
                    logger.info(f"Deleted old backup: {filename}")
                    
        logger.info(f"Retention policy applied. Deleted {deleted_count} old backups.")
    except Exception as e:
        logger.error(f"Failed to enforce retention policy: {e}")
        
    return {"status": "success", "file": backup_filename}
