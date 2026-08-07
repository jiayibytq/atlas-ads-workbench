# Demo Report Happy Path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a one-click local happy path that turns validated seller inputs into a clearly labeled, non-executable SP demo report with visible budget allocation, a deterministic explanation, and an immutable run snapshot.

**Architecture:** Add a pure `demo_report` generator that consumes the existing feasibility result and returns three fixed SP rows. Expose it through one token-protected local endpoint that creates the existing immutable decision-plan snapshot, then make the browser page consume that response and render a six-column table plus deterministic summary.

**Tech Stack:** Python 3 standard library, `unittest`, localhost `ThreadingHTTPServer`, plain HTML/CSS/JavaScript, Git.

## Global Constraints

- Bind only to `127.0.0.1` and preserve the existing `X-Atlas-Session` token boundary.
- Use Python standard library only; add no package dependency.
- Generate exactly three SP demo rows with budget shares `30%`, `45%`, and `25%`.
- Derive total daily budget only from the existing deterministic feasibility calculation.
- Round money to two decimals with `ROUND_HALF_UP`; make the final row absorb the rounding difference so row budgets equal the displayed total.
- Use fixed demo targets only: `demo running socks`, `demo compression socks`, and `DEMO-ASIN-001`.
- Always return `report_type: "demo"`, `is_executable: false`, `external_data_used: false`, and `model_calls: 0`.
- The explanation must be deterministic; do not call an LLM.
- Do not connect Amazon, MCP, a seller spreadsheet, or any external network source.
- Do not generate formal SB or SD recommendations.
- Preserve existing historical run snapshots without migration or mutation.
- Keep the existing feasibility, Gate, and architecture endpoints available as secondary diagnostic paths.

## File Structure

- Create `src/atlas_ads_workbench/demo_report.py`: pure demo-report generation and cent-accurate budget allocation.
- Create `tests/test_demo_report.py`: unit contract for rows, totals, transparency, summary, and warnings.
- Modify `src/atlas_ads_workbench/server.py`: add the one-click `/api/demo-report` endpoint and freeze the report into `decision-plan.json`.
- Modify `tests/test_server.py`: verify endpoint response, authorization behavior, and snapshot round-trip.
- Modify `assets/workbench.html`: promote one primary action and render the six-column report table.
- Modify `tests/test_workbench_asset.py`: static page contract for the happy path.
- Modify `tests/test_server.py`: update the root-page copy assertion after the phase banner changes.
- Modify `README.md`: describe the demo-report happy path and its non-executable boundary.
- Modify `SKILL.md`: teach the local Skill how to launch and explain the demo report.
- Modify `tests/test_public_contract.py`: prevent public documentation from losing the demo-data boundary.

---

### Task 1: Pure Demo Report Generator

**Files:**
- Create: `tests/test_demo_report.py`
- Create: `src/atlas_ads_workbench/demo_report.py`

**Interfaces:**
- Consumes: `build_demo_report(feasibility: Mapping[str, Any])`, where `feasibility` is the dictionary returned by `calculate_feasibility()`.
- Produces: `build_demo_report(feasibility: Mapping[str, Any]) -> Dict[str, Any]`.
- Output row keys: `ad_type`, `purpose`, `budget_share_percent`, `daily_budget_usd`, `target`, `target_type`, `is_demo`.

- [ ] **Step 1: Write the failing generator tests**

Create `tests/test_demo_report.py`:

```python
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atlas_ads_workbench.demo_report import build_demo_report
from atlas_ads_workbench.feasibility import calculate_feasibility
from atlas_ads_workbench.models import validate_intake


def make_intake(**overrides):
    payload = {
        "marketplace": "US",
        "product_stage": "launch",
        "monthly_sales_target": 300,
        "product_price_usd": 32.99,
        "target_tacos_percent": 15,
        "ad_sales_share_percent": 80,
        "benchmark_cpc_usd": 1.2,
        "benchmark_cvr_percent": 10,
        "business_goals": "Validate the demo report flow.",
    }
    payload.update(overrides)
    return validate_intake(payload)


class DemoReportTests(unittest.TestCase):
    def test_builds_three_fixed_sp_rows_with_visible_budget_allocation(self):
        feasibility = calculate_feasibility(make_intake())
        report = build_demo_report(feasibility)

        self.assertEqual(report["report_version"], 1)
        self.assertEqual(report["report_type"], "demo")
        self.assertFalse(report["is_executable"])
        self.assertFalse(report["external_data_used"])
        self.assertEqual(report["model_calls"], 0)
        self.assertEqual(len(report["rows"]), 3)
        self.assertEqual(
            [row["budget_share_percent"] for row in report["rows"]],
            [30, 45, 25],
        )
        self.assertEqual(
            [row["target"] for row in report["rows"]],
            [
                "demo running socks",
                "demo compression socks",
                "DEMO-ASIN-001",
            ],
        )
        self.assertTrue(all(row["ad_type"] == "SP" for row in report["rows"]))
        self.assertTrue(all(row["is_demo"] for row in report["rows"]))

    def test_row_budgets_equal_the_displayed_total_after_rounding(self):
        feasibility = calculate_feasibility(make_intake())
        report = build_demo_report(feasibility)

        allocated = round(
            sum(row["daily_budget_usd"] for row in report["rows"]), 2
        )
        self.assertEqual(allocated, report["total_daily_budget_usd"])
        self.assertEqual(report["total_daily_budget_usd"], 49.49)

    def test_infeasible_inputs_add_a_warning_without_hiding_the_demo(self):
        feasibility = calculate_feasibility(make_intake())
        report = build_demo_report(feasibility)

        self.assertEqual(len(report["warnings"]), 1)
        self.assertIn("输入假设存在可行性冲突", report["warnings"][0])
        self.assertIn("固定演示规则", report["summary"])
        self.assertEqual(len(report["rows"]), 3)

    def test_feasible_inputs_have_no_feasibility_warning(self):
        feasibility = calculate_feasibility(
            make_intake(benchmark_cpc_usd=0.5, benchmark_cvr_percent=20)
        )
        report = build_demo_report(feasibility)

        self.assertEqual(report["warnings"], [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the generator tests and verify RED**

Run:

```bash
python3 -m unittest tests.test_demo_report -v
```

Expected: `ERROR` with `ModuleNotFoundError: No module named 'atlas_ads_workbench.demo_report'`.

- [ ] **Step 3: Implement the minimal pure generator**

Create `src/atlas_ads_workbench/demo_report.py`:

```python
"""Deterministic, explicitly non-executable SP demo reports."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Mapping


CENT = Decimal("0.01")
DEMO_ROWS = (
    {
        "ad_type": "SP",
        "purpose": "探索搜索词",
        "budget_share_percent": 30,
        "target": "demo running socks",
        "target_type": "自动采样",
    },
    {
        "ad_type": "SP",
        "purpose": "验证核心词",
        "budget_share_percent": 45,
        "target": "demo compression socks",
        "target_type": "精准",
    },
    {
        "ad_type": "SP",
        "purpose": "验证关联商品",
        "budget_share_percent": 25,
        "target": "DEMO-ASIN-001",
        "target_type": "商品投放",
    },
)


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def build_demo_report(feasibility: Mapping[str, Any]) -> Dict[str, Any]:
    """Build a fixed-data report from the seller-derived total budget."""

    total = _money(Decimal(str(feasibility["daily_ad_spend_cap_usd"])))
    rows = []
    allocated = Decimal("0.00")
    for index, template in enumerate(DEMO_ROWS):
        if index == len(DEMO_ROWS) - 1:
            budget = total - allocated
        else:
            share = Decimal(str(template["budget_share_percent"])) / Decimal("100")
            budget = _money(total * share)
            allocated += budget
        rows.append(
            {
                **template,
                "daily_budget_usd": float(budget),
                "is_demo": True,
            }
        )

    warnings = []
    if not feasibility["is_feasible_at_benchmark"]:
        warnings.append(
            "当前输入假设存在可行性冲突；本表仅用于演示流程，不可直接执行。"
        )

    return {
        "report_version": 1,
        "report_type": "demo",
        "is_executable": False,
        "data_source": "seller_input_and_fixed_demo_data",
        "external_data_used": False,
        "model_calls": 0,
        "total_daily_budget_usd": float(total),
        "budget_basis": "卖家月销售目标 × 产品售价 × 目标 TACoS ÷ 30",
        "allocation_rule": "demo-report-v1: 30% / 45% / 25%",
        "rows": rows,
        "summary": (
            "本次演示将总日预算拆分为三种 SP 任务：自动采样用于收集搜索词信号，"
            "精准投放用于验证核心词，商品投放用于演示关联 ASIN 测试。"
            "预算分配来自固定演示规则，不代表真实市场建议。"
            "正式执行前仍需补充关键词、商品定向和账户资格证据。"
        ),
        "warnings": warnings,
    }
```

- [ ] **Step 4: Run the generator tests and verify GREEN**

Run:

```bash
python3 -m unittest tests.test_demo_report -v
```

Expected: `Ran 4 tests` and `OK`.

- [ ] **Step 5: Commit the generator**

```bash
git add tests/test_demo_report.py src/atlas_ads_workbench/demo_report.py
git commit -m "Add deterministic SP demo report generator"
```

---

### Task 2: One-Click Report API and Immutable Snapshot

**Files:**
- Modify: `tests/test_server.py`
- Modify: `src/atlas_ads_workbench/server.py`

**Interfaces:**
- Consumes: `build_demo_report(feasibility: Mapping[str, Any]) -> Dict[str, Any]` from Task 1.
- Produces: token-protected `POST /api/demo-report`.
- Request body: existing source-neutral envelope `{"intake": {...}, "evidence_context": {...}}`; the raw intake body remains accepted by `_validated_intake_and_context()`.
- Response body: `{"run": <manifest>, "report": <demo_report>}` with HTTP `201`.
- Snapshot: `decision-plan.json` contains a `demo_report` value byte-for-byte equivalent to the response report.

- [ ] **Step 1: Write the failing API and snapshot tests**

Add these methods to `LocalServerTests` in `tests/test_server.py`:

```python
    def test_demo_report_endpoint_creates_and_returns_the_same_frozen_report(self):
        status, response = self.request(
            "/api/demo-report",
            "POST",
            {"intake": valid_payload(), "evidence_context": {}},
            token="test-token",
        )
        run_id = response["run"]["run_id"]
        _, saved = self.request("/api/runs/%s" % run_id, token="test-token")

        self.assertEqual(status, 201)
        self.assertEqual(response["report"]["report_type"], "demo")
        self.assertFalse(response["report"]["is_executable"])
        self.assertEqual(len(response["report"]["rows"]), 3)
        self.assertEqual(
            saved["decision_plan"]["demo_report"],
            response["report"],
        )
        self.assertEqual(
            saved["manifest"]["decision_plan_sha256"],
            response["run"]["decision_plan_sha256"],
        )

    def test_demo_report_endpoint_requires_the_local_session_token(self):
        with self.assertRaises(HTTPError) as error:
            self.request("/api/demo-report", "POST", valid_payload())

        self.assertEqual(error.exception.code, 401)
```

- [ ] **Step 2: Run the endpoint tests and verify RED**

Run:

```bash
python3 -m unittest \
  tests.test_server.LocalServerTests.test_demo_report_endpoint_creates_and_returns_the_same_frozen_report \
  tests.test_server.LocalServerTests.test_demo_report_endpoint_requires_the_local_session_token \
  -v
```

Expected: the first test fails with HTTP `404`; the authorization test may also receive `404` because the route is not registered yet.

- [ ] **Step 3: Register the endpoint and freeze its report**

In `src/atlas_ads_workbench/server.py`, add the import:

```python
from .demo_report import build_demo_report
```

Replace the allowed-path condition at the start of `do_POST()` with:

```python
        if path not in {
            "/api/runs",
            "/api/feasibility",
            "/api/campaign-architecture",
            "/api/gates",
            "/api/demo-report",
        }:
```

After `gates = evaluate_gates(...)` and the `/api/gates` early return, build the existing decision plan, then branch for the demo report:

```python
            decision_plan = {
                "decision_plan_version": 1,
                "data_source": "seller_input_and_deterministic_rule",
                "external_data_used": False,
                "model_calls": 0,
                "evidence_context": evidence_context,
                "feasibility": feasibility,
                "gates": gates,
                "campaign_architecture": architecture,
            }
            if path == "/api/demo-report":
                demo_report = build_demo_report(feasibility)
                decision_plan["demo_report"] = demo_report
                manifest = self.app_server.storage.create_run(
                    intake,
                    self.app_server.workbench_version,
                    decision_plan,
                )
                self._send_json(
                    201,
                    {"run": manifest, "report": demo_report},
                )
                return
            manifest = self.app_server.storage.create_run(
                intake,
                self.app_server.workbench_version,
                decision_plan,
            )
            self._send_json(201, manifest)
```

Remove the old duplicate `decision_plan`, `create_run()`, and `_send_json(201, manifest)` block below this replacement.

- [ ] **Step 4: Run endpoint and regression tests**

Run:

```bash
python3 -m unittest tests.test_server tests.test_storage -v
```

Expected: all server and storage tests pass, including the new two endpoint tests and the existing `/api/runs` response contract.

- [ ] **Step 5: Commit the API**

```bash
git add tests/test_server.py src/atlas_ads_workbench/server.py
git commit -m "Add one-click demo report endpoint"
```

---

### Task 3: Six-Column Page Report and One Primary Action

**Files:**
- Modify: `tests/test_workbench_asset.py`
- Modify: `tests/test_server.py`
- Modify: `assets/workbench.html`

**Interfaces:**
- Consumes: `POST /api/demo-report` response `{"run": manifest, "report": report}` from Task 2.
- Produces: `renderDemoReport(report, manifest)` in page JavaScript.
- DOM IDs: `demo-report`, `demo-meta`, `demo-total`, `demo-report-body`, `demo-summary`, `demo-warnings`.

- [ ] **Step 1: Write failing static UI contract tests**

Replace `test_page_names_the_phase_one_boundary_and_core_actions` in `tests/test_workbench_asset.py` with:

```python
    def test_page_exposes_the_demo_report_happy_path(self):
        page = ASSET.read_text(encoding="utf-8")

        for expected_text in (
            "生成演示报告",
            "演示广告搭建报告",
            "广告类型",
            "广告目的",
            "预算占比",
            "日预算",
            "具体投放词 / ASIN",
            "投放类型",
            "确定性说明",
            "不可直接执行",
            "/api/demo-report",
            "renderDemoReport",
            "scrollIntoView",
            "保存草稿",
            "查看计算详情",
            "不会连接 Amazon",
            "不会上传数据",
        ):
            self.assertIn(expected_text, page)
```

In `tests/test_server.py`, change the root page assertion:

```python
        self.assertIn("演示闭环", page)
```

Replace the old assertion for `"第一阶段：仅保存需求"`.

- [ ] **Step 2: Run the page tests and verify RED**

Run:

```bash
python3 -m unittest tests.test_workbench_asset tests.test_server.LocalServerTests.test_root_returns_the_local_workbench_page -v
```

Expected: failures naming missing `生成演示报告` and `演示闭环`.

- [ ] **Step 3: Add report layout and responsive table styling**

In `assets/workbench.html`, extend the existing style block with:

```css
    .report { display:none; margin-top:26px; background:#fff; border:1px solid var(--line); border-radius:14px; padding:24px; }
    .report.visible { display:block; }
    .report-head { display:flex; justify-content:space-between; gap:18px; align-items:flex-start; margin-bottom:18px; }
    .report-total { color:var(--forest); font-size:28px; font-weight:760; letter-spacing:-.04em; white-space:nowrap; }
    .report-meta { color:#587064; font-size:13px; }
    .report-table-wrap { overflow-x:auto; border:1px solid #dce9e0; border-radius:10px; }
    .report table { width:100%; border-collapse:collapse; min-width:760px; }
    .report th,.report td { padding:12px 13px; border-bottom:1px solid #e2ece5; text-align:left; vertical-align:top; }
    .report th { color:#527063; background:#f2f7f3; font-size:12px; letter-spacing:.02em; }
    .report td { color:#203e31; font-size:13px; }
    .report tbody tr:last-child td { border-bottom:0; }
    .demo-pill { display:inline-block; margin-left:6px; padding:2px 6px; border-radius:999px; background:#fff0d5; color:#82530c; font-size:11px; }
    .report-summary { margin-top:18px; padding:16px; border-left:3px solid var(--green); background:var(--mint); }
    .report-summary h3 { margin:0 0 6px; font-size:15px; }
    .report-summary p { margin:0; color:#315b48; }
    .report-warning { margin-top:10px; color:#71490d; }
    .advanced { grid-column:1/-1; margin-top:4px; }
```

Replace the phase banner copy with:

```html
    <section class="phase"><strong>演示闭环：从卖家输入生成页面广告搭建报告。</strong>使用固定演示关键词与分配规则；不会连接 Amazon，不会上传数据，也不会调用 MCP 或模型，报告不可直接执行。</section>
```

Replace the current `.actions` content with:

```html
        <div class="actions">
          <button class="secondary" type="button" id="save">保存草稿</button>
          <button class="primary" type="submit">生成演示报告</button>
        </div>
        <details class="advanced">
          <summary>查看计算详情</summary>
          <div class="actions">
            <button class="secondary" type="button" id="calculate">计算预算与可行性</button>
            <button class="secondary" type="button" id="gates-button">检查信息完整度</button>
            <button class="secondary" type="button" id="architecture-button">预览广告架构</button>
          </div>
        </details>
```

After the closing `</div>` for the existing `.layout`, add the report section:

```html
    <section class="report" id="demo-report" aria-live="polite">
      <div class="report-head">
        <div>
          <div class="eyebrow">FIXED DEMO DATA · NOT EXECUTABLE</div>
          <h2>演示广告搭建报告</h2>
          <p class="report-meta" id="demo-meta"></p>
        </div>
        <div>
          <div class="hint">总日预算</div>
          <div class="report-total" id="demo-total"></div>
        </div>
      </div>
      <div class="report-table-wrap">
        <table>
          <thead>
            <tr>
              <th>广告类型</th>
              <th>广告目的</th>
              <th>预算占比</th>
              <th>日预算</th>
              <th>具体投放词 / ASIN</th>
              <th>投放类型</th>
            </tr>
          </thead>
          <tbody id="demo-report-body"></tbody>
        </table>
      </div>
      <div class="report-summary">
        <h3>确定性说明</h3>
        <p id="demo-summary"></p>
        <div id="demo-warnings"></div>
      </div>
    </section>
```

- [ ] **Step 4: Render only the server-returned report and replace form submit**

Add this helper and renderer in the page script before the submit handler:

```javascript
    function escapeHtml(value){
      return String(value).replace(/[&<>"']/g, character => ({
        '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
      })[character]);
    }
    function renderDemoReport(report, manifest){
      document.querySelector('#demo-meta').textContent =
        '演示报告 · 卖家填写 + 固定演示数据 · 外部数据未使用 · 模型调用 0 次 · 不可直接执行 · 运行 ' + manifest.run_id;
      document.querySelector('#demo-total').textContent = money(report.total_daily_budget_usd);
      document.querySelector('#demo-report-body').innerHTML = report.rows.map(row =>
        '<tr>' +
          '<td>' + escapeHtml(row.ad_type) + '<span class="demo-pill">演示</span></td>' +
          '<td>' + escapeHtml(row.purpose) + '</td>' +
          '<td>' + percent(row.budget_share_percent) + '</td>' +
          '<td>' + money(row.daily_budget_usd) + '</td>' +
          '<td>' + escapeHtml(row.target) + '</td>' +
          '<td>' + escapeHtml(row.target_type) + '</td>' +
        '</tr>'
      ).join('');
      document.querySelector('#demo-summary').textContent = report.summary;
      document.querySelector('#demo-warnings').innerHTML = report.warnings.map(
        warning => '<div class="report-warning">' + escapeHtml(warning) + '</div>'
      ).join('');
      const section = document.querySelector('#demo-report');
      section.classList.add('visible');
      section.scrollIntoView({behavior:'smooth', block:'start'});
    }
```

Replace the existing `form.addEventListener('submit', ...)` block with:

```javascript
    form.addEventListener('submit', async event => {
      event.preventDefault();
      try {
        if(!token) throw new Error('启动链接缺少本地会话令牌，请重新打开工作台。');
        tell('正在生成演示报告…');
        const response = await api('/api/demo-report', {
          method:'POST',
          body:JSON.stringify(gatePayload())
        });
        renderDemoReport(response.report, response.run);
        tell('演示报告已生成并保存在本机；不可直接执行。');
      } catch(error) {
        tell(error.message, true);
      }
    });
```

Keep the existing `save`, `calculate`, `checkGates`, and `previewArchitecture` functions unchanged.

- [ ] **Step 5: Run UI, server, and full regression tests**

Run:

```bash
python3 -m unittest tests.test_workbench_asset tests.test_server -v
python3 -m unittest discover -s tests -v
git diff --check
```

Expected: all tests pass and `git diff --check` produces no output.

- [ ] **Step 6: Commit the page happy path**

```bash
git add tests/test_workbench_asset.py tests/test_server.py assets/workbench.html
git commit -m "Render one-click demo advertising report"
```

---

### Task 4: Public Skill Contract and Final Verification

**Files:**
- Modify: `tests/test_public_contract.py`
- Modify: `README.md`
- Modify: `SKILL.md`

**Interfaces:**
- Consumes: the user-visible behavior completed in Tasks 1–3.
- Produces: public documentation that names the fixed demo data, deterministic summary, budget-allocation rule, and non-executable boundary.

- [ ] **Step 1: Write the failing public-contract test**

Add this method to `PublicContractTests` in `tests/test_public_contract.py`:

```python
    def test_public_docs_explain_the_demo_report_boundary(self):
        readme = (ROOT / "README.md").read_text("utf-8")
        skill = (ROOT / "SKILL.md").read_text("utf-8")

        for expected_text in (
            "生成演示报告",
            "30% / 45% / 25%",
            "固定演示数据",
            "不可直接执行",
            "模型调用：0",
        ):
            self.assertIn(expected_text, readme)
            self.assertIn(expected_text, skill)
```

- [ ] **Step 2: Run the documentation test and verify RED**

Run:

```bash
python3 -m unittest tests.test_public_contract.PublicContractTests.test_public_docs_explain_the_demo_report_boundary -v
```

Expected: `FAIL` because the current README and Skill do not yet contain the demo-report contract.

- [ ] **Step 3: Add the exact public boundary to README**

Add this section before `## 开发` in `README.md`:

```markdown
## 演示报告 Happy Path

卖家填写基础资料后，可以点击“生成演示报告”，在页面查看三行 SP 广告搭建表。报告展示广告目的、预算占比、日预算、固定演示关键词或 ASIN，以及投放类型。

- 总日预算来自卖家输入的确定性公式。
- Campaign 预算使用 `30% / 45% / 25%` 固定演示规则。
- 关键词和 ASIN 是固定演示数据，不是 Amazon 或类目查询结果。
- 总结由确定性模板生成，模型调用：0。
- 报告不可直接执行，不会连接 Amazon、MCP 或外部网络。
```

- [ ] **Step 4: Update the Skill workflow and boundaries**

Replace the `## Purpose` paragraph in `SKILL.md` with:

```markdown
Launch the local workbench for a seller to review inputs and generate a clearly labeled SP demo report. The report displays total-budget allocation, fixed demo targets, and a deterministic explanation, then freezes the result in a local run snapshot.
```

Add these steps after the launcher instructions in `## Application`:

```markdown
4. Tell the seller to complete the required inputs and click “生成演示报告”.
5. Explain that total daily budget comes from seller inputs, while Campaign allocation uses the `30% / 45% / 25%` fixed demo rule.
6. Identify the keywords and ASIN as 固定演示数据, not marketplace evidence.
7. Explain the visible boundaries: 模型调用：0, no Amazon or MCP connection, and the report is 不可直接执行.
8. Treat the saved run as a traceable demo report, not an advertising strategy.
```

Remove or renumber old application steps so the section contains one sequential list and no contradictory “input-only” Phase 1 wording.

Add this bullet under `## Common Pitfalls`:

```markdown
- Do not hide the fixed `30% / 45% / 25%` allocation rule or describe it as an Amazon best practice.
```

- [ ] **Step 5: Run public contract and complete regression verification**

Run:

```bash
python3 -m unittest tests.test_public_contract tests.test_skill_contract -v
python3 -m unittest discover -s tests -v
git diff --check
git status --short
```

Expected:

- all tests pass;
- `git diff --check` produces no output;
- `git status --short` lists only `README.md`, `SKILL.md`, and `tests/test_public_contract.py`.

- [ ] **Step 6: Commit the public contract**

```bash
git add README.md SKILL.md tests/test_public_contract.py
git commit -m "Document demo report happy path"
```

- [ ] **Step 7: Final repository verification**

Run:

```bash
python3 -m unittest discover -s tests -v
git diff --check
git status --short
git log -4 --oneline
```

Expected:

- all tests pass;
- `git diff --check` produces no output;
- `git status --short` produces no output;
- the latest four commits correspond to Tasks 1–4.

Do not push or publish until the user explicitly approves the verified implementation.
