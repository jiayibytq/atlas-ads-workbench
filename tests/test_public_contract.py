import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atlas_ads_workbench.models import validate_intake


class PublicContractTests(unittest.TestCase):
    def test_public_example_is_valid_and_contains_no_external_claims(self):
        example = json.loads((ROOT / "examples" / "intake.example.json").read_text("utf-8"))
        intake = validate_intake(example)

        self.assertEqual(intake["data_source"], "seller_input")
        self.assertFalse(intake["external_data_used"])

    def test_architecture_document_names_local_security_and_phase_boundary(self):
        document = (ROOT / "docs" / "architecture" / "phase-1.md").read_text("utf-8")

        for expected_text in ("127.0.0.1", "URL fragment", "不会连接 Amazon", "intake.json"):
            self.assertIn(expected_text, document)

    def test_public_rule_and_output_contracts_name_the_evidence_boundary(self):
        rules = (ROOT / "contracts" / "decision-rules.yaml").read_text("utf-8")
        schema = json.loads((ROOT / "contracts" / "output-schema.json").read_text("utf-8"))

        for gate_id in ("FEASIBILITY-GATE-001", "SB-GATE-001", "SD-GATE-001"):
            self.assertIn(gate_id, rules)
        self.assertIn("keyword_targeting_evidence", rules)
        self.assertIn("product_targeting_evidence", rules)
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["title"], "Atlas Ads Decision Output")
        self.assertEqual(
            schema["$defs"]["decision"]["required"],
            ["decision_id", "status", "claim", "evidence", "rule", "assumptions", "next_action"],
        )

    def test_decision_contract_document_explains_that_rules_are_not_data_connections(self):
        document = (ROOT / "docs" / "architecture" / "decision-contract.md").read_text("utf-8")

        for expected_text in (
            "decision-rules.yaml",
            "output-schema.json",
            "不会连接 Amazon",
            "不生成策略结论",
        ):
            self.assertIn(expected_text, document)


if __name__ == "__main__":
    unittest.main()
