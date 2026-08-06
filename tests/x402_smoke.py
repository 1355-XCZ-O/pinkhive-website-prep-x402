"""Optional smoke test; run only after requirements-x402.txt is installed.

Uses a placeholder receiving address and public Base Sepolia facilitator. It
does not sign or settle anything; it verifies that the unpaid product route is
actually challenged with HTTP 402 by the installed SDK.
"""
import os
import base64
import json

os.environ.setdefault("X402_PAY_TO", "0x0000000000000000000000000000000000000001")
os.environ.setdefault("X402_NETWORK", "eip155:84532")

from fastapi.testclient import TestClient
from app.x402_server import app


with TestClient(app) as client:
    health = client.get("/health")
    unpaid = client.post(
        "/v1/site-prep",
        json={"site_name": "Smoke", "site_summary": "Test", "pages": [{"url": "https://example.com", "html": "<h1>Test</h1>"}]},
    )
    unpaid_ship_guard = client.post(
        "/v1/claude-ship-guard",
        json={"project_name": "Smoke", "commit_style": "descriptive"},
    )
assert health.status_code == 200, health.text
assert unpaid.status_code == 402, unpaid.text
assert "payment-required" in {key.lower() for key in unpaid.headers}
assert unpaid_ship_guard.status_code == 402, unpaid_ship_guard.text
assert "payment-required" in {key.lower() for key in unpaid_ship_guard.headers}
encoded = unpaid_ship_guard.headers["payment-required"]
challenge = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
payment = challenge["accepts"][0]
assert payment["network"] == "eip155:8453", payment
assert payment["amount"] == "50000", payment
assert payment["payTo"] == "0x8CfB0c37Af0C40f96c44fd45FdEC30b430Bc6A6e", payment
assert challenge["extensions"]["bazaar"]["info"]["input"]["method"] == "POST", challenge
print("x402 smoke: health=200 both-paid-routes=402 payment-required-header=true")
