import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from shop.services.recommendation_service import RecommendationEngine
from shop.models import Product

RecommendationEngine.load_faiss_indexes()

pid = "144"
print(f"Checking product {pid}")
try:
    product = Product.objects.get(id=pid)
    print(f"Product Name: {product.name}")
except:
    print("Product not found in DB!")

if RecommendationEngine._product_ids is not None:
    if pid in RecommendationEngine._product_ids:
        print("Product IS IN FAISS index.")
    else:
        print("Product IS NOT in FAISS index.")
else:
    print("FAISS index not loaded.")

res = RecommendationEngine.get_related_products(pid, 5)
print(f"Recommendations returned for {pid}:")
for p in res:
    print(f"- {p['name']} (ID: {p['id']})")
