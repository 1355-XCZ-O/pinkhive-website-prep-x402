import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from app.core import build_site_bundle
from app.metering import Meter
from app.server import Handler


class CoreTests(unittest.TestCase):
    def test_bundle(self):
        value = build_site_bundle({"site_name": "T", "site_summary": "S", "pages": [{"url": "https://e.test/a", "html": "<title>A</title><h1>Hello</h1><p>World</p>"}]})
        self.assertEqual(value["unit"]["pages"], 1)
        self.assertIn("[A](https://e.test/a)", value["llms_txt"])
        self.assertIn("# Hello", value["llms_full_txt"])

    def test_limits(self):
        with self.assertRaisesRegex(ValueError, "at most 1"):
            build_site_bundle({"site_name": "T", "site_summary": "S", "pages": [{"url": "https://e.test", "html": "x"}, {"url": "https://e.test/2", "html": "y"}]}, max_pages=1)


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        os.environ["API_KEYS_JSON"] = json.dumps(["paid-test-key"])
        Handler.meter = Meter(os.path.join(cls.temp.name, "usage.db"))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.temp.cleanup()

    def request(self, path, payload=None, key=None):
        headers = {"Content-Type": "application/json"}
        if key:
            headers["X-API-Key"] = key
        data = json.dumps(payload).encode() if payload is not None else None
        return urllib.request.urlopen(urllib.request.Request(self.base + path, data=data, headers=headers))

    def test_health(self):
        with self.request("/health") as response:
            self.assertTrue(json.load(response)["paid_route_ready"])

    def test_unpaid_rejected(self):
        try:
            self.request("/v1/site-prep", {})
        except urllib.error.HTTPError as caught:
            self.assertEqual(caught.code, 401)
            caught.close()
        else:
            self.fail("unpaid request was accepted")

    def test_paid_e2e_and_meter(self):
        payload = {"site_name": "Acme", "site_summary": "Docs", "pages": [{"url": "https://example.com", "html": "<title>Home</title><h1>Welcome</h1>"}]}
        with self.request("/v1/site-prep", payload, "paid-test-key") as response:
            result = json.load(response)
        self.assertEqual(result["metered_units"], 1)
        self.assertTrue(result["request_id"])
        with self.request("/v1/usage", key="paid-test-key") as response:
            usage = json.load(response)
        self.assertGreaterEqual(usage["successful_requests"], 1)


if __name__ == "__main__":
    unittest.main()
