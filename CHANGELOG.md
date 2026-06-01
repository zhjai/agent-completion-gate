# Changelog

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
