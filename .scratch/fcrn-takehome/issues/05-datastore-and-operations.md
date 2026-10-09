# Datastore, schema and operations story

Type: grilling
Status: resolved
Blocked by: 04

## Question

Which datastore stores every sample, and how would we deploy and operate it?

Decide:
- The store. SQLite from the stdlib is the zero-dependency option. DuckDB, Postgres/Timescale or InfluxDB are the alternatives.
- The table schema and the timestamp format.
- How writes avoid blocking the event loop: batching, a thread, or a writer task.
- The deploy and operate story for the README: where it runs, retention, backups, monitoring.

## Comments

- From Runtime and clock design: the writer task calls a sync `write_batch(list[Sample])` with everything on the queue. A sync write blocks the loop, so decide if it runs in a thread (`asyncio.to_thread`). Note that looptime runs thread work in zero fake time. The writer also flushes on cancel. `Sample.at` is a UTC `datetime`, built from a wall anchor plus loop time. The step test writes 12,601 samples.
- Store decided (grilling session): plain Postgres on RDS. Timescale is not on RDS, because its TSL licence blocks AWS from hosting it. InfluxDB 3 Core on Timestream has no compaction and limits queries to about 72 h, so it is weak for long history. FCR-N samples must last for months, and Postgres handles 10 rows/s per battery easily. The README names Timescale (Tiger Cloud or self-hosted) as the step for fleet scale.

## Answer

| Decision | Answer |
|---|---|
| Store | Plain PostgreSQL on Amazon RDS. See [ADR 0001](../../../docs/adr/0001-postgres-on-rds-for-samples.md) for why not Timescale or InfluxDB. Timescale (hypertable plus compression) is the scale-up path. |
| Schema | One table, `samples(run_id uuid, at timestamptz, frequency_hz, commanded_w, actual_w, soc)`. The four values are `double precision`, all columns are `NOT NULL`, and there is no primary key. Indexes: BRIN on `at`, B-tree on `(run_id, at)`. Watts are floats, for example 1.34 MW = `1340000.0`. Each process run gets a new `run_id`. |
| Migrations | yoyo-migrations with plain `.sql` files (`0001.create-samples.sql` plus a `.rollback.sql`). They run as a deploy step (`yoyo apply`), never when the app starts. Tests apply the same files through yoyo's Python API. |
| Writes | psycopg 3 async (`AsyncConnection`, `cursor.copy()`). `write_batch(list[Sample])` becomes `async`, so there is no thread. This replaces the sync `write_batch` from Runtime and clock design. The writer still drains the queue and flushes on cancel. |
| Optimisations in code | `COPY` per batch, narrow types, BRIN index. Partitioning, retention and rollups are README only. |
| Config | pydantic-settings reads env vars and `.env` (`env_file=".env"`). `.env` is gitignored, and `.env.example` is committed with the sizing values. Vars: `DATABASE_URL`, `FCRN_CAPACITY_W`, `BATTERY_MAX_POWER_W`, `BATTERY_ENERGY_WH`, `BATTERY_INITIAL_SOC`. It checks `0 ≤ SoC ≤ 1` and `Pmax ≥ C_FCR-N`. f_ref = 50.0 Hz and Δf_max = 0.1 Hz stay in code. The 10 Hz tick stays in code. The only CLI flag is `--fast`. |
| pydantic vs dataclasses | pydantic only at trust boundaries (`Settings`, and a future network BESS adapter). Frozen dataclasses for our own values (`Sample`, `BatteryState`, the `Battery` seam). |
| Tests | Unit tests and the step test use an in-memory fake store. One integration test starts Postgres with testcontainers, applies the migrations, runs a short simulation and reads the rows back. No docker-compose. |
| README operate section | (1) RDS for PostgreSQL 17, Multi-AZ, private subnet, same region and VPC as the dispatcher. (2) `yoyo apply` as a deploy step. (3) Monthly range partitions with `pg_partman`, dropped after 13 months by `pg_cron`. The README notes that Fingrid's data-retention terms set the real figure. (4) RDS automated backups with PITR, plus an optional Parquet export of old partitions to S3. (5) CloudWatch alarms on free storage, CPU and replica lag, plus app alarms for a sample gap over 10 s and a growing writer queue. (6) Timescale as the scale-up path. A local run uses `docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=dev postgres:17`. |
