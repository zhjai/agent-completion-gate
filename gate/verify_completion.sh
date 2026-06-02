#!/usr/bin/env sh
# verify_completion.sh — the EXTERNAL VERIFIER. Part of the PROTECTED gate
# (human/CI-maintained, read-only to the worker). This is the ONLY thing that
# may grant `complete`. Its exit code is the ONE canonical completion signal:
#
#   exit 0  -> complete GRANTED by the external verifier
#   exit 1  -> NOT granted (worker overstep, blocked gate, or no valid proposal)
#   exit 2  -> usage / config error (fail closed)
#
# The state-machine guard (a worker may reach at most `candidate_complete`; only this
# verifier grants `complete`) is enforced INSIDE the protected Python entrypoint
# check_acceptance.py — NOT in this shell, so there is no shell-side parser to shadow
# or spoof. This wrapper only invokes the gate hermetically and, on a clean pass,
# records the verifier-owned verdict.
#
# HERMETICITY — what this defends, and what it assumes:
#   - The gate is invoked as a FILE, so sys.path[0] is the protected gate/ dir, never the
#     repo cwd: a worker-planted `yaml.py` in the repo can't shadow `import yaml`.
#   - `python3 -E` ignores PYTHON* env (PYTHONPATH / PYTHONHOME), closing that shadow too.
#   - It does NOT honour a $PYTHON override. You MUST run it where PATH and the interpreter
#     are not worker-controlled (e.g. CI, or a hook the human owns). A hostile launch
#     environment can defeat any script; that is an assumption, not a guarantee we can make
#     in-script. See ../integrations/README.md for the trust model.
set -u

usage() {
  echo "usage: verify_completion.sh --manifest M --inventory I --candidate C [--repo DIR]" >&2
  echo "         [--strict-surfaces] [--touched IDS | --diff-base REF] [--verdict-out FILE]" >&2
  exit 2
}

MANIFEST="" ; INVENTORY="" ; CANDIDATE="" ; REPO="." ; VERDICT_OUT="" ; STRICT=""
TOUCHED_SET=0 ; TOUCHED_VAL="" ; DIFF_BASE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --manifest)        MANIFEST="${2:-}";    shift 2 ;;
    --inventory)       INVENTORY="${2:-}";   shift 2 ;;
    --candidate)       CANDIDATE="${2:-}";   shift 2 ;;
    --repo)            REPO="${2:-}";        shift 2 ;;
    --verdict-out)     VERDICT_OUT="${2:-}"; shift 2 ;;
    --strict-surfaces) STRICT="--strict-surfaces"; shift ;;
    --touched)         TOUCHED_SET=1; TOUCHED_VAL="${2:-}"; shift 2 ;;
    --diff-base)       DIFF_BASE="${2:-}";   shift 2 ;;
    -h|--help)         usage ;;
    *) echo "unknown arg: $1" >&2; usage ;;
  esac
done
[ -n "$MANIFEST" ] && [ -n "$INVENTORY" ] && [ -n "$CANDIDATE" ] || usage

HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
GATE="$HERE/check_acceptance.py"
[ -f "$GATE" ]      || { echo "ERROR: check_acceptance.py not found next to verify_completion.sh" >&2; exit 2; }
[ -f "$CANDIDATE" ] || { echo "REJECT: candidate file missing: $CANDIDATE (fail closed)" >&2; exit 1; }

# --diff-base REF: derive the TRUSTED touched set from `git diff REF...HEAD` against the
# inventory's per-surface `paths` globs (so the uncovered-surface rule doesn't trust the worker).
if [ -n "$DIFF_BASE" ]; then
  DERIVE="$HERE/derive_touched.py"
  [ -f "$DERIVE" ] || { echo "ERROR: derive_touched.py not found next to verify_completion.sh" >&2; exit 2; }
  RAW="$(python3 -E "$DERIVE" --inventory "$INVENTORY" --git-diff "$DIFF_BASE")" \
    || { echo "ERROR: derive_touched failed (fail closed)" >&2; exit 2; }
  TOUCHED_VAL="$(printf '%s' "$RAW" | tr '\n' ',' | sed 's/,*$//')"
  TOUCHED_SET=1
  echo "diff-derived touched surfaces (base $DIFF_BASE): ${TOUCHED_VAL:-<none>}"
fi

# Run the PROTECTED gate hermetically. It enforces BOTH the state machine
# (overstep / not-a-proposal) AND the artifact checks, and is authoritative.
set +e
if [ "$TOUCHED_SET" -eq 1 ]; then
  python3 -E "$GATE" --manifest "$MANIFEST" --inventory "$INVENTORY" \
    --candidate "$CANDIDATE" --repo "$REPO" $STRICT --touched "$TOUCHED_VAL"
else
  python3 -E "$GATE" --manifest "$MANIFEST" --inventory "$INVENTORY" \
    --candidate "$CANDIDATE" --repo "$REPO" $STRICT
fi
rc=$?
set +e

if [ "$rc" -ne 0 ]; then
  echo
  echo "NOT GRANTED (rc=$rc): state stays 'blocked'/'candidate_complete'. 'complete' is NOT granted."
  exit "$rc"
fi

# Gate passed -> the EXTERNAL VERIFIER grants complete. This is the canonical signal.
echo
echo "COMPLETE-GRANTED: external verifier ran the protected gate against real artifacts and it passed."
if [ -n "$VERDICT_OUT" ]; then
  {
    echo "state: complete"
    echo "verdict: COMPLETE-OK"
    echo "granted_by: verify_completion.sh (external verifier)"
    echo "candidate: $CANDIDATE"
  } > "$VERDICT_OUT" || { echo "ERROR: could not write verdict to $VERDICT_OUT" >&2; exit 2; }
  echo "wrote verifier-owned verdict -> $VERDICT_OUT  (keep this OUTSIDE the worker-writable workspace)"
fi
exit 0
