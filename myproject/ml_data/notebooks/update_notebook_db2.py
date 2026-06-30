import json
import os

notebook_path = "c:/Users/rudra/Downloads/E-Commerce-Website/myproject/ml_data/notebooks/02_train_two_tower.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

def replace_source(nb_obj, keyword, new_source_text):
    for cell in nb_obj.get('cells', []):
        if cell.get('cell_type') == 'code':
            source_list = cell.get('source', [])
            source_str = "".join(source_list)
            if keyword in source_str:
                new_source_lines = [line + '\\n' for line in new_source_text.split('\\n')]
                if new_source_lines:
                    new_source_lines[-1] = new_source_lines[-1].rstrip('\\n')
                cell['source'] = new_source_lines
                return True
    return False

# Section 3
s3_text = """# Fetch missing price and category metadata using Django ORM
import os
import sys
import django
import pandas as pd
import numpy as np
import tensorflow as tf

# Setup Django environment
sys.path.append(os.path.abspath('../../'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from shop.models import Product

# Fetch products from DB
products_qs = Product.objects.all().values('id', 'price', 'category_fk__name')
db_products = pd.DataFrame(products_qs)
db_products.rename(columns={'category_fk__name': 'category'}, inplace=True)
db_products['id'] = db_products['id'].astype(str)

# Merge the database metadata into the existing products_df
products_df = products_df.merge(db_products, on='id', how='left')

# Calculate price buckets
def get_price_bucket(price):
    if price < 5000:
        return "Budget"
    elif price < 20000:
        return "Mid Range"
    else:
        return "Premium"

products_df['price'] = pd.to_numeric(products_df['price'], errors='coerce').fillna(0)
products_df['price_bucket'] = products_df['price'].apply(get_price_bucket)
products_df['category'] = products_df['category'].fillna("Unknown").astype(str)

# Merge metadata into interactions
train_interactions_df = train_interactions_df.merge(
    products_df[['id', 'category', 'price_bucket']], 
    left_on='product_id', 
    right_on='id', 
    how='left'
)
train_interactions_df['category'] = train_interactions_df['category'].fillna("Unknown").astype(str)
train_interactions_df['price_bucket'] = train_interactions_df['price_bucket'].fillna("Budget").astype(str)

# Create tf.data.Dataset from DataFrames
interactions_dataset = tf.data.Dataset.from_tensor_slices({
    "user_id": tf.cast(train_interactions_df['user_id'].values, tf.string),
    "product_id": tf.cast(train_interactions_df['product_id'].values, tf.string),
    "category": tf.cast(train_interactions_df['category'].values, tf.string),
    "price_bucket": tf.cast(train_interactions_df['price_bucket'].values, tf.string)
})

products_dataset = tf.data.Dataset.from_tensor_slices({
    "product_id": tf.cast(products_df['id'].values, tf.string),
    "category": tf.cast(products_df['category'].values, tf.string),
    "price_bucket": tf.cast(products_df['price_bucket'].values, tf.string)
})

# Unique vocabularies
unique_user_ids = np.unique(train_interactions_df['user_id'].values)
unique_product_ids = np.unique(products_df['id'].values)
unique_categories = np.unique(products_df['category'].values)
unique_price_buckets = np.unique(products_df['price_bucket'].values)

print(f"Vocabularies built: {len(unique_user_ids)} users, {len(unique_product_ids)} products, {len(unique_categories)} categories, {len(unique_price_buckets)} price buckets.")"""

replace_source(nb, "import tensorflow as tf", s3_text)

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Notebook successfully updated.")
