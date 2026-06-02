# Changelog

## v0.3.0

- **Diff-derived touched surfaces** — close the `touched_surfaces` self-report gap (a worker could omit a surface it touched):
  - `gate/derive_touched.py` maps changed files to surfaces via per-surface `paths` globs in the inventory, from a changed-file list or `git diff BASE...HEAD`.
  - `check_acceptance.py --touched IDS` accepts a TRUSTED touched set (precedence: `--strict-surfaces` > `--touched` > worker self-report).
  - `verify_completion.sh --diff-base REF` derives the set from git and passes it through; `--touched IDS` for a precomputed set.
  - `surface_inventory.yaml` gains optional `paths` globs; `examples/diff_demo.sh` shows a worker under-reporting `exports` getting caught (default GRANTS, diff-derived BLOCKS).
  - Hardened (bypasses found + reproduced in agent-arena review, then closed): `derive_touched.py` uses `git diff --no-renames --name-only -z` — a rename out of a surface's path no longer hides it (old path is kept), and special-char/newline paths stay raw instead of being git-quoted past the globs (and non-UTF-8 paths round-trip via `surrogateescape` instead of crashing). `examples/diff_rename_test.sh` is a runnable regression for both.
- **Productionization** (external review: the repo was a concept kit; these make it usable out of the box):
  - **Defaults no longer brick.** The shipped `gate/acceptance_manifest.yaml` + `control/surface_inventory.yaml` are now EMPTY, passable templates (you opt into strictness). The realistic SwanLab spec moved to `examples/swanlab/`. Previously the default inventory + manifest + `--strict-surfaces` could never reach `complete`.
  - **Bug:** `review_queue` as a list of strings no longer crashes (`AttributeError`); both dict and string review items are handled.
  - **New:** `check_acceptance.py --agent-writable-root DIR` fails closed if a protected spec is reachable inside the worker-writable workspace — it checks the **literal** path too, so a symlink placed in the root but pointing outside can't bypass it (a bypass found + reproduced in review). Makes invariant #1 enforceable at runtime, not just documented.
  - `examples/swanlab/` uses `.json` (the loader never truly supported JSONC).
  - **Self-CI + tests:** `tests/test_gate.py` (12 cases incl. overstep, missing/non-mapping/conflicting candidate, string `review_queue`, `--strict-surfaces`, `--touched`, `--agent-writable-root`, and import-shadow resistance) + `.github/workflows/test.yml` (compile + tests + all example scripts).
  - **README rewritten** for a first-time reader: plain "what is this", a 60-second quick start, "use it in your project" steps, and what the agent does after installing the skill — concepts moved below. English + 中文.

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
