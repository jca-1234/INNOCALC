"""InnoCalc version numbers: ``v<Major>.<Patch>.<Minor>``.

* **Major** - saved calculations or engineering results may change; re-verify.
* **Patch** - a correction or addition that leaves existing saved calculations valid.
* **Minor** - presentation, wording or documentation only; results are identical.

Python packaging needs PEP 440, so ``pyproject.toml`` carries the same three
numbers without the ``v`` (``v0.0.1`` -> ``0.0.1``).
"""

from __future__ import annotations

import re

PATTERN = re.compile(r"^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
FIRST = "v0.0.1"


def parse(version: str) -> tuple[int, int, int]:
    """``'v1.2.3'`` -> ``(1, 2, 3)`` as (major, patch, minor)."""
    match = PATTERN.fullmatch(str(version or "").strip())
    if not match:
        raise ValueError(f"Version {version!r} is not in the form vMajor.Patch.Minor, e.g. v0.0.1")
    return int(match[1]), int(match[2]), int(match[3])


def bump(version: str, part: str) -> str:
    major, patch, minor = parse(version)
    if part == "major":
        return f"v{major + 1}.0.0"
    if part == "patch":
        return f"v{major}.{patch + 1}.0"
    if part == "minor":
        return f"v{major}.{patch}.{minor + 1}"
    raise ValueError("part must be major, patch or minor")


def packaging(version: str) -> str:
    """The PEP 440 spelling used in pyproject.toml."""
    parse(version)
    return version[1:]
