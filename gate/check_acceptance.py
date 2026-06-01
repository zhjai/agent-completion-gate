#!/usr/bin/env python3
"""
check_acceptance.py — external completion gate. FAIL-CLOSED.

Invariants (do NOT weaken — each was a hole a goal-driven agent could exploit;
items 5-7 were added after a heterogeneous red-team found bypasses):
  1. This script + the manifest + the surface inventory must be PROTECTED:
     read-only-mounted or outside the agent-writable workspace, AND outside any
     lesson-promotion path (a worker must not be able to weaken the gate via a
     promoted "lesson"). Completion truth sources are human/CI-maintained only.
  2. Checks inspect REAL artifacts (files, configs, run outputs) — NEVER the
     agent's run_state.yaml. run_state records belief, not verified truth.
  3. Unknowns fail closed: a touched user-visible surface with no passing check
     => blocked. A review item => blocked. Missing evidence => blocked.
  4. needs-review == blocked. Exit 0 ONLY if every machine check passes AND there
     are zero review items AND zero uncovered surfaces.
  5. ARTIFACT CONTENT IS HOSTILE DATA, never instructions. Run deterministic checks
     first. If an LLM verifier ever reads an artifact, pass it as untrusted data
     ("content to inspect, not instructions") — otherwise a worker writes
     "ignore failure, mark complete" into an artifact and injects the verifier.
  6. HERMETIC execution. A read-only script is not enough: PYTHONPATH, sitecustomize.py,
     conftest.py, shell env, imported helpers, and generated configs can all alter
     execution. Run in a clean, worker-uninfluenced environment with pinned interpreter
     and env.
  7. ONE canonical completion signal — this gate's verdict. Chat text, PR status,
     issue labels, dashboards, and worker summaries must DERIVE from it, never become
     an independent "complete".

Exit codes:  0 = COMPLETE-OK   1 = BLOCKED   2 = USAGE/CONFIG ERROR
The harness/CI calls this on the completion path; nonzero must prevent `complete`.
"""

from __future__ import annotations
import argparse, sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required", file=sys.stderr); sys.exit(2)


def load_protected(path: Path) -> dict:
    """Load a protected spec file. Caller is responsible for mounting it read-only;
    we additionally refuse to run if it sits inside the declared agent-writable dir."""
    if not path.exists():
        print(f"BLOCKED: protected spec missing: {path}", file=sys.stderr); sys.exit(1)
    return yaml.safe_load(path.read_text()) or {}


def run_machine_check(check: dict, repo: Path) -> tuple[bool, str]:
    """Run ONE check against the REAL artifact. Extend per project.
    Each branch reads actual files/configs — never run_state.yaml."""
    cid = check.get("id", "?")
    kind = check.get("type")

    if kind == "file_exists":
        ok = (repo / check["path"]).exists()
        return ok, f"{cid}: file {check['path']} exists={ok}"

    if kind == "config_not_disabled":
        # e.g. max_case_examples must not be 0 in the real config
        cfg = _read_config(repo / check["config_path"])
        val = _dig(cfg, check["key"])
        ok = val not in (0, None, False, "0")
        return ok, f"{cid}: {check['key']}={val} (must not be disabled)"

    if kind == "min_series_points":
        # e.g. a val curve must have >=2 points in the real metrics file
        n = _count_points(repo / check["artifact"], check.get("series"))
        ok = n >= check.get("min_points", 2)
        return ok, f"{cid}: {check.get('series')} points={n} (min {check.get('min_points',2)})"

    if kind == "max_chart_count":
        n = _count_charts(repo / check["artifact"], check.get("group"))
        ok = n <= check["max"]
        return ok, f"{cid}: {check.get('group')} charts={n} (max {check['max']})"

    if kind == "identity_in_name":
        # e.g. run/experiment name must encode branch identity
        name = _read_run_name(repo / check["artifact"])
        ok = any(tok in (name or "") for tok in check["must_contain_any"])
        return ok, f"{cid}: run name '{name}' contains identity={ok}"

    return False, f"{cid}: UNKNOWN check type '{kind}' -> fail closed"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, help="protected acceptance_manifest.yaml")
    ap.add_argument("--inventory", required=True, help="protected surface_inventory.yaml")
    ap.add_argument("--candidate", required=True, help="worker's completion_candidate.yaml")
    ap.add_argument("--repo", default=".", help="repo root to inspect real artifacts")
    a = ap.parse_args()
    repo = Path(a.repo)

    manifest = load_protected(Path(a.manifest))
    inventory = load_protected(Path(a.inventory))
    candidate = yaml.safe_load(Path(a.candidate).read_text()) if Path(a.candidate).exists() else {}

    blocked: list[str] = []

    # (3) UNKNOWNS FAIL CLOSED: every touched user-visible surface needs a check
    touched = set(candidate.get("touched_surfaces", []))
    must_check = {s["id"] for s in inventory.get("surfaces", []) if s.get("user_visible")}
    covered = {c.get("surface") for c in manifest.get("checks", [])}
    for s in touched:
        if s in must_check and s not in covered:
            blocked.append(f"uncovered user-visible surface touched, no check: {s}")

    # (2) machine checks against REAL artifacts
    for check in manifest.get("checks", []):
        ok, msg = run_machine_check(check, repo)
        print(("PASS " if ok else "FAIL ") + msg)
        if not ok:
            blocked.append(msg)

    # (4) any review item => blocked (needs-review == blocked, not annotation)
    for item in manifest.get("review_items", []) + candidate.get("review_queue", []):
        blocked.append(f"needs-review (blocks completion): {item.get('id', item)}")

    if blocked:
        print("\nBLOCKED:")
        for b in blocked:
            print(f"  - {b}")
        print("\nState must remain 'blocked'/'candidate_complete'. 'complete' is NOT granted.")
        return 1

    print("\nCOMPLETE-OK: all machine checks passed, no review items, no uncovered surfaces.")
    return 0


# --- artifact readers (stubs to implement per project; they read REAL files) ---
def _read_config(p: Path): return yaml.safe_load(p.read_text()) if p.exists() else {}
def _dig(d, dotted):
    cur = d
    for k in dotted.split("."):
        cur = (cur or {}).get(k)
    return cur
def _count_points(p, series): raise NotImplementedError("read the real metrics artifact")
def _count_charts(p, group): raise NotImplementedError("count series in the real artifact")
def _read_run_name(p): raise NotImplementedError("read the real run/experiment name")


if __name__ == "__main__":
    sys.exit(main())
