# Pure core

Status: resolved
Blocked by: 01
TDD: yes

## Task

Build the droop law, the `Sample` value and the battery, with no asyncio in the pure parts.

- `droop.py`: `F_REF_HZ = 50.0`, `DF_MAX_HZ = 0.1`, `droop(f_hz, capacity_w) -> float`. It saturates at ±C. Example: `droop(49.85, 1e6) == 1e6`.
- `sample.py`: `Sample(at, frequency_hz, commanded_w, actual_w, soc)`, a frozen dataclass.
- `battery.py`: the `Battery` seam (frozen dataclass of `set_power`, `get_power`, `get_soc`), `BatteryState`, the pure `advance` and `command`, and the closure `simulated_battery(capacity_wh, pmax_w, soc0) -> Battery`. It reads time only through `loop.time()`.

Tests in `tests/test_droop.py` and `tests/test_battery.py`:

- Hypothesis properties: SoC stays in [0, 1] for any start SoC, commands and time gaps. Droop is monotonic. Droop stays within ±C. Actual power stays within ±Pmax.
- Examples: 1 MW for 30 min moves SoC from 0.5 to 0.25. SoC 0.01 then 10 min at 1 MW gives SoC 0 and actual 0. 49.85 Hz commands +1 MW.
- One test drives `simulated_battery` on a looptime loop and checks that SoC moves with loop time.

The throwaway prototype `.scratch/fcrn-takehome/prototypes/runtime.py` shows a working shape. Do not copy its module-level constants: sizing values arrive as arguments.

## Read

- [Battery interface and simulated battery behaviour](../../fcrn-takehome/issues/03-battery-interface-and-behaviour.md)
- [Battery sizing](../../fcrn-takehome/issues/02-battery-sizing.md)
- [Test plan](../../fcrn-takehome/issues/06-test-plan.md): property and example tests.

## Acceptance check

- `uv run pytest tests/test_droop.py tests/test_battery.py` passes.
- `droop.py`, `sample.py` and `battery.py` import nothing from the package, and `test_imports.py` passes.
- The standard check passes.

## Answer

- `droop.py`, `sample.py` and `battery.py` follow the prototype shape. The sizing values arrive as arguments: `advance(state, now, capacity_wh)` and `command(state, power_w, now, capacity_wh, pmax_w)`.
- `advance` and `command` share one rule: power drops to 0 W when it pushes SoC past 0 or 1. Example: SoC 0.5, then 1 MW for exactly 3600 s, gives SoC 0 and actual 0 W. A clamp check alone missed this case, because SoC landed exactly on 0.
- The ±Pmax property checks a single large command, and it also checks every step of a random command sequence.
- The looptime test passes `asyncio.new_event_loop()` to `looptime.patch_event_loop` with a `ty: ignore`, because `ty` wants a `BaseEventLoop`.
- `capacity_wh` keeps the name from this ticket. The glossary says to avoid "Capacity" for usable energy capacity, so a later task may rename it to `usable_energy_wh`.
