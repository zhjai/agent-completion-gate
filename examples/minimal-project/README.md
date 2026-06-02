# Minimal project — "add a monthly sales report page"

The everyday version of the failure (no ML needed). You ask an agent to **add a monthly sales
report page**. It builds the page, tests pass, it says done. But:

- the chart has **one data point**,
- the **CSV export** the user asked for was never created,
- (and the title still says "Untitled", the empty state is broken, no screenshot…).

The agent honestly believes it's done — the headline goal *is* done. **The goal just wasn't the
acceptance criteria.** A human distilled what "done" really means into
[`acceptance_manifest.yaml`](acceptance_manifest.yaml); the gate enforces it against the real files.

```bash
sh examples/minimal-project/run.sh
```

- `before/` — what the agent first shipped → the gate returns **BLOCKED**; it cannot call this done.
- `after/`  — the agent fixed the real artifacts → the gate returns **COMPLETE-OK**.

Same `completion_candidate.yaml` (`status: candidate_complete`) both times — only the **real
artifacts** differ, and that's all the gate trusts. The agent can never write `complete` itself.

> Honest note: the gate doesn't know your project. Someone writes the checks
> (`min_series_points` on the chart, `file_exists` on the export). That's the point — completion
> authority moves from the agent's self-report to explicit, human-written checks.
