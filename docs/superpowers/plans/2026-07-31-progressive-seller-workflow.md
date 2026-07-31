# Progressive Seller Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current all-at-once form and Gate dump with a progressive seller workflow that calculates budget first, explains feasibility second, and only then collects evidence for the advertising modules the seller chooses.

**Architecture:** Keep the existing localhost server, deterministic feasibility engine, evidence envelope, immutable run storage, and narrow API endpoints. Add a small workflow-selection contract, make Gate evaluation selection-aware, and reorganize the single-page UI into progressive sections without adding a frontend framework or external dependency. Historical run snapshots keep their original contract versions.

**Tech Stack:** Python 3 standard library, `unittest`, static HTML/CSS/JavaScript, YAML/JSON contracts, localhost HTTP API.

## Global Constraints

- The first result after basic intake is total budget and deterministic feasibility, not SB/SD eligibility.
- Seller-entered values remain `status: confirmed` and `source: seller_input`; they must never impersonate verified evidence.
- Do not connect to Amazon, MCP, or a language model in this release.
- Keep `external_data_used: false`, `model_calls: 0`, and `is_executable: false` visible wherever a report is rendered.
- Unselected advertising modules are `not_applicable`; they are not “missing information.”
- A feasibility conflict does not erase the budget calculation, but it must remain visible in every downstream preview and saved run.
- Gate IDs and versions remain visible in the expandable technical-details area, not as primary seller-facing copy.
- UI copy is Chinese; internal contract fields and Gate IDs remain stable English identifiers.
- No new runtime dependency or frontend build step.
- Every behavior change follows red-green-refactor and ends with a focused commit.

---

## File Responsibility Map

- `assets/workbench.html`: progressive sections, seller-facing copy, local workflow state, API orchestration, and report rendering.
- `src/atlas_ads_workbench/workflow.py`: validation and normalization of selected advertising modules.
- `src/atlas_ads_workbench/gates.py`: deterministic Gate applicability and seller-facing status metadata.
- `src/atlas_ads_workbench/server.py`: request-envelope parsing and propagation of selected modules into Gates and frozen runs.
- `contracts/decision-rules.yaml`: versioned applicability rules and evidence requirements.
- `contracts/output-schema.json`: decision statuses allowed in future structured outputs.
- `tests/test_workflow.py`: selected-module normalization.
- `tests/test_gates.py`: applicability, conflicts, and evidence-state behavior.
- `tests/test_server.py`: API-envelope and frozen-run integration.
- `tests/test_workbench_asset.py`: progressive-page interaction contract.
- `tests/test_public_contract.py`: public contract versions and status vocabulary.
- `README.md`, `SKILL.md`, `docs/architecture/decision-contract.md`: seller workflow and evidence-boundary documentation.

---

### Task 1: Define the selected-module contract

**Files:**
- Create: `src/atlas_ads_workbench/workflow.py`
- Create: `tests/test_workflow.py`
- Modify: `contracts/decision-rules.yaml`
- Modify: `contracts/output-schema.json`
- Modify: `tests/test_public_contract.py`

**Interfaces:**
- Consumes: raw request value `selected_ad_modules`.
- Produces: `normalize_selected_ad_modules(value: Any) -> list[str]`.
- Allowed module IDs: `sp`, `sb`, `sd`, `sd_cross_sell`.
- Allowed decision statuses: `not_applicable`, `information_required`, `verification_required`, `constraint_conflict`, `ready_for_rule_evaluation`, `review_required`, `approved`, `rejected`.

- [ ] **Step 1: Write failing module-normalization tests**

```python
# tests/test_workflow.py
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atlas_ads_workbench.workflow import WorkflowValidationError, normalize_selected_ad_modules


class WorkflowSelectionTests(unittest.TestCase):
    def test_normalizes_unique_modules_in_supported_order(self):
        self.assertEqual(
            normalize_selected_ad_modules(["sd_cross_sell", "sp", "sp", "sb"]),
            ["sp", "sb", "sd_cross_sell"],
        )

    def test_rejects_unknown_module(self):
        with self.assertRaisesRegex(WorkflowValidationError, "unsupported advertising module"):
            normalize_selected_ad_modules(["sp", "amazon_magic"])

    def test_allows_budget_only_path(self):
        self.assertEqual(normalize_selected_ad_modules([]), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
python3 -m unittest tests.test_workflow -v
```

Expected: `ModuleNotFoundError: No module named 'atlas_ads_workbench.workflow'`.

- [ ] **Step 3: Implement the smallest module normalizer**

```python
# src/atlas_ads_workbench/workflow.py
"""Stable workflow selection for progressive seller intake."""

from typing import Any, List


class WorkflowValidationError(ValueError):
    """Raised when the seller workflow selection is invalid."""


SUPPORTED_AD_MODULES = ("sp", "sb", "sd", "sd_cross_sell")


def normalize_selected_ad_modules(value: Any) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise WorkflowValidationError("selected_ad_modules must be an array of strings")
    unknown = sorted(set(value) - set(SUPPORTED_AD_MODULES))
    if unknown:
        raise WorkflowValidationError(
            "unsupported advertising module: %s" % ", ".join(unknown)
        )
    return [module for module in SUPPORTED_AD_MODULES if module in value]
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run:

```bash
python3 -m unittest tests.test_workflow -v
```

Expected: `Ran 3 tests` and `OK`.

- [ ] **Step 5: Add contract-v2 assertions before editing contracts**

```python
# Add to tests/test_public_contract.py
def test_decision_contract_v2_names_progressive_workflow_statuses(self):
    rules = (ROOT / "contracts" / "decision-rules.yaml").read_text("utf-8")
    schema = json.loads((ROOT / "contracts" / "output-schema.json").read_text("utf-8"))

    self.assertIn("contract_version: 2", rules)
    self.assertIn("selected_ad_modules", rules)
    self.assertIn("not_applicable", rules)
    statuses = schema["$defs"]["decision"]["properties"]["status"]["enum"]
    for status in (
        "not_applicable",
        "verification_required",
        "constraint_conflict",
    ):
        self.assertIn(status, statuses)
```

- [ ] **Step 6: Run the contract test and verify RED**

Run:

```bash
python3 -m unittest tests.test_public_contract.PublicContractTests.test_decision_contract_v2_names_progressive_workflow_statuses -v
```

Expected: FAIL because the existing contract is version 1 and lacks the new statuses.

- [ ] **Step 7: Upgrade the public contracts**

Change the YAML header and add an applicability section:

```yaml
contract_version: 2

workflow_selection:
  field: selected_ad_modules
  allowed_values: [sp, sb, sd, sd_cross_sell]
  empty_meaning: budget_only
  unselected_gate_status: not_applicable
```

Add `applies_when` to the SB and SD rules:

```yaml
  - id: SB-GATE-001
    version: 2
    applies_when:
      selected_ad_modules_contains_any: [sb]

  - id: SD-GATE-001
    version: 2
    applies_when:
      selected_ad_modules_contains_any: [sd, sd_cross_sell]
```

Replace the decision status enum in `contracts/output-schema.json` with:

```json
[
  "not_applicable",
  "information_required",
  "verification_required",
  "constraint_conflict",
  "ready_for_rule_evaluation",
  "review_required",
  "approved",
  "rejected"
]
```

Keep the schema’s top-level `schema_version` constant unchanged until the runtime begins emitting this general decision envelope; only the allowed vocabulary expands.

- [ ] **Step 8: Verify the contracts**

Run:

```bash
python3 -m unittest tests.test_public_contract tests.test_workflow -v
```

Expected: all public-contract and workflow tests pass.

- [ ] **Step 9: Commit**

```bash
git add contracts/decision-rules.yaml contracts/output-schema.json src/atlas_ads_workbench/workflow.py tests/test_workflow.py tests/test_public_contract.py
git commit -m "Define progressive workflow selection"
```

---

### Task 2: Make Gate evaluation selection-aware

**Files:**
- Modify: `src/atlas_ads_workbench/gates.py`
- Modify: `tests/test_gates.py`

**Interfaces:**
- Consumes: `selected_ad_modules: Sequence[str]` from Task 1.
- Produces: `evaluate_gates(intake, feasibility, context, selected_ad_modules=())`.
- Every Gate result adds `applicable: bool`, `seller_status: str`, and `seller_message: str`.
- FEASIBILITY returns `constraint_conflict` when the arithmetic conflicts.

- [ ] **Step 1: Write failing Gate-behavior tests**

```python
# Add to tests/test_gates.py
def test_budget_only_path_does_not_mark_sb_or_sd_as_missing(self):
    gates = evaluate_gates(
        current_intake,
        calculate_feasibility(current_intake),
        {},
        selected_ad_modules=[],
    )

    self.assertEqual(gates["SB-GATE-001"]["status"], "not_applicable")
    self.assertEqual(gates["SD-GATE-001"]["status"], "not_applicable")
    self.assertFalse(gates["SB-GATE-001"]["applicable"])

def test_only_selected_module_is_evaluated(self):
    gates = evaluate_gates(
        current_intake,
        calculate_feasibility(current_intake),
        {},
        selected_ad_modules=["sb"],
    )

    self.assertEqual(gates["SB-GATE-001"]["status"], "verification_required")
    self.assertEqual(gates["SD-GATE-001"]["status"], "not_applicable")

def test_feasibility_conflict_has_an_unambiguous_status(self):
    gate = evaluate_gates(
        current_intake,
        calculate_feasibility(current_intake),
        {},
        selected_ad_modules=[],
    )["FEASIBILITY-GATE-001"]

    self.assertEqual(gate["status"], "constraint_conflict")
    self.assertEqual(gate["seller_status"], "存在数值冲突")
```

- [ ] **Step 2: Run the Gate tests and verify RED**

Run:

```bash
python3 -m unittest tests.test_gates -v
```

Expected: errors for the unsupported `selected_ad_modules` argument and failures for the old statuses.

- [ ] **Step 3: Add a not-applicable result helper**

```python
def _not_applicable_gate(gate_id: str) -> Dict[str, Any]:
    return {
        "gate_id": gate_id,
        "version": 2,
        "applicable": False,
        "status": "not_applicable",
        "seller_status": "未选择",
        "seller_message": "你没有选择此广告类型，因此本次无需补充资料。",
        "passed_fields": [],
        "missing_fields": [],
        "stale_fields": [],
        "conflicting_fields": [],
        "next_action": {"type": "none", "label": "No action required."},
    }
```

- [ ] **Step 4: Separate seller-input gaps from verification gaps**

Update `_evidence_gate` to include applicability and choose a seller status:

```python
missing_external = [
    rule["field"]
    for rule in required
    if "verified" in rule.get("accepted_statuses", [])
    and rule["field"] in missing_fields
]
status = "verification_required" if missing_external else "information_required"
seller_status = "等待外部验证" if missing_external else "待补充资料"
```

Return:

```python
{
    "gate_id": gate_id,
    "version": 2,
    "applicable": True,
    "status": "ready_for_rule_evaluation" if not missing_fields else status,
    "seller_status": "资料已齐全" if not missing_fields else seller_status,
    "seller_message": (
        "资料已达到规则评估条件。"
        if not missing_fields
        else "只补充已选择广告类型所需的资料；系统不会猜测缺失证据。"
    ),
    # Preserve passed_fields, missing_fields, stale_fields,
    # conflicting_fields, and next_action from the current contract.
}
```

- [ ] **Step 5: Evaluate only selected SB/SD modules**

Change the signature:

```python
def evaluate_gates(
    intake: Mapping[str, Any],
    feasibility: Mapping[str, Any],
    context: Mapping[str, Any],
    selected_ad_modules: Sequence[str] = (),
) -> Dict[str, Dict[str, Any]]:
```

Select Gates:

```python
selected = set(selected_ad_modules)
sb_gate = (
    _evidence_gate("SB-GATE-001", SB_REQUIRED_EVIDENCE, context)
    if "sb" in selected
    else _not_applicable_gate("SB-GATE-001")
)
sd_gate = (
    _evidence_gate("SD-GATE-001", SD_REQUIRED_EVIDENCE, context)
    if selected.intersection({"sd", "sd_cross_sell"})
    else _not_applicable_gate("SD-GATE-001")
)
```

Keep the current requirement dictionaries, but extract them as module-level `SB_REQUIRED_EVIDENCE` and `SD_REQUIRED_EVIDENCE` constants so the selection branch does not duplicate them.

- [ ] **Step 6: Give feasibility a truthful status**

Set:

```python
has_conflict = not feasibility["is_feasible_at_benchmark"]
feasibility_gate = {
    "gate_id": "FEASIBILITY-GATE-001",
    "version": 2,
    "applicable": True,
    "status": "constraint_conflict" if has_conflict else "ready_for_rule_evaluation",
    "seller_status": "存在数值冲突" if has_conflict else "目标可行",
    "seller_message": (
        "预算可以计算，但当前 CPC、CVR、TACoS 与广告销售占比不能同时满足。"
        if has_conflict
        else "基础信息完整，当前假设下未检测到数值冲突。"
    ),
    # Preserve the existing evidence lists and next action.
}
```

- [ ] **Step 7: Run Gate tests and verify GREEN**

Run:

```bash
python3 -m unittest tests.test_gates -v
```

Expected: all Gate tests pass.

- [ ] **Step 8: Commit**

```bash
git add src/atlas_ads_workbench/gates.py tests/test_gates.py
git commit -m "Scope gates to selected ad modules"
```

---

### Task 3: Carry workflow selection through the localhost API and frozen runs

**Files:**
- Modify: `src/atlas_ads_workbench/server.py`
- Modify: `tests/test_server.py`

**Interfaces:**
- Consumes request envelope:

```json
{
  "intake": {},
  "selected_ad_modules": ["sp", "sb"],
  "evidence_context": {}
}
```

- Produces `_validated_workflow_request() -> tuple[intake, selected_ad_modules, evidence_context]`.
- Frozen decision plans record `selected_ad_modules`.

- [ ] **Step 1: Add failing API tests**

```python
def test_gates_only_evaluate_selected_modules(self):
    status, gates = self.request(
        "/api/gates",
        "POST",
        {
            "intake": valid_payload(),
            "selected_ad_modules": ["sb"],
            "evidence_context": {},
        },
        token="test-token",
    )

    self.assertEqual(status, 200)
    self.assertEqual(gates["SB-GATE-001"]["status"], "verification_required")
    self.assertEqual(gates["SD-GATE-001"]["status"], "not_applicable")

def test_run_freezes_selected_modules(self):
    status, manifest = self.request(
        "/api/runs",
        "POST",
        {
            "intake": valid_payload(),
            "selected_ad_modules": ["sp", "sd_cross_sell"],
            "evidence_context": {},
        },
        token="test-token",
    )
    _, run = self.request("/api/runs/%s" % manifest["run_id"], token="test-token")

    self.assertEqual(status, 201)
    self.assertEqual(
        run["decision_plan"]["selected_ad_modules"],
        ["sp", "sd_cross_sell"],
    )

def test_api_rejects_unknown_ad_module(self):
    with self.assertRaises(HTTPError) as error:
        self.request(
            "/api/gates",
            "POST",
            {
                "intake": valid_payload(),
                "selected_ad_modules": ["unsupported"],
                "evidence_context": {},
            },
            token="test-token",
        )

    self.assertEqual(error.exception.code, 400)
```

- [ ] **Step 2: Run server tests and verify RED**

Run:

```bash
python3 -m unittest tests.test_server.LocalServerTests.test_gates_only_evaluate_selected_modules tests.test_server.LocalServerTests.test_run_freezes_selected_modules tests.test_server.LocalServerTests.test_api_rejects_unknown_ad_module -v
```

Expected: failures because the server ignores `selected_ad_modules`.

- [ ] **Step 3: Parse the complete workflow envelope**

Import:

```python
from .workflow import WorkflowValidationError, normalize_selected_ad_modules
```

Replace `_validated_intake_and_context` with:

```python
def _validated_workflow_request(self):
    payload = self._read_object()
    if "intake" not in payload:
        return validate_intake(payload), [], {}
    raw_intake = payload.get("intake")
    raw_context = payload.get("evidence_context", {})
    selected = normalize_selected_ad_modules(payload.get("selected_ad_modules", []))
    captured_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return (
        validate_intake(raw_intake),
        selected,
        normalize_evidence_context(raw_context, captured_at),
    )
```

For draft PUT, unpack as:

```python
intake, _, _ = self._validated_workflow_request()
```

For POST, unpack as:

```python
intake, selected_ad_modules, evidence_context = self._validated_workflow_request()
```

- [ ] **Step 4: Propagate selection into Gates and snapshots**

Call:

```python
gates = evaluate_gates(
    intake,
    feasibility,
    evidence_context,
    selected_ad_modules=selected_ad_modules,
)
```

Add to `decision_plan`:

```python
"selected_ad_modules": selected_ad_modules,
```

Catch the new validation error:

```python
except (IntakeValidationError, EvidenceValidationError, WorkflowValidationError) as error:
    self._error(400, "bad_request", str(error))
```

- [ ] **Step 5: Run the server suite**

Run:

```bash
python3 -m unittest tests.test_server -v
```

Expected: all server tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/atlas_ads_workbench/server.py tests/test_server.py
git commit -m "Persist progressive workflow selection"
```

---

### Task 4: Rebuild the page as a progressive budget-first flow

**Files:**
- Modify: `assets/workbench.html`
- Modify: `tests/test_workbench_asset.py`

**Interfaces:**
- Section IDs: `basic-intake`, `feasibility-result`, `module-selection`, `strategy-evidence`, `review-plan`.
- Client state: `workflowState = { feasibility: null, selectedModules: new Set(), evidenceContext: {} }`.
- Primary first-step button: `计算目标预算`.

- [ ] **Step 1: Replace the old asset-contract assertion with failing progressive-flow assertions**

```python
def test_page_reveals_the_progressive_seller_workflow_in_order(self):
    page = ASSET.read_text(encoding="utf-8")

    section_ids = [
        'id="basic-intake"',
        'id="feasibility-result"',
        'id="module-selection"',
        'id="strategy-evidence"',
        'id="review-plan"',
    ]
    positions = [page.index(section_id) for section_id in section_ids]
    self.assertEqual(positions, sorted(positions))

    for text in (
        "计算目标预算",
        "目标月销售额",
        "月广告预算上限",
        "日广告预算上限",
        "选择下一步广告目标",
        "暂时只确认总预算",
        "完善广告框架资料",
    ):
        self.assertIn(text, page)

def test_sb_and_sd_evidence_sections_start_hidden(self):
    page = ASSET.read_text(encoding="utf-8")

    self.assertIn('data-module-evidence="sb" hidden', page)
    self.assertIn('data-module-evidence="sd" hidden', page)
    self.assertIn('data-module-evidence="sd_cross_sell" hidden', page)

def test_primary_flow_does_not_render_raw_gate_statuses(self):
    page = ASSET.read_text(encoding="utf-8")

    self.assertNotIn("ready_for_rule_evaluation</b>", page)
    self.assertIn("查看规则与证据详情", page)
```

- [ ] **Step 2: Run the asset tests and verify RED**

Run:

```bash
python3 -m unittest tests.test_workbench_asset -v
```

Expected: failures because the current page is an all-at-once form.

- [ ] **Step 3: Create the five sequential sections**

Use this page backbone:

```html
<section class="panel workflow-step" id="basic-intake">
  <div class="step-label">第 1 步 · 基础目标</div>
  <h2>先计算你能承受的广告预算</h2>
  <form id="intake-form">
    <!-- Keep the existing basic intake controls only. -->
    <div class="actions">
      <button class="secondary" type="button" id="save">保存草稿</button>
      <button class="primary" type="submit">计算目标预算</button>
    </div>
  </form>
</section>

<section class="panel workflow-step" id="feasibility-result" hidden aria-live="polite">
  <div class="step-label">第 2 步 · 预算与可行性</div>
  <h2>你的目标预算</h2>
  <div id="feasibility-summary"></div>
  <details>
    <summary>查看计算公式和可调整杠杆</summary>
    <div id="feasibility-details"></div>
  </details>
</section>

<section class="panel workflow-step" id="module-selection" hidden>
  <div class="step-label">第 3 步 · 选择广告目标</div>
  <h2>你接下来希望搭建哪些广告？</h2>
  <div class="module-grid" id="module-options"></div>
  <button class="primary" type="button" id="continue-to-evidence">继续完善方案</button>
  <button class="secondary" type="button" id="budget-only">暂时只确认总预算</button>
</section>

<section class="panel workflow-step" id="strategy-evidence" hidden>
  <div class="step-label">第 4 步 · 详细资料</div>
  <h2>完善广告框架资料</h2>
  <p class="sub">只填写你选择的广告类型所需内容。</p>
  <div data-module-evidence="sp" hidden></div>
  <div data-module-evidence="sb" hidden></div>
  <div data-module-evidence="sd" hidden></div>
  <div data-module-evidence="sd_cross_sell" hidden></div>
  <button class="primary" type="button" id="review-evidence">检查所选广告资料</button>
</section>

<section class="panel workflow-step" id="review-plan" hidden>
  <div class="step-label">第 5 步 · 审核并生成</div>
  <h2>广告框架审核</h2>
  <div id="selected-gate-summary"></div>
  <button class="primary" type="button" id="generate-report">生成演示报告</button>
  <details>
    <summary>查看规则与证据详情</summary>
    <div id="technical-gate-details"></div>
  </details>
</section>
```

Move the existing supplemental fields out of the basic form and into the matching module evidence containers.

- [ ] **Step 4: Add seller-facing advertising module cards**

```javascript
const AD_MODULES = [
  {id:'sp', title:'SP 基础投放', description:'验证关键词和商品投放方向。'},
  {id:'sb', title:'SB 品牌推广', description:'用于品牌防守、品牌词或品类词推广。'},
  {id:'sd', title:'SD 再营销', description:'面向浏览或购买行为进行再营销。'},
  {id:'sd_cross_sell', title:'SD 老品导流', description:'通过相关老品为新品引流。'}
];

const workflowState = {
  feasibility: null,
  selectedModules: new Set(),
  evidenceContext: {}
};

document.querySelector('#module-options').innerHTML = AD_MODULES.map(module => `
  <label class="module-card">
    <input type="checkbox" value="${module.id}" data-ad-module>
    <strong>${module.title}</strong>
    <span>${module.description}</span>
  </label>
`).join('');
```

- [ ] **Step 5: Make form submission calculate budget only**

```javascript
form.addEventListener('submit', async event => {
  event.preventDefault();
  try {
    tell('正在计算目标预算…');
    const result = await api('/api/feasibility', {
      method:'POST',
      body:JSON.stringify(payload())
    });
    workflowState.feasibility = result;
    renderFeasibility(result);
    revealStep('feasibility-result');
    revealStep('module-selection');
    tell(
      result.is_feasible_at_benchmark
        ? '基础预算已计算，当前假设下未检测到冲突。'
        : '基础预算已计算，但当前假设存在数值冲突。'
    );
  } catch(error) {
    tell(error.message, true);
  }
});
```

`renderFeasibility` must render the four primary values first:

```javascript
function renderFeasibility(result){
  document.querySelector('#feasibility-summary').innerHTML = `
    <div class="metric"><span>目标月销售额</span><b>${money(result.monthly_revenue_target_usd)}</b></div>
    <div class="metric"><span>月广告预算上限</span><b>${money(result.monthly_ad_spend_cap_usd)}</b></div>
    <div class="metric"><span>日广告预算上限</span><b>${money(result.daily_ad_spend_cap_usd)}</b></div>
    <div class="metric"><span>所需 CVR / 当前 CVR</span><b>${percent(result.required_cvr_percent)} / ${percent(result.benchmark_cvr_percent)}</b></div>
  `;
  document.querySelector('#feasibility-details').innerHTML = renderLevers(result);
}
```

- [ ] **Step 6: Reveal only selected evidence sections**

```javascript
document.querySelector('#continue-to-evidence').addEventListener('click', () => {
  workflowState.selectedModules = new Set(
    [...document.querySelectorAll('[data-ad-module]:checked')].map(input => input.value)
  );
  if (!workflowState.selectedModules.size) {
    tell('请选择至少一种广告类型，或点击“暂时只确认总预算”。', true);
    return;
  }
  document.querySelectorAll('[data-module-evidence]').forEach(section => {
    section.hidden = !workflowState.selectedModules.has(section.dataset.moduleEvidence);
  });
  revealStep('strategy-evidence');
});
```

The budget-only action sets an empty selection and reveals the review step with:

```text
本次只确认总预算；未选择 SB 或 SD，因此无需补充对应资料。
```

- [ ] **Step 7: Run asset tests and verify GREEN**

Run:

```bash
python3 -m unittest tests.test_workbench_asset -v
```

Expected: all asset-contract tests pass.

- [ ] **Step 8: Commit**

```bash
git add assets/workbench.html tests/test_workbench_asset.py
git commit -m "Add budget-first seller workflow"
```

---

### Task 5: Render seller-facing readiness separately from technical Gate details

**Files:**
- Modify: `assets/workbench.html`
- Modify: `tests/test_workbench_asset.py`
- Modify: `tests/test_server.py`

**Interfaces:**
- Request payload includes `selected_ad_modules`.
- Primary summary statuses: `目标可行`, `存在数值冲突`, `待补充资料`, `等待外部验证`, `资料已齐全`, `未选择`.
- Technical details retain Gate ID, version, internal status, passed fields, missing fields, and conflicts.

- [ ] **Step 1: Add failing UI contract assertions**

```python
def test_page_separates_seller_readiness_from_technical_gate_details(self):
    page = ASSET.read_text(encoding="utf-8")

    for text in (
        "存在数值冲突",
        "待补充资料",
        "等待外部验证",
        "资料已齐全",
        "未选择",
        "technical-gate-details",
        "seller_status",
        "seller_message",
    ):
        self.assertIn(text, page)

    self.assertIn("selected_ad_modules", page)
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
python3 -m unittest tests.test_workbench_asset.WorkbenchAssetContractTests.test_page_separates_seller_readiness_from_technical_gate_details -v
```

Expected: FAIL because the current page renders raw Gate data.

- [ ] **Step 3: Send selected modules to Gate evaluation**

```javascript
const gatePayload = () => ({
  intake: payload(),
  selected_ad_modules: [...workflowState.selectedModules],
  evidence_context: evidenceContext()
});
```

- [ ] **Step 4: Render a primary seller summary**

```javascript
function renderSellerGateSummary(gates){
  const applicable = Object.values(gates).filter(gate => gate.applicable);
  document.querySelector('#selected-gate-summary').innerHTML = applicable.map(gate => `
    <article class="readiness-card readiness-${escapeHtml(gate.status)}">
      <strong>${escapeHtml(gate.seller_status)}</strong>
      <p>${escapeHtml(gate.seller_message)}</p>
    </article>
  `).join('');
}
```

Do not render `passed_fields` or internal status names in this primary summary.

- [ ] **Step 5: Render expandable technical evidence**

```javascript
function renderTechnicalGateDetails(gates){
  document.querySelector('#technical-gate-details').innerHTML =
    Object.values(gates).map(gate => `
      <article class="metric">
        <span>
          <b>${escapeHtml(gate.gate_id)} · v${gate.version}</b><br>
          internal status: ${escapeHtml(gate.status)}
        </span>
        <div class="lever">
          已满足：${escapeHtml(gate.passed_fields.join('、') || '无')}<br>
          待补充：${escapeHtml(gate.missing_fields.join('、') || '无')}<br>
          冲突：${escapeHtml(gate.conflicting_fields.join('、') || '无')}
        </div>
      </article>
    `).join('');
}
```

- [ ] **Step 6: Keep report generation possible but visibly constrained**

Before calling `/api/demo-report`, call `/api/gates` with `gatePayload()`. Render the Gate summary, then allow the fixed demo report while preserving:

```text
演示报告可以生成，但存在冲突或待验证资料的模块不得描述为可执行广告建议。
```

Do not generate real Campaign allocations for blocked modules. The existing fixed demo rows retain their “演示” label.

- [ ] **Step 7: Run page and server tests**

Run:

```bash
python3 -m unittest tests.test_workbench_asset tests.test_server -v
```

Expected: all page and server tests pass.

- [ ] **Step 8: Commit**

```bash
git add assets/workbench.html tests/test_workbench_asset.py tests/test_server.py
git commit -m "Separate readiness from gate diagnostics"
```

---

### Task 6: Update documentation and coaching copy

**Files:**
- Modify: `README.md`
- Modify: `SKILL.md`
- Modify: `docs/architecture/decision-contract.md`
- Modify: `tests/test_public_contract.py`

**Interfaces:**
- Public workflow phrase: `基础输入 → 预算与可行性 → 选择广告目标 → 补充证据 → 审核并生成`.
- Evidence-state copy distinguishes seller confirmation from external verification.

- [ ] **Step 1: Write failing documentation assertions**

```python
def test_public_docs_explain_the_progressive_seller_workflow(self):
    readme = (ROOT / "README.md").read_text("utf-8")
    skill = (ROOT / "SKILL.md").read_text("utf-8")
    decision_contract = (
        ROOT / "docs" / "architecture" / "decision-contract.md"
    ).read_text("utf-8")

    workflow = "基础输入 → 预算与可行性 → 选择广告目标 → 补充证据 → 审核并生成"
    self.assertIn(workflow, readme)
    self.assertIn(workflow, skill)
    self.assertIn("未选择的广告类型不执行 Gate", decision_contract)
    self.assertIn("卖家已填写不等于外部已验证", decision_contract)
```

- [ ] **Step 2: Run the documentation test and verify RED**

Run:

```bash
python3 -m unittest tests.test_public_contract.PublicContractTests.test_public_docs_explain_the_progressive_seller_workflow -v
```

Expected: FAIL because the current documentation describes a one-click demo path.

- [ ] **Step 3: Update README**

Add:

```markdown
## 渐进式卖家工作流

工作台按照 `基础输入 → 预算与可行性 → 选择广告目标 → 补充证据 → 审核并生成` 展开。

基础输入完成后，系统只计算卖家目标对应的销售额、月广告预算、日预算与可行性。SB、SD 和老品导流资料只有在卖家选择对应广告目标后才会出现。未选择的广告类型不执行 Gate，也不会被显示成“信息不完整”。
```

- [ ] **Step 4: Update SKILL coaching instructions**

Replace the direct one-click instruction with:

```markdown
4. 引导卖家先完成基础输入并点击“计算目标预算”。
5. 解释目标预算、所需 CVR、卖家假设 CVR 和可调整杠杆。
6. 让卖家选择需要搭建的广告类型；不要默认要求完成全部 SB/SD 资料。
7. 只收集所选广告类型需要的卖家信息和外部证据。
8. 明确区分“卖家已填写”“等待外部验证”“资料已验证”和“不适用”。
9. 最终报告继续显示模型调用、外部数据使用、规则版本和不可执行边界。
```

- [ ] **Step 5: Update the decision contract**

Add:

```markdown
## Gate 的适用范围

未选择的广告类型不执行 Gate，状态记录为 `not_applicable`。这不是缺少资料。

卖家已填写不等于外部已验证。卖家填写的品牌、ASIN、库存或毛利可以记录为 `confirmed`；账户资格、品牌注册资格和广告展示资格只有授权外部来源才能记录为 `verified`。
```

- [ ] **Step 6: Run public contract tests**

Run:

```bash
python3 -m unittest tests.test_public_contract tests.test_skill_contract -v
```

Expected: all public and Skill contract tests pass.

- [ ] **Step 7: Commit**

```bash
git add README.md SKILL.md docs/architecture/decision-contract.md tests/test_public_contract.py
git commit -m "Document progressive seller journey"
```

---

### Task 7: Verify the complete happy path

**Files:**
- Modify only if a failing verification reveals a defect in the files owned by Tasks 1–6.

**Interfaces:**
- Happy path A: budget only.
- Happy path B: SP selected without external targeting evidence.
- Happy path C: SB selected with seller-confirmed fields but external eligibility still pending.
- Happy path D: feasibility conflict continues into a non-executable demo report.

- [ ] **Step 1: Run the complete automated suite**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: all tests pass with zero failures and zero errors.

- [ ] **Step 2: Launch the local workbench**

Run:

```bash
python3 scripts/launch_workbench.py --no-browser
```

Expected: one loopback URL containing a dynamic local port and a URL-fragment session token, followed by a running local server.

- [ ] **Step 3: Verify budget-only interaction**

In the browser:

1. Keep the default basic inputs.
2. Click `计算目标预算`.
3. Confirm the page first shows target monthly revenue, monthly budget, daily budget, and required/current CVR.
4. Confirm no SB or SD missing-field warning is visible.
5. Click `暂时只确认总预算`.
6. Confirm the review step says no advertising modules were selected.

- [ ] **Step 4: Verify selected-module interaction**

In the same local page:

1. Select only `SB 品牌推广`.
2. Continue to evidence.
3. Confirm only the SB evidence section is visible.
4. Check selected advertising information.
5. Confirm SB says `等待外部验证`.
6. Confirm SD is absent from the seller summary.
7. Expand technical details and confirm SD is `not_applicable`.

- [ ] **Step 5: Verify the conflict remains visible**

Use the existing default seller assumptions that produce a required CVR above the seller CVR. Confirm:

- the total budget remains visible;
- the primary feasibility status is `存在数值冲突`;
- the three adjustment levers remain visible in details;
- the generated demo report remains `不可直接执行`;
- model calls remain `0`;
- external data remains `未使用`.

- [ ] **Step 6: Inspect the saved run**

Open the latest local run and confirm its decision plan contains:

```json
{
  "selected_ad_modules": ["sb"],
  "external_data_used": false,
  "model_calls": 0
}
```

Confirm the Gate snapshot includes version 2, the feasibility conflict, SB verification gaps, and SD `not_applicable`.

- [ ] **Step 7: Run repository hygiene checks**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; only intentional implementation changes are present before the final commit.

- [ ] **Step 8: Close verification**

If Step 1–7 exposes a defect, return to the task that owns that behavior, add a failing regression test there, complete its red-green cycle, and then repeat Task 7 from Step 1. If no defect is found, do not create an empty commit.

---

## Release Slices

### Release 1 — Now: Interaction clarity

- Budget-first progressive sections.
- Seller-facing feasibility result.
- Explicit module selection.
- Selection-aware SB/SD Gates.
- Separate seller readiness from technical diagnostics.
- No new external data connection.

### Release 2 — Next: Manual evidence intake

- Search Term and Campaign report upload.
- Keyword and product-targeting evidence normalization.
- Evidence source, captured time, and validation-state display.
- Real campaign draft only after targeting evidence exists.

### Release 3 — Later: Authorized data and delivery

- Amazon Ads, catalog, and inventory MCP adapters.
- Verified eligibility fields.
- XLSX and Markdown delivery artifacts.
- Human approval and agent-memory handoff.

Release 2 and Release 3 are intentionally excluded from this implementation plan. They require separate contracts and independent implementation plans after Release 1 is validated with sellers.
