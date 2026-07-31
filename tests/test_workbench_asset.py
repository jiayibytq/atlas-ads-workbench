from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "assets" / "workbench.html"


class WorkbenchAssetContractTests(unittest.TestCase):
    def test_page_exposes_the_demo_report_happy_path(self):
        page = ASSET.read_text(encoding="utf-8")

        for expected_text in (
            "生成演示报告",
            "演示广告搭建报告",
            "广告类型",
            "广告目的",
            "预算占比",
            "日预算",
            "具体投放词 / ASIN",
            "投放类型",
            "确定性说明",
            "不可直接执行",
            "/api/demo-report",
            "renderDemoReport",
            "scrollIntoView",
            "保存草稿",
            "查看计算详情",
            "不会连接 Amazon",
            "不会上传数据",
        ):
            self.assertIn(expected_text, page)

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


if __name__ == "__main__":
    unittest.main()
