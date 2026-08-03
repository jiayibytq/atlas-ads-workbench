from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ModelRoutingContractTests(unittest.TestCase):
    def test_contract_defines_all_task_levels_and_exact_runtime_models(self):
        contract = (ROOT / "contracts" / "model-routing.yaml").read_text(encoding="utf-8")

        self.assertIn("L0:", contract)
        self.assertIn("L1:", contract)
        self.assertIn("L2:", contract)
        self.assertIn("L3:", contract)
        self.assertIn("model: none", contract)
        self.assertIn("model: gpt-5.6-terra", contract)
        self.assertIn("model: gpt-5.6-sol", contract)

    def test_contract_caps_sol_delegation_at_three_independent_luna_agents(self):
        contract = (ROOT / "contracts" / "model-routing.yaml").read_text(encoding="utf-8")

        self.assertIn("max_luna_subagents: 3", contract)
        self.assertIn("independent", contract)
        self.assertIn("read-only or isolated", contract)

    def test_contract_reserves_final_review_and_writes_for_sol(self):
        contract = (ROOT / "contracts" / "model-routing.yaml").read_text(encoding="utf-8")

        self.assertIn("final_review: sol", contract)
        self.assertIn("writes: sol", contract)
        self.assertIn("synthesis: sol", contract)

    def test_contract_requires_sol_and_user_approval_for_external_or_executable_actions(self):
        contract = (ROOT / "contracts" / "model-routing.yaml").read_text(encoding="utf-8")

        self.assertIn("requires_model: gpt-5.6-sol", contract)
        self.assertIn("requires_user_approval: true", contract)
        for action in (
            "real seller data",
            "external MCP/API access",
            "account mutations",
            "executable campaign actions",
        ):
            self.assertIn(action, contract)

    def test_policy_and_skill_explain_routing_and_restart_after_update(self):
        policy = (ROOT / "docs" / "model-routing-policy.md").read_text(encoding="utf-8")
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("反模式", policy)
        self.assertIn("L0", policy)
        self.assertIn("Luna", policy)
        self.assertIn("Sol", policy)
        self.assertIn("更新 Skill", skill)
        self.assertIn("请帮我更新 Atlas Ads skill", skill)
        self.assertIn("新开一个会话", skill)


if __name__ == "__main__":
    unittest.main()
