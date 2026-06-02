#!/usr/bin/env sh
# Diff-derived touched surfaces — catch a worker that UNDER-REPORTS what it touched.
# Requires: python3 + pyyaml.  (Uses a static changed-files list so it's deterministic;
# in CI you'd pass `--git-diff <base>` / verify_completion.sh --diff-base <ref> instead.)
set -e
cd "$(dirname "$0")"
GATE=../gate/check_acceptance.py
DERIVE=../gate/derive_touched.py

echo "Pretend change set (examples/fixtures/changed_files.txt):"
sed 's/^/  /' fixtures/changed_files.txt
echo
echo "The worker's candidate.yaml self-reports touched_surfaces: [case_examples, metrics_curves]"
echo "  -> it did NOT mention 'exports', even though exports/data.csv changed."
echo "     'exports' is user-visible in inventory.yaml and has NO check in manifest.yaml."

echo
echo "===== DEFAULT (trusts the worker self-report) -> GRANTED (the gap) ====="
python3 -E "$GATE" --manifest manifest.yaml --inventory inventory.yaml \
  --candidate candidate.yaml --repo fixtures/good && echo "(exit 0 — 'exports' slipped through)"

echo
echo "===== DIFF-DERIVED touched set (TRUSTED) ====="
TOUCHED=$(python3 -E "$DERIVE" --inventory inventory.yaml \
  --changed-files-from fixtures/changed_files.txt | tr '\n' ',' | sed 's/,*$//')
echo "derive_touched -> $TOUCHED"
echo
echo "===== gate with --touched (TRUSTED) -> BLOCKED ('exports' uncovered) ====="
python3 -E "$GATE" --manifest manifest.yaml --inventory inventory.yaml \
  --candidate candidate.yaml --repo fixtures/good --touched "$TOUCHED" \
  || echo "(exit $? — caught the under-reported surface the self-report hid)"
