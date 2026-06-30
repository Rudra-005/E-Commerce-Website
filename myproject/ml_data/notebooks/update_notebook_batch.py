import json

notebook_path = "c:/Users/rudra/Downloads/E-Commerce-Website/myproject/ml_data/notebooks/02_train_two_tower.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Find Section 13 and replace batch(100) with batch(128)
for cell in nb.get('cells', []):
    if cell.get('cell_type') == 'code':
        source_str = "".join(cell.get('source', []))
        if "tfrs.layers.factorized_top_k.BruteForce" in source_str and "products_dataset.batch(100)" in source_str:
            new_source = source_str.replace("products_dataset.batch(100)", "products_dataset.batch(128)")
            cell['source'] = [line + '\\n' for line in new_source.split('\\n')]
            if cell['source']:
                cell['source'][-1] = cell['source'][-1].rstrip('\\n')
            break

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Notebook Section 13 updated to fix batch mismatch.")
