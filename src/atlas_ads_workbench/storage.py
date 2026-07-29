"""Local, atomic persistence for drafts and immutable intake runs."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
from typing import Any, Dict, Mapping, Optional


class StorageError(RuntimeError):
    """Raised when local workbench data cannot be safely read or written."""


class LocalStorage:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.drafts_dir = self.root / "drafts"
        self.runs_dir = self.root / "runs"
        self.draft_path = self.drafts_dir / "current-intake.json"

    @staticmethod
    def _canonical_json(payload: Mapping[str, Any]) -> bytes:
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")

    @staticmethod
    def _write_json_atomically(path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_name(".%s.%s.tmp" % (path.name, secrets.token_hex(4)))
        try:
            temporary_path.write_text(
                json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            temporary_path.replace(path)
        except OSError as error:
            temporary_path.unlink(missing_ok=True)
            raise StorageError("could not write %s" % path.name) from error

    @staticmethod
    def _read_json(path: Path, label: str) -> Dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise StorageError("%s was not found" % label)
        except (OSError, json.JSONDecodeError) as error:
            raise StorageError("%s could not be read; remove or repair the file" % label) from error
        if not isinstance(payload, dict):
            raise StorageError("%s must contain a JSON object" % label)
        return payload

    def save_draft(self, intake: Mapping[str, Any]) -> None:
        self._write_json_atomically(self.draft_path, intake)

    def load_draft(self) -> Optional[Dict[str, Any]]:
        if not self.draft_path.exists():
            return None
        return self._read_json(self.draft_path, "draft")

    def create_run(
        self,
        intake: Mapping[str, Any],
        workbench_version: str,
        decision_plan: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        run_id = "%s-%s" % (
            datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"),
            secrets.token_hex(3),
        )
        run_dir = self.runs_dir / run_id
        if run_dir.exists():
            raise StorageError("run_id collision; try again")

        canonical_intake = self._canonical_json(intake)
        manifest = {
            "run_id": run_id,
            "created_at": created_at,
            "status": "intake_captured",
            "workbench_version": workbench_version,
            "intake_sha256": hashlib.sha256(canonical_intake).hexdigest(),
            "data_source": "seller_input",
            "external_data_used": False,
            "model_calls": 0,
            "phase_notice": "No Amazon, MCP, or model data was used in this run.",
        }
        if decision_plan is not None:
            manifest["decision_plan_sha256"] = hashlib.sha256(
                self._canonical_json(decision_plan)
            ).hexdigest()

        try:
            run_dir.mkdir(parents=True, exist_ok=False)
            self._write_json_atomically(run_dir / "intake.json", intake)
            if decision_plan is not None:
                self._write_json_atomically(run_dir / "decision-plan.json", decision_plan)
            self._write_json_atomically(run_dir / "manifest.json", manifest)
        except (OSError, StorageError) as error:
            raise StorageError("could not create immutable run") from error
        return manifest

    def load_run(self, run_id: str) -> Dict[str, Dict[str, Any]]:
        if not run_id or Path(run_id).name != run_id:
            raise StorageError("invalid run_id")
        run_dir = self.runs_dir / run_id
        result = {
            "intake": self._read_json(run_dir / "intake.json", "run intake"),
            "manifest": self._read_json(run_dir / "manifest.json", "run manifest"),
        }
        decision_path = run_dir / "decision-plan.json"
        if decision_path.exists():
            result["decision_plan"] = self._read_json(decision_path, "decision plan")
        return result
