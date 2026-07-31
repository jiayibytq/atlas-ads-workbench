---
name: atlas-ads-workbench
description: Launch the local-first Atlas Ads Workbench when a seller asks to “生成 SP 演示报告” or “打开工作台” to review Amazon advertising build inputs and a transparent local snapshot.
---

# Atlas Ads Workbench

## Purpose

Launch the local workbench for a seller to review inputs and generate a clearly labeled SP demo report. The report displays total-budget allocation, fixed demo targets, and a deterministic explanation, then freezes the result in a local run snapshot.

## Input

Accept partial information. Let the seller fill the remaining fields in the browser. Treat all submitted values as seller assumptions, not marketplace facts.

## Application

1. From the repository root, run:

   ```bash
   python3 scripts/launch_workbench.py
   ```

2. Keep the process running while the seller uses the local page. The launcher opens a `127.0.0.1` URL carrying a one-time session token in the URL fragment.
3. Tell the seller that drafts and run snapshots stay in `~/.atlas-ads-workbench/` by default.
4. Tell the seller to complete the required inputs and click “生成演示报告”.
5. Explain that total daily budget comes from seller inputs, while Campaign allocation uses the `30% / 45% / 25%` fixed demo rule.
6. Identify the keywords and ASIN as 固定演示数据, not marketplace evidence.
7. Explain the visible boundaries: 模型调用：0, no Amazon or MCP connection（不会连接 Amazon 或 MCP，且不会上传数据）, and the report is 不可直接执行.
8. Treat the saved run as a traceable demo report, not an advertising strategy.

## Common Pitfalls

- Do not open `assets/workbench.html` with `file://`; that bypasses the local API and has no session token.
- Do not bind the server to a LAN address or expose the local URL publicly.
- Do not put credentials, cookies, seller account identifiers, or real marketplace exports into the repository.
- 固定演示预算允许展示，但不得描述为真实或可执行；真实预算仍需授权证据。
- Do not hide the fixed `30% / 45% / 25%` allocation rule or describe it as an Amazon best practice.

## References

- `README.md` for the public data boundary and project status.
- `docs/architecture/phase-1.md` for the storage and API contract.
- `docs/architecture/decision-contract.md` for evidence, rule, and output boundaries.
