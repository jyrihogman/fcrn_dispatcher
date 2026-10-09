import ast
from pathlib import Path

import pytest

PACKAGE = "fcrn_dispatcher"
PACKAGE_DIR = Path(__file__).parent.parent / "src" / PACKAGE

# The controller stays independent of timing, networking, persistence and
# simulation. The runtime gets write_batch and the sizing values as arguments,
# so it never imports store or settings.
ALLOWED_IMPORTS: dict[str, set[str]] = {
    "__init__": set(),
    "droop": set(),
    "sample": set(),
    "battery": set(),
    "settings": set(),
    "step_test": {"sample"},
    "store": {"sample"},
    "runtime": {"droop", "battery", "sample"},
    "__main__": {
        "droop",
        "battery",
        "sample",
        "settings",
        "step_test",
        "store",
        "runtime",
    },
}

MODULES = sorted(path.stem for path in PACKAGE_DIR.glob("*.py"))


def imported_names(module: str) -> tuple[set[str], set[str]]:
    """Return (package modules, top-level external packages) the module imports."""
    tree = ast.parse((PACKAGE_DIR / f"{module}.py").read_text())
    internal: set[str] = set()
    external: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[0] == PACKAGE:
                    internal.add(parts[1] if len(parts) > 1 else "__init__")
                else:
                    external.add(parts[0])
        elif isinstance(node, ast.ImportFrom):
            parts = node.module.split(".") if node.module else []
            if node.level == 0 and parts[0] != PACKAGE:
                external.add(parts[0])
                continue
            inside_package = parts if node.level else parts[1:]
            if inside_package:
                internal.add(inside_package[0])
            else:
                internal.update(alias.name for alias in node.names)
    return internal, external


@pytest.mark.parametrize("module_name", MODULES)
def test_module_has_an_import_rule(module_name: str) -> None:
    assert module_name in ALLOWED_IMPORTS, f"add {module_name} to ALLOWED_IMPORTS"


@pytest.mark.parametrize("module_name", MODULES)
def test_module_imports_only_allowed_package_modules(module_name: str) -> None:
    internal, _ = imported_names(module_name)
    forbidden = internal - ALLOWED_IMPORTS.get(module_name, set()) - {module_name}
    assert not forbidden, f"{module_name} must not import {sorted(forbidden)}"


@pytest.mark.parametrize("module_name", MODULES)
def test_only_settings_imports_pydantic(module_name: str) -> None:
    _, external = imported_names(module_name)
    pydantic = {name for name in external if name.startswith("pydantic")}
    assert module_name == "settings" or not pydantic, (
        f"{module_name} must not import {sorted(pydantic)}"
    )
