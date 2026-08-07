from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def parse_minimal_yaml_mapping(text):
    """Parse the scalar mappings used by the routing contract without PyYAML.

    The contract deliberately keeps its policy fields to mappings, scalar values,
    and explanatory lists. Lists are ignored here because these tests verify the
    executable routing fields, not prose examples.
    """
    root = {}
    stack = [(-1, root)]

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith(("#", "- ")):
            continue
        indentation = len(raw_line) - len(raw_line.lstrip())
        stripped = raw_line.strip()
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        value = value.strip()
        while indentation <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if not value:
            child = {}
            parent[key] = child
            stack.append((indentation, child))
        elif value == "true":
            parent[key] = True
        elif value == "false":
            parent[key] = False
        elif value.isdigit():
            parent[key] = int(value)
        else:
            parent[key] = value.strip('"')

    return root


class ModelRoutingContractTests(unittest.TestCase):
    def setUp(self):
        self.contract_text = (ROOT / "contracts" / "model-routing.yaml").read_text(encoding="utf-8")
        self.contract = parse_minimal_yaml_mapping(self.contract_text)

    def test_contract_defines_all_task_levels_and_exact_runtime_models(self):
        task_levels = self.contract["task_levels"]

        self.assertEqual(task_levels["L0"]["model"], "none")
        self.assertEqual(task_levels["L1"]["model"], "gpt-5.6-terra")
        self.assertEqual(task_levels["L2"]["model"], "gpt-5.6-sol")
        self.assertEqual(task_levels["L3"]["model"], "gpt-5.6-sol")

    def test_contract_caps_sol_delegation_at_three_independent_luna_agents(self):
        delegation = self.contract["delegation"]

        self.assertEqual(delegation["coordinator"], "sol")
        self.assertEqual(delegation["max_luna_subagents"], 3)
        self.assertIn("independent", delegation["allowed_luna_work"])
        self.assertIn("read-only", delegation["allowed_luna_work"])
        self.assertIn("isolated implementation", delegation["allowed_luna_work"])

    def test_contract_allows_isolated_luna_implementation_but_reserves_integration_and_review_for_sol(self):
        delegation = self.contract["delegation"]

        self.assertIn("isolated implementation", delegation["allowed_luna_work"])
        self.assertEqual(delegation["sol_owns"]["synthesis"], "sol")
        self.assertEqual(delegation["sol_owns"]["integration"], "sol")
        self.assertEqual(delegation["sol_owns"]["final_review"], "sol")
        self.assertEqual(delegation["sol_owns"]["external_actions"], "sol")
        self.assertEqual(delegation["sol_owns"]["user_approval"], "sol")

    def test_contract_requires_sol_and_user_approval_for_external_or_executable_actions(self):
        level = self.contract["task_levels"]["L3"]

        self.assertEqual(level["requires_model"], "gpt-5.6-sol")
        self.assertIs(level["requires_user_approval"], True)
        self.assertIn("local seller-provided form inputs", self.contract_text)
        self.assertIn("external MCP/API access", self.contract_text)
        self.assertIn("account mutations", self.contract_text)
        self.assertIn("executable campaign actions", self.contract_text)

    def test_policy_and_skill_explain_routing_and_restart_after_update(self):
        policy = (ROOT / "docs" / "model-routing-policy.md").read_text(encoding="utf-8")
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("反模式", policy)
        self.assertIn("L0", policy)
        self.assertIn("Luna", policy)
        self.assertIn("Sol", policy)
        self.assertIn("隔离实现", policy)
        self.assertIn("集成", policy)
        self.assertIn("本地表单中主动填写", policy)
        self.assertIn("更新 Skill", skill)
        self.assertIn("请帮我更新 Atlas Ads skill", skill)
        self.assertIn("新开一个会话", skill)
        self.assertIn("隔离实现", skill)
        self.assertIn("集成", skill)


if __name__ == "__main__":
    unittest.main()
