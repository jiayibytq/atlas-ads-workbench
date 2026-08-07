# Skill Self-Update and Model Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an installed Atlas Ads skill update itself from its Git remote when the user asks in chat, while documenting enforceable Luna/Sol model-routing and permission boundaries.

**Architecture:** The installed skill remains a Git checkout (including clone, symlink, and worktree layouts). `scripts/update_skill.py` discovers its own checkout, refuses dirty or ambiguous sources, fetches the configured ref, validates the prospective commit in a temporary worktree, then performs a fast-forward only. A repository contract and SKILL instructions define L0 deterministic work, Luna/Terra for simple work, Sol for difficult work and orchestration, and user approval for external or executable actions.

**Tech Stack:** Python 3 standard library, Git CLI, Markdown, YAML/JSON contracts, `unittest`.

## Global Constraints

- Do not depend on a fixed installation path; resolve the repository with `git rev-parse --show-toplevel`.
- Do not update a dirty checkout, an unknown remote, a diverged ref, or a detached checkout without configured source metadata.
- Validate the prospective commit before changing the active checkout; use fast-forward-only integration.
- A failed update must leave the previous active commit unchanged.
- L0 deterministic tasks use no model; simple tasks use Luna (runtime mapping: `gpt-5.6-terra`); difficult reasoning and final review use Sol (`gpt-5.6-sol`).
- Sol may delegate at most three independent read-only or isolated Luna sub-agents; Sol owns synthesis, writes, external actions, and final approval.
- Real seller data, external MCP/API access, account mutations, or executable campaign actions require Sol plus explicit user approval.
- Every update and delegated run reports version/model/source evidence; never claim an unverified update or recommendation.

---

### Task 1: Add model-routing and permission contracts

**Files:**
- Create: `contracts/model-routing.yaml`
- Create: `docs/model-routing-policy.md`
- Modify: `SKILL.md`
- Test: `tests/test_model_routing_contract.py`

**Interfaces:** The YAML contract is the machine-readable source; the Markdown and SKILL sections are the agent-facing explanation. Tests must verify the exact model mappings, L0 no-model rule, three-Luna ceiling, Sol review boundary, and user-approval boundary.

- [ ] Write tests that parse the contract text and assert required task levels, model names, limits, and permission phrases.
- [ ] Run `python3 -m unittest tests.test_model_routing_contract -v`; expect failure because the contract does not exist.
- [ ] Add the YAML contract and a pedagogical policy with examples and anti-patterns.
- [ ] Add an “更新 Skill” trigger and model-routing section to `SKILL.md`; state that the current session must be restarted after a successful update.
- [ ] Run the focused test and the existing skill contract tests; commit as `docs: define model routing and update permissions`.

### Task 2: Implement safe self-update command

**Files:**
- Create: `scripts/update_skill.py`
- Create: `skill-source.json`
- Test: `tests/test_skill_updater.py`

**Interfaces:** `python3 scripts/update_skill.py --check [--json]` reports source/current/target status without mutation. `python3 scripts/update_skill.py --update [--json]` fetches, validates in a temporary worktree, and fast-forwards. JSON output includes `status`, `current_commit`, `target_commit`, `source`, `validation`, and `changed`.

- [ ] Add fixture helpers that create a temporary bare remote and clone with `subprocess`; cover clean fast-forward, dirty checkout refusal, diverged history refusal, missing remote/ref refusal, and validation failure preserving `HEAD`.
- [ ] Run `python3 -m unittest tests.test_skill_updater -v`; expect failure because the updater is absent.
- [ ] Implement Git discovery with `git rev-parse`, remote/ref metadata, `fetch`, ancestor checks, temporary worktree validation, and `merge --ff-only`; use no shell interpolation.
- [ ] Add `skill-source.json` with the canonical `origin` remote and `main` stable ref, while allowing a valid checkout to use its own configured remote URL.
- [ ] Run focused updater tests and the full suite; commit as `feat: add safe skill self-update command`.

### Task 3: Document installation and update handoff

**Files:**
- Modify: `README.md`
- Modify: `CONTRIBUTING.md`
- Modify: `tests/test_public_contract.py`

**Interfaces:** Documentation must show installation as a Git checkout and the natural-language invocation “请帮我更新 Atlas Ads skill”. It must explain that successful updates require a new chat session to load the new SKILL.md and show the evidence returned by the updater.

- [ ] Add the install/update flow, failure behavior, source metadata, and release guidance to README.
- [ ] Add contributor guidance: push commits/tags to the configured remote; do not publish unvalidated main changes.
- [ ] Extend public-contract tests to require the update command, clean-checkout boundary, and session-restart notice.
- [ ] Run `python3 -m unittest discover -s tests -v` and `git diff --check`; commit as `docs: document skill update lifecycle`.

### Task 4: Whole-branch review and PR update

**Files:**
- Review: all changes from the branch base through `HEAD`

- [ ] Generate a review package with `scripts/review-package $(git merge-base origin/main HEAD) HEAD`.
- [ ] Dispatch a Sol whole-branch reviewer with the exact global constraints above.
- [ ] Fix all Critical/Important findings with one Luna implementation pass where possible, then re-review.
- [ ] Push the execution branch to the existing draft PR and verify the remote head SHA and checks.
