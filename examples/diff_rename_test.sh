#!/usr/bin/env sh
# Regression test for two diff-derivation bypasses (found + reproduced in agent-arena review):
#   1. RENAME elision — a file moved OUT of a surface's path must still flag that surface.
#   2. SPECIAL-CHAR path — a path with a newline must not slip past glob matching.
# Builds throwaway git repos. Requires git + python3 + pyyaml. Exits nonzero on regression.
set -eu
cd "$(dirname "$0")"
DERIVE="$(cd .. && pwd)/gate/derive_touched.py"
INV="$(pwd)/inventory.yaml"   # has surface 'exports' with paths ["exports/*", "*.csv"]

fail() { echo "FAIL: $1"; exit 1; }

# --- case 1: rename exports/data.csv -> renamed.bin (out of the exports surface) ---
T1="$(mktemp -d)"; trap 'rm -rf "$T1" "${T2:-}"' EXIT
( cd "$T1"
  git init -q && git config user.email t@t && git config user.name t
  mkdir exports && echo x > exports/data.csv && git add -A && git commit -qm base
)
BASE1="$(cd "$T1" && git rev-parse HEAD)"
( cd "$T1" && git mv exports/data.csv renamed.bin && git commit -qm "rename out of exports" )
echo "case 1 (rename): default name-only shows -> $(cd "$T1" && git diff --name-only "$BASE1"...HEAD | tr '\n' ' ')"
TOUCHED1="$(cd "$T1" && python3 -E "$DERIVE" --inventory "$INV" --git-diff "$BASE1")"
echo "  derive_touched -> ${TOUCHED1:-<none>}"
printf '%s\n' "$TOUCHED1" | grep -qx exports || fail "rename hid the 'exports' surface"
echo "  PASS: rename did not hide 'exports'"

# --- case 2: a path containing a newline under exports/ ---
T2="$(mktemp -d)"
( cd "$T2"
  git init -q && git config user.email t@t && git config user.name t
  echo base > seed && git add -A && git commit -qm base
)
BASE2="$(cd "$T2" && git rev-parse HEAD)"
( cd "$T2" && mkdir exports && printf 'x' > "exports/evil
name.csv" && git add -A && git commit -qm "newline path" )
TOUCHED2="$(cd "$T2" && python3 -E "$DERIVE" --inventory "$INV" --git-diff "$BASE2")"
echo "case 2 (newline path): derive_touched -> ${TOUCHED2:-<none>}"
printf '%s\n' "$TOUCHED2" | grep -qx exports || fail "newline path slipped past the 'exports' glob"
echo "  PASS: newline path matched 'exports'"

echo "ALL REGRESSION CHECKS PASSED"
