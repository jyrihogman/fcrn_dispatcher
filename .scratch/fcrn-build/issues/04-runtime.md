# Runtime

Status: ready-for-agent
Blocked by: 02, 03
TDD: yes

## Task

Build `runtime.py` and the full step test.

- `latest()`: the latest-value cell, a closure pair `read_f()` / `publish(f)`.
- `wall_clock()`: `wall0 + (loop.time() - loop0)`.
- `produce`, `control`, `write`: the three tasks. Control ticks at 10 Hz on a fixed grid, commands `droop(f)`, then reads `get_power()` and `get_soc()` and builds a `Sample`. Control commands 0 W in `finally`. The writer awaits `write_batch` and flushes the queue in `finally`.
- `run(...)`: one `asyncio.TaskGroup`. It ends when the producer finishes the schedule. Failures stop the whole run, and the error reaches the caller.
- Loop factories: the default loop, and `looptime.patch_event_loop(asyncio.new_event_loop(), noop_cycles=1)`.

`runtime` imports `droop`, `battery` and `sample` only. `write_batch` and the sizing values arrive as arguments.

Tests:

- `tests/conftest.py`: the fake store, a list plus `async def write_batch`.
- `tests/test_runtime.py`: `wall_clock` gives wall0 + 105 s after 105 s of loop time. Fail-stop: the battery raises at 700 s, control commands 0 W, the error reaches the caller, and the fake store holds 7,000 samples.
- `tests/test_step_test.py`: the full step test on looptime. Exactly 12,601 samples. For every sample, `|commanded| ≤ C`, `|actual| ≤ Pmax`, `0 ≤ soc ≤ 1`, `actual == commanded` and `commanded == droop(f)`, with `pytest.approx(abs=1)`. Requirement 1 passes.

## Read

- [Runtime and clock design](../../fcrn-takehome/issues/04-runtime-and-clock-design.md)
- [ADR 0002](../../../docs/adr/0002-event-loop-is-the-clock.md)
- [Test plan](../../fcrn-takehome/issues/06-test-plan.md)
- The prototype `.scratch/fcrn-takehome/prototypes/runtime.py`.

## Acceptance check

- The full step test passes on looptime in a few seconds of real time.
- No test uses the real clock.
- The standard check passes.
