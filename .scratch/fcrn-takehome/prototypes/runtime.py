# PROTOTYPE, throwaway. Answers "Runtime and clock design" (issues/04).
# The real code is in `src/`.
#
# Run on accelerated time:  uv run --with looptime==0.7 .scratch/fcrn-takehome/prototypes/runtime.py --fast
# Make the battery fail:    ... --fast --fail-at 700
# Run on real time (21 min): uv run .scratch/fcrn-takehome/prototypes/runtime.py
#
# Shape under test:
#   producer task --(latest-value cell)--> control task --(queue)--> writer task --> store
#   The battery has no task. It integrates lazily on each call (issues/03).
#   The clock is the event loop. The seam is the loop factory, not a Clock class.
import asyncio
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

C_W = 1_000_000.0
PMAX_W = 1_340_000.0
E_WH = 2_000_000.0
TICK_S = 0.1

STEP_TEST = [(50.0, 30), (49.95, 30), (50.0, 300), (49.9, 300), (50.1, 300), (50.0, 300)]


# --- pure core -------------------------------------------------------------

def droop(f_hz: float, capacity_w: float) -> float:
    return max(-capacity_w, min(capacity_w, capacity_w / 0.1 * (50.0 - f_hz)))


@dataclass(frozen=True)
class Sample:
    at: datetime
    frequency_hz: float
    commanded_w: float
    actual_w: float
    soc: float


@dataclass(frozen=True)
class BatteryState:
    soc: float
    power_w: float
    updated_at: float


def advance(s: BatteryState, now: float) -> BatteryState:
    soc = s.soc - s.power_w * (now - s.updated_at) / 3600 / E_WH
    clamped = min(1.0, max(0.0, soc))
    return BatteryState(clamped, 0.0 if clamped != soc else s.power_w, now)


def command(s: BatteryState, power_w: float, now: float) -> BatteryState:
    s = advance(s, now)
    p = max(-PMAX_W, min(PMAX_W, power_w))
    blocked = (p > 0 and s.soc <= 0.0) or (p < 0 and s.soc >= 1.0)
    return replace(s, power_w=0.0 if blocked else p)


# --- seams -----------------------------------------------------------------

@dataclass(frozen=True)
class Battery:
    set_power: Callable[[float], Awaitable[None]]
    get_power: Callable[[], Awaitable[float]]
    get_soc: Callable[[], Awaitable[float]]


def simulated_battery(soc0: float, fail_at: float | None = None) -> Battery:
    loop = asyncio.get_running_loop()
    state = BatteryState(soc0, 0.0, loop.time())

    async def set_power(w: float) -> None:
        nonlocal state
        if fail_at is not None and loop.time() >= fail_at:
            raise ConnectionError(f"BESS unreachable at t={loop.time():.1f}s")
        state = command(state, w, loop.time())

    async def get_power() -> float:
        nonlocal state
        state = advance(state, loop.time())
        return state.power_w

    async def get_soc() -> float:
        nonlocal state
        state = advance(state, loop.time())
        return state.soc

    return Battery(set_power, get_power, get_soc)


def wall_clock() -> Callable[[], datetime]:
    """Wall time = one wall anchor at start + loop time elapsed since then."""
    loop = asyncio.get_running_loop()
    wall0, loop0 = datetime.now(UTC), loop.time()
    return lambda: wall0 + timedelta(seconds=loop.time() - loop0)


def latest(initial: float) -> tuple[Callable[[], float], Callable[[float], None]]:
    box = [initial]
    return (lambda: box[0]), (lambda v: box.__setitem__(0, v))


# --- tasks -----------------------------------------------------------------

async def produce(schedule: list[tuple[float, float]], publish: Callable[[float], None]) -> None:
    for f_hz, duration_s in schedule:
        publish(f_hz)
        await asyncio.sleep(duration_s)


async def control(read_f, battery: Battery, emit: Callable[[Sample], None], stamp) -> None:
    loop = asyncio.get_running_loop()
    next_tick = loop.time()
    try:
        while True:
            f = read_f()
            cmd = droop(f, C_W)
            await battery.set_power(cmd)
            emit(Sample(stamp(), f, cmd, await battery.get_power(), await battery.get_soc()))
            next_tick += TICK_S  # fixed grid, no drift from the work above
            await asyncio.sleep(next_tick - loop.time())
    finally:
        print(f"  control: stopping at t={loop.time():.1f}s, commanding 0 W")
        await battery.set_power(0.0)


async def write(queue: asyncio.Queue, write_batch: Callable[[list[Sample]], None]) -> None:
    def drain() -> list:
        items = []
        while not queue.empty():
            items.append(queue.get_nowait())
        return items

    try:
        while True:
            batch = [await queue.get(), *drain()]
            write_batch([s for s in batch if s is not None])
            if None in batch:
                return
    finally:
        write_batch([s for s in drain() if s is not None])  # flush on cancel too


async def run(schedule, battery: Battery, write_batch) -> None:
    read_f, publish = latest(schedule[0][0])
    queue: asyncio.Queue[Sample | None] = asyncio.Queue()
    stamp = wall_clock()
    async with asyncio.TaskGroup() as tg:
        tg.create_task(write(queue, write_batch))
        controller = tg.create_task(control(read_f, battery, queue.put_nowait, stamp))
        await tg.create_task(produce(schedule, publish))
        controller.cancel()
        await asyncio.wait([controller])
        queue.put_nowait(None)


# --- throwaway driver ------------------------------------------------------

def main() -> None:
    fast = "--fast" in sys.argv
    fail_at = float(sys.argv[sys.argv.index("--fail-at") + 1]) if "--fail-at" in sys.argv else None
    stored: list[Sample] = []

    def write_batch(batch: list[Sample]) -> None:
        stored.extend(batch)

    async def entry() -> None:
        await run(STEP_TEST, simulated_battery(0.5, fail_at), write_batch)

    loop_factory = None
    if fast:
        import looptime
        loop_factory = lambda: looptime.patch_event_loop(asyncio.new_event_loop(), noop_cycles=1)

    try:
        with asyncio.Runner(loop_factory=loop_factory) as runner:
            runner.run(entry())
    except* ConnectionError as eg:
        print(f"  runtime stopped: {eg.exceptions[0]!r}")

    print(f"stored {len(stored)} samples")
    for s in stored[:: len(stored) // 12 or 1]:
        print(f"  {s.at:%H:%M:%S.%f}  f={s.frequency_hz:6.2f}  cmd={s.commanded_w/1e3:7.0f} kW"
              f"  act={s.actual_w/1e3:7.0f} kW  soc={s.soc:.4f}")
    print(f"  last: {stored[-1]}")


if __name__ == "__main__":
    main()
