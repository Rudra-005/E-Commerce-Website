import os
import django
from django.core.management import call_command
import sys

def load_data():
    # 1. Point to NEON DB
    # Using the Neon DB from the user's .env file
    os.environ['DATABASE_URL'] = 'postgresql://neondb_owner:npg_8EhYV1sXiJjC@ep-wandering-scene-auktfd5i.c-10.us-east-1.aws.neon.tech/neondb?sslmode=require'
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
    django.setup()
    
    print("Loading data into Neon database...")
    call_command('loaddata', 'datadump.json')
    print("Loaded successfully.")

if __name__ == "__main__":
    load_data()
