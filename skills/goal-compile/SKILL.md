---
name: goal-compile
description: 'Use when the user states a goal or long-term task for the agent to carry out and keep on track — e.g. "设计goal: ...", "我的目标是...", "goal: add a monthly sales report page", "long-term task proposal: ...", or "use the completion gate to do X". Turns the natural-language goal into completion-gate acceptance criteria (surfaces + machine checks + review_items), auto-initializing the gate if absent, gets the user to confirm the criteria once (like confirming a plan) before work, then drives the task to the gate verdict. The agent DRAFTS criteria; it never self-certifies — a human confirms the criteria, and only the external gate grants complete.'
license: MIT
metadata:
  version: "0.4.0"
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
- The user states a goal / long-term task: "设计goal: …", "我的目标是…", "goal: …", "long-term task proposal: …", "use the gate to build X".

## Procedure (Standard mode — the default)

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
