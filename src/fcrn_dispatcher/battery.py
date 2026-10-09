import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class BatteryState:
    soc: float
    power_w: float
    updated_at: float


def _pushes_past_limit(soc: float, power_w: float) -> bool:
    return (power_w > 0 and soc <= 0.0) or (power_w < 0 and soc >= 1.0)


def advance(state: BatteryState, now: float, capacity_wh: float) -> BatteryState:
    soc = state.soc - state.power_w * (now - state.updated_at) / 3600 / capacity_wh
    clamped = min(1.0, max(0.0, soc))
    power_w = 0.0 if _pushes_past_limit(clamped, state.power_w) else state.power_w
    return BatteryState(clamped, power_w, now)


def command(
    state: BatteryState, power_w: float, now: float, capacity_wh: float, pmax_w: float
) -> BatteryState:
    state = advance(state, now, capacity_wh)
    clamped_w = max(-pmax_w, min(pmax_w, power_w))
    return replace(
        state,
        power_w=0.0 if _pushes_past_limit(state.soc, clamped_w) else clamped_w,
    )


@dataclass(frozen=True)
class Battery:
    set_power: Callable[[float], Awaitable[None]]
    get_power: Callable[[], Awaitable[float]]
    get_soc: Callable[[], Awaitable[float]]


def simulated_battery(capacity_wh: float, pmax_w: float, soc0: float) -> Battery:
    loop = asyncio.get_running_loop()
    state = BatteryState(soc0, 0.0, loop.time())

    async def set_power(power_w: float) -> None:
        nonlocal state
        state = command(state, power_w, loop.time(), capacity_wh, pmax_w)

    async def get_power() -> float:
        nonlocal state
        state = advance(state, loop.time(), capacity_wh)
        return state.power_w

    async def get_soc() -> float:
        nonlocal state
        state = advance(state, loop.time(), capacity_wh)
        return state.soc

    return Battery(set_power, get_power, get_soc)
