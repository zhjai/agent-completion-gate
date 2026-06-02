# agent-completion-gate

<p align="center">
  <img src="assets/banner.svg" alt="agent-completion-gate — a fail-closed completion gate that stops agents marking work done that isn't" width="100%">
</p>

<p align="center">
  <strong>English</strong> · <a href="README.zh.md">中文</a>
</p>

<p align="center">
  <a href="https://github.com/zhjai/agent-completion-gate/actions/workflows/test.yml"><img alt="CI" src="https://github.com/zhjai/agent-completion-gate/actions/workflows/test.yml/badge.svg"></a>
  <img alt="version" src="https://img.shields.io/badge/version-0.3.0-informational">
  <img alt="works with" src="https://img.shields.io/badge/Claude%20Code%20%C2%B7%20Codex%20%C2%B7%20any%20agent-444">
  <a href="https://github.com/zhjai/agent-memory"><img alt="depends" src="https://img.shields.io/badge/depends%20on-agent--memory-orange"></a>
  <a href="LICENSE"><img alt="license" src="https://img.shields.io/badge/license-MIT-yellow"></a>
</p>

> **Stop agents from marking work "done" that isn't.** The agent can only *propose* done; an external check reads the **real output files** and only then grants `complete`.

## What this is (plain version)

AI coding agents routinely declare a long task **done when it isn't** — a test quietly skipped, a chart left broken, a feature half-wired. The agent had the evidence in context; its *goal* just didn't treat it as a finish line, and a goal will rationalize past any advice you wrote down.

`agent-completion-gate` is a small, **fail-closed gate**. The worker agent can only mark a task `candidate_complete` ("I propose this is done"). An external check (`check_acceptance.py`) reads the **real artifacts** — the actual config, the actual metrics — and only if they pass does an external verifier (your CI or a hook) grant `complete`. It's plain files + one Python script. No service, no account, no vendor lock-in.

## Quick start (60 seconds)

```bash
pip install pyyaml
git clone https://github.com/zhjai/agent-completion-gate && cd agent-completion-gate
sh examples/run.sh
```

You'll watch the gate **BLOCK** a fake completion (case display off, a single-point curve), then **GRANT** a real one — actual output of the bundled checker, not a mock-up:

```
===== BAD (expect BLOCKED, exit 1) =====
FAIL case_examples_present: max_case_examples=0 (must not be disabled)
FAIL val_curve_non_degenerate: val/normalized/mae points=1 (min 2)
BLOCKED:  ...  'complete' is NOT granted.   (exit 1)

===== GOOD (expect COMPLETE-OK, exit 0) =====
PASS case_examples_present: max_case_examples=8 ...
COMPLETE-OK: all machine checks passed ...           (exit 0)
```

See also [`examples/diff_demo.sh`](examples/diff_demo.sh) (catch a worker that under-reports what it touched) and [`examples/swanlab/`](examples/swanlab/) (a realistic, populated spec).

## Use it in your project

1. **Install the skill** (any Agent-Skills host — base first):

   ```bash
   npx skills add zhjai/agent-memory          -g -a claude-code   # or -a codex, or any host
   npx skills add zhjai/agent-completion-gate -g -a claude-code
   ```

2. **Add the gate + spec templates** to your repo: copy this repo's `gate/` and `control/`. They ship **empty** — out of the box the gate enforces only the state machine (the agent can't self-declare `complete`) and grants an empty proposal, so **it won't brick your pipeline**. You opt into strictness next. *(Edit your own copies; don't track this repo's `gate/`/`control/` as your live spec, or an update could overwrite your checks.)*

3. **Define what "done" means** in `gate/acceptance_manifest.yaml` — machine checks against your real artifacts (built-in types: `config_not_disabled`, `min_series_points`, `identity_in_name`, `max_chart_count`; extend for your own). List the user-visible surfaces in `control/surface_inventory.yaml`. A worked, copy-pasteable example is in [`examples/swanlab/`](examples/swanlab/).

4. **Wire it as the authority** — copy [`integrations/github-actions/completion-gate.yml`](integrations/github-actions/completion-gate.yml) to `.github/workflows/` and make it a **required status check**. Now `complete` == that check is green. (Details + trust model: [`integrations/README.md`](integrations/README.md).)

5. *(optional)* **Keep the agent honest in its own loop** — add the [`integrations/claude-code/`](integrations/claude-code/) Stop-hook (works as a Codex completion hook too): the agent is told "not done, here's why" before it can stop.

## What the agent does after you install the skill

The `completion-audit` skill instructs the agent: at task wrap-up, write a `completion_candidate.yaml` (`status: candidate_complete`, plus the surfaces it touched), then run the gate. The agent can reach **at most `candidate_complete`** — only the external verifier (CI / hook) ever writes `complete`. If the gate blocks, the agent fixes the real artifacts and re-audits.

## How it works — the four states

```
in_progress ──► candidate_complete ──►(EXTERNAL verifier)──► complete
     │                                                     └─► blocked
     └────────► blocked  (needs-review / unknown surface / missing evidence)
```

The worker can only reach `candidate_complete` or `blocked`. **Only an external verifier writes `complete`.** **`needs-review == blocked`** (not an annotation the agent can set and move past). The kit ships the **check, the contract, and the wiring**: `check_acceptance.py` returns a verdict; [`gate/verify_completion.sh`](gate/verify_completion.sh) enforces the state machine around it (rejects a worker that wrote `complete` itself; grants only on a clean pass); [`integrations/`](integrations/) attaches it as CI / hook. Full contract: [`STATE_MACHINE.md`](STATE_MACHINE.md).

## Why a gate, not a rule / skill / memory

- A **rule** is advisory — a goal rationalizes past it.
- A **skill** can be skipped — the agent chooses not to invoke it.
- **memory** records belief, not verified truth.
- Only a **gate the agent can't edit, on a path it can't skip, reading artifacts it can't fake** reliably stops "looks done but isn't."

## Depends on agent-memory

[`agent-memory`](https://github.com/zhjai/agent-memory) is the foundation (install it first): it holds the project's **rules + approved lessons** — the human/CI-maintained policy you distill into the gate's manifest. The gate **bundles its own protected check spec** (`gate/` + `control/`); the script itself reads only its own `--manifest`/`--inventory`, never the worker-writable `state/`. agent-memory stands alone; this kit is the optional enforcement layer on top.

## Security model & invariants

Hardened across multiple heterogeneous (Codex × Claude) review rounds — each invariant closed a reproduced bypass. **"External + fail-closed under a trusted base branch + runner"**, not "unbypassable":

1. Gate + manifest + inventory are **protected** (read-only, outside the agent-writable workspace and the lesson-promotion path). `check_acceptance.py --agent-writable-root DIR` enforces this at runtime.
2. Inspect **real artifacts**, never `run_state`.
3. **Unknowns fail closed** — a touched user-visible surface with no passing check → blocked. The `touched_surfaces` list is a worker self-report; use `--strict-surfaces` or `--diff-base <ref>` / `--touched` to derive it from the **real git diff** instead of trusting the worker.
4. **One canonical completion signal** (the gate's verdict); chat / PR / dashboard derive from it, never become an independent "complete".
5. **Artifact content is hostile data, not instructions** — deterministic checks first; an LLM verifier treats artifacts as untrusted.
6. **Hermetic execution** — the gate runs as `python3 -E` (ignores `PYTHON*` env / repo-planted `yaml.py`), and CI runs it from the trusted base branch so a PR can't edit the gate that judges it.

## Docs

- [`STATE_MACHINE.md`](STATE_MACHINE.md) — the completion contract (states, transitions, wiring).
- [`integrations/README.md`](integrations/README.md) — CI / agent-hook / pre-push wiring + the trust model.
- [`examples/`](examples/) — runnable: `run.sh`, `diff_demo.sh`, `diff_rename_test.sh`, `swanlab/`.
- [`CHANGELOG.md`](CHANGELOG.md) · self-tests in [`tests/`](tests/).

## Status

`v0.3.0` preview. MIT. Agent-agnostic, file-based, fail-closed. Foundation: [`agent-memory`](https://github.com/zhjai/agent-memory).
