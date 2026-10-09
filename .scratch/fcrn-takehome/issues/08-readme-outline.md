# README outline

Type: grilling
Status: resolved
Blocked by:

## Question

Which sections does the README have, in which order, and what does each one say?

Decide:
- The section list beyond sizing and deploy/operate. Candidates: quick start (`docker run ... postgres:17`, `yoyo apply`, `uv run fcrn-dispatcher --fast`), design overview (tasks, seams, clock), how Requirement 1 is checked, testing, assumptions and limits.
- Whether the design overview includes a diagram, and in which form (ASCII or Mermaid).
- How much each section restates from the resolved tickets, versus a short summary.
- Where the out-of-scope items (NEM/AEM, FCR-D, real BESS adapter) are stated.

## Comments

- From Datastore, schema and operations story: the operate section has six points (RDS, `yoyo apply`, partitions and retention, backups, alarms, Timescale scale-up).
- From Package layout and module seams: the README states that `run_id` serves only step tests, that production reads samples by time, and that a fleet keys on `(battery_id, at)`.

## Answer

The README stands alone. Each section is a short summary, plus a table where one fits, about one screen long. It links only to `CONTEXT.md`, `docs/` and the planning map.

| # | Section | Content |
|---|---|---|
| 1 | What this is | Two lines plus the droop law. |
| 2 | Quick start | `docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=dev postgres:17`, `cp .env.example .env`, `yoyo apply`, `uv run fcrn-dispatcher --fast`. |
| 3 | Assignment map | A table from the six "What to Build" items to the module and the test that deliver each one. |
| 4 | Battery sizing | The table from Battery sizing (C, Pmax, E, SoC limits, starting SoC, losses) with reasons. The Pmax row names the NEM headroom. |
| 5 | Design | A few lines on the three tasks, the `Battery` seam and fail-stop. Links to `docs/architecture.md` and ADR 0002. |
| 6 | Step test and Requirement 1 | The Pss windows, the two ratios and the per-sample checks. Real CLI output, captured from a `--fast` run, for example `Requirement 1 up: +0.000 (allowed -0.05..+0.20)`. Never invented numbers. |
| 7 | Testing | `uv run pytest`, the `integration` marker (skipped without Docker), and the four property tests. |
| 8 | Deploy and operate | The six points from Datastore, schema and operations story. Links to ADR 0001. |
| 9 | Assumptions and out of scope | Assumptions: no losses, an ideal battery response, and a step change in frequency with no ramp. `run_id` serves step tests only, and a fleet would key on `(battery_id, at)`. Out of scope: NEM/AEM, FCR-D, a real BESS adapter, a plot. |
| 10 | How this was planned | Two sentences. They link `.scratch/fcrn-takehome/map.md` and say each ticket holds one decision. |

Other docs:
- `docs/architecture.md`: one Mermaid flowchart. It shows producer → latest-value cell → control → `Battery` seam, and control → queue → writer → Postgres, with the loop-factory seam marked. Short notes on the tasks and seams sit under it. Build task.
- [ADR 0002](../../../docs/adr/0002-event-loop-is-the-clock.md): the event loop is the clock. Written in this session.
- `.scratch/` gets committed to show the planning. The prototype has a "throwaway, real code is in `src/`" header. Ruff and pytest exclude `.scratch/`.
