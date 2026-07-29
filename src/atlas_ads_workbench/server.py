"""A token-protected HTTP boundary for the localhost workbench."""

from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlsplit

from .feasibility import calculate_feasibility
from .models import IntakeValidationError, validate_intake
from .storage import LocalStorage, StorageError


class AtlasHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


class WorkbenchRequestHandler(BaseHTTPRequestHandler):
    server_version = "AtlasAdsWorkbench"
    sys_version = ""

    def log_message(self, format: str, *args: Any) -> None:
        # Deliberately omit headers and bodies: they may contain seller inputs
        # or a session token. BaseHTTPRequestHandler's default logging is also
        # replaced to keep output predictable for the launcher.
        return

    @property
    def app_server(self) -> AtlasHTTPServer:
        return self.server  # type: ignore[return-value]

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def _error(self, status: int, code: str, message: str) -> None:
        self._send_json(status, {"code": code, "message": message})

    def _send_page(self) -> None:
        try:
            encoded = self.app_server.asset_path.read_bytes()
        except OSError:
            self._error(500, "asset_error", "The local workbench page is unavailable.")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def _is_authorized(self) -> bool:
        token = self.headers.get("X-Atlas-Session")
        if token is None:
            self._error(401, "missing_session", "A local session token is required.")
            return False
        if not hmac.compare_digest(token, self.app_server.session_token):
            self._error(403, "invalid_session", "The local session token is invalid.")
            return False
        return True

    def _read_object(self) -> Dict[str, Any]:
        length_header = self.headers.get("Content-Length")
        try:
            length = int(length_header or "0")
        except ValueError as error:
            raise IntakeValidationError("invalid Content-Length") from error
        if length <= 0 or length > 100_000:
            raise IntakeValidationError("request body must be a JSON object under 100 KB")
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise IntakeValidationError("request body must be valid JSON") from error
        if not isinstance(payload, dict):
            raise IntakeValidationError("request body must be a JSON object")
        return payload

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/":
            self._send_page()
            return
        if path == "/health":
            self._send_json(200, {"ok": True, "version": self.app_server.workbench_version})
            return
        if not self._is_authorized():
            return
        if path == "/api/draft":
            self._send_json(200, {"draft": self.app_server.storage.load_draft()})
            return
        if path.startswith("/api/runs/"):
            run_id = path.removeprefix("/api/runs/")
            try:
                self._send_json(200, self.app_server.storage.load_run(run_id))
            except StorageError as error:
                self._error(404, "run_not_found", str(error))
            return
        self._error(404, "not_found", "The requested local resource does not exist.")

    def do_PUT(self) -> None:
        if urlsplit(self.path).path != "/api/draft":
            self._error(404, "not_found", "The requested local resource does not exist.")
            return
        if not self._is_authorized():
            return
        try:
            intake = validate_intake(self._read_object())
            self.app_server.storage.save_draft(intake)
            self._send_json(200, intake)
        except IntakeValidationError as error:
            self._error(400, "bad_request", str(error))
        except StorageError as error:
            self._error(500, "storage_error", str(error))

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if path not in {"/api/runs", "/api/feasibility"}:
            self._error(404, "not_found", "The requested local resource does not exist.")
            return
        if not self._is_authorized():
            return
        try:
            intake = validate_intake(self._read_object())
            if path == "/api/feasibility":
                self._send_json(200, calculate_feasibility(intake))
                return
            manifest = self.app_server.storage.create_run(
                intake, self.app_server.workbench_version
            )
            self._send_json(201, manifest)
        except IntakeValidationError as error:
            self._error(400, "bad_request", str(error))
        except StorageError as error:
            self._error(500, "storage_error", str(error))


def create_server(
    host: str, port: int, session_token: str, storage: LocalStorage, workbench_version: str
) -> AtlasHTTPServer:
    """Create a localhost-only workbench server without starting its loop."""

    if host != "127.0.0.1":
        raise ValueError("Atlas Ads Workbench only binds to 127.0.0.1")
    if not session_token:
        raise ValueError("session_token is required")
    server = AtlasHTTPServer((host, port), WorkbenchRequestHandler)
    server.session_token = session_token
    server.storage = storage
    server.workbench_version = workbench_version
    server.asset_path = Path(__file__).resolve().parents[2] / "assets" / "workbench.html"
    return server
