import asyncio
from collections.abc import Coroutine
from typing import Any

import looptime
import pytest
from hypothesis import given
from hypothesis import strategies as st

from fcrn_dispatcher.battery import BatteryState, advance, command, simulated_battery

CAPACITY_WH = 2_000_000.0
PMAX_W = 1_340_000.0

unit_interval = st.floats(min_value=0.0, max_value=1.0)
steps = st.lists(
    st.tuples(
        st.floats(min_value=-5e6, max_value=5e6),
        st.floats(min_value=0.0, max_value=7200.0),
    ),
    max_size=20,
)


@given(soc0=unit_interval, schedule=steps)
def test_soc_stays_within_zero_and_one_whatever_the_commands(
    soc0: float, schedule: list[tuple[float, float]]
) -> None:
    """A SoC outside [0, 1] would mean the battery stored or gave more than it holds."""
    state = BatteryState(soc0, 0.0, 0.0)
    now = 0.0
    for power_w, gap_s in schedule:
        now += gap_s
        state = command(state, power_w, now, CAPACITY_WH, PMAX_W)
        assert 0.0 <= state.soc <= 1.0
        assert abs(state.power_w) <= PMAX_W
    state = advance(state, now + 3600, CAPACITY_WH)
    assert 0.0 <= state.soc <= 1.0
    assert abs(state.power_w) <= PMAX_W


@given(
    soc0=unit_interval,
    power_w=st.floats(min_value=-1e9, max_value=1e9),
)
def test_actual_power_never_exceeds_pmax(soc0: float, power_w: float) -> None:
    """The inverter rating caps real power, however large the request."""
    state = command(BatteryState(soc0, 0.0, 0.0), power_w, 0.0, CAPACITY_WH, PMAX_W)
    assert abs(state.power_w) <= PMAX_W


def test_energy_balance_moves_soc_by_power_times_time_over_capacity() -> None:
    """1 MW for half an hour from 2 MWh moves SoC by 0.25 (0.5 MWh out of 2 MWh)."""
    state = command(BatteryState(0.5, 0.0, 0.0), 1e6, 0.0, CAPACITY_WH, PMAX_W)
    state = advance(state, 1800.0, CAPACITY_WH)
    assert state.soc == pytest.approx(0.25)
    assert state.power_w == 1e6


def test_discharge_stops_at_empty_within_the_interval() -> None:
    """Power must drop to zero once SoC hits 0, or the model would give energy it lacks."""
    state = command(BatteryState(0.01, 0.0, 0.0), 1e6, 0.0, CAPACITY_WH, PMAX_W)
    state = advance(state, 600.0, CAPACITY_WH)
    assert state.soc == 0.0
    assert state.power_w == 0.0


def test_discharge_stops_when_soc_lands_exactly_on_empty() -> None:
    """Sizing gives exactly 1 h at 1 MW, so SoC hits 0 exactly and power must stop."""
    state = command(BatteryState(0.5, 0.0, 0.0), 1e6, 0.0, CAPACITY_WH, PMAX_W)
    state = advance(state, 3600.0, CAPACITY_WH)
    assert state.soc == 0.0
    assert state.power_w == 0.0


def test_discharge_is_blocked_when_empty_but_charging_is_allowed() -> None:
    """An empty battery cannot discharge, yet it must still accept charge."""
    empty = BatteryState(0.0, 0.0, 0.0)
    assert command(empty, 1e6, 0.0, CAPACITY_WH, PMAX_W).power_w == 0.0
    assert command(empty, -1e6, 0.0, CAPACITY_WH, PMAX_W).power_w == -1e6


def test_charge_is_blocked_when_full_but_discharging_is_allowed() -> None:
    """A full battery cannot charge, yet it must still be able to discharge."""
    full = BatteryState(1.0, 0.0, 0.0)
    assert command(full, -1e6, 0.0, CAPACITY_WH, PMAX_W).power_w == 0.0
    assert command(full, 1e6, 0.0, CAPACITY_WH, PMAX_W).power_w == 1e6


def run_on_looptime(coro: Coroutine[Any, Any, None]) -> None:
    with asyncio.Runner(
        loop_factory=lambda: looptime.patch_event_loop(
            asyncio.new_event_loop(),  # ty: ignore[invalid-argument-type]
            noop_cycles=1,
        )
    ) as runner:
        runner.run(coro)


def test_simulated_soc_follows_event_loop_time() -> None:
    """Simulated SoC must move with loop time, so a 30 min sleep drains 0.25 of SoC instantly."""

    async def scenario() -> None:
        battery = simulated_battery(CAPACITY_WH, PMAX_W, 0.5)
        await battery.set_power(1e6)
        await asyncio.sleep(1800)
        assert await battery.get_soc() == pytest.approx(0.25)
        assert await battery.get_power() == 1e6

    run_on_looptime(scenario())
