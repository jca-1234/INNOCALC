"""InnoCalc Manager - calculation management for Innovis projects."""

import sys
from pathlib import Path

# Design modules and the shared calcpad template live beside this application.
SUITE_ROOT = Path(__file__).resolve().parents[2]
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))

from .version import VERSION, VERSION_HISTORY  # noqa: E402

__all__ = ["SUITE_ROOT", "VERSION", "VERSION_HISTORY"]
