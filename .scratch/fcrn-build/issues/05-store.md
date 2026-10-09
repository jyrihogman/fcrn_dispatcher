# Store

Status: resolved
Blocked by: 02
TDD: yes

## Task

Build the Postgres schema and the sample writer.

- `migrations/0001.create-samples.sql` and `0001.create-samples.rollback.sql`: table `samples(run_id uuid, at timestamptz, frequency_hz, commanded_w, actual_w, soc)`, the four values `double precision`, all `NOT NULL`, no primary key. A BRIN index on `at` and a B-tree on `(run_id, at)`.
- `store.py`: `postgres_store(conn, run_id) -> write_batch`, a closure. `write_batch(list[Sample])` is async and uses psycopg 3 `cursor.copy()`.

`store` imports only `sample` from the package.

Test in `tests/test_postgres.py`, marked `integration`: start Postgres 17 with testcontainers, apply the migrations through yoyo's Python API, write a batch of samples, and read them back by `run_id`. The test skips when Docker is not available. It does not run the runtime; Settings and CLI covers the end-to-end path.

## Read

- [Datastore, schema and operations story](../../fcrn-takehome/issues/05-datastore-and-operations.md)
- [ADR 0001](../../../docs/adr/0001-postgres-on-rds-for-samples.md)
- [Package layout and module seams](../../fcrn-takehome/issues/07-package-layout.md): store shape and `run_id`.

## Acceptance check

- `uv run pytest -m integration` passes with Docker running, and skips with Docker stopped.
- `yoyo apply` and `yoyo rollback` both work against a local `postgres:17`.
- The standard check passes.

## Answer

- `migrations/0001.create-samples.sql` creates `samples` with all six columns `NOT NULL`, a BRIN index on `at` and a B-tree on `(run_id, at)`. The rollback file drops the table.
- `store.py` has `postgres_store(conn, run_id)`. It returns an async `write_batch` that sends one `COPY` per batch inside `conn.transaction()`. The caller opens the connection with `autocommit=True`. Without autocommit, psycopg turns `conn.transaction()` into a savepoint after any earlier query, and the batch stays uncommitted.
- `tests/test_postgres.py` starts `postgres:17` with testcontainers and applies the migrations through yoyo's Python API. It writes two runs with the same timestamps and reads one back by `run_id`. It skips when the `PostgresContainer` constructor cannot reach the Docker daemon. A failed image pull still fails the test.
- I ran `yoyo apply`, `yoyo rollback` and a second `yoyo apply` against `postgres:17` with `postgresql+psycopg://`. All three worked. I pointed `DOCKER_HOST` at a missing socket, and the test skipped.
