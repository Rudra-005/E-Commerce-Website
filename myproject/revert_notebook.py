import nbformat

notebook_path = "c:/Users/rudra/Downloads/E-Commerce-Website/myproject/ml_data/notebooks/02_train_two_tower.ipynb"

nb = nbformat.v4.new_notebook()

nb.cells.extend([
    nbformat.v4.new_markdown_cell("# SECTION 1: Environment Setup\\nSet up environment variables for Keras compatibility, and import required libraries."),
    nbformat.v4.new_code_cell("""import os\\nos.environ['TF_USE_LEGACY_KERAS'] = '1'\\n\\nimport numpy as np\\nimport pandas as pd\\nimport matplotlib.pyplot as plt\\nimport tensorflow as tf\\nimport tensorflow_recommenders as tfrs\\n\\nprint(f"TensorFlow Version: {tf.__version__}")\\nprint(f"TFRS Version: {tfrs.__version__}")"""),

    nbformat.v4.new_markdown_cell("# SECTION 2: Load Data\\nLoad the processed interactions and products datasets."),
    nbformat.v4.new_code_cell("""interactions_path = 'processed_interactions.csv'\\nproducts_path = 'processed_products.csv'\\n\\ntrain_interactions_df = pd.read_csv(interactions_path)\\nproducts_df = pd.read_csv(products_path)\\n\\n# Ensure ID columns are treated as strings for embedding lookups\\ntrain_interactions_df['user_id'] = train_interactions_df['user_id'].astype(str)\\ntrain_interactions_df['product_id'] = train_interactions_df['product_id'].astype(str)\\nproducts_df['id'] = products_df['id'].astype(str)\\n\\nprint("Data successfully loaded!")\\nprint(f"Interactions Shape: {train_interactions_df.shape}")\\nprint(f"Products Shape: {products_df.shape}")"""),

    nbformat.v4.new_markdown_cell("# SECTION 3: Data Preparation\\nConvert Pandas DataFrames into TensorFlow Datasets."),
    nbformat.v4.new_code_cell("""# Create tf.data.Dataset from DataFrames\\ninteractions_dataset = tf.data.Dataset.from_tensor_slices({\\n    "user_id": tf.cast(train_interactions_df['user_id'].values, tf.string),\\n    "product_id": tf.cast(train_interactions_df['product_id'].values, tf.string),\\n})\\n\\nproducts_dataset = tf.data.Dataset.from_tensor_slices({\\n    "product_id": tf.cast(products_df['id'].values, tf.string)\\n})\\n\\n# Unique vocabulary for StringLookups\\nunique_user_ids = np.unique(train_interactions_df['user_id'].values)\\nunique_product_ids = np.unique(products_df['id'].values)\\n\\nprint(f"Vocabularies built: {len(unique_user_ids)} users, {len(unique_product_ids)} products.")"""),

    nbformat.v4.new_markdown_cell("# SECTION 4: Train Validation Split\\nSplit interactions into 80% Train and 20% Validation."),
    nbformat.v4.new_code_cell("""tf.random.set_seed(42)\\n\\n# Shuffle the interactions\\nshuffled = interactions_dataset.shuffle(len(train_interactions_df), seed=42, reshuffle_each_iteration=False)\\n\\ntrain_size = int(0.8 * len(train_interactions_df))\\ntest_size = len(train_interactions_df) - train_size\\n\\ntrain = shuffled.take(train_size)\\ntest = shuffled.skip(train_size).take(test_size)\\n\\nprint(f"Training Samples: {train_size}")\\nprint(f"Validation Samples: {test_size}")"""),

    nbformat.v4.new_markdown_cell("# SECTION 5: User Tower\\nCreate the reusable UserModel class with a StringLookup and Embedding layer."),
    nbformat.v4.new_code_cell("""embedding_dimension = 64\\n\\nclass UserModel(tf.keras.Model):\\n    def __init__(self, unique_user_ids):\\n        super().__init__()\\n        \\n        self.user_embedding = tf.keras.Sequential([\\n            tf.keras.layers.StringLookup(\\n                vocabulary=unique_user_ids, mask_token=None),\\n            tf.keras.layers.Embedding(len(unique_user_ids) + 1, embedding_dimension)\\n        ])\\n        \\n    def call(self, inputs):\\n        return self.user_embedding(inputs)\\n\\nprint("UserModel defined.")"""),

    nbformat.v4.new_markdown_cell("# SECTION 6: Product Tower\\nCreate the reusable ProductModel utilizing only product_id."),
    nbformat.v4.new_code_cell("""class ProductModel(tf.keras.Model):\\n    def __init__(self, unique_product_ids):\\n        super().__init__()\\n        \\n        self.product_id_embedding = tf.keras.Sequential([\\n            tf.keras.layers.StringLookup(\\n                vocabulary=unique_product_ids, mask_token=None),\\n            tf.keras.layers.Embedding(len(unique_product_ids) + 1, embedding_dimension)\\n        ])\\n        \\n    def call(self, inputs):\\n        return self.product_id_embedding(inputs)\\n\\nprint("ProductModel defined.")"""),

    nbformat.v4.new_markdown_cell("# SECTION 7: Two Tower Architecture\\nAssemble the TwoTowerECommerceModel using TFRS."),
    nbformat.v4.new_code_cell("""class TwoTowerECommerceModel(tfrs.Model):\\n    def __init__(self, user_model, product_model, task):\\n        super().__init__()\\n        self.user_model = user_model\\n        self.product_model = product_model\\n        self.task = task\\n        \\n    def compute_loss(self, features, training=False):\\n        user_embeddings = self.user_model(features["user_id"])\\n        product_embeddings = self.product_model(features["product_id"])\\n        \\n        return self.task(user_embeddings, product_embeddings)\\n\\nprint("TwoTowerECommerceModel assembled.")"""),

    nbformat.v4.new_markdown_cell("# SECTION 8: Retrieval Metrics\\nConfigure FactorizedTopK to calculate Recall@10, Recall@20, and Recall@50."),
    nbformat.v4.new_code_cell("""# Initialize the models\\nuser_model = UserModel(unique_user_ids)\\nproduct_model = ProductModel(unique_product_ids)\\n\\n# The FactorizedTopK metric needs the dataset of all possible product embeddings\\ncandidates = products_dataset.batch(128).map(lambda x: product_model(x["product_id"]))\\n\\n# Define the task\\nmetrics = tfrs.metrics.FactorizedTopK(\\n    candidates=candidates,\\n    ks=(10, 20, 50)\\n)\\n\\ntask = tfrs.tasks.Retrieval(\\n    metrics=metrics\\n)\\n\\n# Instantiate the full model\\nmodel = TwoTowerECommerceModel(user_model, product_model, task)\\n\\nprint("Retrieval Metrics and Task configured.")"""),

    nbformat.v4.new_markdown_cell("# SECTION 9: Compile Model\\nCompile the model using Adagrad optimizer."),
    nbformat.v4.new_code_cell("""model.compile(optimizer=tf.keras.optimizers.Adagrad(learning_rate=0.1))\\nprint("Model compiled successfully.")"""),

    nbformat.v4.new_markdown_cell("# SECTION 10: Training\\nTrain the model for 10 epochs."),
    nbformat.v4.new_code_cell("""epochs = 10\\nbatch_size = 8192\\n\\n# Cache, batch, and prefetch for performance\\ncached_train = train.batch(batch_size).cache()\\ncached_test = test.batch(batch_size).cache()\\n\\nprint("Starting model training...")\\nhistory = model.fit(\\n    cached_train,\\n    validation_data=cached_test,\\n    validation_freq=1,\\n    epochs=epochs\\n)"""),

    nbformat.v4.new_markdown_cell("# SECTION 11: Evaluation\\nEvaluate the model on the test dataset."),
    nbformat.v4.new_code_cell("""print("Evaluating model...")\\nevaluation = model.evaluate(cached_test, return_dict=True)\\n\\nprint("\\n--- Evaluation Results ---")\\nprint(f"Recall@10: {evaluation.get('factorized_top_k/top_10_categorical_accuracy', 0):.4f}")\\nprint(f"Recall@20: {evaluation.get('factorized_top_k/top_20_categorical_accuracy', 0):.4f}")\\nprint(f"Recall@50: {evaluation.get('factorized_top_k/top_50_categorical_accuracy', 0):.4f}")"""),
    
    nbformat.v4.new_markdown_cell("# SECTION 12: Save Model\\nSave the model weights."),
    nbformat.v4.new_code_cell("""import os\\nos.makedirs('../model_weights', exist_ok=True)\\nmodel.save_weights('../model_weights/two_tower.weights.h5')\\nprint("Model saved successfully!")""")
])

with open(notebook_path, 'w', encoding='utf-8') as f:
    nbformat.write(nb, f)

print("Notebook generated successfully!")
