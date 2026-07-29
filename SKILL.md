---
name: atlas-ads-workbench
description: Launch the local-first Atlas Ads Workbench when a seller wants to capture Amazon advertising build inputs, save a local draft, or create a transparent run snapshot before strategy generation. Use for requests such as “打开 Atlas Ads 广告工作台”.
---

# Atlas Ads Workbench

## Purpose

Launch the local workbench for a seller to review and save advertising-build inputs. Phase 1 captures inputs and immutable run snapshots only.

## Input

Accept partial information. Let the seller fill the remaining fields in the browser. Treat all submitted values as seller assumptions, not marketplace facts.

## Application

1. From the repository root, run:

   ```bash
   python3 scripts/launch_workbench.py
   ```

2. Keep the process running while the seller uses the local page. The launcher opens a `127.0.0.1` URL carrying a one-time session token in the URL fragment.
3. Tell the seller that drafts and run snapshots stay in `~/.atlas-ads-workbench/` by default.
4. Explain the visible boundaries: Phase 1 **不会连接 Amazon、不会上传数据**，and will not call MCP or a model.
5. Do not claim that a submitted run is an advertising strategy. It is only a frozen, traceable input record for later phases.

## Common Pitfalls

- Do not open `assets/workbench.html` with `file://`; that bypasses the local API and has no session token.
- Do not bind the server to a LAN address or expose the local URL publicly.
- Do not put credentials, cookies, seller account identifiers, or real marketplace exports into the repository.

## References

- `README.md` for the public data boundary and project status.
- `docs/architecture/phase-1.md` when added for the storage and API contract.
