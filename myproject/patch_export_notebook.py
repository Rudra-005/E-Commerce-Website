import json
import os

notebook_path = r"c:\\Users\\rudra\\Downloads\\E-Commerce-Website\\myproject\\ml_data\\notebooks\\03_export_embeddings.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Find Section 3 cell
for cell in nb.get("cells", []):
    if cell["cell_type"] == "code":
        source = "".join(cell["source"])
        if "class TwoTowerECommerceModel(tfrs.Model):" in source:
            # We need to insert the call method into the class
            new_source_lines = []
            for line in cell["source"]:
                if "def compute_loss" in line:
                    new_source_lines.append("    def call(self, features):\\n")
                    new_source_lines.append("        return (self.user_model(features['user_id']), \\n")
                    new_source_lines.append("                self.product_model(features['product_id']))\\n\\n")
                new_source_lines.append(line)
            cell["source"] = new_source_lines
            break

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Export notebook patched with call() method.")
