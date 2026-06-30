import os
from collections import defaultdict
import tensorflow as tf
from shop.models import UserInteraction, Product

class TFRSDataPipeline:
    """
    Extracts rich multi-feature interaction data from Django ORM and converts it to a
    TensorFlow Recommenders compatible tf.data.Dataset.
    """
    INTERACTION_WEIGHTS = {
        'view': 1.0,
        'review': 2.0,
        'wishlist': 3.0,
        'cart': 4.0,
        'purchase': 5.0,
    }

    def __init__(self):
        pass

    def extract_data(self):
        # 1. Fetch all products to get metadata
        products = Product.objects.select_related('category_fk').all()
        product_dict = {}
        for p in products:
            cat = p.category_fk.name if p.category_fk else p.category
            product_dict[p.id] = {
                "category": str(cat).lower().replace(" ", "_"),
                "price": float(p.price),
                "rating": float(p.average_rating)
            }

        # 2. Fetch all interactions ordered by time
        interactions = UserInteraction.objects.order_by('created_at').values(
            'user_id', 'product_id', 'interaction_type'
        )

        # 3. Aggregate user profiles
        user_history = defaultdict(lambda: {
            "viewed": set(),
            "purchased": set(),
            "wishlist": set()
        })

        for interaction in interactions:
            uid = interaction['user_id']
            pid = interaction['product_id']
            itype = interaction['interaction_type']
            
            p_data = product_dict.get(pid)
            if not p_data:
                continue
                
            cat = p_data["category"]
            
            if itype == 'view':
                user_history[uid]["viewed"].add(cat)
            elif itype == 'purchase':
                user_history[uid]["purchased"].add(cat)
            elif itype == 'wishlist':
                user_history[uid]["wishlist"].add(cat)

        # 4. Build arrays
        data = {
            "user_id": [],
            "viewed_categories": [],
            "purchased_categories": [],
            "wishlist_categories": [],
            "product_id": [],
            "product_category": [],
            "product_price": [],
            "product_rating": [],
            "interaction_weight": []
        }

        for interaction in interactions:
            uid = interaction['user_id']
            pid = interaction['product_id']
            itype = interaction['interaction_type']
            
            p_data = product_dict.get(pid)
            if not p_data:
                continue

            w = self.INTERACTION_WEIGHTS.get(itype, 1.0)
            
            hist = user_history[uid]
            viewed_str = " ".join(list(hist["viewed"])) if hist["viewed"] else "none"
            purchased_str = " ".join(list(hist["purchased"])) if hist["purchased"] else "none"
            wishlist_str = " ".join(list(hist["wishlist"])) if hist["wishlist"] else "none"
            
            data["user_id"].append(str(uid))
            data["viewed_categories"].append(viewed_str)
            data["purchased_categories"].append(purchased_str)
            data["wishlist_categories"].append(wishlist_str)
            
            data["product_id"].append(str(pid))
            data["product_category"].append(p_data["category"])
            data["product_price"].append(p_data["price"])
            data["product_rating"].append(p_data["rating"])
            data["interaction_weight"].append(w)
            
        return data

    def build_dataset(self, data_dict):
        dataset = tf.data.Dataset.from_tensor_slices({
            "user_id": tf.cast(data_dict["user_id"], tf.string),
            "viewed_categories": tf.cast(data_dict["viewed_categories"], tf.string),
            "purchased_categories": tf.cast(data_dict["purchased_categories"], tf.string),
            "wishlist_categories": tf.cast(data_dict["wishlist_categories"], tf.string),
            
            "product_id": tf.cast(data_dict["product_id"], tf.string),
            "product_category": tf.cast(data_dict["product_category"], tf.string),
            "product_price": tf.cast(data_dict["product_price"], tf.float32),
            "product_rating": tf.cast(data_dict["product_rating"], tf.float32),
            
            "interaction_weight": tf.cast(data_dict["interaction_weight"], tf.float32)
        })
        return dataset

    def split_dataset(self, dataset, dataset_size, train_ratio=0.8):
        dataset = dataset.shuffle(dataset_size, seed=42, reshuffle_each_iteration=False)
        train_size = int(dataset_size * train_ratio)
        
        train_ds = dataset.take(train_size)
        test_ds = dataset.skip(train_size)
        
        return train_ds, test_ds

    def process_and_save(self, save_dir="ml_data/datasets"):
        print("Extracting multi-feature data from PostgreSQL...")
        data_dict = self.extract_data()
        
        size = len(data_dict["user_id"])
        print(f"Extracted {size} interactions.")
        
        if size == 0:
            print("No data found! Pipeline aborted.")
            return
            
        print("Building TensorFlow Dataset...")
        dataset = self.build_dataset(data_dict)
        
        print(f"Splitting dataset (80/20)...")
        train_ds, test_ds = self.split_dataset(dataset, size)
        
        os.makedirs(save_dir, exist_ok=True)
        train_path = os.path.join(save_dir, "train")
        test_path = os.path.join(save_dir, "test")
        
        print(f"Saving train dataset to {train_path}...")
        train_ds.save(train_path)
        
        print(f"Saving test dataset to {test_path}...")
        test_ds.save(test_path)
        
        print("Dataset pipeline complete!")
