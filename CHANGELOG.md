# Changelog

## v0.4.3

- **Fix: on Codex, `goal-compile` skipped the mandatory confirmation and started working.** Root cause (verified from a real 910b session rollout): Codex loads only a skill's one-line `description` into context, **not** the `SKILL.md` body — unlike Claude Code, which loads the full body. The confirm-before-work guarantee lived almost entirely in the body (step 3), so on Codex the agent only saw a soft half-sentence ("confirms them once") and, being goal-driven, just executed. The skill was correctly installed and loaded — the failure was the host's description-only loading, not a missing install.
- **Fix: the `description` now carries the hard rule itself**, so it binds even when the body is never loaded: "read this SKILL.md in full first", "the user stating a goal is NOT approval of scope or done", "Before ANY draft, outline, sample, placeholder, artifact, file edit, or command … STOP for the user's explicit OK", "Do not preview or partially produce the deliverable before that OK". Hardened across three heterogeneous (Codex) review rounds that reproduced and then closed five rationalization dodges (implicit-approval, criteria-are-obvious, preview/draft, completion-only reading, and the short-artifact "small task" exemption — `copy/文案` is now explicitly covered and "short length does not exempt it"). 1008/1024 chars, single-line, YAML-valid.

## v0.4.2

- **Fix: `goal-compile` was being silently dropped at install** — its `description` was 1072 chars, over the Agent Skills 1024-char limit, so hosts skipped the skill ("Skipped loading 1 skill(s) … exceeds maximum length of 1024 characters"). Trimmed to 784 chars (kept the triggers, the small-task exclusions, and the no-self-certify rule; cut the verbose process prose). Audited all skills in the repo against the spec limits (name ≤64 + format, description ≤1024) — all pass.

## v0.4.1

- **`goal-compile` now right-sizes — small tasks skip the gate.** Two fixes from real-use feedback (settled in agent-arena):
  - **Broader, prefix-free triggering:** natural phrasings fire it too — "帮我完成这个任务/目标", "help me build/implement X", "做一个 X" — not just "设计goal:"/"goal:". No magic word required.
  - **Right-size step 0 (before any ceremony):** the skill now classifies the task first. A typo / one-line / single-function / one-off request is handled **directly with no init, no criteria, no confirmation** (at most a one-line "say 'use the gate' if you want criteria"). The init + confirm + gate ceremony only runs for substantial work (multi-step / multi-file / user-visible artifact). When unsure it defaults to small. Bias: under-fire (recoverable with "use the gate") over over-fire (ceremony on trivial work erodes trust). The gate is per-goal, not per-utterance — sub-steps inside a goal don't re-trigger it.

## v0.4.0

- **Goal-first lazy mode** — new [`goal-compile`](skills/goal-compile/SKILL.md) skill. The user just states a goal in natural language ("设计goal: …", "goal: add a monthly sales report page", "我的目标是…" — no fixed prefix; the skill auto-triggers on intent). It auto-initializes the gate if absent, compiles the goal into acceptance criteria (surfaces + machine checks + review items), **confirms the criteria with the user once, in plain language, before doing the work** (like confirming a plan — no hand-written YAML), then executes and runs the gate. Cuts the old skill→clone→init→hand-write-YAML friction to one sentence + one confirmation.
  - **Trust boundary preserved (the whole point):** the agent only *drafts* criteria and *proposes*; a human confirms them and only the external gate grants `complete`. It never self-certifies. Confirm-before-work (not after) so criteria can't be biased toward whatever was already built. Where CI/CODEOWNERS own the specs, the agent can only propose a diff (stays `needs_criteria_approval` until merged).
  - **Lite mode** (only if the user explicitly opts out of confirming): self-check against the agent's own drafted criteria, reported as **`SELF-CHECK-OK`** — explicitly **not** a verified completion, never `COMPLETE-OK`.
- README leads with this as the recommended path; manual setup kept below for those who want to wire it themselves.
- Fixed the GitHub About/topics that still said "Built on agent-memory" — the gate is standalone (decoupled in v0.3.1).

## v0.3.1

- **Onboarding overhaul** (so a normal developer gets it, OpenSpec-style):
  - `scripts/init.sh` — a deterministic, idempotent scaffolder you run yourself: drops `gate/` (engine + empty manifest), `control/`, `state/`, the CI workflow, and a CODEOWNERS example into your project, then prints exactly what *you* must protect. No more manual `cp`. The new `completion-gate-init` skill is a thin wrapper around it (the script is the authority — the agent never becomes the trust root of its own gate).
  - `examples/minimal-project/` — an everyday "add a monthly sales report page" walkthrough (before → BLOCKED on a 1-point chart + missing CSV export; after → COMPLETE-OK). Replaces the ML/SwanLab story on the first screen; SwanLab stays as the deeper real-incident fixture.
  - **README rewritten, problem-first**: leads with goal-driven agents missing user-visible acceptance details ("the goal is not the acceptance criteria"), an honesty note that a *human* writes the checks (the gate infers nothing), and one positioning line vs OpenSpec. Mechanism / state-machine / invariants moved below the fold. The demo is now "See it in action"; the quick start scaffolds into *your* repo. EN + idiomatic 中文.
- **Fully decoupled from `agent-lessonbook` (formerly agent-memory).** The gate is standalone: it never reads any memory/lesson path at runtime (only `--manifest`/`--inventory`/`--candidate`/`--repo`), no longer says "depends on / built on / install first", and dropped the memory skills from `completion-audit`'s `related_skills`. Invariant #1 no longer references a "lesson-promotion path" (an external concept) — the gate is protected simply because it's outside the agent-writable workspace and human/CI-maintained. A lesson becomes gate policy only when a human edits the protected manifest.
- **Onboarding fixes** (heterogeneous review, reproduced then fixed): `init.sh` no longer silently overwrites engine scripts on re-run (so a user's `run_machine_check()` extensions survive; `--force` to refresh); the `completion-gate-init` skill + README quick-start now give a resolvable command (clone the repo, run `scripts/init.sh` from the checkout) instead of a non-existent skill-dir path; fixed a duplicated section in the Chinese README.

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
- **Docs:** added a banner (`assets/banner.svg`), a Chinese `README.zh.md`, and broadened positioning to any Agent-Skills host (Claude Code · Codex · others). Corrected the dependency boundary — the gate **bundles** its own protected check spec (`acceptance_manifest.yaml` + `control/surface_inventory.yaml`) and is self-contained. *(Earlier in v0.3.x this section described reading `agent-memory`'s `control/`; that coupling was removed — see the decoupling note above.)*

## v0.1.0

> Historical snapshot of v0.1.0 behavior. Superseded by v0.3.1: the gate is now **fully standalone** and does **not** depend on / read `agent-memory` (now [`agent-lessonbook`](https://github.com/zhjai/agent-lessonbook)) at runtime. Invariant #1 below mentions a "lesson-promotion path" — that concept was dropped; the gate is protected simply by being outside the agent-writable workspace.

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
