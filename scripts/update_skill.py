#!/usr/bin/env python3
"""Safely check or fast-forward an installed Atlas Ads skill checkout."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from urllib.parse import urlparse


def git(repository, *arguments, check=True, read_only=False):
    """Run Git without shell interpolation and return its completed process."""
    environment = None
    if read_only:
        environment = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=check,
        text=True,
        capture_output=True,
        env=environment,
    )


def git_output(repository, *arguments, read_only=False):
    return git(repository, *arguments, read_only=read_only).stdout.strip()


def empty_result():
    return {
        "status": "error",
        "current_commit": None,
        "target_commit": None,
        "source": None,
        "validation": {"status": "not_run"},
        "changed": [],
    }


def discover_repository(path, read_only=False):
    candidate = Path(path)
    if candidate.is_file():
        candidate = candidate.parent
    return Path(git_output(candidate, "rev-parse", "--show-toplevel", read_only=read_only))


def normalize_repository_url(value, repository):
    """Return a safe, comparable identity for approved Git repository URLs."""
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.strip()
    parsed = urlparse(candidate)

    if parsed.scheme == "file":
        if parsed.netloc not in {"", "localhost"} or parsed.query or parsed.fragment:
            return None
        return "local:%s" % Path(parsed.path).resolve()
    if parsed.scheme in {"https", "ssh"}:
        if not parsed.hostname or not parsed.path:
            return None
        try:
            port = parsed.port
        except ValueError:
            return None
        if parsed.query or parsed.fragment or parsed.params:
            return None
        if parsed.scheme == "https":
            if parsed.username is not None or parsed.password is not None or port not in {None, 443}:
                return None
        elif (
            parsed.password is not None
            or parsed.username not in {None, "git"}
            or port not in {None, 22}
        ):
            return None
        host = parsed.hostname.lower()
        path = parsed.path.strip("/")
        if path.endswith(".git"):
            path = path[:-4]
        if not path:
            return None
        identity = "%s/%s" % (host, path)
        return identity.lower() if host == "github.com" else identity
    if parsed.scheme:
        return None
    if ":" in candidate and "/" not in candidate.split(":", 1)[0]:
        host_part, path = candidate.split(":", 1)
        if "?" in candidate or "#" in candidate:
            return None
        if host_part.count("@") > 1:
            return None
        if "@" in host_part:
            user, host = host_part.split("@", 1)
            if user != "git":
                return None
        else:
            host = host_part
        host = host.lower()
        path = path.strip("/")
        if path.endswith(".git"):
            path = path[:-4]
        if not host or not path:
            return None
        identity = "%s/%s" % (host, path)
        return identity.lower() if host == "github.com" else identity
    local_path = Path(candidate)
    if not local_path.is_absolute():
        local_path = Path(repository) / local_path
    return "local:%s" % local_path.resolve()


def load_source(repository, read_only=False):
    metadata_path = repository / "skill-source.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(metadata, dict):
        return None

    remote = metadata.get("remote")
    ref = metadata.get("ref")
    if not isinstance(remote, str) or not remote or not isinstance(ref, str) or not ref:
        return None
    if git(
        repository, "check-ref-format", "--branch", ref, check=False, read_only=read_only
    ).returncode:
        return None
    remote_url = git(repository, "remote", "get-url", remote, check=False, read_only=read_only)
    if remote_url.returncode:
        return None
    expected_identity = normalize_repository_url(metadata.get("repository"), repository)
    remote_identity = normalize_repository_url(remote_url.stdout.strip(), repository)
    if expected_identity is None or remote_identity is None or expected_identity != remote_identity:
        return None
    return {
        "remote": remote,
        "ref": ref,
        "url": remote_identity,
        "repository": expected_identity,
        "identity": remote_identity,
        "channel": metadata.get("channel", "stable"),
    }


def resolve_target(repository, source, mode):
    """Return the candidate commit without fetching during a check-only run."""
    if mode == "check":
        remote_ref = "refs/heads/%s" % source["ref"]
        return inspect_target_read_only(repository, source, remote_ref)

    fetched = git(repository, "fetch", "--no-tags", source["remote"], source["ref"], check=False)
    if fetched.returncode:
        return None
    target = git(repository, "rev-parse", "FETCH_HEAD", check=False)
    return target.stdout.strip() if not target.returncode else None


def inspect_target_read_only(repository, source, remote_ref):
    """Fetch comparison objects only into a temporary repository for --check."""
    with TemporaryDirectory(prefix="atlas-ads-update-check-") as temporary_directory:
        object_store = Path(temporary_directory) / "comparison.git"
        cloned = git(
            repository,
            "clone",
            "--bare",
            "--no-local",
            str(repository),
            str(object_store),
            check=False,
            read_only=True,
        )
        if cloned.returncode:
            return None
        fetch_url = comparison_fetch_url(repository, source)
        if fetch_url is None:
            return None
        fetched = git(
            object_store,
            "fetch",
            "--no-tags",
            fetch_url,
            remote_ref,
            check=False,
        )
        if fetched.returncode:
            return None
        target = git(object_store, "rev-parse", "FETCH_HEAD", check=False)
        return target.stdout.strip() if not target.returncode else None


def target_fast_forwards_current_read_only(repository, source, current_commit, target_commit):
    """Compare history in a temporary clone so --check never updates the checkout."""
    with TemporaryDirectory(prefix="atlas-ads-update-ancestry-") as temporary_directory:
        object_store = Path(temporary_directory) / "comparison.git"
        cloned = git(
            repository,
            "clone",
            "--bare",
            "--no-local",
            str(repository),
            str(object_store),
            check=False,
            read_only=True,
        )
        if cloned.returncode:
            return None
        fetch_url = comparison_fetch_url(repository, source)
        if fetch_url is None:
            return None
        fetched = git(
            object_store,
            "fetch",
            "--no-tags",
            fetch_url,
            "refs/heads/%s" % source["ref"],
            check=False,
        )
        if fetched.returncode:
            return None
        target_available = git(object_store, "cat-file", "-e", "%s^{commit}" % target_commit, check=False)
        if target_available.returncode:
            return None
        relation = git(
            object_store,
            "merge-base",
            "--is-ancestor",
            current_commit,
            target_commit,
            check=False,
        )
        return relation.returncode == 0


def comparison_fetch_url(repository, source):
    """Return a safe fetch location that a temporary repository can resolve."""
    remote_url = git(
        repository,
        "remote",
        "get-url",
        source["remote"],
        check=False,
        read_only=True,
    )
    if remote_url.returncode:
        return None
    raw_url = remote_url.stdout.strip()
    if normalize_repository_url(raw_url, repository) != source["identity"]:
        return None
    if not source["identity"].startswith("local:"):
        return raw_url
    parsed = urlparse(raw_url)
    local_path = Path(parsed.path) if parsed.scheme == "file" else Path(raw_url)
    if not local_path.is_absolute():
        local_path = Path(repository) / local_path
    return str(local_path.resolve())


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
        repository = discover_repository(path, read_only=(mode == "check"))
        result["current_commit"] = git_output(
            repository, "rev-parse", "HEAD", read_only=(mode == "check")
        )
    except (OSError, subprocess.CalledProcessError):
        result["status"] = "refused_source"
        return result

    try:
        source = load_source(repository, read_only=(mode == "check"))
        if source is None:
            result["status"] = "refused_source"
            return result
        result["source"] = source

        attached = git(
            repository,
            "symbolic-ref",
            "--quiet",
            "HEAD",
            check=False,
            read_only=(mode == "check"),
        )
        if attached.returncode:
            result["status"] = "refused_detached"
            return result

        status = git(
            repository,
            "status",
            "--porcelain",
            "--untracked-files=all",
            check=False,
            read_only=(mode == "check"),
        )
        if status.returncode:
            result["status"] = "refused_unknown"
            return result
        if status.stdout.strip():
            result["status"] = "refused_dirty"
            return result

        result["target_commit"] = resolve_target(repository, source, mode)
        if not result["target_commit"]:
            result["status"] = "refused_source"
            return result

        if result["target_commit"] == result["current_commit"]:
            result["status"] = "up_to_date"
            return result

        if mode == "check":
            fast_forward = target_fast_forwards_current_read_only(
                repository, source, result["current_commit"], result["target_commit"]
            )
            if fast_forward is None:
                result["status"] = "refused_source"
            else:
                result["status"] = "update_available" if fast_forward else "refused_diverged"
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
        changed = git(
            repository,
            "diff",
            "--name-only",
            result["current_commit"],
            result["target_commit"],
            check=False,
        )
        if changed.returncode:
            result["status"] = "refused_unknown"
            return result
        result["changed"] = changed.stdout.splitlines()

        result["validation"] = validate_target(repository, result["target_commit"])
        if result["validation"]["status"] != "passed":
            result["status"] = "validation_failed"
            return result

        current_after_validation = git(repository, "rev-parse", "HEAD", check=False)
        active_status = git(repository, "status", "--porcelain", "--untracked-files=all", check=False)
        if current_after_validation.returncode or active_status.returncode:
            result["status"] = "refused_unknown"
            return result
        if current_after_validation.stdout.strip() != result["current_commit"]:
            result["status"] = "refused_diverged"
            return result
        if active_status.stdout.strip():
            result["status"] = "refused_dirty"
            return result

        merged = git(repository, "merge", "--ff-only", result["target_commit"], check=False)
        if merged.returncode:
            result["status"] = "refused_diverged"
            return result
        result["status"] = "updated"
        return result
    except (OSError, subprocess.SubprocessError, ValueError):
        result["status"] = "refused_unknown"
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

    result = run_update(Path(__file__).resolve().parent, "check" if arguments.check else "update")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True) if arguments.json else format_result(result))
    return 0 if result["status"] in {"up_to_date", "update_available", "updated"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
