"""Flatten a calculation result into a comparable audit trail.

Used only while refining a module: it turns the whole internal result tree into
dotted-path / value rows so a module's working can be compared line by line
against a reference calculation without opening the report.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterator

from .notation import esc, number
from .sheet import grid, render


def flatten(value: Any, prefix: str = "") -> Iterator[tuple[str, Any]]:
    """Yield ``('axes.x.phiMu', 1.23e8)`` style pairs for every leaf."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield from flatten(item, f"{prefix}.{key}" if prefix else str(key))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from flatten(item, f"{prefix}.{index}")
    else:
        yield prefix, value


def as_dict(result: Any) -> dict[str, Any]:
    return dict(flatten(result))


def as_text(result: Any, digits: int = 6) -> str:
    """Plain text trace, one value per line, suitable for diffing."""
    lines = []
    for path, value in sorted(flatten(result)):
        rendered = f"{value:.{digits}g}" if isinstance(value, float) else str(value)
        lines.append(f"{path} = {rendered}")
    return "\n".join(lines)


def report(inputs: dict[str, Any], result: Any, *, title: str, module_dir: Any = None,
           standalone: bool = True, sections: int = 60) -> str:
    """Render the trace onto calculation-pad sheets."""
    rows = [[esc(path), esc(number(value, 6) if isinstance(value, (int, float))
                            and not isinstance(value, bool) else value)]
            for path, value in sorted(flatten(result))]
    blocks = [grid("Internal Values", ["Path", "Value"], rows[start:start + sections],
                   "Validation trace - not for issue")
              for start in range(0, len(rows), sections)]
    identity = {**inputs, "subject": f"{title} - internal trace",
                "date": datetime.now().strftime("%d/%m/%Y")}
    return render(identity, blocks, default_subject="Validation trace",
                  standalone=standalone, title=f"{title} internal trace",
                  module_dir=module_dir, data_id="calcpad-trace")
