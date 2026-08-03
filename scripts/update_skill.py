#!/usr/bin/env python3
"""Safely check or fast-forward an installed Atlas Ads skill checkout."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


def git(repository, *arguments, check=True):
    """Run Git without shell interpolation and return its completed process."""
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=check,
        text=True,
        capture_output=True,
    )


def git_output(repository, *arguments):
    return git(repository, *arguments).stdout.strip()


def empty_result():
    return {
        "status": "error",
        "current_commit": None,
        "target_commit": None,
        "source": None,
        "validation": {"status": "not_run"},
        "changed": [],
    }


def discover_repository(path):
    return Path(git_output(path, "rev-parse", "--show-toplevel"))


def load_source(repository):
    metadata_path = repository / "skill-source.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    remote = metadata.get("remote")
    ref = metadata.get("ref")
    if not isinstance(remote, str) or not remote or not isinstance(ref, str) or not ref:
        return None
    if git(repository, "check-ref-format", "--branch", ref, check=False).returncode:
        return None
    remote_url = git(repository, "remote", "get-url", remote, check=False)
    if remote_url.returncode:
        return None
    return {
        "remote": remote,
        "ref": ref,
        "url": remote_url.stdout.strip(),
        "repository": metadata.get("repository"),
        "channel": metadata.get("channel", "stable"),
    }


def validation_command(repository):
    if (repository / "tests").is_dir():
        return [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
    return [sys.executable, "-m", "compileall", "-q", "."]


def validate_target(repository, target_commit):
    command = None
    with TemporaryDirectory(prefix="atlas-ads-update-") as temporary_directory:
        worktree = Path(temporary_directory) / "candidate"
        added = git(repository, "worktree", "add", "--detach", str(worktree), target_commit, check=False)
        if added.returncode:
            return {
                "status": "failed",
                "reason": "could_not_create_validation_worktree",
                "output": added.stderr.strip(),
            }
        try:
            command = validation_command(worktree)
            completed = subprocess.run(command, cwd=worktree, text=True, capture_output=True)
            if completed.returncode:
                return {
                    "status": "failed",
                    "reason": "candidate_validation_failed",
                    "command": command,
                    "output": (completed.stdout + completed.stderr).strip(),
                }
            return {"status": "passed", "command": command}
        finally:
            git(repository, "worktree", "remove", "--force", str(worktree), check=False)


def run_update(path, mode):
    """Check or safely fast-forward the checkout containing *path*."""
    result = empty_result()
    try:
        repository = discover_repository(path)
        result["current_commit"] = git_output(repository, "rev-parse", "HEAD")
    except (OSError, subprocess.CalledProcessError):
        result["status"] = "refused_source"
        return result

    if git(repository, "status", "--porcelain", "--untracked-files=all").stdout.strip():
        result["status"] = "refused_dirty"
        return result

    source = load_source(repository)
    if source is None:
        result["status"] = "refused_source"
        return result
    result["source"] = source

    fetched = git(repository, "fetch", "--no-tags", source["remote"], source["ref"], check=False)
    if fetched.returncode:
        result["status"] = "refused_source"
        return result
    target = git(repository, "rev-parse", "FETCH_HEAD", check=False)
    if target.returncode:
        result["status"] = "refused_source"
        return result
    result["target_commit"] = target.stdout.strip()

    if result["target_commit"] == result["current_commit"]:
        result["status"] = "up_to_date"
        return result

    is_ancestor = git(
        repository,
        "merge-base",
        "--is-ancestor",
        result["current_commit"],
        result["target_commit"],
        check=False,
    )
    if is_ancestor.returncode:
        result["status"] = "refused_diverged"
        return result
    result["changed"] = git_output(
        repository, "diff", "--name-only", result["current_commit"], result["target_commit"]
    ).splitlines()

    if mode == "check":
        result["status"] = "update_available"
        return result

    result["validation"] = validate_target(repository, result["target_commit"])
    if result["validation"]["status"] != "passed":
        result["status"] = "validation_failed"
        return result

    merged = git(repository, "merge", "--ff-only", result["target_commit"], check=False)
    if merged.returncode:
        result["status"] = "refused_diverged"
        return result
    result["status"] = "updated"
    return result


def format_result(result):
    source = result["source"] or {}
    lines = [
        "Skill update status: %s" % result["status"],
        "Current commit: %s" % (result["current_commit"] or "unknown"),
        "Target commit: %s" % (result["target_commit"] or "unknown"),
        "Source: %s" % (source.get("url") or "unknown"),
        "Validation: %s" % result["validation"]["status"],
    ]
    if result["changed"]:
        lines.append("Changed: %s" % ", ".join(result["changed"]))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Check or safely update Atlas Ads skill files.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Check for an update without changing HEAD.")
    mode.add_argument("--update", action="store_true", help="Validate then fast-forward to the update.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable update evidence.")
    arguments = parser.parse_args()

    result = run_update(Path(__file__).resolve(), "check" if arguments.check else "update")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True) if arguments.json else format_result(result))
    return 0 if result["status"] in {"up_to_date", "update_available", "updated"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
