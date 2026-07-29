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


if __name__ == "__main__":
    unittest.main()
