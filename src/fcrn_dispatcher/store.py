from collections.abc import Awaitable, Callable
from uuid import UUID

from psycopg import AsyncConnection

from fcrn_dispatcher.sample import Sample

COPY_SAMPLES = (
    "COPY samples (run_id, at, frequency_hz, commanded_w, actual_w, soc) FROM STDIN"
)


def postgres_store(
    conn: AsyncConnection, run_id: UUID
) -> Callable[[list[Sample]], Awaitable[None]]:
    async def write_batch(samples: list[Sample]) -> None:
        async with (
            conn.transaction(),
            conn.cursor() as cursor,
            cursor.copy(COPY_SAMPLES) as copy,
        ):
            for s in samples:
                await copy.write_row(
                    (run_id, s.at, s.frequency_hz, s.commanded_w, s.actual_w, s.soc)
                )

    return write_batch
