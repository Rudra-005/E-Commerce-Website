import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"

import numpy as np
import tensorflow as tf
import tensorflow_recommenders as tfrs
from django.core.management.base import BaseCommand
from django.conf import settings
from shop.ml.model import TwoTowerECommerceModel

class Command(BaseCommand):
    help = 'Train the Two-Tower TFRS Model and export embeddings'

    def handle(self, *args, **kwargs):
        dataset_dir = os.path.join(settings.BASE_DIR, 'ml_data', 'datasets')
        train_path = os.path.join(dataset_dir, 'train')
        test_path = os.path.join(dataset_dir, 'test')
        
        if not os.path.exists(train_path):
            self.stdout.write(self.style.ERROR("Dataset not found. Please run prepare_tfrs_data first."))
            return
            
        self.stdout.write("Loading datasets from disk...")
        train_ds = tf.data.Dataset.load(train_path)
        test_ds = tf.data.Dataset.load(test_path)
        
        self.stdout.write("Building vocabularies...")
        user_ids = train_ds.batch(1000).map(lambda x: x["user_id"])
        unique_user_ids = np.unique(np.concatenate(list(user_ids)))
        
        product_ids = train_ds.batch(1000).map(lambda x: x["product_id"])
        unique_product_ids = np.unique(np.concatenate(list(product_ids)))
        
        categories = train_ds.batch(1000).map(lambda x: x["product_category"])
        unique_categories = np.unique(np.concatenate(list(categories)))
        
        products_dataset = train_ds.map(lambda x: {
            "product_id": x["product_id"],
            "product_category": x["product_category"],
            "product_price": x["product_price"],
            "product_rating": x["product_rating"]
        })
        
        self.stdout.write("Initializing Two-Tower Multi-Task Model...")
        model = TwoTowerECommerceModel(
            unique_user_ids=unique_user_ids,
            unique_product_ids=unique_product_ids,
            unique_categories=unique_categories,
            products_dataset=products_dataset
        )
        
        model.compile(optimizer=tf.keras.optimizers.Adagrad(learning_rate=0.1))
        
        save_dir = os.path.join(settings.BASE_DIR, 'ml_data', 'model_weights')
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, 'twotower')
        
        # 1. RETRAINING SUPPORT
        if os.path.exists(save_path + '.index'):
            self.stdout.write(self.style.SUCCESS(f"Found existing weights at {save_path}. Loading for fine-tuning..."))
            model.load_weights(save_path)
        
        cached_train = train_ds.shuffle(100_000).batch(128).cache()
        cached_test = test_ds.batch(128).cache()
        
        self.stdout.write(self.style.SUCCESS("Starting training for 5 epochs..."))
        model.fit(cached_train, epochs=5)
        
        self.stdout.write("Evaluating model on test set...")
        metrics = model.evaluate(cached_test, return_dict=True)
        
        self.stdout.write(self.style.SUCCESS("\n--- Evaluation Metrics ---"))
        for k, v in metrics.items():
            self.stdout.write(f"{k}: {v:.4f}")
            
        model.save_weights(save_path)
        self.stdout.write(self.style.SUCCESS(f"\nModel trained and weights saved to {save_path}"))
        
        # 2. EXPORT PRODUCT EMBEDDINGS
        self.stdout.write("\nExporting Product Embeddings...")
        all_product_embs = []
        all_product_ids = []
        for batch in products_dataset.batch(128):
            embs = model.product_model(batch)
            all_product_embs.append(embs.numpy())
            all_product_ids.append(batch["product_id"].numpy())
            
        all_product_embs = np.concatenate(all_product_embs, axis=0)
        all_product_ids = np.concatenate(all_product_ids, axis=0)
        np.save(os.path.join(save_dir, 'product_embeddings.npy'), all_product_embs)
        np.save(os.path.join(save_dir, 'product_ids.npy'), all_product_ids)
        
        # 3. EXPORT USER EMBEDDINGS
        self.stdout.write("Exporting User Embeddings...")
        user_ids_seen = set()
        user_features_list = []
        for x in train_ds.as_numpy_iterator():
            uid = x["user_id"]
            if uid not in user_ids_seen:
                user_ids_seen.add(uid)
                user_features_list.append({
                    "user_id": tf.constant([x["user_id"]]),
                    "viewed_categories": tf.constant([x["viewed_categories"]]),
                    "purchased_categories": tf.constant([x["purchased_categories"]]),
                    "wishlist_categories": tf.constant([x["wishlist_categories"]])
                })
        
        all_user_embs = []
        all_user_ids = []
        for x in user_features_list:
            emb = model.user_model(x)
            all_user_embs.append(emb.numpy()[0])
            all_user_ids.append(x["user_id"].numpy()[0])
            
        np.save(os.path.join(save_dir, 'user_embeddings.npy'), np.array(all_user_embs))
        np.save(os.path.join(save_dir, 'user_ids.npy'), np.array(all_user_ids))
        
        # 4. GENERATE RECOMMENDATION EXAMPLES
        self.stdout.write("\nBuilding BruteForce Recommendation Index for examples...")
        index = tfrs.layers.factorized_top_k.BruteForce(model.user_model)
        
        index.index_from_dataset(
            tf.data.Dataset.zip((
                products_dataset.batch(128).map(lambda x: x["product_id"]), 
                products_dataset.batch(128).map(model.product_model)
            ))
        )
        
        self.stdout.write(self.style.SUCCESS("\n--- Example Recommendations ---"))
        for i in range(min(3, len(user_features_list))):
            user_feat = user_features_list[i]
            _, titles = index(user_feat, k=3)
            uid = user_feat["user_id"].numpy()[0].decode('utf-8')
            recs = [t.decode('utf-8') for t in titles[0, :3].numpy()]
            self.stdout.write(f"User {uid} Top 3 Recommendations: {recs}")
