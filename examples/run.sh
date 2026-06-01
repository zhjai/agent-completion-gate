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
