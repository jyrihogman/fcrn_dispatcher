from bisect import bisect_right
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from itertools import accumulate

import pytest

from fcrn_dispatcher.sample import Sample
from fcrn_dispatcher.step_test import (
    DOWN_BOUNDS,
    STEP_TEST,
    UP_BOUNDS,
    requirement_1,
    steady_state_response,
)

C = 1_000_000.0
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
