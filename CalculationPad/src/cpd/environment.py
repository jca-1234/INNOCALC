"""Read-only dependency checks; installation belongs to the suite setup command."""

from __future__ import annotations

import importlib
import importlib.metadata as metadata
import importlib.util
from typing import Any

# import name -> (pip requirement, what the pad uses it for, required?)
PACKAGES: dict[str, tuple[str, str, bool]] = {
    "pint": ("pint>=0.24", "Physical units on pad variables", True),
    "sympy": ("sympy>=1.12", "Symbolic algebra and equation rendering", True),
    "unit_syntax": ("unit-syntax>=0.3", "'5 kN/m' unit literals in exported notebooks", False),
    "handcalcs": ("handcalcs>=1.6", "Rendered hand calculations in exported notebooks", False),
}

_report: dict[str, Any] | None = None


def _version(name: str) -> str:
    try:
        return metadata.version(name.replace("_", "-"))
    except metadata.PackageNotFoundError:
        return ""


def _importable(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def auto_install_allowed() -> bool:
    return False


def status() -> list[dict[str, Any]]:
    """What is installed right now, without changing anything."""
    return [{"package": name, "requirement": requirement, "purpose": purpose,
             "required": required, "installed": _importable(name),
             "version": _version(name)}
            for name, (requirement, purpose, required) in PACKAGES.items()]


def ensure(*, install: bool | None = None, refresh: bool = False) -> dict[str, Any]:
    """Check dependencies without changing the interpreter environment."""
    global _report
    if install:
        raise ValueError("Install dependencies with the suite setup command, not while calculating")
    if _report is not None and not refresh:
        return _report
    missing = [name for name, (_, _, required) in PACKAGES.items()
               if required and not _importable(name)]
    installed: list[str] = []
    problems: list[str] = []
    if missing:
        problems = [f"{name} is not installed; run the suite setup command"
                    for name in missing]
    _report = {"packages": status(), "installed": installed, "problems": problems,
               "ok": not [item for item in status() if item["required"] and not item["installed"]]}
    return _report
