# The event loop is the clock

The code has no `Clock` class. Every task reads time with `loop.time()` and waits with `asyncio.sleep()`. The seam is the loop factory passed to `asyncio.Runner(loop_factory=...)`. Real time uses the default loop. Accelerated time uses `looptime.patch_event_loop(asyncio.new_event_loop(), noop_cycles=1)`. The same seam serves the pytest suite and the CLI `--fast` flag. With it, the 1260 s step test runs in about 2 s.

Samples need wall time, but the code reads only `loop.time()`. So `wall_clock()` takes `datetime.now(UTC)` and `loop.time()` once at start. After that it returns `wall0 + (loop.time() - loop0)`. Example: a run starts at 19:25:30.178 UTC, and a sample at loop +105 s gets 19:27:15.178 UTC.

The assignment asks to "design the clock so tests can run with accelerated or simulated time". A reader may expect a `Clock` interface. This ADR records why there is none.

## Considered Options

- **A hand-written `Clock` protocol** (`now()`, `sleep()`) with a real and a simulated implementation. The simulated clock must know when every task is blocked before it moves time forward. That repeats the work looptime already does, in about 40 to 60 lines. A `clock` parameter must also pass through every task. Timeouts inside libraries such as psycopg stay on real time, so the simulation leaks.
- **trio or anyio with `trio.testing.MockClock`.** It works only on the trio backend. The tests would run trio while production runs asyncio.
- **looptime as a pytest plugin only.** The tests would get fast time, but the CLI would not. With the loop factory as the seam, the CLI `--fast` flag uses the same mechanism as the tests.

## Consequences

- Production code must never call `time.time()`, `time.monotonic()` or `datetime.now()` for timing. The only exception is the single `datetime.now(UTC)` inside `wall_clock()`.
- looptime is a main dependency, because `--fast` needs it at runtime.
