"""Optional smoke test; run only after requirements-x402.txt is installed.

Uses a placeholder receiving address and public Base Sepolia facilitator. It
does not sign or settle anything; it verifies that the unpaid product route is
actually challenged with HTTP 402 by the installed SDK.
"""
import os

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
assert health.status_code == 200, health.text
assert unpaid.status_code == 402, unpaid.text
assert "payment-required" in {key.lower() for key in unpaid.headers}
print("x402 smoke: health=200 unpaid=402 payment-required-header=true")
