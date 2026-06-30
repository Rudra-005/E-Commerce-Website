import json

notebook_path = "c:/Users/rudra/Downloads/E-Commerce-Website/myproject/ml_data/notebooks/02_train_two_tower.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb.get('cells', []):
    if cell.get('cell_type') == 'code':
        source_str = "".join(cell.get('source', []))
        
        # Section 9: Optimizer Learning Rate
        if "optimizer=tf.keras.optimizers.Adagrad(" in source_str:
            new_source = """model.compile(optimizer=tf.keras.optimizers.Adagrad(learning_rate=0.1))
print("Model compiled successfully.")"""
            cell['source'] = [line + '\\n' for line in new_source.split('\\n')]
            cell['source'][-1] = cell['source'][-1].rstrip('\\n')
            
        # Section 10: Training hyperparameters (Remove Early Stopping)
        elif "epochs =" in source_str and "batch_size =" in source_str:
            new_source = """epochs = 10
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
)"""
            cell['source'] = [line + '\\n' for line in new_source.split('\\n')]
            cell['source'][-1] = cell['source'][-1].rstrip('\\n')

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Notebook hyperparameters reverted to original.")
