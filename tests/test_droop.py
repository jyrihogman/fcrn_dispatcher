import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from fcrn_dispatcher.droop import droop


def test_droop_saturates_at_capacity_so_full_activation_is_never_exceeded() -> None:
    """FCR-N never asks for more than the FCR-N capacity C."""
    assert droop(49.85, 1e6) == 1e6


def test_droop_is_proportional_inside_the_normal_band_with_discharge_positive() -> None:
    """At nominal frequency nothing is delivered; high frequency means charging."""
    assert droop(50.0, 1e6) == 0.0
    assert droop(50.05, 1e6) == pytest.approx(-0.5e6)


@given(
    f1=st.floats(min_value=45.0, max_value=55.0),
    f2=st.floats(min_value=45.0, max_value=55.0),
    capacity=st.floats(min_value=1.0, max_value=1e9),
)
def test_lower_frequency_never_asks_for_less_discharge(
    f1: float, f2: float, capacity: float
) -> None:
    """A battery that discharges more when frequency falls is what FCR-N requires."""
    low, high = sorted([f1, f2])
    assume(low < high)
    assert droop(low, capacity) >= droop(high, capacity)


@given(
    f=st.floats(min_value=0.0, max_value=100.0),
    capacity=st.floats(min_value=1.0, max_value=1e9),
)
def test_droop_stays_within_plus_minus_capacity_for_any_frequency(
    f: float, capacity: float
) -> None:
    """The battery must never be commanded beyond the FCR-N capacity."""
    assert -capacity <= droop(f, capacity) <= capacity
