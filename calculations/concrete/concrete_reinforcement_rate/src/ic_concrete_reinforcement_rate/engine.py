"""Reinforcement rate engine: steel weight per cubic metre of concrete.

Working units are mm for geometry, kg/m3 for density, metres for the running
lengths that the schedule accumulates and kg for weight, matching the source
workbook.  This module performs **no design check** and returns no utilisation.

The design basis is a transcription of the retained Structural Toolkit workbook
``Concrete_Rate_500.xls`` (REINFORCEMENT RATE V5.00, sheet ``Rate``).
"""

from __future__ import annotations

import math
from typing import Any

from .version import VERSION

MODULE_ID = "concrete-reinforcement-rate"

BAR = "B"
LIGATURE = "L"
TRANSVERSE = "T"
ROW_TYPES = {
    BAR: "Bar",
    LIGATURE: "Ligature",
    TRANSVERSE: "Transverse ligature set",
}

# Rate!G14 hook length by ligature diameter.
HOOK_LENGTHS = ((8.0, 150.0), (10.0, 165.0), (12.0, 185.0), (16.0, 225.0), (20.0, 275.0))

MAX_ROWS = 21  # Rate!B24:B44
SPACING_THRESHOLD = 100.0  # Rate!F24, values of 100 or more are read as centres
MAX_TIE_SPACING = 600.0  # Cl 8.3.2.2
LIGATURE_OFFSET = 10.0  # Rate!G16 and G17
TIE_COUNT_OFFSET = 12.0  # Rate!G15

ASSUMPTIONS = [
    "This is a quantity calculation. It reports the weight of reinforcement per cubic metre of "
    "concrete and performs no strength, serviceability or detailing check.",
    "In a schedule row, a number of 100 or more is read as bar centres in millimetres and a "
    "number below 100 is read as a count. The interpretation actually used is printed against "
    "every row.",
    "A bar row spans the member width rb; its count is rb divided by the centres. A ligature or "
    "transverse row is distributed along the entered length; its count is that length divided "
    "by the centres, plus one.",
    "One ligature is the section perimeter reduced by the cover and a 10 mm allowance on each "
    "face, plus two hooks.",
    "The transverse ligature set uses the Cl 8.3.2.2 spacing of the lesser of 600 mm and the "
    "member depth.",
]

LIMITATIONS = [
    "Transcribed from Structural Toolkit REINFORCEMENT RATE V5.00. Independent engineering "
    "review of this transcription has not been completed.",
    "LAPS AND LIGATURE COGS ARE EXCLUDED, as they are in the source workbook. The rate is "
    "therefore not a complete estimating quantity.",
    "Wastage, chairs, spacers, tie wire, couplers, starter bars and any bar that leaves the "
    "member are excluded.",
    "The workbook's three template macros for a one-way slab, a two-way slab and a band beam "
    "copy schedules from Settings sheet ranges whose contents were not captured in the review "
    "export, so those templates are not provided.",
    "The workbook's rows 48 to 54 hold a superseded schedule template with a hard coded steel "
    "density of 7850 kg/m3 and a reference to an undefined name. They are dead and are not "
    "transcribed.",
    "The schedule is limited to 21 rows, the number of rows the source workbook provides.",
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


def _non_negative(inputs: dict[str, Any], key: str, label: str) -> float:
    value = _number(inputs, key, label)
    if value < 0:
        raise ValueError(f"{label} ({key}) must be zero or greater")
    return value


def hook_length(ligature_size: float) -> float:
    """Rate!G14 hook length lookup; zero above the largest tabulated diameter."""
    for size, length in HOOK_LENGTHS:
        if ligature_size <= size:
            return length
    return 0.0


def parse_schedule(text: Any) -> list[dict[str, Any]]:
    """Read the schedule text into rows of type, quantity, size, length and description.

    One row per line: ``type, number or centres, bar size, length, description``.
    Blank lines and lines beginning with ``#`` are ignored.
    """
    if text is None:
        return []
    if not isinstance(text, str):
        raise ValueError("The reinforcement schedule must be supplied as text")
    rows: list[dict[str, Any]] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split(",", 4)]
        if len(parts) < 4:
            raise ValueError(
                f"Schedule line {number}: expected 'type, number or centres, size, length"
                f"[, description]', got '{line}'")
        kind = parts[0].upper()
        if kind not in ROW_TYPES:
            raise ValueError(
                f"Schedule line {number}: type must be B, L or T, not '{parts[0]}'")
        values: list[float] = []
        for label, text_value in zip(("number or centres", "size", "length"), parts[1:4]):
            try:
                value = float(text_value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Schedule line {number}: {label} must be a number, not "
                    f"'{text_value}'") from exc
            if not math.isfinite(value) or value < 0:
                raise ValueError(
                    f"Schedule line {number}: {label} must be a finite value of zero or more")
            values.append(value)
        quantity, size, length = values
        if size <= 0:
            raise ValueError(f"Schedule line {number}: the bar size must be greater than zero")
        if quantity > 0 and kind in (LIGATURE, TRANSVERSE) and length <= 0:
            raise ValueError(
                f"Schedule line {number}: a ligature row needs a length to distribute over")
        rows.append({"line": number, "type": kind, "quantity": quantity, "size": size,
                     "length": length,
                     "description": parts[4].strip() if len(parts) > 4 else ""})
        if len(rows) > MAX_ROWS:
            raise ValueError(
                f"The schedule is limited to {MAX_ROWS} rows, the number the source workbook "
                "provides")
    return rows


def compute(inputs: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(inputs, dict):
        raise ValueError("An input dictionary is required")

    # -- Member, Rate sheet rows 10 to 17 ------------------------------------
    L = _positive(inputs, "L", "Length")
    rb = _positive(inputs, "rb", "Width")
    rd = _positive(inputs, "rd", "Depth")
    cover = _non_negative(inputs, "cover", "Cover")
    ligs = _positive(inputs, "ligs", "Ligature size")
    density = _positive(inputs, "density", "Reinforcement density")

    area = rb * rd / 1e6
    volume = area * L / 1000.0
    hook = hook_length(ligs)
    ties = math.ceil((rb - 2.0 * cover - TIE_COUNT_OFFSET) / min(MAX_TIE_SPACING, rd)) + 1 - 2
    ligature = max(0.0, (2.0 * (rb - 2.0 * cover - LIGATURE_OFFSET)
                         + 2.0 * (rd - 2.0 * cover - LIGATURE_OFFSET)
                         + 2.0 * hook) / 1000.0)
    tie_set = ties * (rd - cover - LIGATURE_OFFSET + 2.0 * hook) / 1000.0

    # -- Schedule, Rate sheet rows 24 to 44 ----------------------------------
    rows: list[dict[str, Any]] = []
    total_weight = 0.0
    total_length = 0.0
    for row in parse_schedule(inputs.get("schedule")):
        kind, quantity = row["type"], row["quantity"]
        if quantity == 0:
            count = 0.0
            reading = "ignored, the number or centres is zero"
        elif kind in (LIGATURE, TRANSVERSE):
            count = row["length"] / quantity + 1.0
            reading = f"{quantity:g} mm centres over {row['length']:g} mm"
        elif quantity >= SPACING_THRESHOLD:
            count = rb / quantity
            reading = f"{quantity:g} mm centres across the {rb:g} mm width"
        else:
            count = quantity
            reading = f"a count of {quantity:g}"

        if kind == LIGATURE:
            length = count * ligature
        elif kind == TRANSVERSE:
            length = count * (tie_set + ligature)
        else:
            length = count * row["length"] / 1000.0

        weight = density * math.pi * (row["size"] / 1000.0) ** 2 / 4.0 * length
        if count and (kind in (LIGATURE, TRANSVERSE) or quantity >= SPACING_THRESHOLD):
            mark = f"N{row['size']:.0f}-{quantity:.0f}"
        elif count:
            mark = f"{quantity:.0f}-N{row['size']:.0f}"
        else:
            mark = ""
        if mark:
            mark += {LIGATURE: " L", TRANSVERSE: " L*"}.get(kind, "")
        total_weight += weight
        total_length += length
        rows.append({**row, "count": count, "reading": reading, "totalLength": length,
                     "weight": weight, "mark": mark, "label": ROW_TYPES[kind]})

    rate = total_weight / volume if volume else 0.0

    warnings: list[str] = []
    if not rows:
        warnings.append("The reinforcement schedule is empty, so the rate is zero")
    if hook == 0.0:
        warnings.append(
            f"The ligature size of {ligs:g} mm is above the largest tabulated diameter of "
            "20 mm, so the hook length is taken as zero")
    if ties <= 0:
        warnings.append(
            "The member width leaves no transverse ligature set; check the width, cover and "
            "depth")

    return {
        "module": MODULE_ID,
        "version": VERSION,
        "inputs": {"L": L, "rb": rb, "rd": rd, "cover": cover, "ligs": ligs,
                   "density": density, "title": str(inputs.get("title") or "")},
        "member": {"L": L, "rb": rb, "rd": rd, "cover": cover, "ligs": ligs,
                   "area": area, "volume": volume, "hook": hook, "ties": ties,
                   "ligature": ligature, "tieSet": tie_set, "density": density},
        "schedule": rows,
        "totals": {"weight": total_weight, "length": total_length, "rate": rate,
                   "rows": len(rows)},
        "checks": {},
        "util": {},
        "worstUtil": 0.0,
        "unattainable": [],
        "warnings": warnings,
        "assumptions": list(ASSUMPTIONS),
        "limitations": list(LIMITATIONS),
    }
