Label: wayfinder:map

# FCR-N droop take-home

## Destination

Every design decision for the take-home is made. An ordered list of build tasks, each sized for one agent session, is ready to hand off. No code is written in this map.

## Notes

- Sources: `FCR-N Droop Take-Home Assignment.pdf` and the appendix PDF. Only §3.1.1 and Table 3 are required. §3.5 Table 10 is used for battery sizing.
- Stack: Python 3.15+, `uv`, `asyncio`, pytest, hypothesis, ruff, ty.
- Python style: functional as much as possible. Prefer pure functions. Use a class only where it is absolutely needed.
- The step test also checks Requirement 1 (steady-state response within −5% / +20%).
- Sizing follows the Table 10 LER rules.
- Deliverable docs: one README with the sizing reasons and the deploy and operate story.
- Vocabulary lives in `CONTEXT.md`. Use its terms in tickets.
- For grilling tickets, call the `grilling` and `domain-modeling` skills.
- The parent `~/personal/AGENTS.md` (Rust, OpenSpec) does not apply to this repo.

## Decisions so far

- Destination is a plan, not a build (chart session).
- Repo is its own git repo with a local markdown tracker in `.scratch/` (chart session).
- Python, `uv`, `asyncio` (chart session).
- The step test checks Requirement 1 (chart session).
- Sizing follows the Table 10 LER rules (chart session).
- In-scope docs: README only (chart session).
- [Simulated time for asyncio tests](issues/01-simulated-time-for-asyncio-tests.md): use looptime, and production code reads time only through `loop.time()`.
- [Battery sizing](issues/02-battery-sizing.md): C = 1 MW, Pmax = 1.34 MW, E = 2 MWh usable, SoC starts at 0.5, no losses.
- [Battery interface and simulated battery behaviour](issues/03-battery-interface-and-behaviour.md): positive power means discharge. The seam is a frozen dataclass of async callables. A pure core sits under a closure shell. The controller saturates at ±C, and the battery clamps at Pmax and at the SoC limits.
- [Runtime and clock design](issues/04-runtime-and-clock-design.md): three tasks in a TaskGroup (producer, control, writer). A latest-value cell carries frequency, and a queue carries samples. Control runs at 10 Hz and builds each sample. The event loop is the clock, and the loop factory is the seam (default or looptime). Failures stop the whole run.
- [Datastore, schema and operations story](issues/05-datastore-and-operations.md): plain Postgres on RDS (ADR 0001), one `samples` table with a BRIN index, yoyo SQL migrations, async psycopg 3 `COPY` writes. Config comes from env and `.env` through pydantic-settings. A fake store serves the unit tests, and one testcontainers test covers Postgres.
- [Test plan](issues/06-test-plan.md): Pss is mean actual power over the last 60 s of each step. A pure `requirement_1` serves the step test and the CLI, which exits 1 on FAIL. The step test checks limits, `actual == commanded` and `commanded == droop(f)` on all 12,601 samples. Four hypothesis properties cover the pure core. All runtime tests use looptime, and the Postgres test is marked `integration`.
- [Package layout and module seams](issues/07-package-layout.md): `src/fcrn_dispatcher/` with eight modules and `Sample` in its own module. An `ast` test enforces the import rules. The CLI always runs the step test against Postgres. `run_id` exists only for step tests. The fake store lives in `tests/`.
- [README outline](issues/08-readme-outline.md): ten sections, with the assignment map third and a planning pointer last. The README stands alone. The diagram goes in `docs/architecture.md`, and the clock gets ADR 0002. `.scratch/` gets committed.
- [Build-task breakdown](issues/09-build-task-breakdown.md): seven tasks in a new effort, [fcrn-build](../fcrn-build/spec.md). 02 runs with 03, and 04 with 05. TDD for the four code tasks. Every task passes ruff, ty and pytest and ends with one commit. The PDFs are gitignored.

## Not yet specified

Nothing. The way is clear. The build continues in [fcrn-build](../fcrn-build/spec.md).

## Out of scope

- Normal and alert state energy management (NEM/AEM, §3.5.1 and §3.5.2). The assignment requires only §3.1.1.
- FCR-D, and the dynamic performance and stability tests in the other parts of §3.
- A plot of the step response. The user chose README only.
- A real network-connected BESS adapter. The design keeps the seam for one, but no adapter gets built.
