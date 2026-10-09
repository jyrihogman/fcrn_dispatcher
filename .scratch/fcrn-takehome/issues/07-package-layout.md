# Package layout and module seams

Type: grilling
Status: resolved
Blocked by: 05

## Question

Where do the controller, battery, runtime, entry point and store live, and which imports are allowed between them?

Decide:
- The module list. Example: `droop.py` (pure), `battery.py` (`Battery` seam, `BatteryState`, `simulated_battery`), `runtime.py` (tasks, `run`, `wall_clock`), `store.py`, `__main__.py` (CLI).
- The import rules. The controller must stay independent of timing, networking, persistence and simulation. Example: `droop.py` imports nothing from the package.
- Where `Sample` lives, since the runtime builds it and the store writes it.
- The CLI flags. Known so far: `--fast` picks the looptime loop factory. The store location comes from the Datastore ticket.

## Comments

- From Datastore, schema and operations story: add a settings module (pydantic-settings `Settings`) and a `migrations/` directory of yoyo `.sql` files. The store module holds the async psycopg 3 `write_batch`. pydantic stays at trust boundaries only, so the pure modules must not import it.
- From Test plan: place the pure `steady_state_response` and `requirement_1` functions. The CLI prints the Requirement 1 ratios after a step-test run and exits with code 1 on FAIL. Tests need a pytest marker `integration` for the testcontainers Postgres test.

## Answer

| Decision | Answer |
|---|---|
| Package | `src/fcrn_dispatcher/` (src layout). The name stays: it is the dispatcher of an FCR-N battery and matches the repo and `CONTEXT.md`. |
| Modules | `droop.py` (`droop`, `F_REF_HZ`, `DF_MAX_HZ`), `battery.py` (`Battery` seam, `BatteryState`, `advance`, `command`, `simulated_battery`), `sample.py` (`Sample`), `step_test.py` (`STEP_TEST`, `steady_state_response`, `requirement_1`), `runtime.py` (`latest`, `wall_clock`, `produce`, `control`, `write`, `run`, loop factories), `store.py` (`postgres_store`), `settings.py` (`Settings`), `__main__.py` (CLI wiring). |
| `Sample` | Its own `sample.py`, so the pure modules import neither asyncio nor psycopg. |
| Import rules | `droop`, `sample`, `battery` and `settings` import nothing from the package. `step_test` and `store` import `sample` only. `runtime` imports `droop`, `battery` and `sample`, never `store` or `settings`: `write_batch` and the sizing values arrive as arguments. Only `__main__` imports everything. pydantic appears only in `settings`. One `ast`-based pytest checks a dict of allowed imports. No new dependency. |
| CLI | `uv run fcrn-dispatcher [--fast]` via `[project.scripts]`. `python -m fcrn_dispatcher` also works. It always runs `STEP_TEST` on the simulated battery, writes to Postgres, prints the Requirement 1 ratios and exits 1 on FAIL. `DATABASE_URL` is required, because the CLI is the real-world demo. The only flag is `--fast`. |
| Fake store | `tests/conftest.py`: a list plus an `async def write_batch`. It never ships in the package. |
| looptime | A main dependency, because `--fast` needs it at runtime. |
| Store shape | `postgres_store(conn, run_id) -> write_batch`, a closure. `__main__` creates a `uuid4()` and opens the `AsyncConnection` with `async with`. `Sample` and the runtime never see `run_id`. |
| `run_id` | Kept only to read back the samples of one step test. Example: two overlapping `--fast` runs share wall timestamps, and `WHERE run_id = $1` separates them. In production the process runs for weeks, samples are read by time, and `run_id` carries no meaning. The README says a fleet would key on `(battery_id, at)`. No per-sample event id: `(run_id, at)` already identifies every sample. |
| Layout | `migrations/` and `tests/` at the repo root. One test file per module, plus `test_imports.py`, `test_step_test.py` and `test_postgres.py`. The `integration` marker is registered in `pyproject.toml`. |

Glossary: `CONTEXT.md` now defines **Run** as one process lifetime, and says the run identifier serves only step tests.
