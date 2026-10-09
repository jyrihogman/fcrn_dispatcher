# Battery interface and simulated battery behaviour

Type: grilling
Status: resolved
Blocked by:

## Question

What does the battery interface look like, so that a network-connected BESS can later replace the simulated battery without any controller change? And how does the simulated battery behave?

Decide:
- Sign convention. Example: positive power means discharge to the grid.
- Sync or async methods. A network BESS does I/O, which suggests `async`.
- The method set. Example: `set_power(w)`, `get_power()`, `get_soc()`.
- How actual power differs from commanded power. Clamp to ±Pmax? Clamp to zero when SoC reaches a limit? Add a ramp or delay?
- Who integrates energy over time, and on which clock.
- Whether the controller ever reads SoC, or only the battery and the logger read it.
- What the controller commands below 49.9 Hz or above 50.1 Hz. Does it saturate at ±C_FCR-N, or pass the raw droop value and let the battery clamp at Pmax = 1.34 MW? (Raised by Battery sizing.)

## Answer

| Decision | Answer |
|---|---|
| Sign convention | Positive power = discharge to the grid. |
| Seam | `Battery` is a frozen dataclass of three async callables: `set_power(w)`, `get_power()`, `get_soc()`. A network BESS is another factory that returns a `Battery`. |
| Simulated battery | A pure core and a thin shell. `BatteryState` is a frozen dataclass (`soc`, `power_w`, `updated_at`). Pure functions update it: `advance(state, now)` and `command(state, power_w, now)`. The factory `simulated_battery(capacity_wh, pmax_w, soc0) -> Battery` is a closure that holds the current state. |
| Units | Power in watts as `float`. SoC as a fraction in [0, 1]. |
| `get_power()` | Returns actual power. The logger takes commanded power from the controller. |
| Controller output | Saturates at ±C_FCR-N outside 49.9 to 50.1 Hz. Example: at 49.85 Hz it commands +1 MW, not +1.5 MW. The 0.34 · C headroom is for NEM, which is out of scope. |
| Actual power | The battery clamps it to ±Pmax. It delivers 0 W in a direction that would push SoC past 0 or 1. It has no ramp and no delay, because Requirement 1 checks only the steady state. |
| Energy integration | The battery integrates lazily on every call: actual power × elapsed `loop.time()`. It has no background task. If SoC reaches a limit partway through an interval, SoC clamps to that limit and actual power becomes 0. |
| SoC reader | The controller never reads SoC. Only the battery, the logger and the datastore read it. |
| Failures | Seam callables may raise. The runtime decides how to handle it. The simulated battery never raises. |

Glossary: `CONTEXT.md` now states the sign convention under **Droop law** and defines **Full activation**.
