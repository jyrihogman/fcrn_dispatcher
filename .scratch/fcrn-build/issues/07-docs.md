# Docs

Status: ready-for-agent
Blocked by: 06
TDD: no

## Task

Write the README and the architecture page.

- `README.md`: replace the uv placeholder with the ten sections from README outline, in that order. Paste real output from `uv run fcrn-dispatcher --fast`. Never invent numbers.
- `docs/architecture.md`: one Mermaid flowchart. Producer → latest-value cell → control → `Battery` seam, and control → queue → writer → Postgres, with the loop-factory seam marked. Short notes on the tasks and seams under it.

Write in plain English: one idea per sentence, active voice, no idioms, no em-dashes.

## Read

- [README outline](../../fcrn-takehome/issues/08-readme-outline.md): sections and content.
- [Battery sizing](../../fcrn-takehome/issues/02-battery-sizing.md): the sizing table.
- [Datastore, schema and operations story](../../fcrn-takehome/issues/05-datastore-and-operations.md): the deploy and operate points.
- The map's Out of scope section.

## Acceptance check

- Every command in Quick start runs as written on a clean clone.
- Every row of the assignment map names a module and a test that exist.
- The Mermaid diagram renders on GitHub.
- The standard check passes.
