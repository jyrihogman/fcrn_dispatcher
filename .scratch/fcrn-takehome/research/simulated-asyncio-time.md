# Simulated time for asyncio tests

Research for ticket `issues/01-simulated-time-for-asyncio-tests.md`.
Date checked: 2026-10-09.

## Question

Four asyncio tasks run together: frequency producer, droop controller, battery, logger.
Production uses real wall-clock time.
Tests must run the 21-minute step test in a few seconds.
Which way of faking time fits best?

## Short answer

Use `looptime` with `pytest-asyncio`.
Production code calls `asyncio.sleep()` and reads time with `loop.time()`.
It never calls `time.monotonic()` or `time.time()` for control or integration.
A spike in this session ran the full 21-minute sequence in 0.85 s (see "Spike").

## Background: where asyncio gets its time

`BaseEventLoop.time()` returns `time.monotonic()`.
Every `asyncio.sleep()`, `wait_for()` and `call_later()` uses `loop.time()`.
Source: [cpython 3.12 `Lib/asyncio/base_events.py`, `def time`](https://github.com/python/cpython/blob/3.12/Lib/asyncio/base_events.py).
So any fake must change `loop.time()`, or the loop does not move faster.

## Versions and maintenance

Data from the PyPI JSON API and GitHub on 2026-10-09.

| Package | Latest | Released | Last push to repo | Notes |
|---|---|---|---|---|
| looptime | 0.7 | 2026-01-03 | 2026-10-05 | Single maintainer (nolar). Five releases since 2025-06. MIT. |
| pytest-asyncio | 1.4.0 | 2026-05-26 | n/a | looptime 0.5 fixed support for pytest-asyncio >= 1.1.0. |
| trio | 0.34.0 | 2026-08-11 | n/a | Owns `trio.testing.MockClock`. |
| anyio | 4.15.1 | 2026-09-05 | n/a | Has no clock of its own. |
| time-machine | 3.5.1 | 2026-09-08 | 2026-10-05 | Active (Adam Johnson). |
| freezegun | 1.5.5 | 2025-08-09 | 2025-08-19 | Slower release pace. |

Sources: `https://pypi.org/pypi/<name>/json`, [looptime releases](https://github.com/nolar/looptime/releases), `gh api repos/<owner>/<repo>`.

## Option 1: hand-written `Clock` protocol

### How it works

You define `Clock` with `now()` and `async sleep(seconds)`.
`RealClock` wraps `loop.time()` and `asyncio.sleep()`.
`SimClock` keeps a virtual time and a heap of sleepers.

### Concurrency and determinism

`SimClock` must know when every task is blocked before it advances time.
asyncio has no public "all tasks idle" hook.
The usual trick is to yield with `asyncio.sleep(0)` a few times and then wake the earliest sleeper.
This is a small, home-made version of trio's autojump.
It breaks as soon as code awaits anything that is not `clock.sleep()`, for example `asyncio.wait_for()`, `asyncio.Queue.get()` with a timeout, or an `asyncio.Event` with a timeout.
Those calls still use the real loop clock.

### Code size

About 40 to 60 lines for `SimClock`, plus a `clock` parameter through all four tasks.
You also need tests for the clock itself.

### Verdict

It works, but it rebuilds what looptime already does at the loop level.
It has the weakest guarantee for timeouts.

## Option 2: `looptime` pytest plugin

### How it works

looptime replaces the loop's time with a fake clock in tests only.
When no callback is ready, it jumps the fake time to the next timer instead of waiting.
It patches the loop's selector: `self._selector.select` is replaced.
Source: [looptime API reference, `setup_looptime()`](https://github.com/nolar/looptime/blob/main/_autodocs/api-reference/loop-time-event-loop.md) and `looptime/_internal/loops.py`.
It changes `loop.time()` only.
The README says: "It does NOT speed up time-based tests using the synchronous primitives and the wall-clock time".
Source: [looptime README](https://github.com/nolar/looptime/blob/main/README.md).

Enable it per test with `@pytest.mark.looptime`, or for all tests with `pytest --looptime`.
Options on the marker: `start`, `end`, `idle_timeout`, `idle_step`, `noop_cycles`.
Source: [looptime configuration docs](https://github.com/nolar/looptime/blob/main/docs/configuration.rst).

Example from the README:

```python
@pytest.mark.asyncio
@pytest.mark.looptime
async def test_me():
    await asyncio.sleep(100)
    assert asyncio.get_running_loop().time() == 100
```

Useful extras:

- `looptime` fixture: compare loop time to a number with 1e-9 precision.
- `chronometer` fixture: measure real seconds, to assert the test is fast.
- `end=<seconds>`: fail the test when fake time passes a limit. This stops a stuck loop.
- `idle_timeout` (default 1.0 real second): fail if the loop waits for I/O with no timers.

Source: [looptime tools docs](https://github.com/nolar/looptime/blob/main/docs/tools.rst) and [nuances docs](https://github.com/nolar/looptime/blob/main/docs/nuances.rst).

### Concurrency and determinism

All tasks share one loop and one fake clock.
asyncio wakes timers in a fixed order for a fixed code path.
The spike gave the same log hash in three separate pytest runs.
Thread-pool work (`run_in_executor`) runs in zero fake time.
The `idle_step` option helps when threads must finish first.
Source: [nuances docs, "Sync-async synchronization"](https://github.com/nolar/looptime/blob/main/docs/nuances.rst).

### Code size

Zero lines in production code.
One dev dependency and one marker per test.
The only rule: read time with `loop.time()`, not `time.monotonic()`.

### Cost of `noop_cycles`

looptime runs 42 empty loop cycles by default before each time jump.
This protects timeout code that schedules its timer before the sleep.
With 25,000 timer wake-ups, the spike took 8.8 s at the default and 0.85 s with `noop_cycles=1`.
Pick the tick rates and this option together.

### Verdict

Best fit. No production code change, real asyncio semantics, timeouts included.
The risk is a single maintainer, but the library is small and has no runtime dependencies.

## Option 3: anyio or trio with `MockClock`

### How it works

`trio.testing.MockClock` is a trio clock.
With `autojump_threshold=0`, trio jumps to the next timeout whenever all tasks are blocked.
`rate=10.0` runs time ten times faster than real time.
Source: [trio testing reference](https://github.com/python-trio/trio/blob/main/docs/source/reference-testing.rst) and [`_mock_clock.py`](https://github.com/python-trio/trio/blob/main/src/trio/_core/_mock_clock.py).

anyio has no `MockClock`.
The anyio docs contain no clock or mock-time feature.
Source: [anyio testing docs](https://github.com/agronholm/anyio/blob/master/docs/testing.rst).
anyio passes backend options to `trio.run()`.
So `anyio_backend = ("trio", {"clock": MockClock(autojump_threshold=0)})` works, but on the trio backend only.
Source: [anyio `_backends/_trio.py`](https://github.com/agronholm/anyio/blob/master/src/anyio/_backends/_trio.py).

### Concurrency and determinism

trio's autojump is exact and deterministic. It is the best design of the four.

### Code size

All code must use anyio or trio APIs instead of asyncio.
Tests would run on trio while production runs on asyncio.
The test then checks a different event loop from the one that ships.
The project stack says `asyncio`.

### Verdict

Good tool, wrong stack for this project.

## Option 4: `time-machine` or `freezegun` with asyncio

### time-machine

time-machine mocks `time.time()`, `datetime.now()` and related calls.
It mocks `clock_gettime()` only for `CLOCK_REALTIME`.
It does not mock `time.monotonic()`.
Source: [time-machine usage docs, "Mocked functions"](https://github.com/adamchainz/time-machine/blob/main/docs/usage.rst).
So `loop.time()` and `asyncio.sleep()` stay real.
The 21-minute test still takes 21 minutes.

### freezegun

freezegun freezes `time.monotonic()` and `time.perf_counter()`.
Source: [freezegun README, "Usage"](https://github.com/spulec/freezegun/blob/master/README.rst).
A frozen monotonic clock stops asyncio timers from becoming due, so `asyncio.sleep()` hangs.
freezegun added `real_asyncio=True` to give the loop real monotonic time.
Source: [freezegun README, "real_asyncio parameter"](https://github.com/spulec/freezegun/blob/master/README.rst).
With that flag, sleeps are real again, so there is no speed-up.

### Verdict

Neither tool speeds up asyncio sleeps.
They only help if the logger needs fake wall-clock timestamps (for example a fixed `datetime.now()`).

## Comparison

| Option | Speeds up `asyncio.sleep` | Timeouts work | Deterministic with 4 tasks | Production code change | Extra deps |
|---|---|---|---|---|---|
| Hand-written `Clock` | Yes, for `clock.sleep` only | No, unless routed through the clock | Yes, if written carefully | Clock passed to every task | None |
| looptime | Yes | Yes | Yes (spike: same hash in 3 runs) | None | looptime (dev) |
| trio `MockClock` | Yes, on trio only | Yes | Yes | Rewrite to anyio or trio | anyio, trio |
| time-machine | No | n/a | n/a | None | time-machine |
| freezegun | No (hangs, or real time with `real_asyncio`) | n/a | n/a | None | freezegun |

## Spike

Location: session scratchpad, not in the repo.
Setup: Python 3.12, pytest 9.1.1, pytest-asyncio 1.4.0, looptime 0.7.

Four tasks:

- Producer: steps 50.0, 49.95, 50.0, 49.9, 50.1, 50.0 Hz, 1260 s total.
- Controller: droop law every 0.1 s.
- Battery: integrates power over `loop.time()` deltas every 0.1 s.
- Logger: one sample per second.

Results:

- The loop clock ends at 1260 s. The logger writes 1261 samples (t = 0 to 1260).
- Real time: 8.8 s with default `noop_cycles=42`. 0.85 s with `noop_cycles=1`.
- Three separate runs gave the same energy (89.9999999999979) and the same log hash.

One finding about floats:
Two runs in the same test start at different loop times (0 and 1260).
The `now - last` float deltas then differ in the last bits.
Energy differed at the 14th digit.
So compare energies with `pytest.approx`, or give each run a fresh loop.

## Recommendation

1. Use looptime 0.7 as a dev dependency with pytest-asyncio 1.x.
2. In production code, read time with `asyncio.get_running_loop().time()`. Do not call `time.monotonic()` for control or energy integration.
3. Mark step-test tests with `@pytest.mark.looptime(end=1300, noop_cycles=1)` or similar. The `end` value fails a stuck test fast.
4. If the logger needs wall-clock timestamps, store the loop time and add a start offset. Do not call `datetime.now()` per sample.
5. A thin `now()` helper around `loop.time()` is fine for readability. A full `Clock` protocol with a simulated implementation is not needed.

Ticket 04 (runtime and clock design) should take rule 2 as a constraint.
