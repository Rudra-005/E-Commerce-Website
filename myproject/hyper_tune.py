import os
os.environ['TF_USE_LEGACY_KERAS'] = '1'
import numpy as np
import pandas as pd
import tensorflow as tf
import tensorflow_recommenders as tfrs

interactions_path = 'c:/Users/rudra/Downloads/E-Commerce-Website/myproject/ml_data/notebooks/processed_interactions.csv'
products_path = 'c:/Users/rudra/Downloads/E-Commerce-Website/myproject/ml_data/notebooks/processed_products.csv'

train_interactions_df = pd.read_csv(interactions_path)
products_df = pd.read_csv(products_path)

train_interactions_df['user_id'] = train_interactions_df['user_id'].astype(str)
train_interactions_df['product_id'] = train_interactions_df['product_id'].astype(str)
products_df['id'] = products_df['id'].astype(str)

interactions_dataset = tf.data.Dataset.from_tensor_slices({
    "user_id": tf.cast(train_interactions_df['user_id'].values, tf.string),
    "product_id": tf.cast(train_interactions_df['product_id'].values, tf.string),
})

products_dataset = tf.data.Dataset.from_tensor_slices({
    "product_id": tf.cast(products_df['id'].values, tf.string)
})

unique_user_ids = np.unique(train_interactions_df['user_id'].values)
unique_product_ids = np.unique(products_df['id'].values)

tf.random.set_seed(42)
shuffled = interactions_dataset.shuffle(len(train_interactions_df), seed=42, reshuffle_each_iteration=False)

train_size = int(0.8 * len(train_interactions_df))
test_size = len(train_interactions_df) - train_size

train = shuffled.take(train_size)
test = shuffled.skip(train_size).take(test_size)

def build_and_train(emb_dim, batch_size, lr, epochs):
    class UserModel(tf.keras.Model):
        def __init__(self, unique_user_ids):
            super().__init__()
            self.user_embedding = tf.keras.Sequential([
                tf.keras.layers.StringLookup(vocabulary=unique_user_ids, mask_token=None),
                tf.keras.layers.Embedding(len(unique_user_ids) + 1, emb_dim)
            ])
        def call(self, inputs):
            return self.user_embedding(inputs)

    class ProductModel(tf.keras.Model):
        def __init__(self, unique_product_ids):
            super().__init__()
            self.product_id_embedding = tf.keras.Sequential([
                tf.keras.layers.StringLookup(vocabulary=unique_product_ids, mask_token=None),
                tf.keras.layers.Embedding(len(unique_product_ids) + 1, emb_dim)
            ])
        def call(self, inputs):
            return self.product_id_embedding(inputs)

    class TwoTowerECommerceModel(tfrs.Model):
        def __init__(self, user_model, product_model, task):
            super().__init__()
            self.user_model = user_model
            self.product_model = product_model
            self.task = task
            
        def compute_loss(self, features, training=False):
            user_embeddings = self.user_model(features["user_id"])
            product_embeddings = self.product_model(features["product_id"])
            return self.task(user_embeddings, product_embeddings)

    user_model = UserModel(unique_user_ids)
    product_model = ProductModel(unique_product_ids)

    candidates = products_dataset.batch(128).map(lambda x: product_model(x["product_id"]))

    metrics = tfrs.metrics.FactorizedTopK(
        candidates=candidates,
        ks=(10,)
    )

    task = tfrs.tasks.Retrieval(metrics=metrics)
    model = TwoTowerECommerceModel(user_model, product_model, task)
    model.compile(optimizer=tf.keras.optimizers.Adagrad(learning_rate=lr))

    cached_train = train.batch(batch_size).cache()
    cached_test = test.batch(batch_size).cache()

    early_stopping = tf.keras.callbacks.EarlyStopping(
        monitor="val_factorized_top_k/top_10_categorical_accuracy",
        mode="max",
        patience=5,
        restore_best_weights=True
    )

    history = model.fit(
        cached_train,
        validation_data=cached_test,
        validation_freq=1,
        epochs=epochs,
        callbacks=[early_stopping],
        verbose=0
    )

    eval_res = model.evaluate(cached_test, return_dict=True, verbose=0)
    train_res = model.evaluate(cached_train, return_dict=True, verbose=0)
    
    val_recall_10 = eval_res['factorized_top_k/top_10_categorical_accuracy']
    train_recall_10 = train_res['factorized_top_k/top_10_categorical_accuracy']
    
    print(f"Emb={emb_dim}, Batch={batch_size}, LR={lr} -> Train Recall@10: {train_recall_10:.4f}, Val Recall@10: {val_recall_10:.4f}")
    return val_recall_10, train_recall_10

# Grid Search
configs = [
    (32, 1024, 0.1, 30),
    (64, 1024, 0.1, 30),
    (32, 512, 0.05, 30),
    (64, 512, 0.05, 30),
    (64, 8192, 0.5, 50),
    (32, 2048, 0.1, 50)
]

for emb_dim, bs, lr, eps in configs:
    build_and_train(emb_dim, bs, lr, eps)
