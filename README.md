# Atlas Ads Workbench

一个面向 Amazon 卖家的、本地优先且可解释的广告搭建工作台。它的目标是让卖家先看输入、依据与假设，再逐步形成可审查的广告搭建方案。

## 第一阶段状态

第一阶段正在建立本地 Skill 工作台的基础：输入合同、草稿和不可变运行快照。

- 不会连接 Amazon。
- 不会上传数据。
- 不会调用 MCP、LLM 或生成伪装成真实数据的投放建议。

后续阶段会在明确的数据来源、公式、假设和人工确认边界下，逐步加入预算计算、策略结构、表格导出与经过授权的外部数据连接。

## 本地数据边界

运行时数据将保存在用户本机的 `.atlas-ads-workbench/` 数据目录，不应提交到 Git。项目不会保存 API Key、Cookie、卖家账号或 Amazon session。

## 开发

当前仅需要 Python 标准库：

```bash
python3 -m unittest discover -s tests -v
```

## License

[MIT](LICENSE)
