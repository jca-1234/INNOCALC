"""Third-party libraries the pad relies on, checked and installed when it opens.

The pad is opened from a network drive on machines that are set up by hand, so
it cannot assume Pint and SymPy are present.  :func:`ensure` runs once per
process when the module is opened; anything missing is installed with ``pip``
into the interpreter that is already running.  Nothing here is fatal: the pad
degrades to plain floats and its own expression printer if an install fails, so
a saved sheet always opens.

Set ``CPD_NO_AUTO_INSTALL=1`` to check and report without installing, which is
what a locked-down or offline machine wants.
"""

from __future__ import annotations

import importlib
import importlib.metadata as metadata
import importlib.util
import os
import subprocess
import sys
from typing import Any

# import name -> (pip requirement, what the pad uses it for, required?)
PACKAGES: dict[str, tuple[str, str, bool]] = {
    "pint": ("pint>=0.24", "Physical units on pad variables", True),
    "sympy": ("sympy>=1.12", "Symbolic algebra and equation rendering", True),
    "unit_syntax": ("unit-syntax>=0.3", "'5 kN/m' unit literals in exported notebooks", False),
    "handcalcs": ("handcalcs>=1.6", "Rendered hand calculations in exported notebooks", False),
}

INSTALL_TIMEOUT = 300
_report: dict[str, Any] | None = None


def _version(name: str) -> str:
    try:
        return metadata.version(name.replace("_", "-"))
    except metadata.PackageNotFoundError:
        return ""


def _importable(name: str) -> bool:
    if name in sys.modules:
        return True
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


def _install(requirements: list[str]) -> tuple[bool, str]:
    command = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", *requirements]
    try:
        completed = subprocess.run(command, capture_output=True, text=True,  # noqa: S603 - fixed argument list
                                   timeout=INSTALL_TIMEOUT, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if completed.returncode:
        tail = (completed.stderr or completed.stdout or "").strip().splitlines()
        return False, tail[-1] if tail else f"pip exited {completed.returncode}"
    importlib.invalidate_caches()
    return True, ""


def ensure(*, install: bool | None = None, refresh: bool = False) -> dict[str, Any]:
    """Check the pad's libraries once per process and install what is missing."""
    global _report
    if install:
        raise ValueError("Install dependencies with the suite setup command, not while calculating")
    if _report is not None and not refresh:
        return _report
    if install is None:
        install = auto_install_allowed()
    missing = [name for name, (_, _, required) in PACKAGES.items()
               if required and not _importable(name)]
    installed: list[str] = []
    problems: list[str] = []
    if missing and install:
        ok, error = _install([PACKAGES[name][0] for name in missing])
        if ok:
            installed = [name for name in missing if _importable(name)]
            problems = [f"{name}: installed but still not importable"
                        for name in missing if name not in installed]
        else:
            problems = [f"pip install {' '.join(missing)}: {error}"]
    elif missing:
        problems = [f"{name} is not installed; run the suite setup command"
                    for name in missing]
    _report = {"packages": status(), "installed": installed, "problems": problems,
               "ok": not [item for item in status() if item["required"] and not item["installed"]]}
    return _report
