import json

notebook_path = "c:/Users/rudra/Downloads/E-Commerce-Website/myproject/ml_data/notebooks/02_train_two_tower.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb.get('cells', []):
    if cell.get('cell_type') == 'code':
        source_str = "".join(cell.get('source', []))
        
        # Section 9: Optimizer Learning Rate
        if "optimizer=tf.keras.optimizers.Adagrad(" in source_str:
            new_source = """model.compile(optimizer=tf.keras.optimizers.Adagrad(learning_rate=0.05))
print("Model compiled successfully.")"""
            cell['source'] = [line + '\\n' for line in new_source.split('\\n')]
            cell['source'][-1] = cell['source'][-1].rstrip('\\n')
            
        # Section 10: Training hyperparameters & Early Stopping
        elif "epochs =" in source_str and "batch_size =" in source_str:
            new_source = """epochs = 25
batch_size = 1024

# Cache, batch, and prefetch for performance
cached_train = train.batch(batch_size).cache()
cached_test = test.batch(batch_size).cache()

# Add EarlyStopping to prevent overfitting or underfitting
early_stopping = tf.keras.callbacks.EarlyStopping(
    monitor="val_factorized_top_k/top_10_categorical_accuracy",
    mode="max",
    patience=5,
    restore_best_weights=True
)

print("Starting model training with Early Stopping...")
history = model.fit(
    cached_train,
    validation_data=cached_test,
    validation_freq=1,
    epochs=epochs,
    callbacks=[early_stopping]
)"""
            cell['source'] = [line + '\\n' for line in new_source.split('\\n')]
            cell['source'][-1] = cell['source'][-1].rstrip('\\n')

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Notebook hyperparameters tuned.")
