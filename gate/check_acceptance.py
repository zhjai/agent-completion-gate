#!/usr/bin/env python3
"""
check_acceptance.py — external completion gate. FAIL-CLOSED.

Invariants (do NOT weaken — each was a hole a goal-driven agent could exploit;
items 5-7 were added after a heterogeneous red-team found bypasses):
  1. This script + the manifest + the surface inventory must be PROTECTED:
     read-only-mounted or outside the agent-writable workspace. A worker must not
     be able to edit them. Completion truth sources are human/CI-maintained only.
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
import argparse, json, os, sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required", file=sys.stderr); sys.exit(2)


def load_protected(path: Path, agent_writable_root: "Path | None" = None) -> dict:
    """Load a protected spec file. Caller is responsible for mounting it read-only; if
    --agent-writable-root is given we additionally REFUSE to run when the spec resolves
    inside that root (invariant #1: the gate's spec must be outside the worker's reach)."""
    if not path.exists():
        print(f"BLOCKED: protected spec missing: {path}", file=sys.stderr); sys.exit(1)
    if agent_writable_root is not None:
        try:
            root = agent_writable_root.resolve()
            # Check BOTH the literal location (abspath, normalizes '..' WITHOUT following
            # symlinks) and the symlink-resolved target. The literal check is the important one:
            # if the spec is *reached through* a path inside the writable root, a worker can swap
            # that path for a symlink pointing anywhere — so reject it regardless of target.
            candidates = (Path(os.path.abspath(path)), path.resolve())
        except OSError as e:
            print(f"BLOCKED: cannot resolve spec path ({e}); fail closed.", file=sys.stderr); sys.exit(1)
        for cand in candidates:
            if cand == root or root in cand.parents:
                print(f"BLOCKED: protected spec {path} is reachable inside the agent-writable root "
                      f"{agent_writable_root} — it must be read-only / outside the worker's reach "
                      f"(invariant #1).", file=sys.stderr)
                sys.exit(1)
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
    ap.add_argument("--strict-surfaces", action="store_true",
                    help="require EVERY user-visible surface in the inventory to have a passing "
                         "check; ignore the worker-reported touched_surfaces. Recommended in CI / "
                         "for untrusted workers (the touched_surfaces list is a worker self-report).")
    ap.add_argument("--touched", metavar="IDS",
                    help="comma-separated surface ids that were ACTUALLY touched (TRUSTED, "
                         "caller-supplied — e.g. from derive_touched.py against a git diff). "
                         "Overrides the worker-reported touched_surfaces for the uncovered-surface "
                         "rule. Ignored if --strict-surfaces is set.")
    ap.add_argument("--agent-writable-root", metavar="DIR",
                    help="fail closed if the manifest/inventory resolve INSIDE this dir "
                         "(the worker's writable workspace). Enforces invariant #1 at runtime.")
    a = ap.parse_args()
    repo = Path(a.repo)
    awr = Path(a.agent_writable_root) if a.agent_writable_root else None

    manifest = load_protected(Path(a.manifest), awr)
    inventory = load_protected(Path(a.inventory), awr)
    candidate = yaml.safe_load(Path(a.candidate).read_text()) if Path(a.candidate).exists() else {}
    if not isinstance(candidate, dict):
        print(f"BLOCKED: candidate is not a mapping ({type(candidate).__name__}); fail closed.", file=sys.stderr)
        return 1

    blocked: list[str] = []

    # (1b) STATE GUARD — a worker may reach at most `candidate_complete`. Enforced HERE,
    # in the protected entrypoint, so there is no shell-side parser to shadow or spoof.
    state, serr = candidate_state(candidate)
    if serr:
        blocked.append(f"invalid completion candidate: {serr} (fail closed)")
    elif state == "complete":
        blocked.append("worker overstep: candidate declares 'complete'; a worker may reach at most 'candidate_complete'")
    elif state != "candidate_complete":
        blocked.append(f"not a completion proposal: status='{state}' (expected 'candidate_complete')")

    # (3) UNKNOWNS FAIL CLOSED: every user-visible surface needs a passing check.
    must_check = {s["id"] for s in inventory.get("surfaces", []) if s.get("user_visible")}
    covered = {c.get("surface") for c in manifest.get("checks", [])}
    if a.strict_surfaces:
        # Do NOT trust the worker's touched_surfaces: require coverage of ALL user-visible surfaces.
        for s in sorted(must_check):
            if s not in covered:
                blocked.append(f"strict-surfaces: user-visible surface '{s}' has no check")
    elif a.touched is not None:
        # TRUSTED touched set (e.g. derive_touched.py from a git diff). Overrides the worker.
        touched = {t.strip() for t in a.touched.split(",") if t.strip()}
        for s in sorted(touched):
            if s in must_check and s not in covered:
                blocked.append(f"touched user-visible surface (trusted/diff-derived), no check: {s}")
    else:
        # Default: use the worker-reported touched_surfaces. This is a SELF-REPORT, not trusted
        # evidence — a worker can omit a surface it touched. Use --strict-surfaces, or pass a
        # diff-derived --touched, whenever the worker is untrusted.
        touched = set(candidate.get("touched_surfaces", []) or [])
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
        item_id = item.get("id", item) if isinstance(item, dict) else item
        blocked.append(f"needs-review (blocks completion): {item_id}")

    if blocked:
        print("\nBLOCKED:")
        for b in blocked:
            print(f"  - {b}")
        print("\nState must remain 'blocked'/'candidate_complete'. 'complete' is NOT granted.")
        return 1

    print("\nCOMPLETE-OK: all machine checks passed, no review items, no uncovered surfaces.")
    return 0


def candidate_state(candidate: dict):
    """Read the worker-proposed state STRICTLY. Returns (state, error).
    Scalar string only; NO truthiness fallback (so `status: []` can't silently defer to
    `state:`); conflicting `status`/`state` is an error. The worker's status is a CLAIM
    to validate, never a verdict to trust."""
    has_status = "status" in candidate
    has_state = "state" in candidate
    if has_status and has_state and candidate.get("status") != candidate.get("state"):
        return None, "conflicting 'status' and 'state' fields"
    if has_status:
        raw = candidate.get("status")
    elif has_state:
        raw = candidate.get("state")
    else:
        return None, "no 'status'/'state' field"
    if not isinstance(raw, str):
        return None, f"status must be a string scalar, got {type(raw).__name__}"
    return raw.strip(), None


# --- artifact readers: read REAL files (JSON or YAML). Extend per project. ---
def _load(p: Path):
    if not p.exists():
        return {}
    txt = p.read_text()
    try:
        return json.loads(txt)        # artifacts are DATA, parsed structurally — never executed/instructed
    except Exception:
        return yaml.safe_load(txt) or {}
def _read_config(p: Path): return _load(p)
def _dig(d, dotted):
    cur = d
    for k in dotted.split("."):
        cur = (cur or {}).get(k)
    return cur
def _count_points(p, series):
    v = _load(p).get(series)
    return len(v) if isinstance(v, list) else 0
def _count_charts(p, group):
    return sum(1 for k in _load(p) if str(k).split("/")[0] == group)
def _read_run_name(p):
    return _load(p).get("name")


if __name__ == "__main__":
    sys.exit(main())
