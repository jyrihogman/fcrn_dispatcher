# Settings and CLI

Status: resolved
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

## Comments

- From Store: open the `AsyncConnection` with `autocommit=True`. `write_batch` wraps each `COPY` in `conn.transaction()`. Without autocommit, any earlier query opens a transaction, the `COPY` runs in a savepoint, and nothing commits until the connection closes.
- From Store: yoyo needs the `postgresql+psycopg://` scheme, and psycopg needs `postgresql://`. Example: `yoyo apply --database postgresql+psycopg://postgres:dev@localhost:5432/postgres migrations`. `.env.example` keeps the psycopg form for `DATABASE_URL`.

## Answer

- `src/fcrn_dispatcher/settings.py`: `Settings` with `env_file=".env"`. Every var is required, so `.env.example` holds the only copy of the sizing values. The sizing values must be positive. SoC must lie in [0, 1]. A model validator rejects `BATTERY_MAX_POWER_W < FCRN_CAPACITY_W`.
- `src/fcrn_dispatcher/__main__.py`: `main()` parses `--fast`, loads `Settings`, prints the run id, runs `STEP_TEST` into Postgres and reads the run's samples back with `store.read_samples`. The Postgres test uses the same function. It prints both ratios, appends ` FAIL` to a line out of bounds and exits 1.
- `tests/test_settings.py`: the three tests. They set env vars with `monkeypatch` and pass `_env_file=None`, so they never read `.env`.
- Acceptance: `uv run fcrn-dispatcher --fast` and `python -m fcrn_dispatcher --fast` both print `+0.000` for up and down and exit 0 in about 4.5 s. Each run stored 12,600 rows. `BATTERY_ENERGY_WH=10000` drains the battery and gives `up: -1.000 ... FAIL`, `down: +1.000 ... FAIL`, exit 1.
- Postgres.app on macOS also listens on `localhost:5432` and accepts the `.env.example` URL. The `docker run -p 5432:5432` container then never receives the connection. Docs should mention it or use another port.
