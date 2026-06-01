#!/usr/bin/env sh
# stop_gate.sh — Claude Code Stop-hook / Codex completion-hook adapter.
# Blocks an agent from declaring "done" until the external gate grants `complete`.
#
# In Claude Code, a Stop hook that exits 2 BLOCKS the stop and feeds stderr back to
# the model — so the agent is told, in its own loop, that it is not done and why.
# (Wire via .claude/settings.json -> hooks.Stop; see settings.hooks.json. Confirm the
# hook schema for your Claude Code version.) For Codex, attach it to the completion/
# stop hook the same way: nonzero == not done.
set -u
GATE_DIR="${GATE_DIR:-gate}"
MANIFEST="${MANIFEST:-$GATE_DIR/acceptance_manifest.yaml}"
INVENTORY="${INVENTORY:-control/surface_inventory.yaml}"
CANDIDATE="${CANDIDATE:-state/completion_candidate.yaml}"
REPO="${REPO:-.}"

# No completion proposed -> let the agent stop normally (the gate gates COMPLETION,
# not every pause).
[ -f "$CANDIDATE" ] || exit 0

out="$(sh "$GATE_DIR/verify_completion.sh" \
  --manifest "$MANIFEST" --inventory "$INVENTORY" --candidate "$CANDIDATE" --repo "$REPO" 2>&1)"
rc=$?
if [ "$rc" -ne 0 ]; then
  echo "Completion gate did NOT grant 'complete' — do not declare this task done." >&2
  echo "Fix the REAL artifacts, set status back to candidate_complete, and let the gate re-audit." >&2
  echo "--- gate output ---" >&2
  echo "$out" >&2
  exit 2   # Claude Code: block the stop and return this to the model
fi
exit 0
