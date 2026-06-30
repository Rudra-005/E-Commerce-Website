import os
os.environ['TF_USE_LEGACY_KERAS'] = '1'

import numpy as np
import pandas as pd
import tensorflow as tf
import tensorflow_recommenders as tfrs

def export_product_embeddings():
    print("Loading data to build vocabularies...")
    ml_data_dir = os.path.join(os.path.dirname(__file__), 'ml_data')
    interactions_path = os.path.join(ml_data_dir, 'notebooks', 'processed_interactions.csv')
    products_path = os.path.join(ml_data_dir, 'notebooks', 'processed_products.csv')
    weights_path = os.path.join(ml_data_dir, 'model_weights', 'two_tower.weights.h5')
    export_dir = os.path.join(ml_data_dir, 'embeddings')
    
    train_interactions_df = pd.read_csv(interactions_path)
    train_interactions_df['user_id'] = train_interactions_df['user_id'].astype(str)
    unique_user_ids = np.unique(train_interactions_df['user_id'].values)

    products_df = pd.read_csv(products_path)
    products_df['id'] = products_df['id'].astype(str)
    unique_product_ids = np.unique(products_df['id'].values)
    
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
            pass

    user_model = UserModel(unique_user_ids)
    product_model = AdvancedProductModel(unique_product_ids)
    task = tfrs.tasks.Retrieval()
    model = TwoTowerECommerceModel(user_model, product_model, task)
    
    print("Building model graph...")
    model({"user_id": tf.constant(["dummy"]), "product_id": tf.constant(["dummy"])})
    
    print("Loading weights...")
    model.load_weights(weights_path)
    
    print("Generating product embeddings...")
    product_dataset = tf.data.Dataset.from_tensor_slices(unique_product_ids).batch(128)
    product_embeddings = []
    
    for batch in product_dataset:
        emb = model.product_model(batch)
        product_embeddings.append(emb.numpy())
        
    product_embeddings_np = np.concatenate(product_embeddings, axis=0)
    
    emb_path = os.path.join(export_dir, 'product_embeddings.npy')
    id_path = os.path.join(export_dir, 'product_ids.npy')
    
    os.makedirs(export_dir, exist_ok=True)
    np.save(emb_path, product_embeddings_np)
    np.save(id_path, unique_product_ids)
    
    print(f"Product embeddings shape: {product_embeddings_np.shape}")
    print(f"Saved to {export_dir}")

if __name__ == '__main__':
    export_product_embeddings()
