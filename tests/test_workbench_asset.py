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
    def assert_appears_in_order(self, source, *markers):
        positions = [source.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))

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

    def test_calculation_scrolls_to_feasibility_and_reveals_modules_without_second_scroll(self):
        page = ASSET.read_text(encoding="utf-8")
        handler = page[page.index("form.addEventListener('submit'"):page.index(
            "document.querySelector('#continue-to-evidence')"
        )]

        self.assertIn("function revealStep(id, shouldScroll=true)", page)
        self.assertIn("if(shouldScroll)", page)
        self.assert_appears_in_order(
            handler,
            "renderFeasibility(result);",
            "revealStep('feasibility-result');",
            "revealStep('module-selection', false);",
        )

    def test_evidence_controls_belong_to_validated_form_and_hidden_controls_are_disabled(self):
        page = ASSET.read_text(encoding="utf-8")
        evidence_form = page[page.index('<form id="evidence-form"'):page.index(
            "</form>", page.index('<form id="evidence-form"')
        )]

        for field in (
            'name="brand_registry_status"',
            'name="sd_campaign_goal"',
            'name="contribution_margin"',
        ):
            self.assertIn(field, evidence_form)
        self.assertIn('id="review-evidence"', evidence_form)
        self.assertIn('type="submit"', evidence_form)
        self.assertIn("evidenceForm.addEventListener('submit'", page)
        self.assertIn("if(!evidenceForm.reportValidity())", page)
        self.assertIn(
            "workflowState.selectedModules.has(section.dataset.moduleEvidence)", page
        )
        self.assertIn("section.hidden = !selected", page)
        self.assertIn("control.disabled = !selected", page)
        self.assertIn("syncEvidenceSections();", page)

    def test_advanced_modules_are_mutually_exclusive_but_sp_can_remain_selected(self):
        page = ASSET.read_text(encoding="utf-8")

        self.assertIn("SB、SD 再营销、SD 老品导流每次只能选择一种；可同时选择 SP。", page)
        self.assertIn("{id:'sp', title:'SP 基础投放', advanced:false", page)
        for module_id in ("sb", "sd", "sd_cross_sell"):
            self.assertIn(f"{{id:'{module_id}'", page)
        self.assertGreaterEqual(page.count("advanced:true"), 3)
        self.assertIn("function enforceAdvancedModuleExclusivity(changedInput)", page)
        self.assertIn("other.checked = false", page)
        self.assertIn("enforceAdvancedModuleExclusivity(input)", page)

    def test_recalculation_resets_downstream_state_before_feasibility_request(self):
        page = ASSET.read_text(encoding="utf-8")
        handler = page[page.index("form.addEventListener('submit'"):page.index(
            "document.querySelector('#continue-to-evidence')"
        )]

        self.assert_appears_in_order(
            handler,
            "resetDownstream();",
            "api('/api/feasibility'",
            "renderFeasibility(result);",
        )
        for reset_contract in (
            "workflowState.selectedModules = new Set();",
            "document.querySelector('#strategy-evidence').hidden = true;",
            "document.querySelector('#review-plan').hidden = true;",
            "document.querySelector('#selected-gate-summary').innerHTML = '';",
            "document.querySelector('#technical-gate-details').innerHTML = '';",
            "document.querySelector('#architecture-data').innerHTML = '';",
            "document.querySelector('#demo-report').classList.remove('visible');",
        ):
            self.assertIn(reset_contract, page)

    def test_endpoint_wiring_validates_evidence_before_gate_review(self):
        page = ASSET.read_text(encoding="utf-8")
        review_handler = page[page.index("evidenceForm.addEventListener('submit'"):page.index(
            "document.querySelector('#gates-button')"
        )]

        self.assert_appears_in_order(
            review_handler,
            "evidenceForm.reportValidity()",
            "evidenceContext();",
            "await checkGates();",
            "revealStep('review-plan');",
        )
        for endpoint in (
            "api('/api/feasibility'",
            "api('/api/gates'",
            "api('/api/campaign-architecture'",
            "api('/api/demo-report'",
        ):
            self.assertIn(endpoint, page)

    def test_feasibility_updates_persistent_sidebar_for_both_outcomes(self):
        page = ASSET.read_text(encoding="utf-8")
        handler = page[page.index("form.addEventListener('submit'"):page.index(
            "document.querySelector('#continue-to-evidence')"
        )]

        self.assertIn("function updateFeasibilityStatus(result)", page)
        self.assertIn("状态：目标预算已计算 · 当前假设可行", page)
        self.assertIn("状态：目标预算已计算 · 存在数值冲突", page)
        self.assert_appears_in_order(
            handler,
            "renderFeasibility(result);",
            "updateFeasibilityStatus(result);",
            "revealStep('feasibility-result');",
        )


if __name__ == "__main__":
    unittest.main()
