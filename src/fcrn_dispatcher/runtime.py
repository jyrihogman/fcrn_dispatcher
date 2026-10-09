import asyncio
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime, timedelta

import looptime

from fcrn_dispatcher.battery import Battery
from fcrn_dispatcher.droop import droop
from fcrn_dispatcher.sample import Sample

TICK_S = 0.1

type WriteBatch = Callable[[list[Sample]], Awaitable[None]]


def fast_loop() -> asyncio.AbstractEventLoop:
    return looptime.patch_event_loop(
        asyncio.new_event_loop(),  # ty: ignore[invalid-argument-type]
        noop_cycles=1,
    )


def wall_clock() -> Callable[[], datetime]:
    """Wall time is one wall anchor at start plus the loop time elapsed since then."""
    loop = asyncio.get_running_loop()
    wall0, loop0 = datetime.now(UTC), loop.time()
    return lambda: wall0 + timedelta(seconds=loop.time() - loop0)


def latest(initial: float) -> tuple[Callable[[], float], Callable[[float], None]]:
    value = initial

    def read() -> float:
        return value

    def publish(new: float) -> None:
        nonlocal value
        value = new

    return read, publish


async def produce(
    schedule: Sequence[tuple[float, float]], publish: Callable[[float], None]
) -> None:
    for frequency_hz, duration_s in schedule:
        publish(frequency_hz)
        await asyncio.sleep(duration_s)


async def control(
    read_f: Callable[[], float],
    battery: Battery,
    capacity_w: float,
    ticks: int,
    emit: Callable[[Sample], None],
    stamp: Callable[[], datetime],
) -> None:
    """Sample on a fixed grid of exactly `ticks` ticks, so float drift and timer order
    cannot add or drop a sample at the end of the schedule."""
    loop = asyncio.get_running_loop()
    start = loop.time()
    try:
        for n in range(ticks):
            await asyncio.sleep(start + n * TICK_S - loop.time())
            frequency_hz = read_f()
            commanded_w = droop(frequency_hz, capacity_w)
            await battery.set_power(commanded_w)
            emit(
                Sample(
                    stamp(),
                    frequency_hz,
                    commanded_w,
                    await battery.get_power(),
                    await battery.get_soc(),
                )
            )
    finally:
        await battery.set_power(0.0)


async def write(queue: asyncio.Queue[Sample | None], write_batch: WriteBatch) -> None:
    def drain() -> list[Sample | None]:
        items = []
        while not queue.empty():
            items.append(queue.get_nowait())
        return items

    # A cancel can stop write_batch partway, so `finally` writes the pending samples
    # again together with the backlog.
    pending: list[Sample] = []
    try:
        while True:
            batch = [await queue.get(), *drain()]
            pending = [s for s in batch if s is not None]
            await write_batch(pending)
            pending = []
            if None in batch:
                return
    finally:
        if rest := [*pending, *(s for s in drain() if s is not None)]:
            await write_batch(rest)


async def run(
    schedule: Sequence[tuple[float, float]],
    battery: Battery,
    capacity_w: float,
    write_batch: WriteBatch,
) -> None:
    """Run the schedule until the producer finishes. Any failure stops every task."""
    read_f, publish = latest(schedule[0][0])
    queue: asyncio.Queue[Sample | None] = asyncio.Queue()
    ticks = round(sum(duration_s for _, duration_s in schedule) / TICK_S)
    async with asyncio.TaskGroup() as tg:
        tg.create_task(write(queue, write_batch))
        tg.create_task(produce(schedule, publish))
        await tg.create_task(
            control(read_f, battery, capacity_w, ticks, queue.put_nowait, wall_clock())
        )
        queue.put_nowait(None)
