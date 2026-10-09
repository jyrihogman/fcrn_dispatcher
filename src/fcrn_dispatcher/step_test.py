from collections.abc import Sequence
from itertools import accumulate
from statistics import fmean

from fcrn_dispatcher.sample import Sample

STEP_TEST: list[tuple[float, int]] = [
    (50.0, 30),
    (49.95, 30),
    (50.0, 300),
    (49.9, 300),
    (50.1, 300),
    (50.0, 300),
]
UP_BOUNDS = (-0.05, 0.2)
DOWN_BOUNDS = (-0.2, 0.05)
PSS_WINDOW_S = 60


def _steady_state_power(samples: Sequence[Sample], end_s: int) -> float:
    """Mean actual power over the last PSS_WINDOW_S seconds before end_s."""
    start_at = samples[0].at
    return fmean(
        s.actual_w
        for s in samples
        if end_s - PSS_WINDOW_S <= (s.at - start_at).total_seconds() < end_s
    )


def steady_state_response(samples: Sequence[Sample]) -> tuple[float, float]:
    """Return (dp1, dp2) from the steady-state powers of the step test."""
    pss0, pss1, pss2, pss3 = (
        _steady_state_power(samples, end_s)
        for end_s in list(accumulate(d for _, d in STEP_TEST))[2:]
    )
    baseline = (pss0 + pss3) / 2
    return pss1 - baseline, pss2 - baseline


def requirement_1(dp1: float, dp2: float, capacity_w: float) -> tuple[float, float]:
    """Return the (up, down) ratios of requirement 1 against the capacity."""
    return (dp1 - capacity_w) / capacity_w, (dp2 + capacity_w) / capacity_w
