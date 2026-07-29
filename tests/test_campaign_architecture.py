from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atlas_ads_workbench.campaign_architecture import build_campaign_architecture
from atlas_ads_workbench.feasibility import calculate_feasibility
from atlas_ads_workbench.models import validate_intake


def make_intake(**overrides):
    payload = {
        "marketplace": "US", "product_stage": "launch", "monthly_sales_target": 300,
        "product_price_usd": 32.99, "target_tacos_percent": 15,
        "ad_sales_share_percent": 80, "benchmark_cpc_usd": 1.2,
        "benchmark_cvr_percent": 10, "business_goals": "Validate core keywords first.",
    }
    payload.update(overrides)
    return validate_intake(payload)


class CampaignArchitectureTests(unittest.TestCase):
    def test_launch_allocation_is_a_fully_explained_budget_draft(self):
        current_intake = make_intake()
        architecture = build_campaign_architecture(
            current_intake, calculate_feasibility(current_intake)
        )

        self.assertEqual(architecture["status"], "review_required")
        self.assertEqual(len(architecture["campaigns"]), 4)
        self.assertAlmostEqual(sum(item["budget_share_percent"] for item in architecture["campaigns"]), 100)
        self.assertAlmostEqual(sum(item["daily_budget_usd"] for item in architecture["campaigns"]), 49.485)
        self.assertEqual(architecture["campaigns"][0]["id"], "auto-sampling")
        self.assertIn("deterministic stage rule", architecture["campaigns"][0]["basis"])

    def test_feasible_allocation_is_ready_for_human_review(self):
        current_intake = make_intake(benchmark_cpc_usd=0.5, benchmark_cvr_percent=20)
        architecture = build_campaign_architecture(
            current_intake, calculate_feasibility(current_intake)
        )

        self.assertEqual(architecture["status"], "ready_for_human_review")
        self.assertEqual(architecture["data_source"], "deterministic_rule")
        self.assertFalse(architecture["external_data_used"])
        self.assertEqual(architecture["model_calls"], 0)


if __name__ == "__main__":
    unittest.main()
