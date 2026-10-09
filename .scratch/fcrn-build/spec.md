# FCR-N dispatcher build

This effort builds the take-home. Every design decision is already made in the planning map, [map.md](../fcrn-takehome/map.md). Each decision lives in one ticket under `../fcrn-takehome/issues/`. Read the ticket a task links to. Do not decide again what a ticket already decided.

## Order

| # | Task | Blocked by | Runs in parallel with |
|---|---|---|---|
| 01 | [Scaffold](issues/01-scaffold.md) | | |
| 02 | [Pure core](issues/02-pure-core.md) | 01 | 03 |
| 03 | [Step-test analysis](issues/03-step-test-analysis.md) | 01 | 02 |
| 04 | [Runtime](issues/04-runtime.md) | 02, 03 | 05 |
| 05 | [Store](issues/05-store.md) | 02 | 04 |
| 06 | [Settings and CLI](issues/06-settings-and-cli.md) | 04, 05 | |
| 07 | [Docs](issues/07-docs.md) | 06 | |
| 08 | [Executor shutdown warning on --fast](issues/08-fast-executor-shutdown-warning.md) | | |

## How to work a task

1. Pick the first task whose `Status:` is `ready-for-agent` and whose `Blocked by:` tasks are all `resolved`.
2. Set `Status: claimed` and save the file before any work.
3. Read the planning tickets the task links to, and `CONTEXT.md` for the vocabulary.
4. If the task says TDD, call the `tdd` skill and work red-green-refactor.
5. Build only what the task lists. Follow the Python style in the map Notes: pure functions first, a class only where it is needed, frozen dataclasses for our own values.
6. Meet the task's acceptance check and the standard check below.
7. Append what you did under `## Answer`, set `Status: resolved`, and commit.

## Standard check

Every task is done only when all of these pass:

```sh
uv run ruff format --check
uv run ruff check
uv run ty check
uv run pytest
```

Then make one commit for the task. Write the message in plain English, with no conventional-commit prefix. End it with the co-author trailer of the model that did the work, for example:

```
Add the pure droop law and simulated battery

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

Never commit the PDFs or `.env`.
