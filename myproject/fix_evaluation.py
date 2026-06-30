import json

notebook_path = "c:/Users/rudra/Downloads/E-Commerce-Website/myproject/ml_data/notebooks/02_train_two_tower.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb.get('cells', []):
    if cell.get('cell_type') == 'code':
        source = cell.get('source', [])
        for i, line in enumerate(source):
            if "print(Evaluation, Results)" in line:
                source[i] = line.replace("print(Evaluation, Results)", "print('\\n--- Evaluation Results ---')")

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Fixed Evaluation typo.")
