# Integrations — wiring the gate as the canonical completion signal

`gate/check_acceptance.py` produces a verdict; `gate/verify_completion.sh` is the
**external verifier** that turns that verdict into the four-state contract and is the
**only** thing that grants `complete`. These integrations attach that verifier to the
paths where an agent (or a human) could mark work done, so the contract isn't advisory.

```
worker writes state/completion_candidate.yaml  (status: candidate_complete — a PROPOSAL)
                       │
        ┌──────────────┼───────────────────────────────┐
        ▼              ▼                                 ▼
  CI required check   agent Stop/completion hook     local pre-push hook
  (AUTHORITY)         (fast feedback, in the loop)   (fast feedback)
        │
        └─► verify_completion.sh ─► check_acceptance.py (real artifacts)
                 │ overstep? blocked? → exit ≠ 0, complete NOT granted
                 └ clean pass → exit 0 → complete GRANTED (canonical signal)
```

## The trust model (read this before trusting any of it)

**Authority vs. convenience.** Not all wiring is equal:

| Wiring | Can the worker bypass it? | Role |
|--------|---------------------------|------|
| **CI required check** | No — *given the required setup below*: runs on the platform's runners (env/PATH not worker-controlled), can't be `--no-verify`'d, and runs the gate from the **base branch** so the PR can't edit the gate that judges it | **Authority.** This is where `complete` is really granted. |
| Agent Stop / completion hook | Partly — a worker with edit access to agent settings could remove it; in a managed setup the *human* owns settings | In-loop feedback: tells the agent "not done, here's why" before it stops |
| Local git `pre-push` | Yes — `git push --no-verify`, or just don't install it | Local fast feedback only |

So: **make the CI check a required status check, and protect the gate from the PR it judges.** A read-only script is not enough if the same PR can edit the script, the manifest, or the workflow. Put `gate/`, `control/`, and `.github/workflows/completion-gate.yml` behind **CODEOWNERS + branch protection** (invariant #1: the gate is human/CI-maintained, outside the agent-writable + lesson-promotion path).

**One canonical signal (invariant #7).** `complete` means exactly one thing: `verify_completion.sh` exited 0 (in CI). Every other "done" surface — chat, PR label, dashboard, the worker's own summary — must *derive* from that, never assert it independently. If a surface can say "done" without the gate, that surface is the bypass.

## 1. CI required check — the authority

[`github-actions/completion-gate.yml`](github-actions/completion-gate.yml). Copy to `.github/workflows/`, then mark `verify-completion` **required** in branch protection. Point `MANIFEST` / `INVENTORY` / `CANDIDATE` at your paths. **Fail-closed by default**: a PR with no `completion_candidate.yaml` fails (set `ALLOW_NO_CANDIDATE=1` if you don't gate every merge on completion). The job re-checks `gate/`+`control/` out **from the base branch** (a PR can't be judged by a gate it edits), pins Python, and the verifier runs `python3 -E` so worker repo files / `PYTHON*` env can't shadow `import yaml` (invariant #6). It runs with `--strict-surfaces` so the *which surfaces need a check* decision doesn't trust the worker either.

> **Honest scope.** This is "external + fail-closed under a **trusted base branch + runner**", not magic. The script can't be hermetic against a hostile launch environment — protect the base branch, CODEOWNERS the gate, and keep the runner env out of worker control. The required setup is in the workflow header.

## 2. Agent Stop / completion hook — keep the agent honest in-loop

[`claude-code/stop_gate.sh`](claude-code/stop_gate.sh) + [`claude-code/settings.hooks.json`](claude-code/settings.hooks.json). A Claude Code **Stop** hook that exits `2` blocks the stop and feeds the gate's reasons back to the model, so a goal-driven agent can't declare done while the gate blocks — it's told, in its own loop, exactly what to fix. Wire the same script as Codex's completion/stop hook (nonzero == not done). This is feedback, not authority — the human owns the settings.

## 3. Local `pre-push` — fast feedback

[`git-hooks/pre-push`](git-hooks/pre-push). Bypassable by design (`--no-verify`). Tells you whether your completion proposal would be granted before you push. Set `HARD_BLOCK=1` to refuse pushes carrying a failing proposal.

## Try it (runnable)

The example fixtures exercise the full external verifier, including the overstep guard:

```bash
sh examples/run.sh    # see the three "external verifier" sections at the end
```

You'll see: a worker that wrote `status: complete` itself → **REJECT**; `candidate_complete` + broken artifacts → **BLOCKED**; `candidate_complete` + fixed artifacts → **COMPLETE-GRANTED**. All exit codes are real.
