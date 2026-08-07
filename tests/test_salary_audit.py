import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from app.metering import Meter
from app.salary_audit import build_salary_audit
from app.server import Handler


class SalaryAuditTests(unittest.TestCase):
    def test_disclosed_and_incomplete_records_are_stable(self):
        result = build_salary_audit({"job_postings": [{"@type": "JobPosting", "title": "A", "baseSalary": {"currency": "usd", "value": {"minValue": 1, "maxValue": 2, "unitText": "YEAR"}}}, {"@type": "JobPosting", "title": "B"}]})
        self.assertEqual(result["unit"]["billable_request_units"], 1)
        self.assertEqual([item["disclosure_status"] for item in result["audits"]], ["disclosed", "incomplete"])
        self.assertIn("missing_base_salary", result["audits"][1]["issues"])

    def test_schema_rejects_extra_root_keys_and_non_job_posting(self):
        with self.assertRaisesRegex(ValueError, "only job_postings"):
            build_salary_audit({"job_postings": [], "other": True})
        with self.assertRaisesRegex(ValueError, "JobPosting"):
            build_salary_audit({"job_postings": [{"@type": "Article"}]})


class SalaryAuditHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(); os.environ["API_KEYS_JSON"] = json.dumps(["salary-paid-key"])
        Handler.meter = Meter(os.path.join(cls.temp.name, "usage.db")); cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True); cls.thread.start(); cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=2); cls.temp.cleanup()

    def request(self, key):
        payload = {"job_postings": [{"@type": "JobPosting", "title": "A"}]}
        return urllib.request.urlopen(urllib.request.Request(self.base + "/v1/salary-disclosure-audit", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "X-API-Key": "salary-paid-key", "Idempotency-Key": key}))

    def test_paid_request_is_metered_once_for_same_idempotency_key(self):
        with self.request("salary-001") as response: first = json.load(response)
        with self.request("salary-001") as response: second = json.load(response)
        self.assertEqual(first["request_id"], second["request_id"])
        self.assertEqual(Handler.meter.summary("salary-paid-key")["units"], 1)

    def test_unpaid_request_is_rejected(self):
        payload = {"job_postings": [{"@type": "JobPosting"}]}
        request = urllib.request.Request(self.base + "/v1/salary-disclosure-audit", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with self.assertRaises(urllib.error.HTTPError) as caught: urllib.request.urlopen(request)
        self.assertEqual(caught.exception.code, 401)
