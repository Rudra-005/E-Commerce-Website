import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from shop.models import Product

prods = Product.objects.filter(name="Noise Gaming Headphones ANC")
print(f"Found {prods.count()} products with this name:")
for p in prods:
    print(f"- ID: {p.id}, Category: {p.category_fk.name if p.category_fk else p.category}")
