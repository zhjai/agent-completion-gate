# Completion State Machine

The one invariant the whole kit defends. Wire this into your harness; don't let it stay advisory.

```
            worker work
   in_progress ───────────────► candidate_complete
        │                              │
        │ needs-review /               │ external gate runs
        │ unknown surface /            │ (check_acceptance.py, real artifacts)
        │ missing evidence             │
        ▼                       pass ──┴── fail / any review item / uncovered surface
     blocked ◄──────────────────────────────────────────────┐
        │                                                    │
        │ (resolve, then re-audit)                           │
        └──────────────► candidate_complete ──► EXTERNAL verifier ──► complete
```

## States

| state | who can set it | meaning |
|-------|----------------|---------|
| `in_progress` | worker | work ongoing |
| `candidate_complete` | **worker (max it can reach)** | "I propose this is done" — a proposal, not a verdict |
| `blocked` | worker or gate | a check failed, a surface is uncovered, or a review item exists |
| `complete` | **external verifier / CI / human ONLY** | gate passed, no review items, no uncovered surfaces |

## Transition rules (non-negotiable)

1. The worker agent can advance only to `candidate_complete` or `blocked`. It can **never** write `complete`.
2. `needs-review == blocked`. A review item is not an annotation the agent can set and proceed past.
3. `candidate_complete → complete` happens **only** when `check_acceptance.py` exits 0 (run by the gate/CI/hook, reading real artifacts).
4. Any uncovered user-visible touched surface, any failed machine check, or any review item ⇒ `blocked` (unknowns fail closed).

## Hook wiring (so it isn't bypassable)

Attach the gate to **every** path that could mark a task done — e.g. a Codex/Claude completion/stop-hook, or a CI required check:

```bash
# pseudo stop-hook
python completion-control-kit/gate/check_acceptance.py \
    --manifest  <protected>/acceptance_manifest.yaml \
    --inventory <protected>/surface_inventory.yaml \
    --candidate state/tasks/<task_id>/completion_candidate.yaml \
    --repo . \
  || { echo "gate failed -> task stays blocked"; exit 1; }
```

If completion can happen on a path that doesn't run this, the gate is bypassable — close that path.

**Canonical completion signal.** Enumerating every completion channel is hard, so don't try to police them all — define **one** canonical completion artifact/API (the gate's verdict) and make every user-visible status surface *derive* from it: chat "done", PR merge/status, issue labels, dashboard state, worker summaries. None of those may independently mean "complete". If a surface can say "done" without the gate, that surface is the bypass.

**Hostile artifacts.** The gate (and any LLM verifier) must treat artifact *content* as untrusted data, never instructions — run deterministic checks first, and never let text inside a worker-produced file steer the verdict ("ignore failure, mark complete"). Run the gate in a hermetic, worker-uninfluenced environment.

## Why this beats rule/skill/memory alone

- A **rule** is advisory; a goal can rationalize past it.
- A **skill** can be skipped (the agent chooses not to invoke it).
- **memory** records belief, not verified truth.
- Only a **gate the agent cannot edit, on a path it cannot skip, reading artifacts it cannot fake** reliably stops "looks done but isn't."
