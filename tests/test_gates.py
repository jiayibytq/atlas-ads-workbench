from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atlas_ads_workbench.gates import evaluate_gates
from atlas_ads_workbench.feasibility import calculate_feasibility
from atlas_ads_workbench.models import validate_intake


def intake():
    return validate_intake({
        "marketplace": "US", "product_stage": "launch", "monthly_sales_target": 300,
        "product_price_usd": 32.99, "target_tacos_percent": 15,
        "ad_sales_share_percent": 80, "benchmark_cpc_usd": 1.2,
        "benchmark_cvr_percent": 10, "business_goals": "Validate core keywords first.",
    })


def evidence(value, status="confirmed"):
    return {"value": value, "status": status, "source": "seller_input", "captured_at": "2026-07-30"}


class GateTests(unittest.TestCase):
    def test_feasibility_gate_allows_calculation_but_surfaces_constraint_conflict(self):
        current_intake = intake()
        gates = evaluate_gates(current_intake, calculate_feasibility(current_intake), {})
        gate = gates["FEASIBILITY-GATE-001"]

        self.assertEqual(gate["status"], "ready_for_rule_evaluation")
        self.assertEqual(gate["conflicting_fields"], ["benchmark_cvr_percent"])
        self.assertEqual(gate["missing_fields"], [])

    def test_sb_gate_requires_verified_account_and_brand_evidence(self):
        current_intake = intake()
        context = {
            "advertiser_account_status": evidence("active", "verified"),
            "brand_registry_status": evidence("enrolled", "verified"),
            "campaign_goal": evidence("brand_defense"),
            "eligible_advertised_asins": evidence(["B0NEW123"], "verified"),
        }
        gates = evaluate_gates(current_intake, calculate_feasibility(current_intake), context)

        self.assertEqual(gates["SB-GATE-001"]["status"], "ready_for_rule_evaluation")

    def test_sd_gate_names_missing_evidence_without_inferring_it(self):
        current_intake = intake()
        gates = evaluate_gates(current_intake, calculate_feasibility(current_intake), {})
        gate = gates["SD-GATE-001"]

        self.assertEqual(gate["status"], "information_required")
        self.assertIn("display_eligibility_status", gate["missing_fields"])
        self.assertIn("catalog_relationship", gate["missing_fields"])
        self.assertEqual(gate["next_action"]["type"], "collect_seller_input")


if __name__ == "__main__":
    unittest.main()
