import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from docker.errors import DockerException
from testcontainers.community.postgres import PostgresContainer
from yoyo import get_backend, read_migrations

from fcrn_dispatcher.sample import Sample
from fcrn_dispatcher.store import postgres_store

pytestmark = pytest.mark.integration

MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"
START = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    # The constructor connects to the Docker daemon.
    # A failed image pull later must fail the test, not skip it.
    try:
        container = PostgresContainer("postgres:17", driver=None)
    except DockerException:
        pytest.skip("Docker is not available")
    with container:
        url = container.get_connection_url()
        backend = get_backend(url.replace("postgresql://", "postgresql+psycopg://"))
        with backend.lock():
            backend.apply_migrations(
                backend.to_apply(read_migrations(str(MIGRATIONS_DIR)))
            )
        yield url


def test_write_batch_stores_samples_that_read_back_by_run_id(database_url: str) -> None:
    """Two runs share wall timestamps, so only run_id tells their samples apart."""
    samples = [
        Sample(
            at=START + timedelta(seconds=tick / 10),
            frequency_hz=49.9 + tick / 100,
            commanded_w=1_000_000.0 - tick * 0.5,
            actual_w=999_999.25 - tick,
            soc=0.5 - tick / 1000,
        )
        for tick in range(5)
    ]
    run_id = uuid4()

    async def write_two_runs_and_read_one() -> list[Sample]:
        async with await psycopg.AsyncConnection.connect(
            database_url, autocommit=True
        ) as conn:
            await postgres_store(conn, run_id)(samples)
            await postgres_store(conn, uuid4())(samples[:2])
            cursor = await conn.execute(
                "SELECT at, frequency_hz, commanded_w, actual_w, soc"
                " FROM samples WHERE run_id = %s ORDER BY at",
                (run_id,),
            )
            return [Sample(*row) for row in await cursor.fetchall()]

    assert asyncio.run(write_two_runs_and_read_one()) == samples
