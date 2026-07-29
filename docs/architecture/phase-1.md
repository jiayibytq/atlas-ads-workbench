# Phase 1 Architecture: Local Intake Workbench

## Scope

Phase 1 captures a seller's advertising-build inputs, a mutable draft, and an immutable run snapshot. It **不会连接 Amazon**、不会调用 MCP 或模型、不会生成广告策略或 XLSX。

## Request flow

```text
Codex Skill
  -> scripts/launch_workbench.py
  -> 127.0.0.1 local HTTP server
  -> browser workbench
  -> validated intake.json + manifest.json
```

The launcher chooses an available local port, creates a high-entropy session token, then opens a URL such as `http://127.0.0.1:43123/#token=...`. The token stays in the URL fragment (`URL fragment`) and is sent only as an `X-Atlas-Session` request header. It is not written to a draft, run manifest, server log, or browser storage.

## Local data contract

By default, the workbench writes only to `~/.atlas-ads-workbench/`:

```text
drafts/current-intake.json
runs/<run_id>/intake.json
runs/<run_id>/manifest.json
```

- `current-intake.json` is a mutable, atomically written seller draft.
- `intake.json` is copied when a run is created and is never modified afterward.
- `manifest.json` records run ID, timestamp, phase status, input SHA-256, data provenance, and resource use.

The manifest states `data_source: seller_input`, `external_data_used: false`, and `model_calls: 0`. This is the visible transparency contract for Phase 1.

## Security boundary

The server accepts only `127.0.0.1`; it is not a LAN server. `/health` is public only to permit the launcher to verify readiness. All draft and run endpoints require the one-time session token. Real seller exports, credentials, cookies, API keys, and Amazon session data must never be stored in this repository.

## Next boundary

Phase 2 may add deterministic feasibility calculations on the frozen `intake.json`. Each result must name its formula, seller assumption, and any external data source. A language model must not be the authority for arithmetic, data provenance, or budget validation.
