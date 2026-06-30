import urllib.request
import json

try:
    req = urllib.request.Request("http://localhost:8000/products/?search=shoes", headers={"X-Requested-With": "XMLHttpRequest"})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print(f"Total products returned via AJAX: {len(data['products'])}")
        for i, p in enumerate(data['products'][:5]):
            print(f"{i+1}. {p['name']}")
except Exception as e:
    print(f"Error: {e}")
