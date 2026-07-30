from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atlas_ads_workbench.evidence import EvidenceValidationError, normalize_evidence_context


class EvidenceContextTests(unittest.TestCase):
    def test_normalizes_confirmed_seller_evidence_with_provenance(self):
        context = normalize_evidence_context({
            "campaign_goal": {"value": "cross_sell", "status": "confirmed"}
        }, "2026-07-30T10:00:00+08:00")

        self.assertEqual(context["campaign_goal"]["source"], "seller_input")
        self.assertEqual(context["campaign_goal"]["captured_at"], "2026-07-30T10:00:00+08:00")
        self.assertEqual(context["campaign_goal"]["status"], "confirmed")

    def test_rejects_verified_claim_without_an_external_source(self):
        with self.assertRaisesRegex(EvidenceValidationError, "verified"):
            normalize_evidence_context({
                "brand_registry_status": {"value": "enrolled", "status": "verified"}
            }, "2026-07-30T10:00:00+08:00")

    def test_preserves_mcp_evidence_when_it_has_source_and_timestamp(self):
        context = normalize_evidence_context({
            "display_eligibility_status": {
                "value": "eligible",
                "status": "verified",
                "source": "amazon_ads_mcp",
                "captured_at": "2026-07-30T09:30:00+08:00"
            }
        }, "2026-07-30T10:00:00+08:00")

        self.assertEqual(context["display_eligibility_status"]["source"], "amazon_ads_mcp")


if __name__ == "__main__":
    unittest.main()
