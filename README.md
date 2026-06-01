# agent-completion-gate

> **Stop agents from marking work "done" that isn't.** A fail-closed completion gate + a four-state machine: a worker can only *propose* done — an external verifier grants it. Built on [`agent-memory`](https://github.com/zhjai/agent-memory).

## The failure it prevents (30 seconds)

A goal-driven agent finishes a long task and declares success — "plan executed, tests pass." But it shipped with the case display turned off, run names colliding, and the val curve a single point. **The agent had all that in context; the goal just didn't treat it as a completion criterion.** Rules and skills don't fix this (a goal rationalizes past advice). A gate it can't edit does.

```
# worker proposes done (it can only reach candidate_complete, never complete):
state: candidate_complete

$ check_acceptance --manifest <protected>/acceptance_manifest.yaml --repo .
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

Worker can only reach `candidate_complete` or `blocked`. **Only an external verifier writes `complete`.** **`needs-review == blocked`** (not an annotation the agent can set and move on). See [`STATE_MACHINE.md`](STATE_MACHINE.md).

## Depends on agent-memory (the gate uses memory)

The gate is the enforcement layer; [`agent-memory`](https://github.com/zhjai/agent-memory) is its foundation:

- The gate reads agent-memory's **read-only `control/`** (rules + `surface_inventory`) as its spec for *what must be checked* — human/CI-maintained, **outside any lesson-promotion path**, so a worker can't weaken the gate via a promoted "lesson".
- The gate **never** trusts agent-memory's worker-writable `state/` (run_state) as truth — it inspects real artifacts.
- Install `agent-memory` first; this kit layers on top.

## Non-negotiable principles (each closed a real bypass found in heterogeneous review)

1. Gate + manifest + inventory are **protected** (read-only, outside the agent-writable workspace, outside the lesson-promotion path).
2. Inspect **real artifacts**, never `run_state`.
3. **Unknowns fail closed** — a touched user-visible surface with no passing check → blocked.
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

> Dependency boundary: this repo **bundles** its own `gate/` + `surface_inventory.yaml`; **project-specific completion rules and approved lessons live in `agent-memory`'s read-only `control/`**, which the gate reads as its spec. Pin a compatible `agent-memory` version.

## Status

`v0.1.0` preview. MIT. Agent-agnostic, file-based, fail-closed. Foundation: [`agent-memory`](https://github.com/zhjai/agent-memory).
