from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atlas_ads_workbench.models import validate_intake
from atlas_ads_workbench.storage import LocalStorage, StorageError


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


class LocalStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.storage = LocalStorage(Path(self.temp_dir.name))
        self.intake = validate_intake(valid_payload())

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_saved_draft_round_trips(self):
        self.storage.save_draft(self.intake)

        self.assertEqual(self.storage.load_draft(), self.intake)

    def test_each_run_has_a_unique_immutable_input_snapshot(self):
        first_run = self.storage.create_run(self.intake, "0.1.0")
        changed_draft = dict(self.intake, monthly_sales_target=999)
        self.storage.save_draft(changed_draft)
        second_run = self.storage.create_run(changed_draft, "0.1.0")

        self.assertNotEqual(first_run["run_id"], second_run["run_id"])
        self.assertEqual(
            self.storage.load_run(first_run["run_id"])["intake"]["monthly_sales_target"],
            300.0,
        )
        self.assertEqual(
            self.storage.load_run(second_run["run_id"])["intake"]["monthly_sales_target"],
            999,
        )

    def test_manifest_names_input_hash_and_phase_one_boundaries(self):
        run = self.storage.create_run(self.intake, "0.1.0")

        manifest = self.storage.load_run(run["run_id"])["manifest"]
        self.assertEqual(manifest["status"], "intake_captured")
        self.assertEqual(manifest["workbench_version"], "0.1.0")
        self.assertEqual(len(manifest["intake_sha256"]), 64)
        self.assertFalse(manifest["external_data_used"])
        self.assertEqual(manifest["model_calls"], 0)

    def test_run_can_freeze_a_decision_plan_with_its_own_hash(self):
        decision_plan = {
            "calculation_version": 1,
            "data_source": "seller_input",
            "external_data_used": False,
            "model_calls": 0,
            "is_feasible_at_benchmark": False,
        }
        manifest = self.storage.create_run(self.intake, "0.2.0", decision_plan)

        saved_run = self.storage.load_run(manifest["run_id"])
        self.assertEqual(saved_run["decision_plan"], decision_plan)
        self.assertEqual(len(manifest["decision_plan_sha256"]), 64)

    def test_corrupt_draft_has_an_actionable_error(self):
        draft_file = Path(self.temp_dir.name) / "drafts" / "current-intake.json"
        draft_file.parent.mkdir(parents=True)
        draft_file.write_text("not json", encoding="utf-8")

        with self.assertRaisesRegex(StorageError, "draft"):
            self.storage.load_draft()


if __name__ == "__main__":
    unittest.main()
