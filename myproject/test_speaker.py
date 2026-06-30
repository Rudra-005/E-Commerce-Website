import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from shop.models import Product

try:
    speaker = Product.objects.get(name="Sony Party Speaker Premium")
    print(f"Name: {speaker.name}")
    print(f"Category string: {speaker.category}")
    if speaker.category_fk:
        print(f"Category FK Name: {speaker.category_fk.name}")
    print(f"Description: {speaker.description}")
except Exception as e:
    print(e)
