# Atlas Ads Workbench

一个面向 Amazon 卖家的、本地优先且可解释的广告搭建工作台。它的目标是让卖家先看输入、依据与假设，再逐步形成可审查的广告搭建方案。

## 当前演示闭环

当前演示闭环支持卖家填写基础资料、生成三行 SP 演示报告，并将结果冻结为本地运行快照。

- 不会连接 Amazon。
- 不会上传数据。
- 不会调用 MCP、LLM 或生成伪装成真实数据的投放建议。
- 总日预算使用卖家输入的确定性公式，Campaign 使用 `30% / 45% / 25%` 固定演示分配。

后续阶段会在明确的数据来源、假设和人工确认边界下，逐步加入经过授权的外部证据、策略结构与表格导出。

## 渐进式卖家工作流

工作台按照 `基础输入 → 预算与可行性 → 选择广告目标 → 补充证据 → 审核并生成` 展开。

基础输入完成后，系统只计算卖家目标对应的销售额、月广告预算、日预算与可行性。SB、SD 和老品导流资料只有在卖家选择对应广告目标后才会出现。未选择的广告类型不执行 Gate，也不会被显示成“信息不完整”。

## 本地数据边界

运行时数据将保存在用户本机的 `.atlas-ads-workbench/` 数据目录，不应提交到 Git。项目不会保存 API Key、Cookie、卖家账号或 Amazon session。

## 安装与手动更新 Skill

Atlas Ads skill 必须以 **Git checkout** 安装，而不是复制单个 `SKILL.md` 或下载 ZIP。安装目录中的 `.git/` 让更新器能够确认当前版本和安全地快进更新；`skill-source.json` 则记录受信任的 Git remote、跟踪分支、仓库标识和更新渠道。

```bash
git clone https://github.com/jiayibytq/atlas-ads-workbench.git
cd atlas-ads-workbench
python3 scripts/update_skill.py --check
```

日常使用时，用户只需在聊天框中说：**“请帮我更新 Atlas Ads skill”**。Agent 会在该 Git checkout 中先执行检查，再在需要时执行：

```bash
python3 scripts/update_skill.py --update
```

更新结果会明确展示旧版本与目标版本的 commit、更新来源、验证状态和将要（或已经）变更的文件。更新器只接受配置来源上的快进更新，并会在隔离的候选版本中运行验证。

- 若本地存在**未提交的本地修改**、来源 metadata 不完整、当前 checkout 处于 detached HEAD，或历史已经分叉，更新会停止，不覆盖现有文件。
- 若候选版本验证失败、网络或 Git 来源不可用，工作台会保留**旧版本**；不要把失败的检查当作已更新。
- 更新成功后，请**新开一个会话**再调用 skill。当前聊天已经加载了旧版 `SKILL.md`，不会在会话中途自动替换指令。

发布者应先在自己的 checkout 验证更改，再将 commit 推送至 `skill-source.json` 配置的 remote/branch；需要可识别版本时，可在已验证的 commit 上创建并推送 Git tag。用户更新的依据始终是其本地 `skill-source.json` 记录的分支，而不是对某个仓库地址的猜测。

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
