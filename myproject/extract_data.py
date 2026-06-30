import os
import django
import pandas as pd

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from shop.models import UserInteraction, Product

def extract_data():
    print("Extracting interactions...")
    interactions = UserInteraction.objects.all().values('user_id', 'product_id', 'interaction_type')
    interactions_df = pd.DataFrame(list(interactions))
    
    print("Extracting products...")
    products = Product.objects.all().values('id', 'name', 'category_fk_id')
    products_df = pd.DataFrame(list(products))
    
    ml_data_dir = os.path.join(os.path.dirname(__file__), 'ml_data', 'notebooks')
    os.makedirs(ml_data_dir, exist_ok=True)
    
    interactions_path = os.path.join(ml_data_dir, 'processed_interactions.csv')
    products_path = os.path.join(ml_data_dir, 'processed_products.csv')
    
    interactions_df.to_csv(interactions_path, index=False)
    products_df.to_csv(products_path, index=False)
    
    print(f"Successfully saved {len(interactions_df)} interactions to {interactions_path}")
    print(f"Successfully saved {len(products_df)} products to {products_path}")

if __name__ == '__main__':
    extract_data()
