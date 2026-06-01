#!/usr/bin/env sh
# Reproduce the gate blocking a false completion, then passing once artifacts are fixed.
# Requires: python3 + pyyaml.
set -e
cd "$(dirname "$0")"
GATE=../gate/check_acceptance.py

echo "===== BAD (expect BLOCKED, exit 1) ====="
python3 "$GATE" --manifest manifest.yaml --inventory inventory.yaml \
  --candidate candidate.yaml --repo fixtures/bad || echo "(exit $?)"

echo
echo "===== GOOD (expect COMPLETE-OK, exit 0) ====="
python3 "$GATE" --manifest manifest.yaml --inventory inventory.yaml \
  --candidate candidate.yaml --repo fixtures/good && echo "(exit 0)"

# --- external verifier (verify_completion.sh): enforces the four-state contract ---
VERIFY=../gate/verify_completion.sh

echo
echo "===== verifier: worker OVERSTEP (candidate says 'complete') -> BLOCKED (overstep), exit 1 ====="
sh "$VERIFY" --manifest manifest.yaml --inventory inventory.yaml \
  --candidate candidate_overstep.yaml --repo fixtures/good || echo "(exit $?)"

echo
echo "===== verifier: candidate_complete + BAD artifacts -> BLOCKED, exit 1 ====="
sh "$VERIFY" --manifest manifest.yaml --inventory inventory.yaml \
  --candidate candidate.yaml --repo fixtures/bad || echo "(exit $?)"

echo
echo "===== verifier: candidate_complete + GOOD artifacts -> COMPLETE-GRANTED, exit 0 ====="
sh "$VERIFY" --manifest manifest.yaml --inventory inventory.yaml \
  --candidate candidate.yaml --repo fixtures/good --verdict-out /tmp/completion_verdict.yaml \
  && echo "(exit 0)"
