"""InnoCalc Manager - calculation management for Innovis projects."""

import sys
from pathlib import Path

SUITE_ROOT = next((candidate for candidate in Path(__file__).resolve().parents
                   if (candidate / "suite.toml").is_file()), None)
if SUITE_ROOT is None:
    raise RuntimeError("InnoCalc suite.toml was not found above the manager installation")
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))

from .version import VERSION, VERSION_HISTORY  # noqa: E402

__all__ = ["SUITE_ROOT", "VERSION", "VERSION_HISTORY"]
