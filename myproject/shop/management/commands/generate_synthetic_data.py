import random
import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from shop.models import Product, UserInteraction

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generates realistic synthetic data for the recommendation system.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting synthetic data generation...")

        TARGET_USERS = 1000
        INTERACTION_DAYS_RANGE = 180
        BATCH_SIZE = 5000

        with transaction.atomic():
            # 1. GENERATE USERS
            self.stdout.write("\n--- Generating Users ---")
            existing_usernames = set(User.objects.values_list('username', flat=True))
            
            new_users = []
            password_hash = make_password('demo_password_123')
            
            for i in range(1, TARGET_USERS + 1):
                username = f"user_{i}"
                if username not in existing_usernames:
                    new_users.append(
                        User(
                            username=username,
                            email=f"{username}@demo.com",
                            password=password_hash,
                            is_active=True
                        )
                    )
            
            if new_users:
                User.objects.bulk_create(new_users, batch_size=BATCH_SIZE)
                self.stdout.write(f"Successfully created {len(new_users)} new users.")
            else:
                self.stdout.write("Users already exist. Skipping creation.")

            # 2. FETCH REQUIRED DATA
            self.stdout.write("\n--- Fetching Existing Data ---")
            users = list(User.objects.filter(username__startswith='user_'))
            product_ids = list(Product.objects.values_list('id', flat=True))
            
            if not product_ids:
                self.stdout.write(self.style.ERROR("No products found! Please populate products first."))
                return

            self.stdout.write(f"Loaded {len(users)} users and {len(product_ids)} products.")

            # 3. GENERATE INTERACTIONS
            self.stdout.write("\n--- Generating Realistic Interactions ---")
            
            now = timezone.now()
            start_date = now - timedelta(days=INTERACTION_DAYS_RANGE)
            
            new_interactions = []
            
            # Use progress tracking
            total_users = len(users)
            
            # Phase 3A: Guarantee minimum coverage for ALL products
            self.stdout.write("Phase 1/2: Guaranteeing 50+ interactions for every single product (Cold Start Fix)...")
            # We want each product to have at least 50-80 views/interactions
            
            # Shuffle users to distribute evenly
            shuffled_users = list(users)
            
            for product_id in product_ids:
                random.shuffle(shuffled_users)
                guaranteed_users = shuffled_users[:random.randint(50, 100)]
                for user in guaranteed_users:
                    random_seconds = random.randint(0, int((now - start_date).total_seconds()))
                    base_time = start_date + timedelta(seconds=random_seconds)
                    new_interactions.append(
                        UserInteraction(
                            user=user,
                            product_id=product_id,
                            interaction_type='view',
                            created_at=base_time
                        )
                    )
                    
                    rand_flow = random.random()
                    if rand_flow < 0.25:
                        wishlist_time = base_time + timedelta(seconds=random.randint(10, 300))
                        new_interactions.append(UserInteraction(user=user, product_id=product_id, interaction_type='wishlist', created_at=wishlist_time))
                    elif rand_flow < 0.35:
                        cart_time = base_time + timedelta(seconds=random.randint(30, 600))
                        new_interactions.append(UserInteraction(user=user, product_id=product_id, interaction_type='cart', created_at=cart_time))
                    elif rand_flow < 0.45:
                        cart_time = base_time + timedelta(seconds=random.randint(30, 600))
                        purchase_time = cart_time + timedelta(seconds=random.randint(60, 1800))
                        new_interactions.append(UserInteraction(user=user, product_id=product_id, interaction_type='cart', created_at=cart_time))
                        new_interactions.append(UserInteraction(user=user, product_id=product_id, interaction_type='purchase', created_at=purchase_time))

            # Phase 3B: General realistic browsing behavior to bulk up volume
            self.stdout.write("Phase 2/2: Generating organic user browsing behavior...")
            for idx, user in enumerate(users, 1):
                # Pick 50-200 random products for this user
                num_products = random.randint(50, 200)
                selected_product_ids = random.sample(product_ids, min(num_products, len(product_ids)))
                
                for product_id in selected_product_ids:
                    random_seconds = random.randint(0, int((now - start_date).total_seconds()))
                    base_time = start_date + timedelta(seconds=random_seconds)
                    
                    new_interactions.append(UserInteraction(user=user, product_id=product_id, interaction_type='view', created_at=base_time))
                    
                    rand_flow = random.random()
                    if rand_flow < 0.214:
                        wishlist_time = base_time + timedelta(seconds=random.randint(10, 300))
                        new_interactions.append(UserInteraction(user=user, product_id=product_id, interaction_type='wishlist', created_at=wishlist_time))
                    elif rand_flow < 0.285:
                        cart_time = base_time + timedelta(seconds=random.randint(30, 600))
                        new_interactions.append(UserInteraction(user=user, product_id=product_id, interaction_type='cart', created_at=cart_time))
                    elif rand_flow < 0.356:
                        cart_time = base_time + timedelta(seconds=random.randint(30, 600))
                        purchase_time = cart_time + timedelta(seconds=random.randint(60, 1800))
                        new_interactions.append(UserInteraction(user=user, product_id=product_id, interaction_type='cart', created_at=cart_time))
                        new_interactions.append(UserInteraction(user=user, product_id=product_id, interaction_type='purchase', created_at=purchase_time))
                    
                if idx % 500 == 0:
                    self.stdout.write(f"  Processed {idx}/{total_users} users...")

            # 4. BULK INSERT INTERACTIONS
            self.stdout.write(f"\nCreated {len(new_interactions)} new interaction records in memory.")
            self.stdout.write("Bulk inserting into PostgreSQL. This might take a few moments...")
            
            UserInteraction.objects.bulk_create(new_interactions, batch_size=BATCH_SIZE)
            
            self.stdout.write(self.style.SUCCESS("Synthetic data successfully appended!"))

        # 5. VALIDATION SECTION (Outside the atomic transaction block to reflect final committed state)
        self.stdout.write("\n" + "="*40)
        self.stdout.write("      DATABASE VALIDATION REPORT")
        self.stdout.write("="*40)
        
        total_db_users = User.objects.count()
        total_db_products = Product.objects.count()
        total_db_interactions = UserInteraction.objects.count()
        
        # Unique User-Product pairs count
        unique_pairs = UserInteraction.objects.values('user_id', 'product_id').distinct().count()
        
        # Interaction Distribution
        distribution = UserInteraction.objects.values('interaction_type').annotate(count=Count('id')).order_by('-count')

        self.stdout.write(f"\nTotal Users:                 {total_db_users}")
        self.stdout.write(f"Total Products:              {total_db_products}")
        self.stdout.write(f"Total Interactions:          {total_db_interactions}")
        self.stdout.write(f"Unique User-Product Pairs:   {unique_pairs}")
        
        self.stdout.write("\nEvent Type Distribution:")
        for dist in distribution:
            event = dist['interaction_type']
            count = dist['count']
            percentage = (count / total_db_interactions) * 100 if total_db_interactions > 0 else 0
            self.stdout.write(f"  - {event.capitalize():<10} {count:<10} ({percentage:.2f}%)")
        
        self.stdout.write("\n" + "="*40)
