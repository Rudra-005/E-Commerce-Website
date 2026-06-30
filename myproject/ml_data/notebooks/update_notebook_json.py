import json
import os

notebook_path = "c:/Users/rudra/Downloads/E-Commerce-Website/myproject/ml_data/notebooks/02_train_two_tower.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Helper function to replace cell source if it contains a keyword
def replace_source(nb_obj, keyword, new_source_text):
    for cell in nb_obj.get('cells', []):
        if cell.get('cell_type') == 'code':
            source_list = cell.get('source', [])
            source_str = "".join(source_list)
            if keyword in source_str:
                # Replace with new source, splitting by newline to keep array format
                new_source_lines = [line + '\\n' for line in new_source_text.split('\\n')]
                if new_source_lines:
                    new_source_lines[-1] = new_source_lines[-1].rstrip('\\n')
                cell['source'] = new_source_lines
                return True
    return False

# Section 3
s3_text = """# Calculate price buckets
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
replace_source(nb, "# Create tf.data.Dataset from DataFrames", s3_text)

# Section 6
s6_text = """from tensorflow.keras.regularizers import l2

class ProductModel(tf.keras.Model):
    def __init__(self, unique_product_ids, unique_categories, unique_price_buckets):
        super().__init__()
        
        self.product_id_embedding = tf.keras.Sequential([
            tf.keras.layers.StringLookup(vocabulary=unique_product_ids, mask_token=None),
            tf.keras.layers.Embedding(len(unique_product_ids) + 1, 32)
        ])
        
        self.category_embedding = tf.keras.Sequential([
            tf.keras.layers.StringLookup(vocabulary=unique_categories, mask_token=None),
            tf.keras.layers.Embedding(len(unique_categories) + 1, 16)
        ])
        
        self.price_bucket_embedding = tf.keras.Sequential([
            tf.keras.layers.StringLookup(vocabulary=unique_price_buckets, mask_token=None),
            tf.keras.layers.Embedding(len(unique_price_buckets) + 1, 8)
        ])
        
        self.dense_layers = tf.keras.Sequential([
            tf.keras.layers.Dense(128, activation="relu"),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(64, kernel_regularizer=l2(1e-5))
        ])
        
    def call(self, inputs):
        # inputs is a dictionary containing product_id, category, price_bucket
        p_emb = self.product_id_embedding(inputs["product_id"])
        c_emb = self.category_embedding(inputs["category"])
        pb_emb = self.price_bucket_embedding(inputs["price_bucket"])
        
        x = tf.concat([p_emb, c_emb, pb_emb], axis=1)
        return self.dense_layers(x)

print("ProductModel defined.")"""
replace_source(nb, "class ProductModel(tf.keras.Model):", s6_text)

# Section 7
s7_text = """class TwoTowerECommerceModel(tfrs.Model):
    def __init__(self, user_model, product_model, task):
        super().__init__()
        self.user_model = user_model
        self.product_model = product_model
        self.task = task
        
    def compute_loss(self, features, training=False):
        user_embeddings = self.user_model(features["user_id"])
        
        product_features = {
            "product_id": features["product_id"],
            "category": features["category"],
            "price_bucket": features["price_bucket"]
        }
        product_embeddings = self.product_model(product_features)
        
        return self.task(user_embeddings, product_embeddings)

print("TwoTowerECommerceModel assembled.")"""
replace_source(nb, "class TwoTowerECommerceModel(tfrs.Model):", s7_text)

# Section 8
s8_text = """# Initialize the models
user_model = UserModel(unique_user_ids)
product_model = ProductModel(unique_product_ids, unique_categories, unique_price_buckets)

# Map the product_dataset through the product_model to get embeddings
# We pass the dictionary containing product_id, category, price_bucket
candidates = products_dataset.batch(128).map(
    lambda x: product_model({
        "product_id": x["product_id"],
        "category": x["category"],
        "price_bucket": x["price_bucket"]
    })
)

# Define the task
metrics = tfrs.metrics.FactorizedTopK(
    candidates=candidates,
    ks=(10, 20, 50)
)

task = tfrs.tasks.Retrieval(
    metrics=metrics
)

# Instantiate the full model
model = TwoTowerECommerceModel(user_model, product_model, task)

print("Retrieval Metrics and Task configured.")"""
replace_source(nb, "user_model = UserModel(unique_user_ids)", s8_text)

# Section 9
s9_text = """model.compile(
    optimizer=tf.keras.optimizers.Adagrad(learning_rate=0.05)
)
print("Model compiled successfully.")"""
replace_source(nb, "model.compile(", s9_text)

# Section 10
s10_text = """epochs = 30
batch_size = 512

# Cache, batch, and prefetch for performance
cached_train = train.batch(batch_size).cache()
cached_test = test.batch(batch_size).cache()

from tensorflow.keras.callbacks import EarlyStopping

early_stopping = EarlyStopping(
    monitor="val_loss",
    patience=3,
    restore_best_weights=True
)

history = model.fit(
    cached_train,
    validation_data=cached_test,
    validation_freq=1,
    epochs=epochs,
    callbacks=[early_stopping]
)"""
replace_source(nb, "cached_train = train.batch(batch_size).cache()", s10_text)

# Check if section 12 is there, if not append new cells
has_sec_12 = False
for cell in nb.get('cells', []):
    if cell.get('cell_type') == 'markdown':
        if "SECTION 12" in "".join(cell.get('source', [])):
            has_sec_12 = True

if not has_sec_12:
    def new_md(text):
        return {"cell_type": "markdown", "metadata": {}, "source": [text]}
    
    def new_code(text):
        lines = [line + '\\n' for line in text.split('\\n')]
        if lines: lines[-1] = lines[-1].rstrip('\\n')
        return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines}
    
    nb['cells'].extend([
        new_md("# SECTION 12: Visualization\\nPlot the Training and Validation Loss over epochs."),
        new_code("plt.figure(figsize=(10, 6))\\nplt.plot(history.history['loss'], label='Train Loss')\\nplt.plot(history.history['val_loss'], label='Validation Loss')\\nplt.title('Two-Tower Model Loss')\\nplt.ylabel('Loss')\\nplt.xlabel('Epoch')\\nplt.legend()\\nplt.grid(True)\\nplt.show()"),
        new_md("# SECTION 13: Recommendation Examples\\nGenerate sample recommendations for random users."),
        new_code("index = tfrs.layers.factorized_top_k.BruteForce(model.user_model)\\nindex.index_from_dataset(\\n  tf.data.Dataset.zip((products_dataset.batch(100).map(lambda x: x['product_id']), candidates))\\n)\\n\\n# Get recommendations for a sample user\\nuser_id = '2'\\n_, titles = index(tf.constant([user_id]))\\nprint(f'Recommendations for user {user_id}: {titles[0, :5]}')"),
        new_md("# SECTION 14: Save Model\\nSave the weights of the trained model."),
        new_code("import os\\nos.makedirs('../model_weights', exist_ok=True)\\nmodel.save_weights('../model_weights/two_tower.weights.h5')\\nprint('Model weights saved successfully!')"),
        new_md("# SECTION 15: Training Metadata\\nSave evaluation metrics for later comparison."),
        new_code("import json\\nmetrics_dict = {\\n    'Recall@10': float(evaluation.get('factorized_top_k/top_10_categorical_accuracy', 0)),\\n    'Recall@20': float(evaluation.get('factorized_top_k/top_20_categorical_accuracy', 0)),\\n    'Recall@50': float(evaluation.get('factorized_top_k/top_50_categorical_accuracy', 0))\\n}\\nwith open('training_metrics.json', 'w') as f:\\n    json.dump(metrics_dict, f, indent=4)\\nprint('Metrics saved successfully!')")
    ])

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Notebook successfully updated.")
