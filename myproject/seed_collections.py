import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from shop.models import Product, ProductCollection
from django.db.models import Avg

# Clear existing
ProductCollection.objects.all().delete()

# BEST SELLERS: top 15 products with highest average rating (which have at least 1 review)
top_products = Product.objects.annotate(
    avg_rating=Avg('reviews__rating')
).filter(avg_rating__isnull=False).order_by('-avg_rating')[:15]

# Fallback if not enough reviewed products
if len(top_products) < 15:
    extra = Product.objects.all().order_by('?')[:15-len(top_products)]
    top_products = list(top_products) + list(extra)

for p in top_products:
    ProductCollection.objects.create(name='best-sellers', product=p)

# NEW ARRIVALS: top 15 newest (highest ID)
newest = Product.objects.order_by('-id')[:15]
for p in newest:
    ProductCollection.objects.create(name='new-arrivals', product=p)

# COLLECTORS EDITIONS: 15 random products
random_products = Product.objects.order_by('?')[:15]
for p in random_products:
    ProductCollection.objects.create(name='collectors-editions', product=p)

print("Collections seeded successfully!")
