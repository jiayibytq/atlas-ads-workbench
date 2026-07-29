from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atlas_ads_workbench.feasibility import calculate_feasibility
from atlas_ads_workbench.models import validate_intake


def intake(**overrides):
    payload = {
        "marketplace": "US",
        "product_stage": "launch",
        "monthly_sales_target": 300,
        "product_price_usd": 32.99,
        "target_tacos_percent": 15,
        "ad_sales_share_percent": 80,
        "benchmark_cpc_usd": 1.2,
        "benchmark_cvr_percent": 10,
        "business_goals": "Validate core keywords before scaling budget.",
    }
    payload.update(overrides)
    return validate_intake(payload)


class FeasibilityTests(unittest.TestCase):
    def test_calculates_budget_and_infeasibility_from_visible_formulae(self):
        result = calculate_feasibility(intake())

        self.assertAlmostEqual(result["monthly_revenue_target_usd"], 9897.0)
        self.assertAlmostEqual(result["monthly_ad_spend_cap_usd"], 1484.55)
        self.assertAlmostEqual(result["daily_ad_spend_cap_usd"], 49.485)
        self.assertAlmostEqual(result["daily_ad_orders_target"], 8.0)
        self.assertAlmostEqual(result["ad_acos_cap_percent"], 18.75)
        self.assertAlmostEqual(result["required_cvr_percent"], 19.400, places=3)
        self.assertFalse(result["is_feasible_at_benchmark"])
        self.assertAlmostEqual(result["implied_tacos_at_benchmark_percent"], 29.100, places=3)
        self.assertEqual(result["basis"][0]["kind"], "seller_input")
        self.assertIn("required_cvr_percent", result["formulae"])

    def test_feasible_case_has_no_constraint_alert(self):
        result = calculate_feasibility(
            intake(benchmark_cpc_usd=0.5, benchmark_cvr_percent=20)
        )

        self.assertTrue(result["is_feasible_at_benchmark"])
        self.assertEqual(result["alerts"], [])
        self.assertEqual(result["levers"], [])

    def test_infeasible_case_exposes_adjustable_levers_without_recommendation_claim(self):
        result = calculate_feasibility(intake())

        lever_names = {lever["field"] for lever in result["levers"]}
        self.assertEqual(
            lever_names,
            {"benchmark_cpc_usd", "target_tacos_percent", "ad_sales_share_percent"},
        )
        self.assertIn("seller assumption", result["alerts"][0]["message"])


if __name__ == "__main__":
    unittest.main()
