# Runtime and clock design

Type: prototype
Status: resolved
Blocked by: 01, 03

## Question

How do the frequency producer, the controller, the battery and the logger run as concurrent asyncio tasks?

Build a rough stub and decide:
- How the tasks pass data. A queue per hop, or a shared "latest value"?
- The tick rate of each task. Example: frequency at 10 Hz, battery integration at 10 Hz.
- What one **sample** is (timestamp, frequency, commanded power, actual power, SoC), and which task builds it.
- The shape of the clock seam, based on the research ticket.
- How the runtime starts, stops and handles a task that fails.
- Whether to keep an explicit clock seam in the code, or rely only on looptime with `loop.time()`. The assignment asks to "design the clock", so a reviewer may expect to see a seam.
- How a sample gets a wall-clock timestamp when the code reads only `loop.time()`.

## Comments

- From Battery interface and simulated battery behaviour: the `Battery` callables may raise. Decide what the dispatcher does then, for example log, retry or stop. The battery shell reads time with `loop.time()`.
- Prototype: [prototypes/runtime.py](../prototypes/runtime.py). Run it with `uv run --with looptime==0.7 .scratch/fcrn-takehome/prototypes/runtime.py --fast`. Add `--fail-at 700` to see the failure path. It stays in `.scratch/`, next to the research notes, because `main` has no commits yet.

## Answer

| Decision | Answer |
|---|---|
| Tasks | Three asyncio tasks in one `asyncio.TaskGroup`: producer, control, writer. The battery has no task. It integrates lazily (see Battery interface). |
| Data passing | Producer to control: a latest-value cell (a closure pair `read_f()` / `publish(f)`). Control wants the newest frequency, not a backlog. Control to writer: an unbounded `asyncio.Queue[Sample \| None]`, so every sample reaches the store. |
| Tick rates | Control ticks at 10 Hz on a fixed grid (`next_tick += 0.1`, then sleep until `next_tick`), so the ticks do not drift. The producer publishes a value and sleeps for that step's duration. |
| Sample | `Sample(at: datetime, frequency_hz, commanded_w, actual_w, soc)`, a frozen dataclass. The control task builds one per tick after `set_power`, then reads `get_power()` and `get_soc()`. The step test gives 12,601 samples (t = 0 to 1260 s). |
| Clock | No `Clock` class. The event loop is the clock. All code reads `loop.time()` and calls `asyncio.sleep()`. The seam is the loop factory: `asyncio.Runner(loop_factory=...)`. Real time uses the default loop. Accelerated time uses `looptime.patch_event_loop(asyncio.new_event_loop(), noop_cycles=1)`. The same seam serves pytest and a CLI `--fast` flag. |
| Wall timestamp | `wall_clock()` takes `datetime.now(UTC)` and `loop.time()` once at start, then returns `wall0 + (loop.time() - loop0)`. Example: start at 19:25:30.178 UTC, sample at loop +105 s → 19:27:15.178 UTC. |
| Start and stop | The run ends when the producer finishes its schedule. The runtime then cancels control. Control commands 0 W in `finally`. The runtime puts a `None` sentinel on the queue, and the writer drains and exits. |
| Failure | Fail-stop. A raising `Battery` callable ends the control task. The TaskGroup cancels the other tasks. Control tries to command 0 W. The writer flushes the queue in `finally`, so no stored sample is lost. The error reaches the caller, and a supervisor restarts the process. |

Prototype evidence: the full step test ran in about 2 s real time with looptime. SoC stayed in [0.46, 0.50], and actual power matched commanded power at every printed sample. With a failure at 700 s, the run stopped, and 7,000 samples were saved.

Note: Datastore, schema and operations story made `write_batch` async (psycopg 3 `COPY`), so the writer awaits it directly and no thread is used.
