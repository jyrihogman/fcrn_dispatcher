# Executor shutdown warning on --fast

Status: needs-triage
Blocked by:
TDD: yes

## Problem

Some `uv run fcrn-dispatcher --fast` runs print this before the results:

```
asyncio/events.py:94: RuntimeWarning: The executor did not finishing joining its threads within 300 seconds.
  self._context.run(self._callback, *self._args)
Run bb875fad-f627-4160-a829-80ba4a317282
Requirement 1 up: +0.000 (allowed -0.05..+0.20)
Requirement 1 down: +0.000 (allowed -0.20..+0.05)
```

The run still passes and stores all 12,600 samples. The warning does not appear on every run. The run in the README had no warning.

## Cause

1. `AsyncConnection.connect()` in `__main__.py` resolves the host with `loop.getaddrinfo()`. That call runs in the loop's default thread-pool executor (`psycopg/_conninfo_attempts_async.py`).
2. On exit, `asyncio.Runner.close()` calls `loop.shutdown_default_executor(300)`. The 300 comes from `asyncio.constants.THREAD_JOIN_TIMEOUT`.
3. `shutdown_default_executor` joins the worker threads in a helper thread. It waits for them with `asyncio.timeout(300)` on loop time.
4. With `--fast`, the loop is a looptime loop. While the loop waits for the helper thread, it has nothing else to do, so looptime moves fake time forward by 300 s at once. The timeout fires before the real threads finish joining.
5. asyncio then prints the warning and calls `executor.shutdown(wait=False)`. The worker threads never get joined.

So this is a race between a real thread join and the fake clock. The default loop never shows it, because 300 real seconds is plenty.

## Fix options

- Shut down the default executor with no timeout before the Runner closes, for example `await asyncio.get_running_loop().shutdown_default_executor()` at the end of `run_step_test`. Fake time can then move forward without a timeout to fire. `Runner.close()` calls it again, which returns at once.
- Pass `hostaddr` in the connection string so psycopg skips DNS. This removes the executor use but makes `.env` harder to write.
- Connect on the default loop and run only the step test on looptime. This splits one run across two loops.

The first option is the smallest change and keeps the loop-factory seam from ADR 0002 as it is.

## Acceptance check

- A test runs `loop.run_in_executor(None, ...)` inside `asyncio.Runner(loop_factory=fast_loop)`, closes the runner, and turns `RuntimeWarning` into an error. It repeats this enough times to fail reliably before the fix.
- `uv run fcrn-dispatcher --fast` prints no warning in 20 runs in a row.
- The standard check passes.
