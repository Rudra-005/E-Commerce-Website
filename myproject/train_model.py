import os
os.environ['TF_USE_LEGACY_KERAS'] = '1'

import numpy as np
import pandas as pd
import tensorflow as tf
import tensorflow_recommenders as tfrs

def train():
    print("Loading data...")
    ml_data_dir = os.path.join(os.path.dirname(__file__), 'ml_data')
    interactions_path = os.path.join(ml_data_dir, 'notebooks', 'processed_interactions.csv')
    products_path = os.path.join(ml_data_dir, 'notebooks', 'processed_products.csv')
    
    interactions_df = pd.read_csv(interactions_path)
    interactions_df['user_id'] = interactions_df['user_id'].astype(str)
    interactions_df['product_id'] = interactions_df['product_id'].astype(str)
    
    products_df = pd.read_csv(products_path)
    products_df['id'] = products_df['id'].astype(str)
    
    unique_user_ids = np.unique(interactions_df['user_id'].values)
    unique_product_ids = np.unique(products_df['id'].values)
    
    print(f"Unique Users: {len(unique_user_ids)}")
    print(f"Unique Products: {len(unique_product_ids)}")
    
    interactions_dataset = tf.data.Dataset.from_tensor_slices({
        "user_id": tf.cast(interactions_df['user_id'].values, tf.string),
        "product_id": tf.cast(interactions_df['product_id'].values, tf.string),
    })
    
    products_dataset = tf.data.Dataset.from_tensor_slices({
        "product_id": tf.cast(products_df['id'].values, tf.string),
    })
    
    tf.random.set_seed(42)
    shuffled = interactions_dataset.shuffle(len(interactions_df), seed=42, reshuffle_each_iteration=False)
    
    train_size = int(0.8 * len(interactions_df))
    train_ds = shuffled.take(train_size).batch(8192).cache()
    test_ds = shuffled.skip(train_size).batch(8192).cache()
    
    embedding_dimension = 64

    class UserModel(tf.keras.Model):
        def __init__(self, unique_user_ids):
            super().__init__()
            self.user_embedding = tf.keras.Sequential([
                tf.keras.layers.StringLookup(vocabulary=unique_user_ids, mask_token=None),
                tf.keras.layers.Embedding(len(unique_user_ids) + 1, embedding_dimension)
            ])
        def call(self, inputs):
            return self.user_embedding(inputs)

    class AdvancedProductModel(tf.keras.Model):
        def __init__(self, unique_product_ids):
            super().__init__()
            self.product_id_embedding = tf.keras.Sequential([
                tf.keras.layers.StringLookup(vocabulary=unique_product_ids, mask_token=None),
                tf.keras.layers.Embedding(len(unique_product_ids) + 1, embedding_dimension)
            ])
        def call(self, inputs):
            return self.product_id_embedding(inputs)

    class TwoTowerECommerceModel(tfrs.Model):
        def __init__(self, user_model, product_model, task):
            super().__init__()
            self.user_model = user_model
            self.product_model = product_model
            self.task = task
            
        def call(self, features):
            return (self.user_model(features['user_id']), 
                    self.product_model(features['product_id']))
            
        def compute_loss(self, features, training=False):
            user_embeddings = self.user_model(features["user_id"])
            product_embeddings = self.product_model(features["product_id"])
            return self.task(user_embeddings, product_embeddings)

    user_model = UserModel(unique_user_ids)
    product_model = AdvancedProductModel(unique_product_ids)
    
    metrics = tfrs.metrics.FactorizedTopK(
        candidates=products_dataset.batch(128).map(lambda x: product_model(x["product_id"]))
    )
    task = tfrs.tasks.Retrieval(metrics=metrics)
    
    model = TwoTowerECommerceModel(user_model, product_model, task)
    model.compile(optimizer=tf.keras.optimizers.Adagrad(learning_rate=0.1))
    
    print("Training model...")
    model.fit(train_ds, validation_data=test_ds, epochs=5)
    
    print("Saving weights...")
    weights_path = os.path.join(ml_data_dir, 'model_weights', 'two_tower.weights.h5')
    os.makedirs(os.path.dirname(weights_path), exist_ok=True)
    model.save_weights(weights_path)
    print(f"Model weights saved to {weights_path}")

if __name__ == '__main__':
    train()
