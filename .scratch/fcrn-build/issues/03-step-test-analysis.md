# Step-test analysis

Status: ready-for-agent
Blocked by: 01
TDD: yes

## Task

Build `step_test.py`: the Table 3 sequence and the pure Requirement 1 check.

- `STEP_TEST`: the schedule as `(frequency_hz, duration_s)` pairs: `[(50.0, 30), (49.95, 30), (50.0, 300), (49.9, 300), (50.1, 300), (50.0, 300)]`. Confirm it against Table 3 in the appendix PDF.
- `steady_state_response(samples) -> (dp1, dp2)`: equations 1 and 2 of §3.1.1. Pss is the mean actual power over the last 60 s of a step: Pss,0 uses 300–360 s, Pss,1 600–660 s, Pss,2 900–960 s, Pss,3 1200–1260 s.
- `requirement_1(dp1, dp2, capacity_w) -> (up, down)`: the two ratios against |ΔPss,theoretical| = C.

This task needs `Sample`. If Pure core has not landed `sample.py` yet, add it here exactly as Pure core specifies; whichever task lands second keeps the first one's file.

Tests in `tests/test_step_test.py` use hand-built samples, not the runtime. Example: an ideal response gives `up == 0.0` and `down == 0.0`. A response of 0.9 · C gives `up == -0.1`, which fails the −5% limit. The full 12,601-sample step test is added to this file by the Runtime task.

## Read

- [Test plan](../../fcrn-takehome/issues/06-test-plan.md): Pss windows and Requirement 1.
- Appendix PDF §3.1.1 and Table 3.

## Acceptance check

- The unit tests pass, including one ratio just inside and one just outside each bound.
- `step_test.py` imports only `sample` from the package.
- The standard check passes.
