import os
import django
from django.core.management import call_command

def load_data_fast():
    os.environ['DATABASE_URL'] = 'postgresql://neondb_owner:npg_8EhYV1sXiJjC@ep-wandering-scene-auktfd5i.c-10.us-east-1.aws.neon.tech/neondb?sslmode=require'
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
    
    # Disable Celery by overriding settings
    os.environ['CELERY_TASK_ALWAYS_EAGER'] = 'True'
    os.environ['CELERY_TASK_STORE_EAGER_RESULT'] = 'True'
    
    django.setup()
    
    print("Loading data into Neon database (Fast Mode)...")
    call_command('loaddata', 'datadump.json')
    print("Loaded successfully.")

if __name__ == "__main__":
    load_data_fast()
