import importlib.util
import json
from pathlib import Path
from shutil import copy2
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
UPDATER = ROOT / "scripts" / "update_skill.py"


def run_git(directory, *arguments):
    return subprocess.run(
        ["git", *arguments],
        cwd=directory,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def git_result(directory, *arguments):
    return subprocess.run(
        ["git", *arguments],
        cwd=directory,
        text=True,
        capture_output=True,
    )


def write_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_updater():
    spec = importlib.util.spec_from_file_location("atlas_skill_updater", UPDATER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SkillUpdaterTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.remote = self.root / "remote.git"
        self.publisher = self.root / "publisher"
        self.checkout = self.root / "installed-skill"
        run_git(self.root, "init", "--bare", str(self.remote))
        run_git(self.root, "clone", str(self.remote), str(self.publisher))
        self._configure_author(self.publisher)
        write_text(self.publisher / "skill-source.json", json.dumps({
            "repository": str(self.remote),
            "remote": "origin",
            "ref": "main",
            "channel": "stable",
        }))
        write_text(self.publisher / "tests" / "test_smoke.py", "import unittest\n\nclass SmokeTests(unittest.TestCase):\n    def test_smoke(self):\n        self.assertTrue(True)\n")
        write_text(self.publisher / "version.txt", "one\n")
        (self.publisher / "scripts").mkdir()
        copy2(UPDATER, self.publisher / "scripts" / "update_skill.py")
        self._commit_and_push(self.publisher, "initial skill")
        run_git(self.root, "clone", str(self.remote), str(self.checkout))
        self._configure_author(self.checkout)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _configure_author(self, directory):
        run_git(directory, "config", "user.email", "tests@example.invalid")
        run_git(directory, "config", "user.name", "Updater tests")

    def _commit_and_push(self, directory, message):
        run_git(directory, "add", ".")
        run_git(directory, "commit", "-m", message)
        run_git(directory, "push", "origin", "main")

    def _publish_update(self, filename="version.txt", content="two\n"):
        write_text(self.publisher / filename, content)
        self._commit_and_push(self.publisher, "publish update")
        return run_git(self.publisher, "rev-parse", "HEAD")

    def test_clean_checkout_fast_forwards_only_after_validation(self):
        updater = load_updater()
        original_head = run_git(self.checkout, "rev-parse", "HEAD")
        target_head = self._publish_update()

        result = updater.run_update(self.checkout, mode="update")

        self.assertEqual(result["status"], "updated")
        self.assertEqual(result["current_commit"], original_head)
        self.assertEqual(result["target_commit"], target_head)
        self.assertEqual(result["validation"]["status"], "passed")
        self.assertEqual(run_git(self.checkout, "rev-parse", "HEAD"), target_head)
        self.assertEqual(result["changed"], ["version.txt"])

    def test_check_reports_available_update_without_changing_head(self):
        updater = load_updater()
        original_head = run_git(self.checkout, "rev-parse", "HEAD")
        target_head = self._publish_update()
        fetch_head_before = git_result(self.checkout, "rev-parse", "--verify", "FETCH_HEAD")

        result = updater.run_update(self.checkout, mode="check")
        fetch_head_after = git_result(self.checkout, "rev-parse", "--verify", "FETCH_HEAD")

        self.assertEqual(result["status"], "update_available")
        self.assertEqual(result["target_commit"], target_head)
        self.assertEqual(result["validation"]["status"], "not_run")
        self.assertEqual(run_git(self.checkout, "rev-parse", "HEAD"), original_head)
        self.assertEqual(fetch_head_after.returncode, fetch_head_before.returncode)
        self.assertEqual(fetch_head_after.stdout, fetch_head_before.stdout)

    def test_cli_check_and_update_return_json_evidence(self):
        target_head = self._publish_update()
        command = [sys.executable, self.checkout / "scripts" / "update_skill.py"]

        checked = subprocess.run(
            [*command, "--check", "--json"], text=True, capture_output=True
        )

        self.assertEqual(checked.returncode, 0, checked.stderr)
        check_result = json.loads(checked.stdout)
        self.assertEqual(check_result["status"], "update_available")
        self.assertEqual(check_result["target_commit"], target_head)

        updated = subprocess.run(
            [*command, "--update", "--json"], text=True, capture_output=True
        )

        self.assertEqual(updated.returncode, 0, updated.stderr)
        update_result = json.loads(updated.stdout)
        self.assertEqual(update_result["status"], "updated")
        self.assertEqual(update_result["target_commit"], target_head)
        self.assertEqual(run_git(self.checkout, "rev-parse", "HEAD"), target_head)

    def test_dirty_checkout_is_refused_without_changing_head(self):
        updater = load_updater()
        original_head = run_git(self.checkout, "rev-parse", "HEAD")
        self._publish_update()
        write_text(self.checkout / "local-note.txt", "keep me\n")

        result = updater.run_update(self.checkout, mode="update")

        self.assertEqual(result["status"], "refused_dirty")
        self.assertEqual(run_git(self.checkout, "rev-parse", "HEAD"), original_head)

    def test_diverged_history_is_refused_without_changing_head(self):
        updater = load_updater()
        write_text(self.checkout / "local-only.txt", "local\n")
        run_git(self.checkout, "add", "local-only.txt")
        run_git(self.checkout, "commit", "-m", "local change")
        original_head = run_git(self.checkout, "rev-parse", "HEAD")
        self._publish_update()

        result = updater.run_update(self.checkout, mode="update")

        self.assertEqual(result["status"], "refused_diverged")
        self.assertEqual(run_git(self.checkout, "rev-parse", "HEAD"), original_head)

    def test_missing_remote_or_ref_is_refused_without_changing_head(self):
        updater = load_updater()
        original_head = run_git(self.checkout, "rev-parse", "HEAD")
        run_git(self.checkout, "remote", "remove", "origin")

        missing_remote = updater.run_update(self.checkout, mode="update")

        self.assertEqual(missing_remote["status"], "refused_source")
        self.assertEqual(run_git(self.checkout, "rev-parse", "HEAD"), original_head)

        run_git(self.checkout, "remote", "add", "origin", str(self.remote))
        write_text(self.checkout / "skill-source.json", json.dumps({
            "repository": str(self.remote),
            "remote": "origin",
            "ref": "not-a-branch",
        }))
        run_git(self.checkout, "add", "skill-source.json")
        run_git(self.checkout, "commit", "-m", "configure an unavailable source")
        invalid_source_head = run_git(self.checkout, "rev-parse", "HEAD")

        missing_ref = updater.run_update(self.checkout, mode="update")

        self.assertEqual(missing_ref["status"], "refused_source")
        self.assertEqual(run_git(self.checkout, "rev-parse", "HEAD"), invalid_source_head)

    def test_repository_identity_mismatch_is_refused_before_fetch_or_merge(self):
        updater = load_updater()
        original_head = run_git(self.checkout, "rev-parse", "HEAD")
        self._publish_update()
        untrusted_remote = self.root / "untrusted.git"
        run_git(self.root, "init", "--bare", str(untrusted_remote))
        fetch_head_before = git_result(self.checkout, "rev-parse", "--verify", "FETCH_HEAD")
        run_git(self.checkout, "remote", "set-url", "origin", str(untrusted_remote))

        result = updater.run_update(self.checkout, mode="update")
        fetch_head_after = git_result(self.checkout, "rev-parse", "--verify", "FETCH_HEAD")

        self.assertEqual(result["status"], "refused_source")
        self.assertIsNone(result["target_commit"])
        self.assertEqual(run_git(self.checkout, "rev-parse", "HEAD"), original_head)
        self.assertEqual(fetch_head_after.returncode, fetch_head_before.returncode)
        self.assertEqual(fetch_head_after.stdout, fetch_head_before.stdout)

    def test_normalizes_common_github_repository_url_forms(self):
        updater = load_updater()
        variants = (
            "https://github.com/jiayibytq/atlas-ads-workbench.git",
            "https://github.com/jiayibytq/atlas-ads-workbench",
            "git@github.com:jiayibytq/atlas-ads-workbench.git",
            "ssh://git@github.com/jiayibytq/atlas-ads-workbench.git",
        )

        normalized = {
            updater.normalize_repository_url(value, self.checkout) for value in variants
        }

        self.assertEqual(normalized, {"github.com/jiayibytq/atlas-ads-workbench"})

    def test_validation_failure_preserves_active_head(self):
        updater = load_updater()
        original_head = run_git(self.checkout, "rev-parse", "HEAD")
        target_head = self._publish_update(
            "tests/test_failing_update.py",
            "import unittest\n\nclass FailingUpdateTests(unittest.TestCase):\n    def test_failure(self):\n        self.fail('invalid release')\n",
        )

        result = updater.run_update(self.checkout, mode="update")

        self.assertEqual(result["status"], "validation_failed")
        self.assertEqual(result["target_commit"], target_head)
        self.assertEqual(result["validation"]["status"], "failed")
        self.assertEqual(run_git(self.checkout, "rev-parse", "HEAD"), original_head)

    def test_detached_checkout_is_refused_before_fetch_or_merge(self):
        updater = load_updater()
        original_head = run_git(self.checkout, "rev-parse", "HEAD")
        self._publish_update()
        fetch_head_before = git_result(self.checkout, "rev-parse", "--verify", "FETCH_HEAD")
        run_git(self.checkout, "checkout", "--detach")

        result = updater.run_update(self.checkout, mode="update")
        fetch_head_after = git_result(self.checkout, "rev-parse", "--verify", "FETCH_HEAD")

        self.assertEqual(result["status"], "refused_detached")
        self.assertEqual(run_git(self.checkout, "rev-parse", "HEAD"), original_head)
        self.assertEqual(fetch_head_after.returncode, fetch_head_before.returncode)
        self.assertEqual(fetch_head_after.stdout, fetch_head_before.stdout)

    def test_symlink_and_linked_worktree_resolve_to_their_own_checkout(self):
        updater = load_updater()
        target_head = self._publish_update()
        symlink = self.root / "atlas-skill-link"
        symlink.symlink_to(self.checkout, target_is_directory=True)

        checked = updater.run_update(symlink, mode="check")

        self.assertEqual(checked["status"], "update_available")
        self.assertEqual(checked["target_commit"], target_head)

        linked_worktree = self.root / "linked-worktree"
        run_git(
            self.checkout,
            "worktree",
            "add",
            "-b",
            "linked-skill-update",
            str(linked_worktree),
            "HEAD",
        )

        updated = updater.run_update(linked_worktree, mode="update")

        self.assertEqual(updated["status"], "updated")
        self.assertEqual(run_git(linked_worktree, "rev-parse", "HEAD"), target_head)


if __name__ == "__main__":
    unittest.main()
