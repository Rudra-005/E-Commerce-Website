import urllib.request
import json

try:
    url = "http://localhost:8000/api/recommendations/?type=similar&target_id=144"
    print(f"Requesting: {url}")
    req = urllib.request.Request(url, headers={"X-Requested-With": "XMLHttpRequest"})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print(f"Full response data: {data}")
except Exception as e:
    print(f"Error: {e}")
