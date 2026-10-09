# Scaffold

Status: resolved
Blocked by:
TDD: no

## Task

Commit the planning work, then create the empty project.

1. Write `.gitignore` with `*.pdf`, `.env`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`.
2. Commit the planning work as it is: `.gitignore`, `.scratch/`, `docs/`, `CONTEXT.md`, `AGENTS.md`. Check with `git status` that no PDF is staged.
3. Run `uv init --package --name fcrn-dispatcher --python 3.15` in the repo root. `--package` is needed, because uv before 0.12 makes no build system without it. Keep the `.gitignore` from step 1.
4. Empty `src/fcrn_dispatcher/__init__.py`. Point `[project.scripts]` at `fcrn-dispatcher = "fcrn_dispatcher.__main__:main"`. Leave the uv placeholder `README.md`; the Docs task replaces it.
5. Dependencies: `uv add looptime psycopg[binary] pydantic-settings yoyo-migrations` and `uv add --dev pytest hypothesis testcontainers ruff ty`. looptime is a main dependency, because `--fast` needs it at runtime.
6. In `pyproject.toml`: ruff and pytest exclude `.scratch/`. Register the pytest marker `integration`. Set `testpaths = ["tests"]`.
7. Write `.env.example` with the sizing values and a local URL:
   ```
   DATABASE_URL=postgresql://postgres:dev@localhost:5432/postgres
   FCRN_CAPACITY_W=1000000
   BATTERY_MAX_POWER_W=1340000
   BATTERY_ENERGY_WH=2000000
   BATTERY_INITIAL_SOC=0.5
   ```
8. Write `tests/test_imports.py`. It holds the full allowed-imports dict from Package layout and module seams, parses each module in `src/fcrn_dispatcher/` with `ast`, and fails when a module imports a package module that the dict does not allow. It checks only modules that exist, so it guards each later task as its modules arrive. Also check that only `settings` imports pydantic.
9. Commit the scaffold.

## Read

- [Package layout and module seams](../../fcrn-takehome/issues/07-package-layout.md): the import rules and the layout.
- [Datastore, schema and operations story](../../fcrn-takehome/issues/05-datastore-and-operations.md): the env vars.
- [README outline](../../fcrn-takehome/issues/08-readme-outline.md): `.scratch/` is committed and excluded from ruff and pytest.

## Acceptance check

- `git log` shows two commits: the planning work, then the scaffold. No PDF is tracked.
- The standard check passes.
- `test_imports.py` fails if you add `import fcrn_dispatcher.store` to a scratch `droop.py`. Remove the scratch file after.

## Answer

- Committed the planning work first, then ran `uv init --package`. No PDF is tracked.
- `tests/test_imports.py` holds the allowed-imports dict. It also fails when a module in the package has no entry in the dict. It catches `import fcrn_dispatcher.x`, `from fcrn_dispatcher import x`, `from .x import y` and `from . import x`.
- Two changes beyond the task list:
  - `ty` also excludes `.scratch/`. Without it, `ty check` fails on a looptime type error in the prototype.
  - pytest runs with `-p no:looptime_plugin`. The looptime pytest plugin expects pytest-asyncio and crashes on every parametrized test without it. The design uses looptime through the loop factory, not through the plugin, so the plugin is not needed.
