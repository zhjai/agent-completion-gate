# Worked example — the SwanLab incident

A realistic, populated `acceptance_manifest.yaml` + `surface_inventory.yaml` modelling the
failure that motivated this kit: a run shipped with case display off, run names colliding, and
a degenerate (single-point) val curve, while the agent declared the task done.

These show what a **real** protected spec looks like. To use:

```bash
cp examples/swanlab/acceptance_manifest.yaml gate/acceptance_manifest.yaml
cp examples/swanlab/surface_inventory.yaml   control/surface_inventory.yaml
# then adapt the artifact paths / globs to your repo
```

The **shipped** `gate/acceptance_manifest.yaml` and `control/surface_inventory.yaml` are
intentionally **empty templates** — a fresh install does not block (it enforces only the state
machine: the worker still cannot self-declare `complete`). You opt into artifact strictness by
adding checks/surfaces, or by copying this example.

> This is a **strict, realistic** spec. Its inventory lists only surfaces it actually checks, so
> `--strict-surfaces` is satisfied on *coverage* — but it also carries `review_items:
> dashboard_readability`, so the gate **blocks until a human resolves that review item** and the
> artifacts pass. That's intentional: it models the incident (the run looked done but wasn't).
> Drop the review item / add your own checks to let a clean run through.
