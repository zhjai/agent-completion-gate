#!/usr/bin/env sh
# init.sh — scaffold the completion gate into YOUR project. Run this YOURSELF (a human),
# from your project root. It is the AUTHORITATIVE setup path; the completion-gate-init skill
# is only a convenience wrapper around this same script.
#
#   sh /path/to/agent-completion-gate/scripts/init.sh [--dest .] [--force] [--advisory]
#
# What it creates in --dest (default: current dir):
#   gate/check_acceptance.py  gate/verify_completion.sh  gate/derive_touched.py
#   gate/acceptance_manifest.yaml      (EMPTY, passable template — you add checks)
#   control/surface_inventory.yaml     (EMPTY template — you add surfaces)
#   state/.gitkeep                     (where the agent writes completion_candidate.yaml)
#   .github/workflows/completion-gate.yml
#   .github/CODEOWNERS.completion-gate.example
#
# Idempotent: existing files are NOT overwritten unless --force — including the engine scripts
# (gate/*.py, verify_completion.sh), so local edits to them survive a re-run. Use --force to
# refresh the engine to this checkout's version (your manifest/inventory are still kept unless
# --force is given AND you re-confirm — see below).
set -eu

DEST="." ; FORCE="" ; ADVISORY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dest)     DEST="${2:?--dest needs a path}"; shift 2 ;;
    --force)    FORCE=1; shift ;;
    --advisory) ADVISORY=1; shift ;;
    -h|--help)  sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

SRC="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"   # the agent-completion-gate repo root
[ -f "$SRC/gate/check_acceptance.py" ] || { echo "ERROR: run from the agent-completion-gate checkout (gate/ not found at $SRC)" >&2; exit 2; }
mkdir -p "$DEST" && DEST="$(CDPATH= cd -- "$DEST" && pwd)"

copy_once() {   # src_rel  dest_rel  — never overwrite without --force
  d="$DEST/$2"
  if [ -e "$d" ] && [ -z "$FORCE" ]; then echo "  · $2 exists (kept; --force to replace)"; return; fi
  mkdir -p "$(dirname "$d")"; cp "$SRC/$1" "$d"; echo "  ✓ $2";
}

echo "completion-gate init  (dest: $DEST)"

# Engine: created once, then yours. NOT silently overwritten — you may extend run_machine_check()
# with project-specific check types, and a re-run must not wipe that. Use --force to refresh.
copy_once gate/check_acceptance.py  gate/check_acceptance.py
copy_once gate/verify_completion.sh gate/verify_completion.sh
copy_once gate/derive_touched.py    gate/derive_touched.py
chmod +x "$DEST/gate/verify_completion.sh" "$DEST/gate/check_acceptance.py" "$DEST/gate/derive_touched.py" 2>/dev/null || true

# Specs + state + CI: created once, then yours to edit.
copy_once gate/acceptance_manifest.yaml      gate/acceptance_manifest.yaml
copy_once control/surface_inventory.yaml     control/surface_inventory.yaml
copy_once integrations/github-actions/completion-gate.yml  .github/workflows/completion-gate.yml
mkdir -p "$DEST/state"; [ -e "$DEST/state/.gitkeep" ] || { : > "$DEST/state/.gitkeep"; echo "  ✓ state/.gitkeep"; }

# CODEOWNERS example (don't clobber a real CODEOWNERS).
cat > "$DEST/.github/CODEOWNERS.completion-gate.example" <<'EOF'
# Append these to your .github/CODEOWNERS so a worker can't weaken the gate in the PR it must pass:
/gate/                                   @your-team
/control/                                @your-team
/.github/workflows/completion-gate.yml   @your-team
EOF
echo "  ✓ .github/CODEOWNERS.completion-gate.example"

if [ -n "$ADVISORY" ]; then
  echo "  (advisory mode requested — see the workflow's ALLOW_NO_CANDIDATE / required-check notes)"
fi

cat <<EOF

Scaffold done. The gate is NOT authoritative yet — it currently only enforces the state machine
(the agent can propose 'candidate_complete' but cannot self-declare 'complete'). To make it real:

  1. Define acceptance: add at least one surface to control/surface_inventory.yaml and one check
     to gate/acceptance_manifest.yaml. (Empty specs pass — they don't know your project yet.)
  2. Make it the AUTHORITY: mark the 'verify-completion' job a REQUIRED status check in branch
     protection, and CODEOWNERS-protect gate/, control/, and the workflow
     (see .github/CODEOWNERS.completion-gate.example).
  3. Commit gate/ + control/ + .github/ to your repo.

Sanity check (should print COMPLETE-OK on the empty template):
  printf 'status: candidate_complete\\ntouched_surfaces: []\\nreview_queue: []\\n' > state/completion_candidate.yaml
  python3 -E gate/check_acceptance.py --manifest gate/acceptance_manifest.yaml \\
    --inventory control/surface_inventory.yaml --candidate state/completion_candidate.yaml --repo .
EOF
