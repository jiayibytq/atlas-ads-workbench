from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atlas_ads_workbench.models import IntakeValidationError, validate_intake


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


class IntakeValidationTests(unittest.TestCase):
    def test_valid_payload_is_normalized_with_schema_and_transparency(self):
        intake = validate_intake(valid_payload())

        self.assertEqual(intake["schema_version"], 1)
        self.assertEqual(intake["marketplace"], "US")
        self.assertEqual(intake["product_price_usd"], 32.99)
        self.assertEqual(intake["data_source"], "seller_input")
        self.assertEqual(intake["external_data_used"], False)
        self.assertEqual(intake["model_calls"], 0)

    def test_missing_marketplace_is_rejected_with_field_name(self):
        payload = valid_payload()
        del payload["marketplace"]

        with self.assertRaisesRegex(IntakeValidationError, "marketplace"):
            validate_intake(payload)

    def test_zero_product_price_is_rejected(self):
        payload = valid_payload()
        payload["product_price_usd"] = 0

        with self.assertRaisesRegex(IntakeValidationError, "product_price_usd"):
            validate_intake(payload)

    def test_tacos_above_one_hundred_is_rejected(self):
        payload = valid_payload()
        payload["target_tacos_percent"] = 101

        with self.assertRaisesRegex(IntakeValidationError, "target_tacos_percent"):
            validate_intake(payload)

    def test_unknown_product_stage_is_rejected(self):
        payload = valid_payload()
        payload["product_stage"] = "unicorn"

        with self.assertRaisesRegex(IntakeValidationError, "product_stage"):
            validate_intake(payload)


if __name__ == "__main__":
    unittest.main()
