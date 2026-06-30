import urllib.request
import json
import ssl

try:
    # ID 194 is Puma Sports Shoes Comfort
    url = "http://localhost:8000/api/recommendations/?type=similar&product_id=194"
    req = urllib.request.Request(url, headers={"X-Requested-With": "XMLHttpRequest"})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        for p in data['recommendations'][:5]:
            print(f"- {p['name']}")
except Exception as e:
    print(f"Error: {e}")
