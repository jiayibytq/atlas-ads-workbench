from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RepositoryContractTests(unittest.TestCase):
    def test_open_source_baseline_files_exist(self):
        for relative_path in (
            "README.md",
            "LICENSE",
            "CONTRIBUTING.md",
            ".gitignore",
            ".github/workflows/test.yml",
        ):
            self.assertTrue((ROOT / relative_path).is_file(), relative_path)

    def test_readme_declares_local_data_boundary(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("不会连接 Amazon", readme)
        self.assertIn("不会上传数据", readme)

    def test_gitignore_excludes_local_and_secret_data(self):
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".atlas-ads-workbench/", ignored)
        self.assertIn(".env", ignored)


if __name__ == "__main__":
    unittest.main()
