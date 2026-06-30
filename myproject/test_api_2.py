import urllib.request
import json

try:
    url = "http://localhost:8000/api/recommendations/?type=similar&product_id=144"
    print(f"Requesting: {url}")
    req = urllib.request.Request(url, headers={"X-Requested-With": "XMLHttpRequest"})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print(f"Total products returned via AJAX: {len(data['recommendations'])}")
        for i, p in enumerate(data['recommendations'][:5]):
            print(f"{i+1}. {p['name']} (ID: {p['id']})")
except Exception as e:
    print(f"Error: {e}")
