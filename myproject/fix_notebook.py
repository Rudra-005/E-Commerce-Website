import json
import os

notebook_path = r"c:\\Users\\rudra\\Downloads\\E-Commerce-Website\\myproject\\ml_data\\notebooks\\01_data_analysis.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# The first code cell is the second cell overall (index 1)
# Let's find the first code cell that imports tensorflow
for cell in nb.get("cells", []):
    if cell["cell_type"] == "code":
        source = "".join(cell["source"])
        if "import tensorflow as tf" in source:
            # Prepend the env variable setting
            new_source = [
                "import os\\n",
                "os.environ['TF_USE_LEGACY_KERAS'] = '1'\\n",
                "\\n"
            ] + cell["source"]
            cell["source"] = new_source
            break

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Notebook updated successfully.")
