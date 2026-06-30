import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from shop.models import Product
from shop.views import get_fuzzy_search_results

all_products = Product.objects.all()

print("Testing 'shoes':")
res1 = get_fuzzy_search_results("shoes", all_products)
print([p.name for p in res1])

print("\nTesting 's':")
res2 = get_fuzzy_search_results("s", all_products, limit=10)
print([p.name for p in res2])
