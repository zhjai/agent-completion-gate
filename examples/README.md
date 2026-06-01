# Example: the gate blocking a false completion (real, runnable)

The SwanLab failure that motivated this kit, as a **runnable fixture**. The gate reads the **real files** and refuses to let the run reach `complete`. The transcripts below are actual output of `gate/check_acceptance.py` against the fixtures in this folder — not illustrations.

Reproduce:

```bash
sh examples/run.sh
# or directly:
python3 gate/check_acceptance.py \
  --manifest examples/manifest.yaml --inventory examples/inventory.yaml \
  --candidate examples/candidate.yaml --repo examples/fixtures/bad
```

## Before — worker proposes done, gate BLOCKS (exit 1)

[`fixtures/bad/`](fixtures/bad/): `config.json` has `max_case_examples: 0` (case display off); `metrics.json` has a single `val/normalized/mae` point (no curve).

```
$ check_acceptance ... --repo examples/fixtures/bad
FAIL case_examples_present: max_case_examples=0 (must not be disabled)
FAIL val_curve_non_degenerate: val/normalized/mae points=1 (min 2)

BLOCKED:
  - case_examples_present: max_case_examples=0 (must not be disabled)
  - val_curve_non_degenerate: val/normalized/mae points=1 (min 2)

State must remain 'blocked'/'candidate_complete'. 'complete' is NOT granted.
exit=1
```

## After — artifacts fixed, gate PASSES (exit 0)

[`fixtures/good/`](fixtures/good/): `max_case_examples: 8`; `val/normalized/mae` has 5 points.

```
$ check_acceptance ... --repo examples/fixtures/good
PASS case_examples_present: max_case_examples=8 (must not be disabled)
PASS val_curve_non_degenerate: val/normalized/mae points=5 (min 2)

COMPLETE-OK: all machine checks passed, no review items, no uncovered surfaces.
exit=0
```

## What this proves

- The gate reads **real config/metrics** (`config.json`, `metrics.json`) — never the worker's `run_state`.
- A goal-driven worker **cannot reach `complete`** while the real artifacts are broken; the state stays `blocked`.
- The bundled `check_acceptance.py` ships working readers for these check types (`config_not_disabled`, `min_series_points`, `identity_in_name`, `max_chart_count`); extend per project for your own artifact formats.
- Add a `review_items` entry and it blocks too — `needs-review == blocked`.
