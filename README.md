# agent-completion-gate

<p align="center">
  <img src="assets/banner.svg" alt="agent-completion-gate — a fail-closed completion gate that stops agents marking work done that isn't" width="100%">
</p>

<p align="center">
  <strong>English</strong> · <a href="README.zh.md">中文</a>
</p>

<p align="center">
  <img alt="skill" src="https://img.shields.io/badge/agent--skill-agent--completion--gate-1f6feb">
  <img alt="version" src="https://img.shields.io/badge/version-0.2.0-informational">
  <img alt="works with" src="https://img.shields.io/badge/Claude%20Code%20%C2%B7%20Codex%20%C2%B7%20any%20agent-444">
  <a href="https://github.com/zhjai/agent-memory"><img alt="depends" src="https://img.shields.io/badge/depends%20on-agent--memory-orange"></a>
  <a href="LICENSE"><img alt="license" src="https://img.shields.io/badge/license-MIT-yellow"></a>
</p>

> **Stop agents from marking work "done" that isn't.** A fail-closed completion gate + a four-state machine: a worker can only *propose* done — an external verifier grants it. Built on [`agent-memory`](https://github.com/zhjai/agent-memory). Works with **any** Agent-Skills host — Claude Code, Codex, and others — not a single vendor.

## The failure it prevents (30 seconds)

A goal-driven agent finishes a long task and declares success — "plan executed, tests pass." But it shipped with the case display turned off, run names colliding, and the val curve a single point. **The agent had all that in context; the goal just didn't treat it as a completion criterion.** Rules and skills don't fix this (a goal rationalizes past advice). A gate it can't edit does.

```
# worker proposes done (it can only reach candidate_complete, never complete):
state: candidate_complete

$ check_acceptance --manifest <protected>/acceptance_manifest.yaml \
                   --inventory <protected>/surface_inventory.yaml \
                   --candidate state/<task>/completion_candidate.yaml --repo .
  FAIL  case_examples_present:     max_case_examples=0 (must not be disabled)
  FAIL  val_curve_non_degenerate:  val/mae points=1 (min 2)
  BLOCK needs-review:              dashboard_readability
  → BLOCKED. state stays 'blocked'. 'complete' is NOT granted.

# worker fixes the real artifacts, re-runs; external verifier then grants:
state: complete
```

The gate reads **real artifacts** (actual config, actual metrics), not the agent's self-report — so the agent can't talk its way to done.

## Why a gate, not a rule / skill / memory

- A **rule** is advisory — a goal rationalizes past it.
- A **skill** can be skipped — the agent chooses not to invoke it.
- **memory** records belief, not verified truth.
- Only a **gate the agent can't edit, on a path it can't skip, reading artifacts it can't fake** reliably stops "looks done but isn't."

## Four-state machine

```
in_progress ──► candidate_complete ──►(EXTERNAL verifier)──► complete
     │                                                     └─► blocked
     └────────► blocked  (needs-review / unknown surface / missing evidence)
```

Worker can only reach `candidate_complete` or `blocked`. **Only an external verifier writes `complete`.** **`needs-review == blocked`** (not an annotation the agent can set and move on). The kit ships the **check, the contract, and the wiring**: `check_acceptance.py` returns a verdict; [`gate/verify_completion.sh`](gate/verify_completion.sh) enforces the state machine around it (rejects a worker that wrote `complete` itself; grants `complete` only on a clean pass); and [`integrations/`](integrations/) attaches it as a **CI required check** (the authority), an **agent Stop-hook**, and a **pre-push** hook. See [`STATE_MACHINE.md`](STATE_MACHINE.md).

## Depends on agent-memory (the gate uses memory)

The gate is the enforcement layer; [`agent-memory`](https://github.com/zhjai/agent-memory) is its foundation:

- The gate's **protected completion spec** — `acceptance_manifest.yaml` + `control/surface_inventory.yaml` — is **bundled in this repo**, kept read-only, **outside the agent-writable workspace and outside any lesson-promotion path**, so a worker can't weaken the gate via a promoted "lesson".
- It reads `agent-memory`'s **read-only `control/`** for the project's **rules and approved lessons** (the policy layer the gate must honor) — human/CI-maintained, never worker-writable.
- The gate **never** trusts agent-memory's worker-writable `state/` (run_state) as truth — it inspects real artifacts.
- Install `agent-memory` first; this kit layers on top.

## Non-negotiable principles (each closed a real bypass found in heterogeneous review)

1. Gate + manifest + inventory are **protected** (read-only, outside the agent-writable workspace, outside the lesson-promotion path).
2. Inspect **real artifacts**, never `run_state`.
3. **Unknowns fail closed** — a touched user-visible surface with no passing check → blocked. (The default reads the worker's self-reported `touched_surfaces`; run `--strict-surfaces`, or feed a diff-derived candidate, so this rule doesn't trust the worker.)
4. **One canonical completion signal** (the gate's verdict); chat / PR / dashboard derive from it, never become an independent "complete".
5. **Artifact content is hostile data, not instructions** — deterministic checks first; an LLM verifier treats artifacts as untrusted (else a worker writes "mark complete" into a file and injects it).
6. **Hermetic execution** — a read-only script isn't enough; pin env (PYTHONPATH / sitecustomize / conftest / generated configs).

## Install

The `skills` CLI installs **skills, not repo dependencies** — install the base first:

```bash
# 1. base (the gate's check spec reads agent-memory's read-only control/):
npx skills add zhjai/agent-memory -g -a claude-code
# 2. then the gate:
npx skills add zhjai/agent-completion-gate -g -a claude-code
```

Not a Claude Code user? Swap the host — the skill is agent-agnostic:

```bash
npx skills add zhjai/agent-memory -g -a codex   # Codex
npx skills add zhjai/agent-completion-gate -g -a codex
# … or any other Agent-Skills host (the gate is a plain Python script + file conventions)
```

> Dependency boundary: this repo **bundles** its own `gate/` + `surface_inventory.yaml`; **project-specific completion rules and approved lessons live in `agent-memory`'s read-only `control/`**, which the gate reads as its spec. Pin a compatible `agent-memory` version.

## Status

`v0.2.0` preview. MIT. Agent-agnostic, file-based, fail-closed. Foundation: [`agent-memory`](https://github.com/zhjai/agent-memory).
