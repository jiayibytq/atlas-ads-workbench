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


if __name__ == "__main__":
    unittest.main()
