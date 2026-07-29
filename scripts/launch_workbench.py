#!/usr/bin/env python3
"""Launch Atlas Ads Workbench on a token-protected loopback URL."""

import argparse
from pathlib import Path
import secrets
import sys
from urllib.parse import urlencode
import webbrowser


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from atlas_ads_workbench.server import create_server
from atlas_ads_workbench.storage import LocalStorage


WORKBENCH_VERSION = "0.1.0"


def build_workbench_url(port: int, session_token: str) -> str:
    return "http://127.0.0.1:%s/#%s" % (port, urlencode({"token": session_token}))


def prepare_server(storage_root: Path, version: str):
    session_token = secrets.token_urlsafe(32)
    server = create_server(
        host="127.0.0.1",
        port=0,
        session_token=session_token,
        storage=LocalStorage(storage_root),
        workbench_version=version,
    )
    return server, session_token


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch Atlas Ads Workbench locally.")
    parser.add_argument(
        "--no-browser", action="store_true", help="Print the local URL without opening it."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path.home() / ".atlas-ads-workbench",
        help="Local directory for drafts and immutable run snapshots.",
    )
    arguments = parser.parse_args()
    server, session_token = prepare_server(arguments.data_dir, WORKBENCH_VERSION)
    url = build_workbench_url(server.server_port, session_token)
    print("Atlas Ads Workbench is running locally.", flush=True)
    print(url, flush=True)
    if not arguments.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nAtlas Ads Workbench stopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
