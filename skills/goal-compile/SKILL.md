---
name: goal-compile
description: 'Use when the user sets a substantial, multi-step or long-running goal/task — naturally phrased, no prefix needed: "设计goal: ...", "goal: ...", "我的目标是...", "帮我完成这个任务/目标", "help me build/implement X", "做一个X". For work that produces a user-visible artifact (feature, page, report, export, schema, release, migration, experiment) or spans multiple files/steps. Do NOT use for typo fixes, one-line or single-function tweaks, one-off questions, lookups, or small tasks — handle those directly unless the user explicitly asks for the gate. Compiles the goal into acceptance criteria, confirms them with the user once before work (like a plan), then runs the external gate. The agent only DRAFTS criteria and never self-certifies: a human confirms them; only the external gate grants complete.'
license: MIT
metadata:
  version: "0.4.2"
  author: zhjai
  tags: "goal, completion, gate, acceptance, long-task, goal-first"
  related_skills: "completion-gate-init, completion-audit"
---

# Goal Compile (goal-first entry to the completion gate)

The lazy, goal-first way to use the gate. The user says a goal in natural language; you compile it
into acceptance criteria, **confirm those criteria with the user once** (the way you'd confirm a
plan), then execute and run the gate. The user never hand-writes YAML.

**The one rule that must not break:** you DRAFT the acceptance criteria; you do not get to be the
authority on "done". A human confirms the criteria, and only the external gate grants `complete`.
A goal-driven agent that writes its own lax checks and grades itself has defeated the entire point.

## When to use
- The user sets a **substantial** goal / multi-step / long task, however phrased: "设计goal: …", "goal: …", "我的目标是…", "帮我完成这个任务/目标", "help me build/implement X", "做一个 X", "use the gate to build X". No fixed prefix needed.
- **Not** for small / one-off / single-file work — see step 0.

## Procedure (Standard mode — the default)

0. **Right-size before any ceremony.** Before compiling criteria, asking for confirmation, or initializing the gate, classify the request:
   - **GATE-WORTHY** — the user explicitly asked to use the gate, OR the task is long-running, multi-step, spans multiple files/surfaces, or produces a user-visible artifact (feature, page, report, export, workflow, schema, release, migration, experiment, integration). → continue to step 1.
   - **TOO SMALL** — a typo fix, a one-line / single-function / mechanical single-file edit, a one-off question, a simple lookup, or an ordinary small task. **Do not init, compile, confirm, or write gate specs.** Just do the task, and say at most once: *"Small task — handling it directly; say 'use the gate' if you want acceptance criteria."* Do not ask whether to gate it; do not repeat that line within a run.
   - When **unsure, default to TOO SMALL** unless the user explicitly asked for the gate. Over-firing (ceremony on trivial work) erodes trust in the gate; under-firing is cheap — the user just says "use the gate".
   - **Per goal, not per utterance:** once a goal's criteria are confirmed and being driven, the small sub-steps *inside* that goal do NOT re-trigger this skill.

1. **Auto-init if absent.** If the repo has no `gate/` + `control/surface_inventory.yaml` +
   `gate/acceptance_manifest.yaml`, scaffold them: run `scripts/init.sh --dest .` from an
   `agent-completion-gate` checkout (see the `completion-gate-init` skill). Don't make the user do this.

2. **Compile the goal into acceptance criteria** — break the goal into concrete, user-visible
   acceptance points. For each, decide:
   - **machine check** (a built-in type: `file_exists`, `config_not_disabled`, `min_series_points`,
     `max_chart_count`, `identity_in_name`, or an extension), or
   - **review_item** (can't be machine-judged — needs a human eye, e.g. "empty-state copy reads well").

3. **CONFIRM WITH THE USER — once, in plain language, BEFORE doing the work.** Do not dump YAML.
   List the criteria as a short checklist and ask for sign-off:
   ```
   I'll treat "done" for "<goal>" as:
     ① report page exists            (file_exists: artifacts/report.html)        [auto]
     ② CSV export exists             (file_exists: exports/monthly.csv)          [auto]
     ③ chart has ≥2 data points      (min_series_points: rows ≥ 2)               [auto]
     ④ title is not "Untitled"       (needs a human check)                        [review]
   Look right? Tell me anything to add/drop/loosen.
   ```
   Confirm BEFORE implementing — criteria written after the work get biased toward whatever you
   already built. Apply the user's edits.

4. **Write the criteria to the spec.** Put the confirmed surfaces in
   `control/surface_inventory.yaml` and checks/review_items in `gate/acceptance_manifest.yaml`.
   If these are protected (CI authority / CODEOWNERS), you can only PROPOSE the change (a diff /
   a PR for human approval) — say so; the gate stays blocked as `needs_criteria_approval` until a
   human merges it. If they're local/unprotected (solo use), the user's spoken confirmation in
   step 3 IS the approval.

5. **Do the work** against the confirmed criteria.

6. **Run the gate, don't self-declare.** Write `state/completion_candidate.yaml`
   (`status: candidate_complete`, `touched_surfaces: [...]`) and run
   `check_acceptance.py --manifest … --inventory … --candidate … --repo .`. If `BLOCKED`, fix the
   **real artifacts** (don't loosen the criteria to escape) and re-run. Only the external
   gate/verifier writes `complete`.

## Lite mode (only if the user explicitly opts out of confirming)

If the user says "don't ask me / just do it / fully automatic", you may skip the step-3 confirmation
and self-check against your own drafted criteria. **But then it is NOT verified completion** — it's
a self-checklist. Report the result as **`SELF-CHECK-OK`**, never `COMPLETE-OK`, and say plainly:
"these were my own criteria, not human-confirmed; for a real completion guarantee, confirm the
criteria or wire CI." Lite mode must never be used where CI / a human is supposed to be the authority.

## Do not
- **Do not self-certify.** You draft criteria and propose; a human confirms them and the external
  gate grants `complete`. Never report `COMPLETE-OK` off criteria you wrote and graded yourself.
- **Do not write criteria after building**, then claim they were the goal — confirm before work.
- **Do not loosen/delete a check to get past `BLOCKED`** — fix the real artifact, or surface the
  conflict to the user. Weakening the gate to pass is the exact failure this tool exists to stop.
- **Do not touch protected specs directly** when CI/CODEOWNERS own them — propose a diff for review.
