---
name: completion-gate-init
description: Use when the user asks to set up / install / initialize the completion gate in their project (e.g. "set up the completion gate", "add the completion gate to this repo"). Runs the bundled deterministic scaffolder (scripts/init.sh) to create gate/, control/, state/, and a CI workflow, then tells the user what THEY must protect. Does NOT make the gate authoritative — branch protection + CODEOWNERS are the human's job and must not be done by the agent.
license: MIT
metadata:
  version: "0.4.3"
  author: zhjai
  tags: "completion, gate, init, scaffold, setup, acceptance"
  related_skills: "goal-compile, completion-audit"
---

# Completion Gate Init

Convenience wrapper around the authoritative setup script `scripts/init.sh`. Use it to scaffold
the gate into the user's project. **The script is the source of truth — run it, don't reimplement
it.**

## When to use
- The user asks to set up / initialize / add the completion gate to their repository.

## Procedure
1. Locate an `agent-completion-gate` checkout (the engine + scaffolder live in the **repo**, not
   in this installed skill — `npx skills add` ships skills, not the gate engine). If the user
   doesn't have one, clone it:
   ```
   git clone https://github.com/zhjai/agent-completion-gate
   ```
2. From the user's project root, run the scaffolder, pointing it at the project:
   ```
   sh <checkout>/scripts/init.sh --dest .
   ```
   It creates `gate/` (engine + empty manifest), `control/surface_inventory.yaml`, `state/`,
   `.github/workflows/completion-gate.yml`, and a CODEOWNERS example. It is idempotent and will
   not overwrite existing files (engine or specs) without `--force`.
3. Relay the script's "Next" steps to the user verbatim. Then help with step 1 of those (define
   real surfaces/checks) if asked.

## Do not
- **Do not edit `gate/acceptance_manifest.yaml` to weaken it**, do not move `gate/`/`control/`
  into a worker-writable location, and do not invent your own scaffolding — only run the script.
- **Do not claim the gate is active/authoritative.** It only enforces the state machine until the
  user (a human) sets the required status check + CODEOWNERS. Say so plainly.
- **Do not set up anything that lets you (the agent) grant `complete`.** That asymmetry is the
  whole point: you propose `candidate_complete`; CI / a human verifies.
