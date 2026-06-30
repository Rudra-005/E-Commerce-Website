import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.db.models import Q
from shop.models import Product

all_products = Product.objects.all()

query_str = "s"

# Test 1: iregex with \b
res1 = all_products.filter(
    Q(name__iregex=r'\b' + query_str) | 
    Q(category_fk__name__iregex=r'\b' + query_str)
).distinct()[:10]

print("Test \b 's':")
print([p.name for p in res1])

# Test 2: istartswith
res2 = all_products.filter(
    Q(name__istartswith=query_str) | 
    Q(category_fk__name__istartswith=query_str)
).distinct()[:10]

print("\nTest istartswith 's':")
print([p.name for p in res2])

# Test 3: icontains ordered by istartswith
from django.db.models import Case, When, Value, IntegerField

res3 = all_products.filter(
    Q(name__icontains=query_str) | Q(category_fk__name__icontains=query_str)
).annotate(
    starts=Case(
        When(name__istartswith=query_str, then=Value(1)),
        When(name__iregex=r'\b' + query_str, then=Value(2)),
        default=Value(3),
        output_field=IntegerField()
    )
).order_by('starts', 'name')[:10]

print("\nTest icontains ordered by starts 's':")
print([p.name for p in res3])
