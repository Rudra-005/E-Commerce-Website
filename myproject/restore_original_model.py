import json

notebook_path = "c:/Users/rudra/Downloads/E-Commerce-Website/myproject/ml_data/notebooks/02_train_two_tower.ipynb"

cells = []

def add_markdown(text):
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + '\\n' for line in text.split('\\n')]
    })
    if cells[-1]["source"]:
        cells[-1]["source"][-1] = cells[-1]["source"][-1].rstrip('\\n')

def add_code(text):
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + '\\n' for line in text.split('\\n')]
    })
    if cells[-1]["source"]:
        cells[-1]["source"][-1] = cells[-1]["source"][-1].rstrip('\\n')

# SECTION 1
add_markdown("# SECTION 1: Environment Setup\\nSet up environment variables for Keras compatibility, and import required libraries.")
add_code("""import os
os.environ['TF_USE_LEGACY_KERAS'] = '1'

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tensorflow as tf
import tensorflow_recommenders as tfrs

print(f"TensorFlow Version: {tf.__version__}")
print(f"TFRS Version: {tfrs.__version__}")""")

# SECTION 2
add_markdown("# SECTION 2: Load Data\\nLoad the processed interactions and products datasets.")
add_code("""interactions_path = 'processed_interactions.csv'
products_path = 'processed_products.csv'

train_interactions_df = pd.read_csv(interactions_path)
products_df = pd.read_csv(products_path)

# Ensure ID columns are treated as strings for embedding lookups
train_interactions_df['user_id'] = train_interactions_df['user_id'].astype(str)
train_interactions_df['product_id'] = train_interactions_df['product_id'].astype(str)
products_df['id'] = products_df['id'].astype(str)

print("Data successfully loaded!")
print(f"Interactions Shape: {train_interactions_df.shape}")
print(f"Products Shape: {products_df.shape}")""")

# SECTION 3
add_markdown("# SECTION 3: Data Preparation\\nConvert Pandas DataFrames into TensorFlow Datasets.")
add_code("""# Create tf.data.Dataset from DataFrames
interactions_dataset = tf.data.Dataset.from_tensor_slices({
    "user_id": tf.cast(train_interactions_df['user_id'].values, tf.string),
    "product_id": tf.cast(train_interactions_df['product_id'].values, tf.string),
})

products_dataset = tf.data.Dataset.from_tensor_slices({
    "product_id": tf.cast(products_df['id'].values, tf.string)
})

# Unique vocabulary for StringLookups
unique_user_ids = np.unique(train_interactions_df['user_id'].values)
unique_product_ids = np.unique(products_df['id'].values)

print(f"Vocabularies built: {len(unique_user_ids)} users, {len(unique_product_ids)} products.")""")

# SECTION 4
add_markdown("# SECTION 4: Train Validation Split\\nSplit interactions into 80% Train and 20% Validation.")
add_code("""tf.random.set_seed(42)

# Shuffle the interactions
shuffled = interactions_dataset.shuffle(len(train_interactions_df), seed=42, reshuffle_each_iteration=False)

train_size = int(0.8 * len(train_interactions_df))
test_size = len(train_interactions_df) - train_size

train = shuffled.take(train_size)
test = shuffled.skip(train_size).take(test_size)

print(f"Training Samples: {train_size}")
print(f"Validation Samples: {test_size}")""")

# SECTION 5
add_markdown("# SECTION 5: User Tower\\nCreate the reusable UserModel class with a StringLookup and Embedding layer.")
add_code("""embedding_dimension = 64

class UserModel(tf.keras.Model):
    def __init__(self, unique_user_ids):
        super().__init__()
        
        self.user_embedding = tf.keras.Sequential([
            tf.keras.layers.StringLookup(
                vocabulary=unique_user_ids, mask_token=None),
            tf.keras.layers.Embedding(len(unique_user_ids) + 1, embedding_dimension)
        ])
        
    def call(self, inputs):
        return self.user_embedding(inputs)

print("UserModel defined.")""")

# SECTION 6
add_markdown("# SECTION 6: Product Tower\\nCreate the reusable ProductModel utilizing only product_id.")
add_code("""class ProductModel(tf.keras.Model):
    def __init__(self, unique_product_ids):
        super().__init__()
        
        self.product_id_embedding = tf.keras.Sequential([
            tf.keras.layers.StringLookup(
                vocabulary=unique_product_ids, mask_token=None),
            tf.keras.layers.Embedding(len(unique_product_ids) + 1, embedding_dimension)
        ])
        
    def call(self, inputs):
        return self.product_id_embedding(inputs)

print("ProductModel defined.")""")

# SECTION 7
add_markdown("# SECTION 7: Two Tower Architecture\\nAssemble the TwoTowerECommerceModel using TFRS.")
add_code("""class TwoTowerECommerceModel(tfrs.Model):
    def __init__(self, user_model, product_model, task):
        super().__init__()
        self.user_model = user_model
        self.product_model = product_model
        self.task = task
        
    def compute_loss(self, features, training=False):
        user_embeddings = self.user_model(features["user_id"])
        product_embeddings = self.product_model(features["product_id"])
        
        return self.task(user_embeddings, product_embeddings)

print("TwoTowerECommerceModel assembled.")""")

# SECTION 8
add_markdown("# SECTION 8: Retrieval Metrics & Pipeline Evaluation\\nConfigure FactorizedTopK with candidate evaluation.")
add_code("""# Initialize the models
user_model = UserModel(unique_user_ids)
product_model = ProductModel(unique_product_ids)

# Generate candidates
candidates = products_dataset.batch(128).map(lambda x: product_model(x["product_id"]))

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

print("Retrieval Metrics and Candidate Pipeline configured.")""")

# SECTION 9
add_markdown("# SECTION 9: Compile Model\\nCompile the model using Adagrad optimizer.")
add_code("""model.compile(optimizer=tf.keras.optimizers.Adagrad(learning_rate=0.1))
print("Model compiled successfully.")""")

# SECTION 10
add_markdown("# SECTION 10: Training\\nTrain the original model architecture.")
add_code("""epochs = 10
batch_size = 8192

# Cache, batch, and prefetch for performance
cached_train = train.batch(batch_size).cache()
cached_test = test.batch(batch_size).cache()

print("Starting model training...")
history = model.fit(
    cached_train,
    validation_data=cached_test,
    validation_freq=1,
    epochs=epochs
)""")

# SECTION 11
add_markdown("# SECTION 11: Evaluation\\nEvaluate the model to achieve original metrics.")
add_code("""print("Evaluating model...")
evaluation = model.evaluate(cached_test, return_dict=True)

print(f"Recall@10: {evaluation.get('factorized_top_k/top_10_categorical_accuracy', 0)*100:.2f}%")
print(f"Recall@20: {evaluation.get('factorized_top_k/top_20_categorical_accuracy', 0)*100:.2f}%")
print(f"Recall@50: {evaluation.get('factorized_top_k/top_50_categorical_accuracy', 0)*100:.2f}%")""")

# Construct final notebook JSON
notebook_json = {
    "cells": cells,
    "metadata": {},
    "nbformat": 4,
    "nbformat_minor": 4
}

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(notebook_json, f, indent=1)

print("Original Two-Tower Notebook Restored successfully!")
