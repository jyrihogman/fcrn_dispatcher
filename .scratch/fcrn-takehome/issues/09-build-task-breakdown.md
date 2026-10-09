# Build-task breakdown

Type: grilling
Status: resolved
Blocked by: 08

## Question

What is the ordered list of build tasks, each sized for one agent session, that turns the decisions on this map into the deliverable?

Decide:
- The task list and its order. Each task names the modules and tests it delivers, and its acceptance check.
- Which tasks can run in parallel.
- Where the list lives, so that it can be handed off.

## Comments

- From README outline: the task list needs a docs task for `README.md` and `docs/architecture.md`. It comes last, because the README pastes real `--fast` output. Ruff and pytest must exclude `.scratch/`, and `.scratch/` gets committed. ADR 0002 is already written.

## Answer

The build is a separate effort, [fcrn-build](../../fcrn-build/spec.md). It has one file per task with `Status: ready-for-agent`, a `Blocked by:` line and an acceptance check.

| # | Task | Blocked by | TDD |
|---|---|---|---|
| 01 | Scaffold: commit the planning work, then `uv init --package`, deps, `.env.example`, `test_imports.py` | | no |
| 02 | Pure core: `droop.py`, `sample.py`, `battery.py`, property and example tests | 01 | yes |
| 03 | Step-test analysis: `step_test.py` on hand-built samples | 01 | yes |
| 04 | Runtime: `runtime.py`, fake store, fail-stop test, full 12,601-sample step test | 02, 03 | yes |
| 05 | Store: migrations, `store.py`, testcontainers test | 02 | yes |
| 06 | Settings and CLI: `settings.py`, `__main__.py`, `--fast` against local Postgres | 04, 05 | no |
| 07 | Docs: `README.md` with real `--fast` output, `docs/architecture.md` | 06 | no |

Parallel: 02 with 03, and 04 with 05.

Other decisions:
- Standard check for every task: `ruff format --check`, `ruff check`, `ty check`, `pytest`. ty joins the dev tools.
- Each task ends with one commit: plain English, no conventional-commit prefix, with a co-author trailer.
- The first commit is the planning work as it is. The PDFs are gitignored and never committed.
- Scaffold uses `uv init --package`, because the local uv (0.11.3) makes no build system without `--package`.
