#!/usr/bin/env sh
# Minimal real-project walkthrough: "add a monthly sales report page".
# The agent says done both times. The gate reads the REAL artifacts and disagrees the first time.
set -e
cd "$(dirname "$0")"
GATE=../../gate/check_acceptance.py

echo "Task given to the agent: \"add a monthly sales report page\"."
echo "The agent reports candidate_complete both times. The gate checks the real files."
echo

echo "===== BEFORE — agent did the headline task, missed the details (expect BLOCKED) ====="
echo "  artifacts/report.json: title 'Untitled', 1 data point, export_csv: false; no exports/monthly.csv"
python3 -E "$GATE" --manifest acceptance_manifest.yaml --inventory surface_inventory.yaml \
  --candidate completion_candidate.yaml --repo before || echo "  -> BLOCKED (exit $?). The agent could NOT call this done."

echo
echo "===== AFTER — agent fixed the real artifacts (expect COMPLETE-OK) ====="
echo "  3 data points + exports/monthly.csv present"
python3 -E "$GATE" --manifest acceptance_manifest.yaml --inventory surface_inventory.yaml \
  --candidate completion_candidate.yaml --repo after && echo "  -> COMPLETE-OK (exit 0)."
