# Changelog

## v0.2.0

- **Shipped enforcement wiring** (`integrations/`) so "only an external verifier writes `complete`" is true out of the box, not left to the reader:
  - `gate/verify_completion.sh` — the external verifier: rejects a worker that wrote `complete` itself, requires `candidate_complete`, runs the gate against real artifacts, and grants `complete` only on a clean pass. Its exit code is the one canonical signal.
  - `integrations/github-actions/completion-gate.yml` — CI required check (the **authority**: runs outside the worker's control, gates the merge; hermetic, pinned Python; optional `STRICT` mode).
  - `integrations/claude-code/` — Claude Code Stop hook (`exit 2` blocks "done" and feeds the gate's reasons back to the agent); doubles as a Codex completion hook.
  - `integrations/git-hooks/pre-push` — local fast-feedback hook (bypassable by design; optional `HARD_BLOCK`).
  - `examples/run.sh` now exercises the verifier end to end (overstep → blocked, blocked, granted) against the bundled fixtures.
- **Hardened against a heterogeneous red-team pass** (bypasses found by Codex, each reproduced then closed, then re-verified):
  - The state-machine guard moved **into the protected `check_acceptance.py`** (no shell-side parser to shadow). Status is read strictly — scalar only, no `status or state` truthiness fallback, conflicting `status`/`state` rejected, non-mapping candidate rejected.
  - The gate is invoked with **`python3 -E`** (and as a file, not via `python -`), so a worker-planted `yaml.py` or `PYTHON*` env can no longer shadow `import yaml` to fake the verdict (invariant #6 — which this kit had warned about and then violated).
  - **`--strict-surfaces`** requires every user-visible surface to have a passing check, so "unknowns fail closed" no longer trusts the worker's self-reported `touched_surfaces`.
  - CI template now **fail-closes on an absent candidate** by default (`ALLOW_NO_CANDIDATE` to opt out) and runs `gate/`+`control/` from the **base branch**, so a PR can't be judged by a gate it edits.
  - Docs corrected to stop overclaiming hermeticity / unbypassability — stated as "external + fail-closed under a trusted base branch + runner".
- **Docs:** added a banner (`assets/banner.svg`), a Chinese `README.zh.md`, and broadened positioning to any Agent-Skills host (Claude Code · Codex · others). Corrected the dependency boundary — the gate **bundles** its own protected check spec (`acceptance_manifest.yaml` + `control/surface_inventory.yaml`); it reads `agent-memory`'s read-only `control/` for **rules + approved lessons** only.

## v0.1.0

- Initial preview of `agent-completion-gate`: a **fail-closed completion gate + four-state machine** that stops a goal-driven agent from declaring work done that isn't.
- State machine: `in_progress → candidate_complete → (external verifier) → complete | blocked`. The worker can only reach `candidate_complete` or `blocked`; only an external verifier writes `complete`. **`needs-review == blocked`** (not an annotation).
- Six non-negotiable invariants, each closing a bypass found in heterogeneous review:
  1. protected gate/manifest/inventory (outside the agent-writable workspace AND outside the lesson-promotion path);
  2. inspect real artifacts, never `run_state`;
  3. unknowns fail closed;
  4. one canonical completion signal (chat/PR/dashboard derive from it);
  5. artifact content is hostile data, not instructions (deterministic checks first; LLM verifier treats artifacts as untrusted);
  6. hermetic execution (pin env).
- **Depends on [`agent-memory`](https://github.com/zhjai/agent-memory)**: reads its read-only `control/` (rules + `surface_inventory`) as the check spec; never trusts the worker-writable `state/`.
- Designed and hardened across multiple agent-arena rounds (Claude × Codex) — including a round where Codex itself invoked Claude as a red-team sub-agent, which caught the self-policing and verifier-injection holes.
