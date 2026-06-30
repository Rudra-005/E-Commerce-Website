import json
import os

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
import json

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
add_markdown("# SECTION 5: Deep User Tower\\nCreate the reusable UserModel class with Embedding and Deep layers.")
add_code("""embedding_dimension = 128

class UserModel(tf.keras.Model):
    def __init__(self, unique_user_ids):
        super().__init__()
        
        self.user_embedding = tf.keras.Sequential([
            tf.keras.layers.StringLookup(
                vocabulary=unique_user_ids, mask_token=None),
            tf.keras.layers.Embedding(len(unique_user_ids) + 1, embedding_dimension),
            tf.keras.layers.Dense(256, activation="relu", kernel_regularizer=tf.keras.regularizers.l2(1e-6)),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(128, kernel_regularizer=tf.keras.regularizers.l2(1e-6))
        ])
        
    def call(self, inputs):
        return self.user_embedding(inputs)

print("Deep UserModel defined.")""")

# SECTION 6
add_markdown("# SECTION 6: Deep Product Tower\\nCreate the reusable ProductModel utilizing product_id with deep layers.")
add_code("""class ProductModel(tf.keras.Model):
    def __init__(self, unique_product_ids):
        super().__init__()
        
        self.product_id_embedding = tf.keras.Sequential([
            tf.keras.layers.StringLookup(
                vocabulary=unique_product_ids, mask_token=None),
            tf.keras.layers.Embedding(len(unique_product_ids) + 1, embedding_dimension),
            tf.keras.layers.Dense(256, activation="relu", kernel_regularizer=tf.keras.regularizers.l2(1e-6)),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(128, kernel_regularizer=tf.keras.regularizers.l2(1e-6))
        ])
        
    def call(self, inputs):
        return self.product_id_embedding(inputs)

print("Deep ProductModel defined.")""")

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
add_markdown("# SECTION 8: Retrieval Metrics & Pipeline Evaluation\\nConfigure FactorizedTopK with optimized pipeline.")
add_code("""# Initialize the models
user_model = UserModel(unique_user_ids)
product_model = ProductModel(unique_product_ids)

# Optimized candidate generation for FactorizedTopK
# We apply .cache() and .prefetch(AUTOTUNE) to dramatically speed up metric calculation during training.
candidates = products_dataset.batch(128).cache().map(
    lambda x: product_model(x["product_id"])
).prefetch(tf.data.AUTOTUNE)

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

print("Retrieval Metrics and Optimized Candidate Pipeline configured.")""")

# SECTION 9
add_markdown("# SECTION 9: Compile Model\\nCompile the model using Adam optimizer.")
add_code("""# You requested to test Adam(0.001) and provide code for Adam(0.0005)

# Example for Adam(0.0005):
# model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.0005))

# Active optimizer:
model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001))
print("Model compiled successfully with Adam optimizer.")""")

# SECTION 10
add_markdown("# SECTION 10: Training & Callbacks\\nTrain the model with Early Stopping and ReduceLROnPlateau.")
add_code("""epochs = 50
batch_size = 1024

# Cache, batch, and prefetch for performance
cached_train = train.batch(batch_size).cache().prefetch(tf.data.AUTOTUNE)
cached_test = test.batch(batch_size).cache().prefetch(tf.data.AUTOTUNE)

# 1. Early Stopping
early_stopping = tf.keras.callbacks.EarlyStopping(
    monitor="val_factorized_top_k/top_50_categorical_accuracy",
    patience=5,
    restore_best_weights=True,
    verbose=1
)

# 2. Learning Rate Scheduler
reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
    monitor="val_loss",
    factor=0.5,
    patience=2,
    verbose=1
)

print("Starting deep model training...")
history = model.fit(
    cached_train,
    validation_data=cached_test,
    validation_freq=1,
    epochs=epochs,
    callbacks=[early_stopping, reduce_lr]
)""")

# SECTION 11
add_markdown("# SECTION 11: Evaluation & Visualization\\nEvaluate the model and visualize performance metrics over epochs.")
add_code("""print("Evaluating model...")
evaluation = model.evaluate(cached_test, return_dict=True)

# Generate plots
fig, axs = plt.subplots(1, 2, figsize=(16, 5))

# Plot 1: Loss
axs[0].plot(history.history['loss'], label='Training Loss')
axs[0].plot(history.history['val_loss'], label='Validation Loss')
axs[0].set_title('Model Loss')
axs[0].set_xlabel('Epoch')
axs[0].set_ylabel('Loss')
axs[0].legend()
axs[0].grid(True)

# Plot 2: Recall Metrics
axs[1].plot(history.history['factorized_top_k/top_10_categorical_accuracy'], label='Train Recall@10', linestyle='--')
axs[1].plot(history.history['val_factorized_top_k/top_10_categorical_accuracy'], label='Val Recall@10', linewidth=2)
axs[1].plot(history.history['val_factorized_top_k/top_20_categorical_accuracy'], label='Val Recall@20', linewidth=2)
axs[1].plot(history.history['val_factorized_top_k/top_50_categorical_accuracy'], label='Val Recall@50', linewidth=2)
axs[1].set_title('Recall Metrics')
axs[1].set_xlabel('Epoch')
axs[1].set_ylabel('Recall')
axs[1].legend()
axs[1].grid(True)

plt.show()

# Print Table
print("\\n" + "="*50)
print(f"{'Metric':<20} | {'Baseline':<10} | {'New Value':<10}")
print("-" * 50)
print(f"{'Recall@10':<20} | {'2.28%':<10} | {evaluation.get('factorized_top_k/top_10_categorical_accuracy', 0)*100:.2f}%")
print(f"{'Recall@20':<20} | {'4.83%':<10} | {evaluation.get('factorized_top_k/top_20_categorical_accuracy', 0)*100:.2f}%")
print(f"{'Recall@50':<20} | {'12.13%':<10} | {evaluation.get('factorized_top_k/top_50_categorical_accuracy', 0)*100:.2f}%")
print("=" * 50)""")

# SECTION 12
add_markdown("# SECTION 12: Save Model & Export Metrics\\nAutomatically save best model and export metrics.")
add_code("""import os
import json

# Save Best Model
os.makedirs('../model_weights', exist_ok=True)
model_path = '../model_weights/best_two_tower.weights.h5'
model.save_weights(model_path)
print(f"Best model weights saved successfully to {model_path}!")

# Export Metrics
metrics_data = {
    "Recall@10": evaluation.get('factorized_top_k/top_10_categorical_accuracy', 0),
    "Recall@20": evaluation.get('factorized_top_k/top_20_categorical_accuracy', 0),
    "Recall@50": evaluation.get('factorized_top_k/top_50_categorical_accuracy', 0),
    "Loss": evaluation.get('loss', 0)
}

with open('training_metrics.json', 'w') as f:
    json.dump(metrics_data, f, indent=4)
print("Training metrics exported to training_metrics.json")""")

# Construct final notebook JSON
notebook_json = {
    "cells": cells,
    "metadata": {},
    "nbformat": 4,
    "nbformat_minor": 4
}

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(notebook_json, f, indent=1)

print("Deep Architecture Notebook generated successfully!")
