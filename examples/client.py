"""No-dependency prepaid-key client."""
import json
import os
import urllib.request

url = os.environ.get("WEBSITE_PREP_URL", "http://127.0.0.1:8402/v1/site-prep")
key = os.environ["WEBSITE_PREP_API_KEY"]
with open(os.path.join(os.path.dirname(__file__), "request.json"), "rb") as handle:
    request = urllib.request.Request(url, data=handle.read(), headers={"Content-Type": "application/json", "X-API-Key": key})
with urllib.request.urlopen(request) as response:
    print(json.dumps(json.load(response), indent=2, ensure_ascii=False))

