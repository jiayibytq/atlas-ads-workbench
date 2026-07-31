# Atlas Ads Workbench

一个面向 Amazon 卖家的、本地优先且可解释的广告搭建工作台。它的目标是让卖家先看输入、依据与假设，再逐步形成可审查的广告搭建方案。

## 当前演示闭环

当前演示闭环支持卖家填写基础资料、生成三行 SP 演示报告，并将结果冻结为本地运行快照。

- 不会连接 Amazon。
- 不会上传数据。
- 不会调用 MCP、LLM 或生成伪装成真实数据的投放建议。
- 总日预算使用卖家输入的确定性公式，Campaign 使用 `30% / 45% / 25%` 固定演示分配。

后续阶段会在明确的数据来源、假设和人工确认边界下，逐步加入经过授权的外部证据、策略结构与表格导出。

## 本地数据边界

运行时数据将保存在用户本机的 `.atlas-ads-workbench/` 数据目录，不应提交到 Git。项目不会保存 API Key、Cookie、卖家账号或 Amazon session。

## 演示报告 Happy Path

卖家填写基础资料后，可以点击“生成演示报告”，在页面查看三行 SP 广告搭建表。报告展示广告目的、预算占比、日预算、固定演示关键词或 ASIN，以及投放类型。

- 总日预算来自卖家输入的确定性公式。
- Campaign 预算使用 `30% / 45% / 25%` 固定演示规则。
- 关键词和 ASIN 是固定演示数据，不是 Amazon 或类目查询结果。
- 总结由确定性模板生成，模型调用：0。
- 报告不可直接执行，不会连接 Amazon、MCP 或外部网络。

## 开发

当前仅需要 Python 标准库：

```bash
python3 -m unittest discover -s tests -v
```

## 启动本地工作台

```bash
git clone https://github.com/jiayibytq/atlas-ads-workbench.git
cd atlas-ads-workbench
python3 scripts/launch_workbench.py
```

启动器只绑定本机 `127.0.0.1`，并自动打开一个带一次性会话 token 的页面。不要直接用 `file://` 打开 `assets/workbench.html`，否则页面无法访问本地 API。

可查看 [Phase 1 架构说明](docs/architecture/phase-1.md)、[决策合同](docs/architecture/decision-contract.md) 和 [示例输入](examples/intake.example.json)。

## License

[MIT](LICENSE)
