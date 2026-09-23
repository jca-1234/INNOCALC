"""Concrete Column Design - AS 3600:2018 design tool (Python core)."""

import sys
from pathlib import Path

for _candidate in Path(__file__).resolve().parents:
    if (_candidate / "suite.toml").is_file():
        if str(_candidate) not in sys.path:
            sys.path.insert(0, str(_candidate))
        break

from .version import VERSION, VERSION_HISTORY  # noqa: E402

__all__ = ["VERSION", "VERSION_HISTORY"]
