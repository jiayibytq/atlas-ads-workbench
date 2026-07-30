import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atlas_ads_workbench.server import create_server
from atlas_ads_workbench.storage import LocalStorage


def valid_payload():
    return {
        "marketplace": "US",
        "product_stage": "launch",
        "monthly_sales_target": 300,
        "product_price_usd": 32.99,
        "target_tacos_percent": 15,
        "ad_sales_share_percent": 80,
        "benchmark_cpc_usd": 1.2,
        "benchmark_cvr_percent": 10,
        "business_goals": "Validate core keywords before scaling.",
    }


class LocalServerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.server = create_server(
            host="127.0.0.1",
            port=0,
            session_token="test-token",
            storage=LocalStorage(Path(self.temp_dir.name)),
            workbench_version="0.1.0",
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = "http://127.0.0.1:%s" % self.server.server_port

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=1)
        self.temp_dir.cleanup()

    def request(self, path, method="GET", payload=None, token=None):
        headers = {}
        if token is not None:
            headers["X-Atlas-Session"] = token
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(self.base_url + path, data=data, headers=headers, method=method)
        with urlopen(request) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_health_is_public_and_names_workbench_version(self):
        status, body = self.request("/health")

        self.assertEqual(status, 200)
        self.assertEqual(body, {"ok": True, "version": "0.1.0"})

    def test_root_returns_the_local_workbench_page(self):
        with urlopen(self.base_url + "/") as response:
            page = response.read().decode("utf-8")

        self.assertEqual(response.status, 200)
        self.assertIn("Atlas Ads", page)
        self.assertIn("第一阶段：仅保存需求", page)

    def test_api_rejects_missing_and_wrong_tokens(self):
        with self.assertRaises(HTTPError) as missing:
            self.request("/api/draft")
        self.assertEqual(missing.exception.code, 401)

        with self.assertRaises(HTTPError) as wrong:
            self.request("/api/draft", token="wrong-token")
        self.assertEqual(wrong.exception.code, 403)

    def test_authorized_client_can_save_and_read_draft(self):
        status, saved = self.request(
            "/api/draft", "PUT", valid_payload(), token="test-token"
        )
        _, loaded = self.request("/api/draft", token="test-token")

        self.assertEqual(status, 200)
        self.assertEqual(saved["marketplace"], "US")
        self.assertEqual(loaded["draft"], saved)

    def test_authorized_client_can_create_and_read_run(self):
        status, manifest = self.request(
            "/api/runs", "POST", valid_payload(), token="test-token"
        )
        _, run = self.request("/api/runs/%s" % manifest["run_id"], token="test-token")

        self.assertEqual(status, 201)
        self.assertEqual(run["manifest"], manifest)
        self.assertEqual(run["intake"]["data_source"], "seller_input")
        self.assertFalse(run["decision_plan"]["feasibility"]["is_feasible_at_benchmark"])
        self.assertEqual(len(run["decision_plan"]["campaign_architecture"]["campaigns"]), 4)
        self.assertEqual(len(manifest["decision_plan_sha256"]), 64)

    def test_authorized_client_can_calculate_transparent_feasibility(self):
        status, result = self.request(
            "/api/feasibility", "POST", valid_payload(), token="test-token"
        )

        self.assertEqual(status, 200)
        self.assertEqual(result["data_source"], "seller_input")
        self.assertFalse(result["external_data_used"])
        self.assertIn("required_cvr_percent", result["formulae"])

    def test_authorized_client_can_preview_a_campaign_architecture(self):
        status, architecture = self.request(
            "/api/campaign-architecture", "POST", valid_payload(), token="test-token"
        )

        self.assertEqual(status, 200)
        self.assertEqual(architecture["status"], "review_required")
        self.assertEqual(len(architecture["campaigns"]), 4)

    def test_authorized_client_can_evaluate_versioned_gates(self):
        status, gates = self.request(
            "/api/gates", "POST", valid_payload(), token="test-token"
        )

        self.assertEqual(status, 200)
        self.assertEqual(gates["SB-GATE-001"]["status"], "information_required")
        self.assertIn("brand_registry_status", gates["SB-GATE-001"]["missing_fields"])

    def test_invalid_json_returns_a_structured_bad_request(self):
        request = Request(
            self.base_url + "/api/draft",
            data=b"not json",
            headers={
                "Content-Type": "application/json",
                "X-Atlas-Session": "test-token",
            },
            method="PUT",
        )

        with self.assertRaises(HTTPError) as error:
            urlopen(request)
        self.assertEqual(error.exception.code, 400)
        self.assertEqual(
            json.loads(error.exception.read().decode("utf-8"))["code"], "bad_request"
        )


if __name__ == "__main__":
    unittest.main()
