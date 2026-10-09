# Battery sizing

Type: grilling
Status: resolved
Blocked by:

## Question

What values do we pick for C_FCR-N, Pmax, usable energy capacity E, and the starting SoC? What reasons go in the README?

Starting point from Table 10 (LER): Pmax ≥ 1.34 · C_FCR-N, and E covers 1 h of full activation in each direction. Example: C = 1 MW, Pmax = 1.34 MW, E = 2 MWh usable, SoC starts at 0.5.

Also decide:
- whether to model round-trip efficiency or self-discharge, or leave both out
- whether the SoC limits are 0 and 1, or a narrower usable window

## Answer

| Parameter | Value | Reason for the README |
|---|---|---|
| C_FCR-N | 1 MW (configurable) | Round numbers. Full activation is ±1 MW. The design does not depend on scale. |
| Pmax | 1.34 MW | Table 10 requires ±1.34 · C for an LER. The extra 0.34 · C is headroom for NEM, which this project leaves out. Droop alone never asks for more than C. |
| E | 2 MWh usable | Table 10 requires 1 h · C in each direction. Starting at SoC 0.5 gives exactly 1 h each way. A real unit has a larger nameplate, for example 2.5 MWh used between 10% and 90%. |
| SoC limits | 0 and 1 of usable E | §3.5 defines SoC over the energy available for FCR. This keeps SoC ∈ [0, 1] as the invariant. |
| Starting SoC | 0.5 (constructor argument) | §3.5 suggests SoC near 50% for symmetric reserves. Property tests pass other values. |
| Losses | None | The battery is ideal: energy changes by power × time. Losses make SoC drift, and fixing drift is NEM's job, which is out of scope. |

Fact for the test plan: the step test moves SoC very little. The 5 min at 49.9 Hz uses C × 5/60 h ≈ 0.083 MWh, and the 5 min at 50.1 Hz puts the same amount back.
