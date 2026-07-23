import os
import django
import json
from django.db import transaction

def fast_load():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
    django.setup()
    
    from shop.models import Product, Category, UserProfile, ShippingAddress, Order, OrderItem
    from django.contrib.auth.models import User
    
    print("Reading json...")
    with open('datadump_filtered.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print(f"Total objects to load: {len(data)}")
    
    # 1. Users
    users_data = [item for item in data if item['model'] == 'auth.user']
    with transaction.atomic():
        print("Inserting Users...")
        for u in users_data:
            fields = u['fields']
            fields.pop('groups', None)
            fields.pop('user_permissions', None)
            User.objects.update_or_create(pk=u['pk'], defaults=fields)
            
    # 2. Categories
    cat_data = [item for item in data if item['model'] == 'shop.category']
    with transaction.atomic():
        print("Inserting Categories...")
        for c in cat_data:
            fields = c['fields']
            Category.objects.update_or_create(pk=c['pk'], defaults=fields)
            
    # 3. Products
    prod_data = [item for item in data if item['model'] == 'shop.product']
    with transaction.atomic():
        print("Inserting Products (using bulk_create to bypass signals)...")
        products_to_create = []
        for p in prod_data:
            fields = p['fields']
            cat_id = fields.pop('category')
            fields['category_id'] = cat_id
            fields['id'] = p['pk']
            products_to_create.append(Product(**fields))
            
        Product.objects.all().delete()
        Product.objects.bulk_create(products_to_create)
        
    print("Done bulk loading core models!")

if __name__ == '__main__':
    fast_load()
