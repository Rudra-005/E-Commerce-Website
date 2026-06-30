import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from shop.models import Product
from shop.views import get_fuzzy_search_results

all_products = Product.objects.all()

res = get_fuzzy_search_results("shoes", all_products)
print("Shoes search results:")
for i, p in enumerate(res[:5]):
    print(f"{i+1}. {p.name}")

if len(res) == 0:
    print("NO SHOES RETURNED???")
