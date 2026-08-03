from pathlib import Path
import re
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atlas_ads_workbench.gates import GATE_VERSIONS, evaluate_gates
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

        self.assertEqual(gate["status"], "constraint_conflict")
        self.assertEqual(gate["seller_status"], "存在数值冲突")
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
        gates = evaluate_gates(
            current_intake,
            calculate_feasibility(current_intake),
            context,
            selected_ad_modules=["sb"],
        )

        self.assertEqual(gates["SB-GATE-001"]["status"], "ready_for_rule_evaluation")

    def test_sd_gate_names_missing_evidence_without_inferring_it(self):
        current_intake = intake()
        gates = evaluate_gates(
            current_intake,
            calculate_feasibility(current_intake),
            {},
            selected_ad_modules=["sd"],
        )
        gate = gates["SD-GATE-001"]

        self.assertEqual(gate["status"], "verification_required")
        self.assertIn("display_eligibility_status", gate["missing_fields"])
        self.assertNotIn("catalog_relationship", gate["missing_fields"])
        self.assertEqual(
            gate["next_action"]["type"],
            "collect_seller_input_and_external_evidence",
        )

    def test_sd_cross_sell_requires_old_product_evidence_in_addition_to_standard_sd_fields(self):
        current_intake = intake()
        gates = evaluate_gates(
            current_intake,
            calculate_feasibility(current_intake),
            {},
            selected_ad_modules=["sd_cross_sell"],
        )
        gate = gates["SD-GATE-001"]

        self.assertIn("old_product_asins", gate["missing_fields"])
        self.assertIn("catalog_relationship", gate["missing_fields"])
        self.assertIn("contribution_margin", gate["missing_fields"])

    def test_confirmed_only_field_missing_is_information_required_not_verification_required(self):
        current_intake = intake()
        context = {
            "display_eligibility_status": evidence("eligible", "verified"),
            "new_product_asin": evidence("B0NEW123"),
            "inventory_health": evidence("healthy"),
        }
        gate = evaluate_gates(
            current_intake,
            calculate_feasibility(current_intake),
            context,
            selected_ad_modules=["sd"],
        )["SD-GATE-001"]

        self.assertEqual(gate["status"], "information_required")
        self.assertEqual(gate["missing_fields"], ["campaign_goal"])
        self.assertEqual(gate["next_action"]["type"], "collect_seller_input")

    def test_runtime_gate_ids_and_versions_match_decision_rule_contract(self):
        contract = (ROOT / "contracts" / "decision-rules.yaml").read_text(encoding="utf-8")
        contract_gates = {
            gate_id: int(version)
            for gate_id, version in re.findall(
                r"^  - id: ([A-Z0-9-]+)\n    version: (\d+)$",
                contract,
                flags=re.MULTILINE,
            )
        }
        current_intake = intake()
        runtime_gates = evaluate_gates(
            current_intake,
            calculate_feasibility(current_intake),
            {},
            selected_ad_modules=["sb", "sd"],
        )

        self.assertEqual(
            {gate_id: gate["version"] for gate_id, gate in runtime_gates.items()},
            {
                gate_id: contract_gates[gate_id]
                for gate_id in runtime_gates
            },
        )
        self.assertEqual(contract_gates, GATE_VERSIONS)

    def test_budget_only_path_does_not_mark_sb_or_sd_as_missing(self):
        current_intake = intake()
        gates = evaluate_gates(
            current_intake,
            calculate_feasibility(current_intake),
            {},
            selected_ad_modules=[],
        )

        self.assertEqual(gates["SB-GATE-001"]["status"], "not_applicable")
        self.assertEqual(gates["SD-GATE-001"]["status"], "not_applicable")
        self.assertFalse(gates["SB-GATE-001"]["applicable"])

    def test_only_selected_module_is_evaluated(self):
        current_intake = intake()
        gates = evaluate_gates(
            current_intake,
            calculate_feasibility(current_intake),
            {},
            selected_ad_modules=["sb"],
        )

        self.assertEqual(gates["SB-GATE-001"]["status"], "verification_required")
        self.assertEqual(gates["SD-GATE-001"]["status"], "not_applicable")

    def test_feasibility_conflict_has_an_unambiguous_status(self):
        current_intake = intake()
        gate = evaluate_gates(
            current_intake,
            calculate_feasibility(current_intake),
            {},
            selected_ad_modules=[],
        )["FEASIBILITY-GATE-001"]

        self.assertEqual(gate["status"], "constraint_conflict")
        self.assertEqual(gate["seller_status"], "存在数值冲突")


if __name__ == "__main__":
    unittest.main()
