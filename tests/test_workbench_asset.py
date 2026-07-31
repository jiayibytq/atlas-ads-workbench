from pathlib import Path
from html.parser import HTMLParser
import unittest


ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "assets" / "workbench.html"


class InputAttributeParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inputs = {}

    def handle_starttag(self, tag, attrs):
        if tag != "input":
            return
        attributes = dict(attrs)
        if name := attributes.get("name"):
            self.inputs[name] = attributes


class WorkbenchAssetContractTests(unittest.TestCase):
    def test_page_reveals_the_progressive_seller_workflow_in_order(self):
        page = ASSET.read_text(encoding="utf-8")

        section_ids = [
            'id="basic-intake"',
            'id="feasibility-result"',
            'id="module-selection"',
            'id="strategy-evidence"',
            'id="review-plan"',
        ]
        positions = [page.index(section_id) for section_id in section_ids]
        self.assertEqual(positions, sorted(positions))

        for text in (
            "计算目标预算",
            "目标月销售额",
            "月广告预算上限",
            "日广告预算上限",
            "选择下一步广告目标",
            "暂时只确认总预算",
            "完善广告框架资料",
        ):
            self.assertIn(text, page)

    def test_sb_and_sd_evidence_sections_start_hidden(self):
        page = ASSET.read_text(encoding="utf-8")

        self.assertIn('data-module-evidence="sb" hidden', page)
        self.assertIn('data-module-evidence="sd" hidden', page)
        self.assertIn('data-module-evidence="sd_cross_sell" hidden', page)

    def test_primary_flow_does_not_render_raw_gate_statuses(self):
        page = ASSET.read_text(encoding="utf-8")

        self.assertNotIn("ready_for_rule_evaluation</b>", page)
        self.assertIn("查看规则与证据详情", page)

    def test_page_uses_a_session_fragment_without_persisting_the_token(self):
        page = ASSET.read_text(encoding="utf-8")

        self.assertIn("location.hash", page)
        self.assertIn("X-Atlas-Session", page)
        self.assertNotIn("localStorage", page)

    def test_report_renders_server_transparency_fields_and_freezes_sidebar_status(self):
        page = ASSET.read_text(encoding="utf-8")

        for expected_contract in (
            "report.budget_basis",
            "report.allocation_rule",
            "report.external_data_used",
            "report.model_calls",
            "report.is_executable",
            "report.feasibility_status",
            'id="run-status"',
            "已冻结演示报告",
        ):
            self.assertIn(expected_contract, page)

    def test_report_table_and_focus_contract_are_accessible(self):
        page = ASSET.read_text(encoding="utf-8")

        self.assertIn(
            'class="report-table-wrap" tabindex="0" aria-label="演示广告预算表，可横向滚动"',
            page,
        )
        self.assertIn("<caption>演示广告预算分配</caption>", page)
        self.assertEqual(page.count('<th scope="col">'), 6)
        self.assertIn('id="demo-report" aria-live="polite" tabindex="-1"', page)
        self.assertIn("section.focus({preventScroll:true})", page)

    def test_benchmark_cvr_accepts_decimal_percentage_values(self):
        parser = InputAttributeParser()
        parser.feed(ASSET.read_text(encoding="utf-8"))

        self.assertEqual(parser.inputs["benchmark_cvr_percent"].get("step"), "0.01")


if __name__ == "__main__":
    unittest.main()
