import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atlas_ads_workbench.workflow import WorkflowValidationError, normalize_selected_ad_modules


class WorkflowSelectionTests(unittest.TestCase):
    def test_normalizes_unique_modules_in_supported_order(self):
        self.assertEqual(
            normalize_selected_ad_modules(["sd_cross_sell", "sp", "sp", "sb"]),
            ["sp", "sb", "sd_cross_sell"],
        )

    def test_rejects_unknown_module(self):
        with self.assertRaisesRegex(WorkflowValidationError, "unsupported advertising module"):
            normalize_selected_ad_modules(["sp", "amazon_magic"])

    def test_allows_budget_only_path(self):
        self.assertEqual(normalize_selected_ad_modules([]), [])


if __name__ == "__main__":
    unittest.main()
