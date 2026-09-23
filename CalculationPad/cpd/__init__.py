"""Compatibility entry for python -m cpd.dev from the repository folder."""

import sys
from pathlib import Path

_repository = Path(__file__).resolve().parents[1]
__path__.append(str(_repository / "src" / "cpd"))
if str(_repository.parent) not in sys.path:
    sys.path.insert(0, str(_repository.parent))

from .version import VERSION, VERSION_HISTORY

__all__ = ["VERSION", "VERSION_HISTORY"]
