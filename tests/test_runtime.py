import asyncio
from collections.abc import Awaitable, Callable
from datetime import timedelta

import pytest

from fcrn_dispatcher.battery import Battery, simulated_battery
from fcrn_dispatcher.runtime import fast_loop, run, wall_clock
from fcrn_dispatcher.sample import Sample
from fcrn_dispatcher.step_test import STEP_TEST

C = 1_000_000.0


def test_wall_clock_moves_with_loop_time() -> None:
    """Samples get wall time from loop time, so 105 s of loop time adds 105 s."""

    async def scenario() -> None:
        stamp = wall_clock()
        wall0 = stamp()
        await asyncio.sleep(105)
        assert stamp() - wall0 == timedelta(seconds=105)

    with asyncio.Runner(loop_factory=fast_loop) as runner:
        runner.run(scenario())


@pytest.mark.parametrize("write_s", [0, 1])
def test_battery_failure_stops_the_run_and_keeps_every_sample(
    stored: list[Sample],
    write_batch: Callable[[list[Sample]], Awaitable[None]],
    write_s: float,
) -> None:
    """A lost battery must stop the run at 0 W, raise to the caller and lose no sample.
    A slow store (write_s=1) leaves a batch in flight and a backlog when the run stops."""
    commands: list[float] = []

    async def slow_write_batch(batch: list[Sample]) -> None:
        await asyncio.sleep(write_s)
        await write_batch(batch)

    async def scenario() -> None:
        loop = asyncio.get_running_loop()
        inner = simulated_battery(2_000_000.0, 1_340_000.0, 0.5)

        async def set_power(power_w: float) -> None:
            commands.append(power_w)
            await inner.set_power(power_w)

        async def get_power() -> float:
            if loop.time() >= 700:
                raise ConnectionError("battery unreachable")
            return await inner.get_power()

        await run(
            STEP_TEST, Battery(set_power, get_power, inner.get_soc), C, slow_write_batch
        )

    with (
        pytest.RaisesGroup(ConnectionError),
        asyncio.Runner(loop_factory=fast_loop) as runner,
    ):
        runner.run(scenario())

    assert commands[-1] == 0.0
    assert len(stored) == 7_000
