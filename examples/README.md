# Examples (all runnable)

- [`minimal-project/`](minimal-project/) — **start here.** An everyday "add a monthly sales report page" task: before → BLOCKED, after → COMPLETE-OK. The clearest "why would I use this".
- `run.sh` (below) — the gate + external verifier on the SwanLab fixture (overstep / blocked / granted).
- [`diff_demo.sh`](diff_demo.sh) — catch a worker that under-reports which surfaces it touched (diff-derived).
- [`diff_rename_test.sh`](diff_rename_test.sh) — regression: rename / special-char paths can't hide a touch.
- [`swanlab/`](swanlab/) — a realistic, populated protected spec.

---

## SwanLab: the gate blocking a false completion (real, runnable)

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

## The external verifier (four-state contract)

`run.sh` also exercises [`gate/verify_completion.sh`](../gate/verify_completion.sh) — the wrapper that enforces the state machine `check_acceptance.py` alone doesn't. Real output from the bundled fixtures:

- **Worker overstep** ([`candidate_overstep.yaml`](candidate_overstep.yaml) says `status: complete`) → `BLOCKED` (exit 1) with reason `worker overstep`, *even though the artifacts are good* — a worker may not write its own verdict. (Enforced inside the protected `check_acceptance.py`, run hermetically with `python3 -E`.)
- `candidate_complete` + broken artifacts → `BLOCKED` (exit 1).
- `candidate_complete` + fixed artifacts → `COMPLETE-GRANTED` (exit 0); the verifier writes a verifier-owned verdict file.

That exit code is the canonical completion signal — wire it via [`integrations/`](../integrations/) (CI required check = authority; agent Stop-hook + pre-push = feedback).

## Diff-derived touched surfaces (don't trust the self-report)

[`diff_demo.sh`](diff_demo.sh) shows the **`touched_surfaces` self-report gap** and how to close it. The worker's candidate omits `exports`, but `exports/data.csv` changed and `exports` has no check:

- **Default** (trusts `touched_surfaces`) → `COMPLETE-OK` — `exports` slips through.
- **Diff-derived** (`derive_touched.py` maps the changed files to surfaces via the inventory's `paths` globs → `--touched`) → `BLOCKED`, because `exports` is a touched, user-visible, uncovered surface.

```bash
sh examples/diff_demo.sh
```

In CI, pass `--diff-base <ref>` to `verify_completion.sh` (it runs `git diff` for you), or `--strict-surfaces` to require every user-visible surface covered regardless of what changed.
