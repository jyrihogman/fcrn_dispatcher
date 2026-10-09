# Simulated time for asyncio tests

Type: research
Status: resolved
Blocked by:

## Question

How can asyncio code that uses wall-clock sleeps run the 21-minute step test in a pytest run of a few seconds?

Compare at least these options:

- A hand-written `Clock` protocol (`now()`, `sleep()`) with a real and a simulated implementation.
- The `looptime` pytest plugin, which fakes the event loop's time.
- anyio or trio with `MockClock`.
- `time-machine` or `freezegun` combined with an asyncio loop.

For each option, report how it works, if it stays deterministic when several tasks run concurrently, and how much code it needs. Give a recommendation for this project.

## Comments

- Findings: [research/simulated-asyncio-time.md](../research/simulated-asyncio-time.md). Recommends looptime.

## Answer

Use looptime (0.7) as a dev dependency. It fakes the asyncio loop clock, so production code needs no change. A prototype ran the 1260 s step sequence in 0.85 s with `noop_cycles=1`, and three runs gave the same output.

Rejected options:
- trio `MockClock` forces tests onto trio while production runs asyncio.
- time-machine and freezegun cannot speed up `asyncio.sleep`.
- A hand-written `Clock` repeats looptime's work, and timeouts outside it stay on real time.

Constraint for the runtime ticket: production code reads time only through `loop.time()`. It never calls `time.monotonic()` or `datetime.now()` per sample.

Open for the runtime ticket: the assignment says "design the clock so tests can run with accelerated time". A reviewer may want to see an explicit clock seam, not only a test plugin. Sample timestamps also need wall time, for example a wall-clock anchor at start plus the loop offset.

Detail: [simulated-asyncio-time.md](../research/simulated-asyncio-time.md)
