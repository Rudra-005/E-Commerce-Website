import os
import django
from django.core.management import call_command
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete

def load_data_very_fast():
    os.environ['DATABASE_URL'] = 'postgresql://neondb_owner:npg_8EhYV1sXiJjC@ep-wandering-scene-auktfd5i.c-10.us-east-1.aws.neon.tech/neondb?sslmode=require'
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
    django.setup()
    
    # DANGEROUS BUT FAST: Disconnect ALL signals temporarily
    pre_save.receivers = []
    post_save.receivers = []
    pre_delete.receivers = []
    post_delete.receivers = []
    
    print("Loading data into Neon database (SUPER FAST MODE)...")
    call_command('loaddata', 'datadump_filtered.json')
    print("Loaded successfully.")

if __name__ == "__main__":
    load_data_very_fast()
