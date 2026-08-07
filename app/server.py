"""Deployable stdlib HTTP service with API-key entitlement and usage metering."""
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .core import build_site_bundle
from .metering import Meter, configured_api_keys
from .salary_audit import build_salary_audit

MAX_BODY_BYTES = int(os.environ.get("MAX_BODY_BYTES", "2000000"))
PRICE_USD = os.environ.get("PRICE_USD", "0.02")


class Handler(BaseHTTPRequestHandler):
    meter = None

    def send_json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def api_key(self) -> str:
        return self.headers.get("X-API-Key", "")

    def authorized(self) -> bool:
        keys = configured_api_keys()
        return bool(keys) and self.api_key() in keys

    def do_GET(self):
        if self.path == "/health":
            keys = configured_api_keys()
            self.send_json(200, {"status": "ok", "paid_route_ready": bool(keys), "metering": "sqlite", "price_usd_per_request": PRICE_USD})
        elif self.path == "/v1/pricing":
            self.send_json(200, {"products": [{"product": "website-prep", "unit": "one request, up to 20 supplied HTML pages", "price_usd": PRICE_USD}, {"product": "salary-disclosure-audit", "unit": "one request, up to 25 JSON-LD JobPosting objects", "price_usd": os.environ.get("SALARY_AUDIT_PRICE_USD", "0.01")}], "payment_modes": ["x402", "prepaid_api_key"]})
        elif self.path == "/v1/usage":
            if not self.authorized():
                self.send_json(401, {"error": "valid X-API-Key required"})
            else:
                self.send_json(200, self.meter.summary(self.api_key()))
        else:
            self.send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path not in {"/v1/site-prep", "/v1/salary-disclosure-audit"}:
            self.send_json(404, {"error": "not found"})
            return
        if not self.authorized():
            self.send_json(402 if not configured_api_keys() else 401, {"error": "payment or valid X-API-Key required", "price_usd": PRICE_USD})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json(400, {"error": "invalid Content-Length"})
            return
        if length <= 0 or length > MAX_BODY_BYTES:
            self.send_json(413, {"error": f"body must be 1..{MAX_BODY_BYTES} bytes"})
            return
        started = time.perf_counter()
        try:
            payload = json.loads(self.rfile.read(length))
            result = build_site_bundle(payload) if self.path == "/v1/site-prep" else build_salary_audit(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            self.send_json(400, {"error": str(exc)})
            return
        elapsed = (time.perf_counter() - started) * 1000
        input_chars = result["unit"].get("input_html_chars", length)
        request_id = self.meter.record(self.api_key(), self.path, 200, 1, input_chars, elapsed, self.headers.get("Idempotency-Key"))
        result["request_id"] = request_id
        result["metered_units"] = 1
        self.send_json(200, result)

    def log_message(self, fmt, *args):
        print(json.dumps({"remote": self.address_string(), "message": fmt % args}, ensure_ascii=False), flush=True)


def run():
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8402"))
    Handler.meter = Meter()
    print(f"website-prep listening on {host}:{port}", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    run()

