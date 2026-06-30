import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from shop.services.recommendation_service import RecommendationEngine
from shop.models import Product

RecommendationEngine.load_faiss_indexes()
pid = "144"

res = RecommendationEngine.get_related_products(pid, 5)
print(f"Recommendations returned for {pid}:")
for p in res:
    print(f"- {p.name} (ID: {p.id})")
