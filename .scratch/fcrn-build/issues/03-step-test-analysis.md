# Step-test analysis

Status: resolved
Blocked by: 01
TDD: yes

## Task

Build `step_test.py`: the Table 3 sequence and the pure Requirement 1 check.

- `STEP_TEST`: the schedule as `(frequency_hz, duration_s)` pairs: `[(50.0, 30), (49.95, 30), (50.0, 300), (49.9, 300), (50.1, 300), (50.0, 300)]`. Confirm it against Table 3 in the appendix PDF.
- `steady_state_response(samples) -> (dp1, dp2)`: equations 1 and 2 of §3.1.1. Pss is the mean actual power over the last 60 s of a step: Pss,0 uses 300–360 s, Pss,1 600–660 s, Pss,2 900–960 s, Pss,3 1200–1260 s.
- `requirement_1(dp1, dp2, capacity_w) -> (up, down)`: the two ratios against |ΔPss,theoretical| = C.

This task needs `Sample`. If Pure core has not landed `sample.py` yet, add it here exactly as Pure core specifies; whichever task lands second keeps the first one's file.

Tests in `tests/test_step_test.py` use hand-built samples, not the runtime. Example: an ideal response gives `up == 0.0` and `down == 0.0`. A response of 0.9 · C gives `up == -0.1`, which fails the −5% limit. The full 12,600-sample step test is added to this file by the Runtime task.

## Read

- [Test plan](../../fcrn-takehome/issues/06-test-plan.md): Pss windows and Requirement 1.
- Appendix PDF §3.1.1 and Table 3.

## Acceptance check

- The unit tests pass, including one ratio just inside and one just outside each bound.
- `step_test.py` imports only `sample` from the package.
- The standard check passes.

## Answer

- `STEP_TEST` matches Table 3 of the appendix: 0.5 min is 30 s and 5 min is 300 s.
- Pure core had not landed `sample.py` yet, so this task adds it as Pure core specifies.
- The Pss windows are half-open. Pss,0 uses `300 <= t < 360`, measured in seconds from the first sample's `at`. Each window holds 600 samples. The sample at 360 s belongs to the next step.
- `steady_state_response` derives the window ends from `STEP_TEST`, so the schedule lives in one place.
- The hand-built samples cover 0 ≤ t < 1260 s, which gives 12,600 samples. Table 3 gives no frequency at 1260 s, the end of the test. The old count of 12,601 came from float drift in `next_tick += 0.1`. The planning tickets now say 12,600.
- Additions beyond the task list: `UP_BOUNDS = (-0.05, 0.2)` and `DOWN_BOUNDS = (-0.2, 0.05)`. The bound tests use them, and the CLI task can reuse them for its FAIL line.
- One test gives 2x the ideal power for 30 s, then 0 W for 30 s, in the last 60 s of each step. Only a mean over exactly 60 s passes it. A 30 s window fails it.
- For the CLI task: `steady_state_response` raises `StatisticsError` when a window is empty. A fail-stop run of 7,000 samples hits this. The CLI must handle a short run.
