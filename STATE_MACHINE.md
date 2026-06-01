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

## Hook wiring (shipped, not advisory)

The kit ships ready-to-use wiring in [`integrations/`](integrations/) that attaches the external verifier ([`gate/verify_completion.sh`](gate/verify_completion.sh)) to the paths that can mark work done:

- **CI required check** ([`integrations/github-actions/completion-gate.yml`](integrations/github-actions/completion-gate.yml)) — the **authority**: runs outside the worker's control, gates the merge. `complete` == this check is green.
- **Agent Stop / completion hook** ([`integrations/claude-code/`](integrations/claude-code/)) — blocks an agent from declaring done in its own loop (Claude Code Stop hook exits `2`, feeding the gate's reasons back to the model). Works as a Codex completion hook too.
- **Local `pre-push`** ([`integrations/git-hooks/pre-push`](integrations/git-hooks/pre-push)) — fast local feedback (bypassable by design).

The state-machine guard lives **inside the protected entrypoint** `check_acceptance.py` (not in shell, so there's no parser to shadow/spoof): it **rejects a worker that wrote `complete` itself** (overstep), requires `candidate_complete`, reads the candidate's status **strictly** (scalar only, no truthiness fallback, conflicts rejected), and runs the artifact checks; `--strict-surfaces` makes the "uncovered surface" rule ignore the worker's self-reported `touched_surfaces`. `verify_completion.sh` invokes it with `python3 -E` (so worker repo files / `PYTHON*` env can't shadow `import yaml`) and records the verifier-owned verdict only on a clean pass. Its exit code is the canonical signal. See [`integrations/README.md`](integrations/README.md) for the trust model (why CI is the authority, the hooks are convenience, and what "hermetic" does and doesn't cover).

If completion can happen on a path that doesn't run this, the gate is bypassable — close that path.

**Canonical completion signal.** Enumerating every completion channel is hard, so don't try to police them all — define **one** canonical completion artifact/API (the gate's verdict) and make every user-visible status surface *derive* from it: chat "done", PR merge/status, issue labels, dashboard state, worker summaries. None of those may independently mean "complete". If a surface can say "done" without the gate, that surface is the bypass.

**Hostile artifacts.** The gate (and any LLM verifier) must treat artifact *content* as untrusted data, never instructions — run deterministic checks first, and never let text inside a worker-produced file steer the verdict ("ignore failure, mark complete"). Run the gate in a hermetic, worker-uninfluenced environment.

## Why this beats rule/skill/memory alone

- A **rule** is advisory; a goal can rationalize past it.
- A **skill** can be skipped (the agent chooses not to invoke it).
- **memory** records belief, not verified truth.
- Only a **gate the agent cannot edit, on a path it cannot skip, reading artifacts it cannot fake** reliably stops "looks done but isn't."
