import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"

import tensorflow as tf
import tensorflow_recommenders as tfrs

class UserModel(tf.keras.Model):
    def __init__(self, unique_user_ids, unique_categories):
        super().__init__()
        
        self.user_embedding = tf.keras.Sequential([
            tf.keras.layers.StringLookup(vocabulary=unique_user_ids, mask_token=None),
            tf.keras.layers.Embedding(len(unique_user_ids) + 2, 32),
        ])
        
        self.category_vectorization = tf.keras.layers.TextVectorization(
            vocabulary=unique_categories,
            output_mode='int',
            output_sequence_length=10
        )
        self.category_embedding = tf.keras.layers.Embedding(self.category_vectorization.vocabulary_size(), 32)
        
        self.dense_1 = tf.keras.layers.Dense(64, activation='relu')
        self.dense_2 = tf.keras.layers.Dense(32)
        
    def call(self, inputs):
        user_emb = self.user_embedding(inputs["user_id"])
        
        viewed_emb = tf.reduce_mean(self.category_embedding(self.category_vectorization(inputs["viewed_categories"])), axis=1)
        purchased_emb = tf.reduce_mean(self.category_embedding(self.category_vectorization(inputs["purchased_categories"])), axis=1)
        wishlist_emb = tf.reduce_mean(self.category_embedding(self.category_vectorization(inputs["wishlist_categories"])), axis=1)
        
        concat_emb = tf.concat([user_emb, viewed_emb, purchased_emb, wishlist_emb], axis=1)
        
        return self.dense_2(self.dense_1(concat_emb))


class ProductModel(tf.keras.Model):
    def __init__(self, unique_product_ids, unique_categories):
        super().__init__()
        
        self.product_embedding = tf.keras.Sequential([
            tf.keras.layers.StringLookup(vocabulary=unique_product_ids, mask_token=None),
            tf.keras.layers.Embedding(len(unique_product_ids) + 2, 32)
        ])
        
        self.category_embedding = tf.keras.Sequential([
            tf.keras.layers.StringLookup(vocabulary=unique_categories, mask_token=None),
            tf.keras.layers.Embedding(len(unique_categories) + 2, 32)
        ])
        
        self.dense_1 = tf.keras.layers.Dense(64, activation='relu')
        self.dense_2 = tf.keras.layers.Dense(32)
        
    def call(self, inputs):
        prod_emb = self.product_embedding(inputs["product_id"])
        cat_emb = self.category_embedding(inputs["product_category"])
        
        price = tf.expand_dims(inputs["product_price"], axis=-1)
        rating = tf.expand_dims(inputs["product_rating"], axis=-1)
        
        concat_emb = tf.concat([prod_emb, cat_emb, price, rating], axis=1)
        
        return self.dense_2(self.dense_1(concat_emb))


class TwoTowerECommerceModel(tfrs.models.Model):
    def __init__(self, unique_user_ids, unique_product_ids, unique_categories, rating_weight=1.0, retrieval_weight=1.0, products_dataset=None):
        super().__init__()
        
        self.user_model = UserModel(unique_user_ids, unique_categories)
        self.product_model = ProductModel(unique_product_ids, unique_categories)
        
        self.rating_weight = rating_weight
        self.retrieval_weight = retrieval_weight
        
        self.rating_task = tfrs.tasks.Ranking(
            loss=tf.keras.losses.MeanSquaredError(),
            metrics=[tf.keras.metrics.RootMeanSquaredError()]
        )
        
        if products_dataset is not None:
            candidate_embeddings = products_dataset.batch(128).map(self.product_model)
            self.retrieval_task = tfrs.tasks.Retrieval(
                metrics=tfrs.metrics.FactorizedTopK(
                    candidates=candidate_embeddings
                )
            )
        else:
            self.retrieval_task = tfrs.tasks.Retrieval()
            
        self.rating_model = tf.keras.Sequential([
            tf.keras.layers.Dense(32, activation="relu"),
            tf.keras.layers.Dense(16, activation="relu"),
            tf.keras.layers.Dense(1)
        ])
        
    def call(self, features):
        user_embeddings = self.user_model({
            "user_id": features["user_id"],
            "viewed_categories": features["viewed_categories"],
            "purchased_categories": features["purchased_categories"],
            "wishlist_categories": features["wishlist_categories"]
        })
        
        product_embeddings = self.product_model({
            "product_id": features["product_id"],
            "product_category": features["product_category"],
            "product_price": features["product_price"],
            "product_rating": features["product_rating"]
        })
        
        return user_embeddings, product_embeddings
        
    def compute_loss(self, features, training=False):
        user_embeddings, product_embeddings = self(features)
        
        rating_predictions = self.rating_model(tf.concat([user_embeddings, product_embeddings], axis=1))
        
        retrieval_loss = self.retrieval_task(user_embeddings, product_embeddings)
        
        rating_loss = self.rating_task(
            labels=features["interaction_weight"],
            predictions=rating_predictions
        )
        
        return (self.rating_weight * rating_loss) + (self.retrieval_weight * retrieval_loss)
