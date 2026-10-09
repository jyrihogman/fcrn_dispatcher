import asyncio
from bisect import bisect_right
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from itertools import accumulate

import pytest

from fcrn_dispatcher.battery import simulated_battery
from fcrn_dispatcher.droop import droop
from fcrn_dispatcher.runtime import fast_loop, run
from fcrn_dispatcher.sample import Sample
from fcrn_dispatcher.step_test import (
    DOWN_BOUNDS,
    STEP_TEST,
    UP_BOUNDS,
    requirement_1,
    steady_state_response,
)

C = 1_000_000.0
PMAX_W = 1_340_000.0
CAPACITY_WH = 2_000_000.0
START = datetime(2026, 1, 1, tzinfo=UTC)
STEP_ENDS = list(accumulate(duration for _, duration in STEP_TEST))
STEP_STARTS = [0, *STEP_ENDS[:-1]]


def ideal_power_w(frequency_hz: float) -> float:
    return C * (50.0 - frequency_hz) / 0.1


def frequency_at(elapsed_s: float) -> float:
    # bisect_right puts a time on a step end into the next step.
    return STEP_TEST[bisect_right(STEP_ENDS, elapsed_s)][0]


def sample_at(elapsed_s: float, power_w: Callable[[float, float], float]) -> Sample:
    frequency_hz = frequency_at(elapsed_s)
    power = power_w(frequency_hz, elapsed_s)
    return Sample(
        at=START + timedelta(seconds=elapsed_s),
        frequency_hz=frequency_hz,
        commanded_w=power,
        actual_w=power,
        soc=0.5,
    )


def step_test_samples(power_w: Callable[[float, float], float]) -> list[Sample]:
    return [sample_at(i / 10, power_w) for i in range(12_600)]


def test_step_test_matches_fingrid_table_3() -> None:
    assert STEP_TEST == [
        (50.0, 30),
        (49.95, 30),
        (50.0, 300),
        (49.9, 300),
        (50.1, 300),
        (50.0, 300),
    ]


def test_ideal_response_gives_zero_deviation_for_requirement_1() -> None:
    samples = step_test_samples(lambda f, _: ideal_power_w(f))
    dp1, dp2 = steady_state_response(samples)
    up, down = requirement_1(dp1, dp2, C)
    assert dp1 == pytest.approx(C)
    assert dp2 == pytest.approx(-C)
    assert up == pytest.approx(0.0)
    assert down == pytest.approx(0.0)


def test_under_delivery_fails_requirement_1_on_both_sides() -> None:
    samples = step_test_samples(lambda f, _: 0.9 * ideal_power_w(f))
    dp1, dp2 = steady_state_response(samples)
    up, down = requirement_1(dp1, dp2, C)
    assert up == pytest.approx(-0.1)
    assert up < UP_BOUNDS[0]
    assert down == pytest.approx(0.1)
    assert down > DOWN_BOUNDS[1]


def test_constant_baseline_is_removed_by_the_50_hz_steady_states() -> None:
    samples = step_test_samples(lambda f, _: ideal_power_w(f) + 50_000)
    dp1, dp2 = steady_state_response(samples)
    assert dp1 == pytest.approx(C)
    assert dp2 == pytest.approx(-C)


def test_pss_is_the_mean_over_exactly_the_last_60_seconds_of_each_step() -> None:
    def settles_late(frequency_hz: float, elapsed_s: float) -> float:
        into_step_s = elapsed_s - max(s for s in STEP_STARTS if s <= elapsed_s)
        if 240 <= into_step_s < 270:
            return 2 * ideal_power_w(frequency_hz)
        return 0.0

    up, down = requirement_1(*steady_state_response(step_test_samples(settles_late)), C)
    assert up == pytest.approx(0.0)
    assert down == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("dp1_ratio", "dp2_ratio", "passes"),
    [
        (0.951, -1.0, True),
        (0.949, -1.0, False),
        (1.199, -1.0, True),
        (1.201, -1.0, False),
        (1.0, -0.951, True),
        (1.0, -0.949, False),
        (1.0, -1.199, True),
        (1.0, -1.201, False),
    ],
)
def test_requirement_1_passes_just_inside_and_fails_just_outside_each_bound(
    dp1_ratio: float, dp2_ratio: float, passes: bool
) -> None:
    up, down = requirement_1(dp1_ratio * C, dp2_ratio * C, C)
    in_bounds = (
        UP_BOUNDS[0] <= up <= UP_BOUNDS[1] and DOWN_BOUNDS[0] <= down <= DOWN_BOUNDS[1]
    )
    assert in_bounds is passes


def test_full_step_test_on_the_simulated_battery_passes_requirement_1(
    stored: list[Sample], write_batch: Callable[[list[Sample]], Awaitable[None]]
) -> None:
    """The 1260 s step test runs on looptime and must deliver droop(f) at every sample."""

    async def scenario() -> None:
        await run(
            STEP_TEST, simulated_battery(CAPACITY_WH, PMAX_W, 0.5), C, write_batch
        )

    with asyncio.Runner(loop_factory=fast_loop) as runner:
        runner.run(scenario())

    assert len(stored) == 12_600
    for s in stored:
        assert abs(s.commanded_w) <= C
        assert abs(s.actual_w) <= PMAX_W
        assert 0.0 <= s.soc <= 1.0
        assert s.actual_w == pytest.approx(s.commanded_w, abs=1)
        assert s.commanded_w == pytest.approx(droop(s.frequency_hz, C), abs=1)
    up, down = requirement_1(*steady_state_response(stored), C)
    assert UP_BOUNDS[0] <= up <= UP_BOUNDS[1]
    assert DOWN_BOUNDS[0] <= down <= DOWN_BOUNDS[1]
