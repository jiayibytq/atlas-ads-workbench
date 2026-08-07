# Contributing

Atlas Ads Workbench is local-first. Never commit real seller data, Amazon
credentials, cookies, API keys, customer exports, or `.env` files.

Run the test suite before opening a pull request:

```bash
python3 -m unittest discover -s tests -v
```

Keep changes narrow, add a behavior-focused test before implementation code,
and describe any new local data written by the workbench.

## 发布可更新的 Skill

用户的安装副本是 Git checkout，并由 `skill-source.json` 指向受信任的 remote
与跟踪分支。每次准备让用户通过“请帮我更新 Atlas Ads skill”获得新版本时：

1. 先在本地运行完整验证，并检查 `git diff --check`。
2. 将验证过的 commit 推送（`push`）到 `skill-source.json` 配置的 remote 和分支；如需版本标记，再在该已验证 commit 上创建并推送 tag。
3. 不要把未经验证的更改直接发布到 `main`，也不要要求用户通过更新器覆盖本地未提交修改。

更新器会在独立的候选 worktree 中验证目标 commit，并且只能 fast-forward。
贡献者不应通过复制文件、重写历史或要求用户手工编辑安装目录来绕开这些边界。
