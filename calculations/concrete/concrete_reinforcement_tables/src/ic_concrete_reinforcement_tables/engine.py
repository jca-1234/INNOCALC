"""Reinforcement reference tables: bar areas and fabric mesh properties.

Working units are mm for diameters and spacings and mm2 (or mm2 per metre) for
areas.  This module is a **lookup table**.  It performs no design check and
returns no utilisation.

The design basis is a transcription of the retained Structural Toolkit workbook
``Concrete_Reinforcement_500.xls`` (REINFORCEMENT V5.00, sheets ``Number``,
``Centres`` and ``Fabric``).
"""

from __future__ import annotations

import math
from typing import Any

from .version import VERSION

MODULE_ID = "concrete-reinforcement-tables"

BAR_SIZES = (12.0, 16.0, 20.0, 24.0, 28.0, 32.0, 40.0)
BAR_COUNTS = tuple(range(1, 31))
BAR_CENTRES = (60.0, 80.0, 100.0, 120.0, 140.0, 160.0, 180.0, 200.0, 225.0, 250.0,
               275.0, 300.0, 350.0, 400.0, 450.0, 500.0, 600.0, 700.0, 800.0, 900.0, 1000.0)
ROUNDINGS = {"-1": "Down to 10 mm2", "0": "Down to 1 mm2"}

# Fabric!rows 9 to 28.  Trench mesh areas are per sheet width, not per metre.
FABRIC = (
    {"name": "RL1218", "family": "Rectangular", "longDia": 11.9, "longCts": 100.0,
     "crossDia": 7.6, "crossCts": 200.0, "wires": None, "note": ""},
    {"name": "RL1118", "family": "Rectangular", "longDia": 10.7, "longCts": 100.0,
     "crossDia": 7.6, "crossCts": 200.0, "wires": None, "note": ""},
    {"name": "RL1018", "family": "Rectangular", "longDia": 9.5, "longCts": 100.0,
     "crossDia": 7.6, "crossCts": 200.0, "wires": None, "note": ""},
    {"name": "RL918", "family": "Rectangular", "longDia": 8.6, "longCts": 100.0,
     "crossDia": 7.6, "crossCts": 200.0, "wires": None, "note": ""},
    {"name": "RL818", "family": "Rectangular", "longDia": 7.6, "longCts": 100.0,
     "crossDia": 7.6, "crossCts": 200.0, "wires": None, "note": ""},
    {"name": "RL718", "family": "Rectangular", "longDia": 6.75, "longCts": 100.0,
     "crossDia": 7.6, "crossCts": 200.0, "wires": None, "note": ""},
    {"name": "SL81", "family": "Square", "longDia": 7.6, "longCts": 100.0,
     "crossDia": 7.6, "crossCts": 100.0, "wires": None, "note": ""},
    {"name": "SL102", "family": "Square", "longDia": 9.5, "longCts": 200.0,
     "crossDia": 9.5, "crossCts": 200.0, "wires": None, "note": ""},
    {"name": "SL92", "family": "Square", "longDia": 8.6, "longCts": 200.0,
     "crossDia": 8.6, "crossCts": 200.0, "wires": None, "note": ""},
    {"name": "SL82", "family": "Square", "longDia": 7.6, "longCts": 200.0,
     "crossDia": 7.6, "crossCts": 200.0, "wires": None, "note": ""},
    {"name": "SL72", "family": "Square", "longDia": 6.75, "longCts": 200.0,
     "crossDia": 6.75, "crossCts": 200.0, "wires": None, "note": ""},
    {"name": "SL62", "family": "Square", "longDia": 6.0, "longCts": 200.0,
     "crossDia": 6.0, "crossCts": 200.0, "wires": None, "note": ""},
    {"name": "SL52", "family": "Square", "longDia": 4.77, "longCts": 200.0,
     "crossDia": 4.77, "crossCts": 200.0, "wires": None, "note": ""},
    {"name": "SL63", "family": "Square", "longDia": 6.0, "longCts": 300.0,
     "crossDia": 6.0, "crossCts": 300.0, "wires": None, "note": "Western Australia only"},
    {"name": "SL53", "family": "Square", "longDia": 4.77, "longCts": 300.0,
     "crossDia": 4.77, "crossCts": 300.0, "wires": None, "note": "Western Australia only"},
    {"name": "L12TM", "family": "Trench", "longDia": 11.9, "longCts": None,
     "crossDia": None, "crossCts": None, "wires": 4.0, "note": "Area per sheet, not per metre"},
    {"name": "L11TM", "family": "Trench", "longDia": 10.7, "longCts": None,
     "crossDia": None, "crossCts": None, "wires": 4.0, "note": "Area per sheet, not per metre"},
    {"name": "L8TM", "family": "Trench", "longDia": 7.6, "longCts": None,
     "crossDia": None, "crossCts": None, "wires": 1.0, "note": "Area per sheet, not per metre"},
)
FABRIC_BY_NAME = {entry["name"]: entry for entry in FABRIC}

ASSUMPTIONS = [
    "This module is a reference lookup. It performs no strength, serviceability or detailing "
    "check and returns no utilisation.",
    "A bar area is pi db^2 / 4. An area per metre is that area multiplied by 1000 divided by "
    "the bar centres.",
    "Table values are rounded DOWN, as the source workbook does, so a tabulated area is always "
    "less than or equal to the exact area. The exact area is printed alongside.",
    "Fabric properties are calculated from the published wire diameter and pitch, not read from "
    "a manufacturer's stated area.",
]

LIMITATIONS = [
    "Transcribed from Structural Toolkit REINFORCEMENT V5.00. Independent engineering review of "
    "this transcription has not been completed.",
    "The fabric properties come from the workbook, which cites the OneSteel 'onemesh 500' "
    "publication. They have not been checked against a current manufacturer's catalogue and "
    "mesh products change. Confirm against a current source before specifying.",
    "The prestressing tendon table of the source workbook is NOT transcribed. The review export "
    "captured its column headings only, not the wire, strand and bar property values.",
    "No steel grade, ductility class, mass per metre, development length or detailing rule is "
    "provided here.",
    "The trench mesh areas are per sheet width, not per metre, and the source records only one "
    "wire for L8TM, which is unusual for a trench mesh product and should be confirmed.",
]


def _number(inputs: dict[str, Any], key: str, label: str) -> float:
    if key not in inputs or isinstance(inputs[key], bool) or inputs[key] in (None, ""):
        raise ValueError(f"{label} ({key}) must be supplied as a finite number")
    try:
        value = float(inputs[key])
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} ({key}) must be supplied as a finite number") from exc
    if not math.isfinite(value):
        raise ValueError(f"{label} ({key}) must be finite")
    return value


def _positive(inputs: dict[str, Any], key: str, label: str) -> float:
    value = _number(inputs, key, label)
    if value <= 0:
        raise ValueError(f"{label} ({key}) must be greater than zero")
    return value


def _option(inputs: dict[str, Any], key: str, label: str, permitted: Any) -> str:
    raw = inputs.get(key)
    if raw in (None, "") or isinstance(raw, bool):
        raise ValueError(f"{label} ({key}) must be one of {', '.join(permitted)}")
    value = str(raw).strip()
    folded = {str(item).upper(): item for item in permitted}
    if value.upper() not in folded:
        raise ValueError(f"{label} ({key}) must be one of {', '.join(permitted)}, not '{value}'")
    return folded[value.upper()]


def rounddown(value: float, digits: int) -> float:
    """Excel ROUNDDOWN, which always rounds towards zero at the given precision."""
    factor = 10.0 ** (-digits)
    return math.floor(value / factor + 1e-9) * factor


def bar_area(db: float) -> float:
    """Area of one bar."""
    return math.pi * db ** 2 / 4.0


def fabric_properties(entry: dict[str, Any]) -> dict[str, Any]:
    """Longitudinal and cross wire areas for one fabric designation."""
    if entry["family"] == "Trench":
        area = bar_area(entry["longDia"]) * entry["wires"]
        return {**entry, "longArea": area, "crossArea": None, "perMetre": False}
    return {**entry,
            "longArea": bar_area(entry["longDia"]) * 1000.0 / entry["longCts"],
            "crossArea": bar_area(entry["crossDia"]) * 1000.0 / entry["crossCts"],
            "perMetre": True}


def compute(inputs: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(inputs, dict):
        raise ValueError("An input dictionary is required")

    db = _positive(inputs, "db", "Bar diameter")
    count = _positive(inputs, "count", "Number of bars")
    centres = _positive(inputs, "centres", "Bar centres")
    digits = int(_option(inputs, "rounding", "Rounding", ROUNDINGS))
    mesh = _option(inputs, "mesh", "Fabric designation", FABRIC_BY_NAME)

    single = bar_area(db)
    selected = {
        "db": db,
        "single": single,
        "count": count,
        "countArea": single * count,
        "countAreaRounded": rounddown(single * count, digits),
        "centres": centres,
        "centresArea": single * 1000.0 / centres,
        "centresAreaRounded": rounddown(single * 1000.0 / centres, digits),
    }

    number_table = [
        {"count": n,
         "areas": [rounddown(bar_area(size) * n, digits) for size in BAR_SIZES]}
        for n in BAR_COUNTS
    ]
    centres_table = [
        {"centres": spacing,
         "areas": [rounddown(bar_area(size) * 1000.0 / spacing, digits)
                   for size in BAR_SIZES]}
        for spacing in BAR_CENTRES
    ]
    fabric_table = [fabric_properties(entry) for entry in FABRIC]

    warnings: list[str] = []
    if db not in BAR_SIZES:
        sizes = ", ".join(f"{size:g}" for size in BAR_SIZES)
        warnings.append(f"The bar diameter of {db:g} mm is not a tabulated size ({sizes} mm)")
    if FABRIC_BY_NAME[mesh].get("note"):
        warnings.append(f"{mesh}: {FABRIC_BY_NAME[mesh]['note']}")

    return {
        "module": MODULE_ID,
        "version": VERSION,
        "inputs": {"db": db, "count": count, "centres": centres, "rounding": digits,
                   "mesh": mesh},
        "selected": selected,
        "mesh": fabric_properties(FABRIC_BY_NAME[mesh]),
        "barSizes": list(BAR_SIZES),
        "numberTable": number_table,
        "centresTable": centres_table,
        "fabricTable": fabric_table,
        "checks": {},
        "util": {},
        "worstUtil": 0.0,
        "unattainable": [],
        "warnings": warnings,
        "assumptions": list(ASSUMPTIONS),
        "limitations": list(LIMITATIONS),
    }
