from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atlas_ads_workbench.demo_report import build_demo_report
from atlas_ads_workbench.feasibility import calculate_feasibility
from atlas_ads_workbench.models import validate_intake


def make_intake(**overrides):
    payload = {
        "marketplace": "US",
        "product_stage": "launch",
        "monthly_sales_target": 300,
        "product_price_usd": 32.99,
        "target_tacos_percent": 15,
        "ad_sales_share_percent": 80,
        "benchmark_cpc_usd": 1.2,
        "benchmark_cvr_percent": 10,
        "business_goals": "Validate the demo report flow.",
    }
    payload.update(overrides)
    return validate_intake(payload)


class DemoReportTests(unittest.TestCase):
    def test_builds_three_fixed_sp_rows_with_visible_budget_allocation(self):
        feasibility = calculate_feasibility(make_intake())
        report = build_demo_report(feasibility)

        self.assertEqual(report["report_version"], 1)
        self.assertEqual(report["report_type"], "demo")
        self.assertFalse(report["is_executable"])
        self.assertFalse(report["external_data_used"])
        self.assertEqual(report["model_calls"], 0)
        self.assertEqual(len(report["rows"]), 3)
        self.assertEqual(
            [row["budget_share_percent"] for row in report["rows"]],
            [30, 45, 25],
        )
        self.assertEqual(
            [row["target"] for row in report["rows"]],
            [
                "demo running socks",
                "demo compression socks",
                "DEMO-ASIN-001",
            ],
        )
        self.assertTrue(all(row["ad_type"] == "SP" for row in report["rows"]))
        self.assertTrue(all(row["is_demo"] for row in report["rows"]))

    def test_row_budgets_equal_the_displayed_total_after_rounding(self):
        feasibility = calculate_feasibility(make_intake())
        report = build_demo_report(feasibility)

        allocated = round(
            sum(row["daily_budget_usd"] for row in report["rows"]), 2
        )
        self.assertEqual(allocated, report["total_daily_budget_usd"])
        self.assertEqual(report["total_daily_budget_usd"], 49.49)

    def test_infeasible_inputs_add_a_warning_without_hiding_the_demo(self):
        feasibility = calculate_feasibility(make_intake())
        report = build_demo_report(feasibility)

        self.assertEqual(len(report["warnings"]), 1)
        self.assertIn("输入假设存在可行性冲突", report["warnings"][0])
        self.assertIn("固定演示规则", report["summary"])
        self.assertEqual(len(report["rows"]), 3)

    def test_feasible_inputs_have_no_feasibility_warning(self):
        feasibility = calculate_feasibility(
            make_intake(benchmark_cpc_usd=0.5, benchmark_cvr_percent=20)
        )
        report = build_demo_report(feasibility)

        self.assertEqual(report["warnings"], [])


if __name__ == "__main__":
    unittest.main()
