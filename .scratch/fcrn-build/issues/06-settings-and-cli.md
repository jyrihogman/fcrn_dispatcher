# Settings and CLI

Status: ready-for-agent
Blocked by: 04, 05
TDD: no

## Task

Wire everything into the CLI.

- `settings.py`: `Settings` with pydantic-settings, `env_file=".env"`. Vars: `DATABASE_URL` (required), `FCRN_CAPACITY_W`, `BATTERY_MAX_POWER_W`, `BATTERY_ENERGY_WH`, `BATTERY_INITIAL_SOC`. It rejects SoC outside [0, 1] and `Pmax < C`.
- `__main__.py`: `main()`. It parses `--fast` (the only flag), loads `Settings`, creates a `uuid4()` run id, opens the `AsyncConnection` with `async with`, and runs `STEP_TEST` on `simulated_battery` through `asyncio.Runner(loop_factory=...)`. After the run it reads the run's samples back, prints both Requirement 1 ratios and exits 1 on FAIL. Example line: `Requirement 1 up: +0.000 (allowed -0.05..+0.20)`.

Tests in `tests/test_settings.py`: valid env loads, SoC 1.5 fails, Pmax below C fails.

## Read

- [Package layout and module seams](../../fcrn-takehome/issues/07-package-layout.md): CLI and `run_id`.
- [Datastore, schema and operations story](../../fcrn-takehome/issues/05-datastore-and-operations.md): config.
- [Test plan](../../fcrn-takehome/issues/06-test-plan.md): CLI output.

## Acceptance check

With a local Postgres (`docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=dev postgres:17`, `cp .env.example .env`, `yoyo apply`):

- `uv run fcrn-dispatcher --fast` prints both ratios and exits 0.
- `python -m fcrn_dispatcher --fast` does the same.
- The `samples` table holds 12,600 rows for that run id.
- The standard check passes.
