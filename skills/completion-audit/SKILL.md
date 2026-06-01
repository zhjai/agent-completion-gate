---
name: completion-audit
description: Use before declaring a long, multi-stage, or artifact-producing task done — prepare a completion CANDIDATE (not a completion). Enumerate touched user-visible surfaces, reconcile thread expectations against the plan, gather real evidence paths, and run the external gate; any uncovered surface, failed check, or review item forces blocked. Use at task wrap-up for long/high-stakes work. Do not use to declare completion yourself — only an external verifier grants `complete`.
license: MIT
metadata:
  version: "0.1.0"
  author: zhjai
  tags: "completion, gate, acceptance, long-task, completion-control, audit"
  related_skills: "resume-context, lesson-promote"
---

# Completion Audit

## When to use
- Wrapping up a long / multi-stage task, or any task that produces user-visible artifacts (runs, dashboards, reports, exports).

## Procedure
1. Enumerate the **touched files / user-visible surfaces** this task changed.
2. Reconcile: compare the plan/objective against **expectations expressed in the thread** (not just what's written in the plan). Differences are surfaced, never silently dropped.
3. Map each touched surface to a check in the protected `acceptance_manifest.yaml` (read-only). Any user-visible surface with **no** check → record in `review_queue.yaml` and mark blocked.
4. Gather **real evidence paths** (actual artifacts/configs), not `run_state` assertions.
5. Write `completion_candidate.yaml` (your proposal; status = `candidate_complete`).
6. Invoke the external gate: `check_acceptance.py --manifest ... --inventory ... --candidate ... --repo .`

## Outputs
- `completion_candidate.yaml` (proposal only)
- `review_queue.yaml` (blocking open items)
- gate result (PASS → an external verifier may grant `complete`; FAIL/any review item → `blocked`)

## Do not
- **Do not set `complete` yourself** — you may only reach `candidate_complete` or `blocked`. Only the external gate/verifier writes `complete`.
- **Do not reclassify a real regression as "subjective" to skip it** — `needs-review == blocked`.
- **Do not feed the gate your `run_state`** as evidence — the gate must read real artifacts.
