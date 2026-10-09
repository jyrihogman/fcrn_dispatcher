# Test plan

Type: grilling
Status: resolved
Blocked by: 02, 03, 04

## Question

Which tests prove the assignment is met, and what does each one assert?

Decide:
- The step test: which time window counts as "steady state" for Pss,0 to Pss,3, and how Requirement 1 is computed and checked.
- How the step test asserts that power and SoC stay inside their limits at every sample.
- The property-based tests. Candidates: SoC stays in [0, 1], droop is monotonic in frequency, commanded power stays within ±C_FCR-N inside the band.
- Which tests run on simulated time and which, if any, touch the real datastore.

## Comments

- From Battery interface and simulated battery behaviour: cover the clamp at a SoC limit, saturation at ±C outside the band, and lazy integration when SoC reaches a limit partway through an interval. The pure core (`advance`, `command`) can take hypothesis tests without asyncio.
- From Runtime and clock design: tests run the runtime on looptime with `noop_cycles=1`. The full step test then takes about 2 s. The control task samples at 10 Hz from t = 0 to t = 1260 s, which gives 12,601 samples. Cover the fail-stop path: a raising battery stops the run, control commands 0 W, and the queued samples still reach the store.
- From Datastore, schema and operations story: unit tests and the step test use an in-memory fake store (`async write_batch`). One integration test uses testcontainers Postgres, applies the yoyo migrations and reads the rows back. Tests build `Settings` directly and never read `.env`.

## Answer

| Area | Decision |
|---|---|
| Pss window | Steady-state power is the mean **actual** power over the last 60 s of each step. Pss,0 uses 300–360 s, Pss,1 uses 600–660 s, Pss,2 uses 900–960 s, Pss,3 uses 1200–1260 s. Actual power, because commanded power cannot show a battery that fails to deliver. The last 60 s stays correct if a ramp is added later. |
| Requirement 1 | Pure package functions: `steady_state_response(samples) -> (dp1, dp2)` (equations 1 and 2) and `requirement_1(dp1, dp2, capacity_w) -> (up, down)`, with \|ΔPss,theoretical\| = C. The step test asserts −0.05 ≤ up ≤ 0.2 and −0.2 ≤ down ≤ 0.05. |
| CLI | After a step-test run the CLI prints both ratios. Example: `Requirement 1 up: +0.000 (allowed -0.05..+0.20)`. It prints FAIL and exits with code 1 when a ratio is out of bounds. |
| Step test per-sample checks | It reads every sample back from the fake store and checks `\|commanded\| ≤ C`, `\|actual\| ≤ Pmax`, `0 ≤ soc ≤ 1`, `actual == commanded`, `commanded == droop(f)`, and exactly 12,601 samples. Floats use `pytest.approx(abs=1)` (1 W). `actual == commanded` is the proof that the battery delivers the requested response throughout. |
| Property tests | Hypothesis on the pure core, no asyncio. (1) SoC stays in [0, 1] for any start SoC, command sequence and time gaps. (2) Droop is monotonic: f1 < f2 gives droop(f1) ≥ droop(f2). (3) Droop stays within ±C for every frequency. (4) Actual power stays within ±Pmax for any command. |
| Example tests | Energy balance: 1 MW for 30 min moves SoC from 0.5 to 0.25. Partway clamp: SoC 0.01, then 10 min at 1 MW, gives SoC 0 and actual 0. Saturation: 49.85 Hz commands +1 MW. Fail-stop: the battery raises at 700 s, control commands 0 W, the error reaches the caller, and the fake store holds 7,000 samples. The step test covers the latest-value cell, because a stale frequency breaks `commanded == droop(f)`. |
| Time | All runtime tests run on looptime with `noop_cycles=1`. No test uses the real clock. `wall_clock()` gets one test on looptime: wall0 + 105 s of loop time gives wall0 + 105 s. |
| Store | Unit tests and the step test use the in-memory fake store. The testcontainers Postgres test has the pytest marker `integration`. It runs by default and is skipped when Docker is not available. |

Glossary: `CONTEXT.md` now defines **Steady-state power** (Pss).
