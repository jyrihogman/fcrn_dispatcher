# Runtime

Status: resolved
Blocked by: 02, 03
TDD: yes

## Task

Build `runtime.py` and the full step test.

- `latest()`: the latest-value cell, a closure pair `read_f()` / `publish(f)`.
- `wall_clock()`: `wall0 + (loop.time() - loop0)`.
- `produce`, `control`, `write`: the three tasks. Control ticks at 10 Hz on a fixed grid, commands `droop(f)`, then reads `get_power()` and `get_soc()` and builds a `Sample`. Control commands 0 W in `finally`. The writer awaits `write_batch` and flushes the queue in `finally`.
- `run(...)`: one `asyncio.TaskGroup`. It ends when the producer finishes the schedule. Failures stop the whole run, and the error reaches the caller.
- The step test samples 0 ≤ t < 1260 s, and no sample at 1260 s. Control computes tick n as `start + n * 0.1`, not `next_tick += 0.1`. The sample count must not depend on float drift or on which of two timers due at the same loop time runs first.
- Loop factories: the default loop, and `looptime.patch_event_loop(asyncio.new_event_loop(), noop_cycles=1)`.

`runtime` imports `droop`, `battery` and `sample` only. `write_batch` and the sizing values arrive as arguments.

Tests:

- `tests/conftest.py`: the fake store, a list plus `async def write_batch`.
- `tests/test_runtime.py`: `wall_clock` gives wall0 + 105 s after 105 s of loop time. Fail-stop: the battery raises at 700 s, control commands 0 W, the error reaches the caller, and the fake store holds 7,000 samples.
- `tests/test_step_test.py`: the full step test on looptime. Exactly 12,600 samples. For every sample, `|commanded| ≤ C`, `|actual| ≤ Pmax`, `0 ≤ soc ≤ 1`, `actual == commanded` and `commanded == droop(f)`, with `pytest.approx(abs=1)`. Requirement 1 passes.

## Read

- [Runtime and clock design](../../fcrn-takehome/issues/04-runtime-and-clock-design.md)
- [ADR 0002](../../../docs/adr/0002-event-loop-is-the-clock.md)
- [Test plan](../../fcrn-takehome/issues/06-test-plan.md)
- The prototype `.scratch/fcrn-takehome/prototypes/runtime.py`.

## Acceptance check

- The full step test passes on looptime in a few seconds of real time.
- No test uses the real clock.
- The standard check passes.

## Answer

- `src/fcrn_dispatcher/runtime.py`: `fast_loop`, `wall_clock`, `latest`, `produce`, `control`, `write` and `run`. There is no default-loop factory: `asyncio.Runner(loop_factory=None)` already gives the default loop.
- Control runs exactly `round(duration / 0.1)` ticks, so it ends after the tick at 1259.9 s. No sample at 1260 s can race the producer's last timer. Then the TaskGroup waits for the producer, so the run still ends when the schedule ends.
- The writer keeps the batch it is writing. A cancel can stop `write_batch` partway, so `finally` writes that batch again with the backlog. A slow-store case of the fail-stop test found this: without it, 6,990 of 7,000 samples reached the store. This assumes a cancelled `write_batch` stores nothing, which holds for a COPY inside one transaction (ticket 05).
- Tests: `tests/conftest.py` (fake store), `tests/test_runtime.py` (wall clock, fail-stop with a fast and a slow store) and the full step test in `tests/test_step_test.py`. The full suite runs in about 2.5 s.
- `uv run ty check` with no paths also scans `.claude/worktrees/`. Check with `uv run ty check src tests` while a parallel worktree exists.
