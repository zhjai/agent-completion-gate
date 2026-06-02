#!/usr/bin/env python3
"""Self-tests for the completion gate. Plain stdlib unittest (no pytest dep).

Run:  python3 tests/test_gate.py        (or: python3 -m unittest -v tests.test_gate)
Each test asserts the gate's EXIT CODE (0 = complete granted, !=0 = not granted).
These double as the security regression suite — most cases are reproductions of bypasses
found in heterogeneous (Codex x Claude) review.
"""
import subprocess, sys, tempfile, textwrap, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "gate" / "check_acceptance.py"
EX = ROOT / "examples"
MANIFEST, INVENTORY = EX / "manifest.yaml", EX / "inventory.yaml"
GOOD, BAD = EX / "fixtures" / "good", EX / "fixtures" / "bad"


def gate(candidate, repo=GOOD, manifest=MANIFEST, inventory=INVENTORY, extra=(), env=None, cwd=None):
    """Run check_acceptance.py hermetically; return (rc, combined_output)."""
    cmd = [sys.executable, "-E", str(GATE), "--manifest", str(manifest),
           "--inventory", str(inventory), "--candidate", str(candidate),
           "--repo", str(repo), *extra]
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=cwd)
    return p.returncode, p.stdout + p.stderr


def write(tmp, text):
    f = Path(tmp) / "candidate.yaml"
    f.write_text(textwrap.dedent(text))
    return f


class GateContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_good_candidate_complete_grants(self):
        rc, out = gate(EX / "candidate.yaml", repo=GOOD)
        self.assertEqual(rc, 0, out)

    def test_bad_artifacts_block(self):
        rc, out = gate(EX / "candidate.yaml", repo=BAD)
        self.assertEqual(rc, 1, out)

    def test_worker_overstep_complete_blocks(self):
        # worker wrote `complete` itself -> overstep, even with good artifacts
        rc, out = gate(EX / "candidate_overstep.yaml", repo=GOOD)
        self.assertEqual(rc, 1, out)
        self.assertIn("overstep", out)

    def test_missing_candidate_fails_closed(self):
        rc, out = gate(Path(self.tmp) / "nope.yaml", repo=GOOD)
        self.assertEqual(rc, 1, out)

    def test_review_queue_string_blocks_not_crash(self):
        c = write(self.tmp, """
            status: candidate_complete
            touched_surfaces: []
            review_queue:
              - dashboard_readability
        """)
        rc, out = gate(c, repo=GOOD)
        self.assertEqual(rc, 1, out)
        self.assertIn("needs-review", out)
        self.assertNotIn("Traceback", out)

    def test_conflicting_status_state_blocks(self):
        c = write(self.tmp, "status: []\nstate: candidate_complete\ntouched_surfaces: []\n")
        rc, out = gate(c, repo=GOOD)
        self.assertEqual(rc, 1, out)

    def test_non_mapping_candidate_blocks(self):
        c = write(self.tmp, "- a\n- b\n")
        rc, out = gate(c, repo=GOOD)
        self.assertEqual(rc, 1, out)

    def test_review_queue_dict_blocks(self):
        c = write(self.tmp, """
            status: candidate_complete
            touched_surfaces: []
            review_queue:
              - id: dash_readability
                description: x
        """)
        rc, out = gate(c, repo=GOOD)
        self.assertEqual(rc, 1, out)
        self.assertIn("dash_readability", out)

    def test_strict_surfaces_blocks_uncovered(self):
        # inventory has 'exports' (user-visible) with no check in manifest
        rc, out = gate(EX / "candidate.yaml", repo=GOOD, extra=["--strict-surfaces"])
        self.assertEqual(rc, 1, out)
        self.assertIn("exports", out)

    def test_touched_trusted_override_blocks(self):
        rc, out = gate(EX / "candidate.yaml", repo=GOOD, extra=["--touched", "case_examples,exports"])
        self.assertEqual(rc, 1, out)
        self.assertIn("exports", out)

    def test_agent_writable_root_rejects_spec_inside(self):
        rc, out = gate(EX / "candidate.yaml", repo=GOOD, extra=["--agent-writable-root", str(EX)])
        self.assertEqual(rc, 1, out)
        self.assertIn("agent-writable", out)

    def test_agent_writable_root_rejects_symlink_out(self):
        # a symlink INSIDE the writable root, pointing to a real spec OUTSIDE it, must still block
        # (the literal path is worker-controlled even though it resolves outside).
        import os
        root = Path(self.tmp) / "writable"; root.mkdir()
        link = root / "manifest.yaml"
        os.symlink(MANIFEST, link)
        rc, out = gate(EX / "candidate.yaml", repo=GOOD, manifest=link,
                       extra=["--agent-writable-root", str(root)])
        self.assertEqual(rc, 1, out)
        self.assertIn("agent-writable", out)

    def test_derive_touched_invalid_bytes_no_crash(self):
        # a changed-files list with a non-UTF-8 byte + NUL separators must not crash the deriver
        p = Path(self.tmp) / "changed"
        p.write_bytes(b"exports/bad_\xff.csv\0config.json\0")
        r = subprocess.run([sys.executable, "-E", str(ROOT / "gate" / "derive_touched.py"),
                            "--inventory", str(INVENTORY), "--changed-files-from", str(p)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("exports", r.stdout)          # exports/* matched despite the bad byte
        self.assertNotIn("Traceback", r.stderr)

    def test_empty_default_specs_pass(self):
        # shipped templates are empty -> a candidate_complete proposal is granted (no brick)
        rc, out = gate(EX / "candidate.yaml", repo=GOOD,
                       manifest=ROOT / "gate" / "acceptance_manifest.yaml",
                       inventory=ROOT / "control" / "surface_inventory.yaml",
                       extra=["--strict-surfaces"])
        self.assertEqual(rc, 0, out)

    def test_import_shadow_does_not_bypass(self):
        # plant a malicious yaml.py + PYTHONPATH; the gate must still BLOCK the overstep+bad case
        Path(self.tmp, "yaml.py").write_text(
            'def safe_load(*a, **k): return {"status": "candidate_complete", "touched_surfaces": []}\n'
            'def safe_dump(*a, **k): return ""\n')
        import os
        env = dict(os.environ, PYTHONPATH=self.tmp)
        rc, out = gate(EX / "candidate_overstep.yaml", repo=BAD, env=env, cwd=self.tmp)
        self.assertNotEqual(rc, 0, out)  # -E must ignore PYTHONPATH; real yaml used


if __name__ == "__main__":
    unittest.main(verbosity=2)
