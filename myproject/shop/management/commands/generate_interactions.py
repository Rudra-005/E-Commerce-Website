import random
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from shop.models import Product, UserInteraction

class Command(BaseCommand):
    help = 'Generates realistic synthetic user interactions (views, wishlists, carts, purchases) using existing data.'

    def handle(self, *args, **kwargs):
        users = list(User.objects.all())
        products = list(Product.objects.select_related('category_fk').all())
        
        if not users or not products:
            self.stdout.write(self.style.ERROR('Not enough users or products in database to generate interactions.'))
            return
            
        target_count = random.randint(20000, 50000)
        
        # 1. Determine preferred categories for users to simulate affinity
        categories = list(set(p.category_fk for p in products if p.category_fk))
        user_preferences = {}
        for user in users:
            if categories:
                num_prefs = min(random.randint(1, 3), len(categories))
                user_preferences[user.id] = random.sample(categories, num_prefs)
            else:
                user_preferences[user.id] = []
                
        # Group products by category
        products_by_category = {}
        for p in products:
            cat = p.category_fk
            if cat not in products_by_category:
                products_by_category[cat] = []
            products_by_category[cat].append(p)
            
        interactions_to_create = []
        now = timezone.now()
        
        self.stdout.write(self.style.SUCCESS(f'Generating approximately {target_count} interactions...'))
        
        # Temporarily disable auto_now_add to allow custom past timestamps in bulk_create
        for field in UserInteraction._meta.local_fields:
            if field.name == "created_at":
                field.auto_now_add = False
        
        while len(interactions_to_create) < target_count:
            user = random.choice(users)
            
            # 80% chance to pick a product from a preferred category, 20% random
            prefs = user_preferences.get(user.id, [])
            if prefs and random.random() < 0.8:
                cat = random.choice(prefs)
                cat_products = products_by_category.get(cat, products)
                product = random.choice(cat_products)
            else:
                product = random.choice(products)
                
            # Random timestamp spread over the last 90 days
            days_ago = random.uniform(0, 90)
            base_time = now - timedelta(days=days_ago)
            
            # Every sequence starts with a View (100% of sequences)
            interactions_to_create.append(UserInteraction(
                user=user,
                product=product,
                interaction_type='view',
                created_at=base_time
            ))
            
            current_time = base_time
            
            # 21.4% of sequences have a Wishlist interaction 
            # (yielding ~15% overall share of interactions)
            if random.random() < 0.214:
                current_time += timedelta(minutes=random.uniform(1, 15))
                interactions_to_create.append(UserInteraction(
                    user=user,
                    product=product,
                    interaction_type='wishlist',
                    created_at=current_time
                ))
                
            # 14.3% of sequences have a Cart interaction
            # (yielding ~10% overall share of interactions)
            if random.random() < 0.143:
                current_time += timedelta(minutes=random.uniform(1, 10))
                interactions_to_create.append(UserInteraction(
                    user=user,
                    product=product,
                    interaction_type='cart',
                    created_at=current_time
                ))
                
                # 50% of Cart interactions lead to Purchase
                # (yielding ~5% overall share of interactions)
                if random.random() < 0.5:
                    current_time += timedelta(minutes=random.uniform(2, 30))
                    interactions_to_create.append(UserInteraction(
                        user=user,
                        product=product,
                        interaction_type='purchase',
                        created_at=current_time
                    ))
                    
        # Bulk create in chunks for memory efficiency
        chunk_size = 5000
        total = len(interactions_to_create)
        for i in range(0, total, chunk_size):
            chunk = interactions_to_create[i:i + chunk_size]
            UserInteraction.objects.bulk_create(chunk)
            self.stdout.write(f'Inserted {min(i + chunk_size, total)} / {total} interactions')
            
        # Re-enable auto_now_add
        for field in UserInteraction._meta.local_fields:
            if field.name == "created_at":
                field.auto_now_add = True
                
        # Calculate resulting distribution to report back
        counts = {'view': 0, 'wishlist': 0, 'cart': 0, 'purchase': 0}
        for item in interactions_to_create:
            counts[item.interaction_type] += 1
            
        self.stdout.write(self.style.SUCCESS('\n--- Final Distribution ---'))
        for k, v in counts.items():
            percentage = (v / total) * 100
            self.stdout.write(f'{k.capitalize()}: {v} ({percentage:.1f}%)')

        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully generated {total} realistic synthetic interactions!'))
