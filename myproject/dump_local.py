import os
import django
from django.core.management import call_command
import sys

def run_migration():
    # 1. Point to local DB
    os.environ['DATABASE_URL'] = 'postgresql://postgres:Rudra@005@localhost:5432/mydb'
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
    django.setup()
    
    print("Dumping data from local database...")
    with open('datadump.json', 'w', encoding='utf-8') as f:
        call_command('dumpdata', exclude=['auth.permission', 'contenttypes', 'admin.logentry', 'sessions'], stdout=f)
    print("Dumped successfully.")

if __name__ == "__main__":
    run_migration()
