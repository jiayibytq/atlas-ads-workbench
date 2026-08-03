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

    def test_decision_contract_v2_names_progressive_workflow_statuses(self):
        rules = (ROOT / "contracts" / "decision-rules.yaml").read_text("utf-8")
        schema = json.loads((ROOT / "contracts" / "output-schema.json").read_text("utf-8"))

        self.assertIn("contract_version: 2", rules)
        self.assertIn("selected_ad_modules", rules)
        self.assertIn("not_applicable", rules)
        statuses = schema["$defs"]["decision"]["properties"]["status"]["enum"]
        for status in (
            "not_applicable",
            "verification_required",
            "constraint_conflict",
        ):
            self.assertIn(status, statuses)

    def test_decision_contract_document_explains_that_rules_are_not_data_connections(self):
        document = (ROOT / "docs" / "architecture" / "decision-contract.md").read_text("utf-8")

        for expected_text in (
            "decision-rules.yaml",
            "output-schema.json",
            "不会连接 Amazon",
            "不生成策略结论",
        ):
            self.assertIn(expected_text, document)

    def test_public_docs_explain_the_demo_report_boundary(self):
        readme = (ROOT / "README.md").read_text("utf-8")
        skill = (ROOT / "SKILL.md").read_text("utf-8")

        for expected_text in (
            "生成演示报告",
            "30% / 45% / 25%",
            "固定演示数据",
            "不可直接执行",
            "模型调用：0",
        ):
            self.assertIn(expected_text, readme)
            self.assertIn(expected_text, skill)

    def test_readme_describes_the_current_demo_budget_flow(self):
        readme = (ROOT / "README.md").read_text("utf-8")

        for expected_text in (
            "当前演示闭环",
            "确定性公式",
            "30% / 45% / 25%",
        ):
            self.assertIn(expected_text, readme)

    def test_public_docs_explain_the_progressive_seller_workflow(self):
        readme = (ROOT / "README.md").read_text("utf-8")
        skill = (ROOT / "SKILL.md").read_text("utf-8")
        decision_contract = (
            ROOT / "docs" / "architecture" / "decision-contract.md"
        ).read_text("utf-8")

        workflow = "基础输入 → 预算与可行性 → 选择广告目标 → 补充证据 → 审核并生成"
        self.assertIn(workflow, readme)
        self.assertIn(workflow, skill)
        self.assertIn("未选择的广告类型不执行 Gate", decision_contract)
        self.assertIn("卖家已填写不等于外部已验证", decision_contract)

    def test_decision_contract_scopes_campaign_prohibitions_to_strategy_advice(self):
        document = (ROOT / "docs" / "architecture" / "decision-contract.md").read_text(
            "utf-8"
        )

        self.assertIn("真实或策略 Campaign 建议", document)
        self.assertIn("固定演示分配", document)
        self.assertIn("仅用于证明 UI 流程", document)
        self.assertIn("不是市场证据，也不可直接执行", document)

    def test_public_docs_explain_skill_update_lifecycle(self):
        readme = (ROOT / "README.md").read_text("utf-8")
        contributing = (ROOT / "CONTRIBUTING.md").read_text("utf-8")

        for expected_text in (
            "Git checkout",
            "请帮我更新 Atlas Ads skill",
            "python3 scripts/update_skill.py --check",
            "python3 scripts/update_skill.py --update",
            "未提交的本地修改",
            "旧版本",
            "新开一个会话",
        ):
            self.assertIn(expected_text, readme)

        for expected_text in (
            "验证",
            "push",
            "main",
            "skill-source.json",
        ):
            self.assertIn(expected_text, contributing)


if __name__ == "__main__":
    unittest.main()
