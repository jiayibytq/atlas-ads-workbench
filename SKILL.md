---
name: atlas-ads-workbench
description: Launch the local-first Atlas Ads Workbench when a seller asks to “生成 SP 演示报告” or “打开工作台” to review Amazon advertising build inputs and a transparent local snapshot.
type: workflow
---

# Atlas Ads Workbench

## Purpose

Launch the local workbench for a seller to review inputs and generate a clearly labeled SP demo report. The report displays total-budget allocation, fixed demo targets, and a deterministic explanation, then freezes the result in a local run snapshot.

## Input

零输入或部分输入都可以开始。邀请卖家带来市场、产品阶段、月销量目标、售价、目标 TACoS、广告销售占比、CPC/CVR 假设和业务目标中的任意部分；缺少的内容由浏览器表单引导补齐，不把输入完整度当作启动门槛。

用户在请求中 inline 提供的内容视为已回答，不要重复询问。所有填写值都属于卖家假设，不是 Amazon 或市场事实。

**示例调用：** `打开工作台，生成 SP 演示报告；美国站新品，售价 36.15 美元，月销量目标 10，目标 TACoS 10%。`

## Key Concepts

- **确定性预算边界：** 总日预算仅由卖家填写的月销量、售价和目标 TACoS 按公开公式计算；金额链使用十进制计算，最终才显示为美分。
- **固定演示分配：** `30% / 45% / 25%` 只负责证明报告生成、分配和保存流程。固定关键词与 ASIN 同样不是市场证据。
- **证据边界：** `external_data_used: false` 与 `model_calls: 0` 说明本次没有调用 Amazon、MCP、外部数据或模型。这提升可追溯性，但不会自动让结果成为建议。
- **人类决策边界：** `is_executable: false` 表示报告只供审阅。真实广告搭建仍需授权账户数据、关键词/商品定向证据、库存与毛利判断以及人工批准。

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

## Examples

### 为什么固定演示预算不是真实建议

卖家给出月销量目标 `10`、售价 `$36.15`、目标 TACoS `10%`。系统可复算：

```text
月销售额 = 10 × 36.15 = 361.50
月广告费上限 = 361.50 × 10% = 36.15
日预算 = 36.15 ÷ 30 = 1.205，按 ROUND_HALF_UP 显示为 1.21
```

报告再按固定演示规则拆成 `30% / 45% / 25%`，这只能证明三行预算加总仍为 `$1.21`。它不能证明三类 Campaign 应获得这些占比：当前缺少授权账户数据、搜索词表现、商品定向证据、真实 CPC/CVR、库存和毛利约束。因此正确结论是“演示报告已生成且预算守恒”，不是“建议按此预算投放”。

当可行性计算显示所需 CVR 高于卖家假设时，报告仍可展示以便验证流程，但 summary 和 warning 必须同时指出冲突；用户应先调整假设并复核，而不是把固定分配当成规避冲突的方法。

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
