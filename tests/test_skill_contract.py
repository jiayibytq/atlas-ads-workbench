from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
    def test_skill_has_valid_triggering_metadata_and_local_boundary(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("name: atlas-ads-workbench", skill)
        self.assertIn("description:", skill)
        self.assertIn("scripts/launch_workbench.py", skill)
        self.assertIn("不会连接 Amazon", skill)
        self.assertIn("不会上传数据", skill)
        self.assertIn("生成 SP 演示报告", skill)
        self.assertIn("打开工作台", skill)

    def test_skill_allows_fixed_demo_budgets_without_calling_them_real_or_executable(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("固定演示预算允许展示", skill)
        self.assertIn("不得描述为真实或可执行", skill)
        self.assertIn("真实预算仍需授权证据", skill)

    def test_skill_has_required_coaching_structure_and_inviting_input(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("type: workflow", skill.split("---", 2)[1])
        for heading in (
            "## Purpose",
            "## Input",
            "## Key Concepts",
            "## Application",
            "## Examples",
            "## Common Pitfalls",
            "## References",
        ):
            self.assertIn(heading, skill)
        self.assertIn("零输入", skill)
        self.assertIn("部分输入", skill)
        self.assertIn("inline", skill)
        self.assertIn("示例调用", skill)
        self.assertIn("为什么固定演示预算不是真实建议", skill)
        self.assertIn("缺少授权账户数据", skill)

    def test_skill_does_not_overclaim_current_external_evidence_capability(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("当前版本只记录卖家已填写的 `confirmed` 资料", skill)
        self.assertIn("等待外部验证", skill)
        self.assertIn("未来接入授权适配器后", skill)


if __name__ == "__main__":
    unittest.main()
