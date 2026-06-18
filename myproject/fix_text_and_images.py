import os
import django
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from shop.models import Product

# 1. Update text in cart.html
with open('myproject/shop/templates/shop/cart.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("TOTAL DAMAGE", "TOTAL AMOUNT")
content = content.replace("YOUR GEAR STASH", "YOUR SHOPPING CART")
content = content.replace("YOUR STASH IS EMPTY!", "YOUR CART IS EMPTY!")

with open('myproject/shop/templates/shop/cart.html', 'w', encoding='utf-8') as f:
    f.write(content)


# 2. Update broken Unsplash URLs
# If Unsplash is blocking, let's use a reliable placeholder service with random seed based on product ID
products = Product.objects.all()
updated_count = 0
for p in products:
    if "unsplash.com" in p.image or "placeholder" in p.image or not p.image:
        # Use placehold.co with a custom text or picsum
        p.image = f"https://picsum.photos/seed/{p.id}/600/600"
        p.save()
        updated_count += 1

print(f"Text updated and {updated_count} product images replaced to fix broken links.")
