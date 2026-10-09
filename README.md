# FCR-N dispatcher

A simulated battery (BESS) provides FCR-N to the Nordic grid. A controller follows the droop law on grid frequency, and every sample goes to Postgres.

The droop law, with positive power meaning discharge to the grid:

```
P = C_FCR-N / Δf_max · (f_ref − f)    f_ref = 50.0 Hz, Δf_max = 0.1 Hz
```

The controller clamps P to ±C_FCR-N. Example: with C_FCR-N = 1 MW, 49.95 Hz gives +0.5 MW, and 50.1 Hz gives −1 MW.

[CONTEXT.md](CONTEXT.md) defines the vocabulary.

## Quick start

You need [uv](https://docs.astral.sh/uv/) and Docker.

```sh
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=dev postgres:17
cp .env.example .env
sleep 3  # give Postgres time to accept connections
uv run yoyo apply --batch --database postgresql+psycopg://postgres:dev@localhost:5432/postgres migrations
uv run fcrn-dispatcher --fast
```

The last command runs the 1260 s step test in a few seconds and stores 12,600 samples. Real output:

```
Run e26de02f-b59a-4283-a3bd-ea9dd750b0e3
Requirement 1 up: +0.000 (allowed -0.05..+0.20)
Requirement 1 down: +0.000 (allowed -0.20..+0.05)
```

Without `--fast`, the same test runs on wall-clock time and takes 21 minutes. The CLI exits with status 1 when a ratio is out of bounds.

If another Postgres already listens on port 5432, publish the container on another port. Then change the port in `.env` and in the `yoyo apply` command.

## Assignment map

| # | What to build | Module | Test |
|---|---|---|---|
| 1 | Battery interface and simulated battery | `battery.py` | `tests/test_battery.py::test_soc_stays_within_zero_and_one_whatever_the_commands` |
| 2 | FCR-N controller on the droop law | `droop.py` | `tests/test_droop.py::test_droop_is_proportional_inside_the_normal_band_with_discharge_positive` |
| 3 | FCR-N step response test (Table 3) | `step_test.py`, `__main__.py` | `tests/test_step_test.py::test_full_step_test_on_the_simulated_battery_passes_requirement_1` |
| 4 | Concurrent simulation runtime with a testable clock | `runtime.py` | `tests/test_runtime.py::test_battery_failure_stops_the_run_and_keeps_every_sample` |
| 5 | Every sample in a datastore, plus [Deploy and operate](#deploy-and-operate) | `store.py`, `migrations/0001.create-samples.sql` | `tests/test_postgres.py::test_write_batch_stores_samples_that_read_back_by_run_id` |
| 6 | pytest with property-based tests | `tests/` | `tests/test_droop.py::test_lower_frequency_never_asks_for_less_discharge` |

All modules are in `src/fcrn_dispatcher/`.

## Battery sizing

`.env.example` sets C_FCR-N, Pmax, E and the starting SoC as environment variables.

| Parameter | Value | Reason |
|---|---|---|
| C_FCR-N | 1 MW | Round numbers keep the math simple. Full activation is ±1 MW. The design does not depend on scale. |
| Pmax | 1.34 MW | Table 10 requires ±1.34 · C for a limited energy reservoir (LER). The extra 0.34 · C is headroom for normal state energy management (NEM), which this project leaves out. Droop alone never asks for more than C. |
| E | 2 MWh usable | Table 10 requires 1 h · C in each direction. Starting at SoC 0.5 gives exactly 1 h each way. A real unit has a larger nameplate, for example 2.5 MWh used between 10% and 90%. |
| SoC limits | 0 and 1 of usable E | §3.5 defines SoC over the energy available for FCR-N. So SoC ∈ [0, 1] is the invariant. |
| Starting SoC | 0.5 | §3.5 suggests SoC near 50% for symmetric reserves. The property tests use other values too. |
| Losses | None | The battery is ideal: energy changes by power × time. Losses make SoC drift, and NEM fixes drift. NEM is out of scope. |

`Settings` rejects a starting SoC outside [0, 1] and a Pmax below C_FCR-N.

## Design

The runtime runs three tasks in one `asyncio.TaskGroup`:

- The **producer** publishes the frequency schedule into a latest-value cell.
- The **control** task ticks at 10 Hz. It reads the cell, commands `droop(f)` to the battery and builds a sample.
- The **writer** drains a queue of samples and writes each batch with one Postgres `COPY`.

The controller talks only to the `Battery` seam: three async callables, `set_power`, `get_power` and `get_soc`. A network-connected BESS can replace the simulated battery without a change to the controller.

The event loop is the clock. Code reads time only through `loop.time()`, apart from one wall-clock anchor at start. The loop factory is the seam: the default loop runs on wall-clock time, and looptime runs on accelerated time. The tests and `--fast` use the same seam.

The run is fail-stop. A failure in any task cancels the others. The control task sets the battery to 0 W, and the writer still stores every sample it already has.

See [docs/architecture.md](docs/architecture.md) for the diagram and [ADR 0002](docs/adr/0002-event-loop-is-the-clock.md) for the clock.

## Step test and Requirement 1

The step test follows Table 3: 50.0 Hz for 30 s, 49.95 Hz for 30 s, then 50.0, 49.9, 50.1 and 50.0 Hz for 300 s each.

The steady-state power Pss is the mean actual power over the last 60 s of each 300 s step. The windows are 300 to 360 s, 600 to 660 s, 900 to 960 s and 1200 to 1260 s from the start. The two 50.0 Hz values give the baseline:

```
baseline = (Pss0 + Pss3) / 2
ΔP1 = Pss1 − baseline    (49.9 Hz)
ΔP2 = Pss2 − baseline    (50.1 Hz)
up   = (ΔP1 − C) / C     allowed −0.05 .. +0.20
down = (ΔP2 + C) / C     allowed −0.20 .. +0.05
```

ΔP1 and ΔP2 are the two steady-state responses (ΔPss) from CONTEXT.md. The ideal battery delivers exactly ±C, so both ratios are 0.000.

The full step test in pytest also checks all 12,600 samples:

- |commanded power| ≤ C_FCR-N
- |actual power| ≤ Pmax
- 0 ≤ SoC ≤ 1
- actual power equals commanded power
- commanded power equals `droop(f)`

The step test moves SoC very little. In the run above, SoC stayed between 0.456 and 0.500 and ended at 0.498.

## Testing

```sh
uv run pytest
```

The tests in `tests/test_postgres.py` have the `integration` marker. They start Postgres 17 with testcontainers and apply the migrations with yoyo. Without Docker they skip. To run without them, use `uv run pytest -m "not integration"`.

The runtime and step tests run on looptime, so the 1260 s step test takes about 2 s.

Four hypothesis property tests cover the pure core:

| Property | Test |
|---|---|
| SoC stays in [0, 1] for any command sequence | `tests/test_battery.py::test_soc_stays_within_zero_and_one_whatever_the_commands` |
| Actual power never exceeds Pmax | `tests/test_battery.py::test_actual_power_never_exceeds_pmax` |
| A lower frequency never asks for less discharge | `tests/test_droop.py::test_lower_frequency_never_asks_for_less_discharge` |
| Droop stays within ±C for any frequency | `tests/test_droop.py::test_droop_stays_within_plus_minus_capacity_for_any_frequency` |

`tests/test_imports.py` checks the import rules between modules. For example, only `settings.py` may import pydantic.

The standard check:

```sh
uv run ruff format --check
uv run ruff check
uv run ty check
uv run pytest
```

## Deploy and operate

1. **Database.** Amazon RDS for PostgreSQL 17, Multi-AZ, in a private subnet. It runs in the same region and VPC as the dispatcher. [ADR 0001](docs/adr/0001-postgres-on-rds-for-samples.md) explains why not Timescale or InfluxDB.
2. **Migrations.** `yoyo apply` runs as a deploy step. The app never migrates on start.
3. **Partitions and retention.** The migration creates a plain table today. In production, `pg_partman` would create monthly range partitions on `at`, and `pg_cron` would drop partitions older than 13 months. Fingrid's data-retention terms set the real figure.
4. **Backups.** RDS automated backups with point-in-time recovery. An export job can also copy old partitions to S3 as Parquet.
5. **Alarms.** CloudWatch alarms on free storage, CPU and replica lag. App alarms on a sample gap over 10 s and on a growing writer queue.
6. **Scale-up.** At fleet scale, move to Timescale (Tiger Cloud or self-hosted). The `samples` table becomes a hypertable with compression.

One battery writes 10 rows per second, about 864,000 rows per day. The table has a BRIN index on `at` and a B-tree index on `(run_id, at)`.

## Assumptions and out of scope

Assumptions:

- The battery has no losses.
- The battery delivers the commanded power at once. There is no ramp or delay.
- The frequency changes in steps, with no ramp between them.
- `run_id` serves step tests only. In production the dispatcher runs for weeks, and queries read samples by time. A fleet would key on `(battery_id, at)`.

Out of scope:

- Normal and alert state energy management (NEM and AEM, §3.5.1 and §3.5.2).
- FCR-D, and the dynamic performance and stability tests.
- A real network-connected BESS adapter. The `Battery` seam allows one.
- A plot of the step response.

## How this was planned

The planning map is [.scratch/fcrn-takehome/map.md](.scratch/fcrn-takehome/map.md). Each ticket under it holds one decision.
