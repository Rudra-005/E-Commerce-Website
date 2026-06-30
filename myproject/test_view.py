import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.test import Client

client = Client()
response = client.get('/products/?search=shoes&sort=price_high', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
print("Response JSON:")
print(response.json())
