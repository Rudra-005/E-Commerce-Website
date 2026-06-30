import json
import os

cells = []

def add_markdown(text):
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [text]
    })

def add_code(text):
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [text]
    })


# Section 1
add_markdown("# SECTION 1: Environment Verification\\nWe verify Python version, TensorFlow version, TFRS version, GPU, and RAM.")
add_code("""import sys
import psutil
import tensorflow as tf
import tensorflow_recommenders as tfrs

print(f"Python Version: {sys.version}")
print(f"TensorFlow Version: {tf.__version__}")
print(f"TensorFlow Recommenders Version: {tfrs.__version__}")

gpus = tf.config.list_physical_devices('GPU')
if gpus:
    print(f"GPU Detection: {len(gpus)} GPU(s) found.")
    for gpu in gpus:
        print(f"  - {gpu.name}")
else:
    print("GPU Detection: No GPU found, using CPU.")

ram = psutil.virtual_memory()
print(f"System RAM: {ram.total / (1024**3):.2f} GB total, {ram.available / (1024**3):.2f} GB available")""")


# Section 2
add_markdown("# SECTION 2: Load Data\\nLoad the `processed_interactions.csv` and `processed_products.csv` files.")
add_code("""import pandas as pd
import os

interactions_path = 'processed_interactions.csv'
products_path = 'processed_products.csv'

if os.path.exists(interactions_path) and os.path.exists(products_path):
    interactions_df = pd.read_csv(interactions_path)
    products_df = pd.read_csv(products_path)
    print("Data loaded successfully from CSVs!")
else:
    print("Error: CSV files not found. Attempting to fetch directly from PostgreSQL as fallback...")
    import psycopg2
    from dotenv import load_dotenv
    env_path = os.path.abspath(os.path.join(os.getcwd(), '..', '..', '.env'))
    load_dotenv(dotenv_path=env_path)
    
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "mydb"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "Rudra@005")
    )
    
    products_query = "SELECT id, name, category, price, description FROM shop_product;"
    interactions_query = "SELECT user_id, product_id, interaction_type AS event_type, created_at AS timestamp FROM shop_userinteraction;"
    
    products_df = pd.read_sql_query(products_query, conn)
    interactions_df = pd.read_sql_query(interactions_query, conn)
    print("Data loaded successfully from PostgreSQL!")""")

# Section 3
add_markdown("# SECTION 3: Dataset Overview\\nDisplay basic counts for Users, Products, Interactions, and Unique User-Product Pairs.")
add_code("""num_users = interactions_df['user_id'].nunique()
num_products = products_df['id'].nunique()
num_interactions = len(interactions_df)
num_unique_pairs = interactions_df.groupby(['user_id', 'product_id']).ngroups

print("=== DATASET OVERVIEW ===")
print(f"Number of Users: {num_users}")
print(f"Number of Products: {num_products}")
print(f"Number of Interactions: {num_interactions}")
print(f"Number of Unique User-Product Pairs: {num_unique_pairs}")""")

# Section 4
add_markdown("# SECTION 4: Data Quality Checks\\nCheck for missing values, duplicate rows, and invalid IDs.")
add_code("""print("=== DATA QUALITY CHECKS ===")

# Missing Values
print("\\nMissing Values in Interactions:")
print(interactions_df.isnull().sum())
print("\\nMissing Values in Products:")
print(products_df.isnull().sum())

# Duplicates
print(f"\\nDuplicate rows in Interactions: {interactions_df.duplicated().sum()}")
print(f"Duplicate rows in Products: {products_df.duplicated().sum()}")

# Invalid IDs
invalid_product_ids = interactions_df[~interactions_df['product_id'].isin(products_df['id'])]
print(f"\\nInteractions with Invalid Product IDs: {len(invalid_product_ids)}")

if len(invalid_product_ids) == 0:
    print("All interaction product IDs are valid.")""")

# Section 5
add_markdown("# SECTION 5: Interaction Analysis\\nCalculate Average Interactions Per User, Per Product, Most Active Users, and Most Popular Products.")
add_code("""avg_interactions_per_user = num_interactions / num_users if num_users > 0 else 0
avg_interactions_per_product = num_interactions / num_products if num_products > 0 else 0

print("=== INTERACTION ANALYSIS ===")
print(f"Average Interactions Per User: {avg_interactions_per_user:.2f}")
print(f"Average Interactions Per Product: {avg_interactions_per_product:.2f}")

print("\\nTop 5 Most Active Users (by interaction count):")
print(interactions_df['user_id'].value_counts().head(5))

print("\\nTop 5 Most Popular Products (by interaction count):")
top_product_ids = interactions_df['product_id'].value_counts().head(5)
for pid, count in top_product_ids.items():
    p_name = products_df[products_df['id'] == pid]['name'].values[0]
    print(f"Product ID {pid} ({p_name}): {count} interactions")""")

# Section 6
add_markdown("# SECTION 6: Interaction Sparsity\\nCalculate the sparsity of the user-product recommendation matrix.")
add_code("""# Sparsity = 1 - (Unique Interactions / (Total Users * Total Products))
possible_interactions = num_users * num_products
sparsity = 1 - (num_unique_pairs / possible_interactions) if possible_interactions > 0 else 1

print("=== INTERACTION SPARSITY ===")
print(f"Possible User-Product Pairs: {possible_interactions}")
print(f"Actual Unique User-Product Pairs: {num_unique_pairs}")
print(f"Recommendation Matrix Sparsity: {sparsity:.4%} ({(sparsity*100):.4f}%)")""")

# Section 7
add_markdown("# SECTION 7: Event Distribution Analysis\\nVisualize the distribution of event types: view, wishlist, cart, purchase.")
add_code("""import matplotlib.pyplot as plt
import seaborn as sns

plt.figure(figsize=(10, 6))
sns.countplot(data=interactions_df, x='event_type', order=['view', 'wishlist', 'cart', 'purchase'], palette='viridis')
plt.title('Event Type Distribution')
plt.xlabel('Event Type')
plt.ylabel('Count')
plt.show()

print("\\nEvent Counts:")
print(interactions_df['event_type'].value_counts())""")

# Section 8
add_markdown("# SECTION 8: User Activity Analysis\\nGenerate histograms and boxplots for user activity levels.")
add_code("""user_activity = interactions_df.groupby('user_id').size()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

# Histogram
sns.histplot(user_activity, bins=50, ax=ax1, color='skyblue')
ax1.set_title('Distribution of User Activity (Histogram)')
ax1.set_xlabel('Number of Interactions per User')
ax1.set_ylabel('Frequency (Number of Users)')

# Boxplot
sns.boxplot(x=user_activity, ax=ax2, color='lightgreen')
ax2.set_title('User Activity Spread (Boxplot)')
ax2.set_xlabel('Number of Interactions per User')

plt.tight_layout()
plt.show()

print("User Activity Stats:")
print(user_activity.describe())""")

# Section 9
add_markdown("# SECTION 9: Product Popularity Analysis\\nGenerate visualizations for top products and long tail distribution.")
add_code("""product_popularity = interactions_df.groupby('product_id').size().sort_values(ascending=False)

plt.figure(figsize=(12, 6))
plt.plot(range(len(product_popularity)), product_popularity.values, color='coral', linewidth=2)
plt.fill_between(range(len(product_popularity)), product_popularity.values, color='coral', alpha=0.3)
plt.title('Product Popularity Long Tail Distribution')
plt.xlabel('Product Rank (Most Popular -> Least Popular)')
plt.ylabel('Number of Interactions')
plt.grid(True, alpha=0.3)
plt.show()

print("Top 10 Products Summary:")
print(product_popularity.head(10))""")

# Section 10
add_markdown("# SECTION 10: Feature Engineering\\nMap Event Weights and create `weighted_interaction_score`.")
add_code("""event_weights = {
    'view': 1,
    'wishlist': 3,
    'cart': 4,
    'purchase': 5
}

interactions_df['weighted_interaction_score'] = interactions_df['event_type'].map(event_weights)

print("=== FEATURE ENGINEERING ===")
print("Mapped Event Weights:")
print(interactions_df[['event_type', 'weighted_interaction_score']].head(10))

# Aggregate to get a final score per user-product pair (using max score)
user_item_matrix = interactions_df.groupby(['user_id', 'product_id'])['weighted_interaction_score'].max().reset_index()
print(f"\\nAggregated User-Item Matrix shape: {user_item_matrix.shape}")
print(user_item_matrix.head())""")

# Section 11
add_markdown("# SECTION 11: Dataset Export\\nSave processed data for the training pipeline.")
add_code("""interactions_df.to_csv('processed_interactions.csv', index=False)
products_df.to_csv('processed_products.csv', index=False)

print("=== DATASET EXPORT ===")
print("Saved 'processed_interactions.csv'")
print("Saved 'processed_products.csv'")""")

# Section 12
add_markdown("# SECTION 12: Recommendation Readiness Report\\nGenerate summary tables and insights.")
add_code("""import numpy as np

readiness_checks = []
if num_users >= 1000:
    readiness_checks.append("✅ Users count is adequate (>= 1000).")
else:
    readiness_checks.append("⚠️ Users count is low for deep learning (< 1000).")
    
if num_interactions >= 50000:
    readiness_checks.append("✅ Interactions count is adequate (>= 50000).")
else:
    readiness_checks.append("⚠️ Interactions count is low for deep learning (< 50000).")

if sparsity < 0.999:
    readiness_checks.append(f"✅ Sparsity is excellent for DL ({sparsity*100:.2f}%).")
else:
    readiness_checks.append(f"⚠️ Matrix is highly sparse ({sparsity*100:.2f}%).")

print("=========================================")
print("   RECOMMENDATION READINESS REPORT")
print("=========================================")
for check in readiness_checks:
    print(check)

print("\\n--- Dataset Final Summary ---")
summary_df = pd.DataFrame({
    'Metric': ['Total Users', 'Total Products', 'Total Interactions', 'Sparsity', 'Avg Interactions/User'],
    'Value': [num_users, num_products, num_interactions, f"{sparsity*100:.2f}%", f"{avg_interactions_per_user:.2f}"]
})
print(summary_df.to_string(index=False))
print("=========================================")""")

notebook = {
 "cells": cells,
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.10.4"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}

output_path = r"c:\\Users\\rudra\\Downloads\\E-Commerce-Website\\myproject\\ml_data\\notebooks\\01_data_analysis.ipynb"
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=1)

print(f"Notebook created at: {output_path}")
