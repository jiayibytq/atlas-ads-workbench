from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "assets" / "workbench.html"


class WorkbenchAssetContractTests(unittest.TestCase):
    def test_page_names_the_phase_one_boundary_and_core_actions(self):
        page = ASSET.read_text(encoding="utf-8")

        for expected_text in (
            "第一阶段：仅保存需求",
            "市场",
            "产品阶段",
            "保存草稿",
            "计算预算与可行性",
            "开始本次搭建",
            "本次运行快照",
            "计算依据",
            "可调整杠杆",
            "预览广告架构",
            "检查信息完整度",
            "SB-GATE-001",
            "SD-GATE-001",
            "广告架构草案",
            "需要人工复核",
            "不会连接 Amazon",
            "不会上传数据",
        ):
            self.assertIn(expected_text, page)

    def test_page_uses_a_session_fragment_without_persisting_the_token(self):
        page = ASSET.read_text(encoding="utf-8")

        self.assertIn("location.hash", page)
        self.assertIn("X-Atlas-Session", page)
        self.assertNotIn("localStorage", page)


if __name__ == "__main__":
    unittest.main()
