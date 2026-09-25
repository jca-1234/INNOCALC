"""Adapter between InnoCalc Manager and the punching shear engine."""

from __future__ import annotations

import math
import tomllib
from copy import deepcopy
from importlib.resources import files
from typing import Any

from . import engine, report
from .version import VERSION

DESCRIPTOR = {**tomllib.loads(files(__package__).joinpath("module.toml").read_text(encoding="utf-8")),
              "version": VERSION}

CHECK_LABELS = {
    "punching": "Punching shear strength",
    "fitmentArea": "Minimum closed fitment area",
    "fitmentSpacing": "Maximum closed fitment spacing",
    "fitmentWidth": "Closed fitment width within a",
    "prestressDepth": "do not less than 0.8 Ds (prestressed)",
    "integrity": "Integrity reinforcement",
}
ALWAYS_ON = ("punching",)

YES_NO = [{"value": "Y", "label": "Yes"}, {"value": "N", "label": "No"}]
L_W = [{"value": "L", "label": "L - Length"}, {"value": "W", "label": "W - Width"}]


def _sizes(values: tuple[float, ...], none_label: str = "") -> list[dict[str, str]]:
    return [{"value": f"{size:g}", "label": none_label if size == 0 and none_label else f"{size:g} mm"}
            for size in values]


def _grades() -> list[dict[str, str]]:
    return [{"value": f"{grade:g}", "label": f"{grade:g} MPa"} for grade in engine.YIELD_STRENGTHS]


def descriptor() -> dict[str, Any]:
    return deepcopy(DESCRIPTOR)


def schema() -> dict[str, Any]:
    return {
        **descriptor(),
        "identity": {"typeLabel": "Member type", "numberLabel": "Member number",
                     "typeOptions": ["Slab", "Flat slab", "Band beam", "Footing"]},
        "groups": [
            {"id": "geometry", "title": "Slab and column", "fields": [
                {"id": "fc", "label": "Concrete strength f'c", "type": "number", "unit": "MPa",
                 "default": 32.0, "help": "20 to 120 MPa, Cl 1.1.2"},
                {"id": "Ds", "label": "Slab depth Ds", "type": "number", "unit": "mm",
                 "default": 200.0},
                {"id": "dom", "label": "Slab distance do", "type": "number", "unit": "mm",
                 "default": 167.0,
                 "help": "Mean depth to the outermost tensile layer, Cl 9.3.1.4; at least 20 mm"},
                {"id": "col", "label": "Circular column", "type": "select", "default": "N",
                 "options": YES_NO},
                {"id": "pL", "label": "Larger column dimension L (or diameter)", "type": "number",
                 "unit": "mm", "default": 600.0},
                {"id": "pW", "label": "Shorter column dimension W", "type": "number",
                 "unit": "mm", "default": 400.0, "showWhen": {"col": ["N"]}},
                {"id": "pPos", "label": "Position", "type": "select", "default": "I",
                 "options": [{"value": key, "label": f"{key} - {title}"}
                             for key, title in engine.POSITION_TITLES.items()]},
                {"id": "pface", "label": "Face on edge (parallel with spandrel at a corner)",
                 "type": "select", "default": "W", "options": L_W,
                 "showWhen": {"pPos": ["E", "C"], "col": ["N"]}},
                {"id": "spanbothsides", "label": "Spandrel both sides of corner", "type": "select",
                 "default": "Y", "options": YES_NO, "showWhen": {"pPos": ["C"]}},
                {"id": "ineffU", "label": "Ineffective portion of perimeter", "type": "number",
                 "unit": "mm", "default": 0.0, "help": "Critical openings, Fig 9.3(A)"},
            ]},
            {"id": "actions", "title": "Design actions", "fields": [
                {"id": "Vstar", "label": "Design shear V*", "type": "number", "unit": "kN",
                 "default": 500.0},
                {"id": "Mvstar", "label": "Moment transferred Mv*", "type": "number",
                 "unit": "kNm", "default": 25.0, "help": "Magnitude, in the direction of a"},
                {"id": "pmDir", "label": "Direction of moment", "type": "select", "default": "L",
                 "options": L_W},
                {"id": "ps", "label": "Average prestress sigma.cp", "type": "number",
                 "unit": "MPa", "default": 0.0},
                {"id": "shearhead", "label": "Shear head", "type": "select", "default": "N",
                 "options": YES_NO},
            ]},
            {"id": "spandrel", "title": "Spandrel beam", "fields": [
                {"id": "span", "label": "Spandrel beam", "type": "select", "default": "N",
                 "options": YES_NO},
                {"id": "ignorespan", "label": "Ignore spandrel for dom", "type": "select",
                 "default": "Y", "options": YES_NO, "showWhen": {"span": ["Y"]}},
                {"id": "Db", "label": "Spandrel depth Db", "type": "number", "unit": "mm",
                 "default": 500.0},
                {"id": "bw", "label": "Width of spandrel bw", "type": "number", "unit": "mm",
                 "default": 400.0},
            ]},
            {"id": "fitments", "title": "Closed fitments", "fields": [
                {"id": "dialp", "label": "Fitment bar size", "type": "select", "default": "12",
                 "options": _sizes(engine.TIE_SIZES, "None")},
                {"id": "ctsp", "label": "Fitment spacing s", "type": "number", "unit": "mm",
                 "default": 200.0},
                {"id": "fyp", "label": "Fitment yield strength fsy.f", "type": "select",
                 "default": "500", "options": _grades()},
                {"id": "cover", "label": "Cover for y1", "type": "number", "unit": "mm",
                 "default": 25.0},
                {"id": "wcl", "label": "Width of closed fitment (O/A)", "type": "number",
                 "unit": "mm", "default": 767.0, "help": "Torsion strip only; not more than a"},
            ]},
            {"id": "integrity", "title": "Integrity reinforcement", "fields": [
                {"id": "Nstar", "label": "Column reaction from floor slab N*", "type": "number",
                 "unit": "kN", "default": 500.0},
                {"id": "fsy", "label": "Bar yield strength fsy", "type": "select", "default": "500",
                 "options": _grades()},
                {"id": "ductility", "label": "Ductility class", "type": "select", "default": "N",
                 "options": [{"value": "N", "label": "N - Normal"},
                             {"value": "L", "label": "L - Low"}]},
                {"id": "ibar", "label": "Bar size", "type": "select", "default": "16",
                 "options": _sizes(engine.BAR_SIZES)},
                {"id": "nIntegrity", "label": "Bottom bars through the column", "type": "number",
                 "default": 16.0, "help": "Total continuous bottom bars provided"},
                {"id": "beams", "label": "Beams with shear reinforcement and 2 continuous bars "
                 "in all spans", "type": "select", "default": "N", "options": YES_NO},
            ]},
            {"id": "transfer", "title": "Moment transfer, Cl 6.10.4.5", "fields": [
                {"id": "simplifiedMethod", "label": "Slab designed by the simplified method",
                 "type": "select", "default": "N", "options": YES_NO,
                 "help": "Yes applies the minimum Mv* at interior supports"},
                {"id": "pLo", "label": "Larger adjoining span Lo", "type": "number", "unit": "mm",
                 "default": 6350.0},
                {"id": "pLod", "label": "Smaller adjoining span Lo'", "type": "number",
                 "unit": "mm", "default": 5850.0},
                {"id": "pLt", "label": "Design strip width Lt", "type": "number", "unit": "mm",
                 "default": 6000.0},
                {"id": "Vdl", "label": "Dead load G", "type": "number", "unit": "kPa",
                 "default": 6.0},
                {"id": "Vll", "label": "Live load Q", "type": "number", "unit": "kPa",
                 "default": 4.0},
            ]},
        ],
        "optional": [
            {"id": "effectiveDepth", "label": "Mean depth dom from two bar layers", "fields": [
                {"id": "domCover", "label": "Cover to tension reinforcement", "type": "number",
                 "unit": "mm", "default": 25.0},
                {"id": "barOuter", "label": "Outer layer bar size", "type": "select",
                 "default": "16", "options": _sizes(engine.BAR_SIZES)},
                {"id": "barInner", "label": "Inner layer bar size", "type": "select",
                 "default": "16", "options": _sizes(engine.BAR_SIZES)},
            ]},
        ],
        "alwaysOn": {key: True for key in ALWAYS_ON},
        "actions": [],
    }


def defaults() -> dict[str, Any]:
    values: dict[str, Any] = {
        "memberType": "Slab", "memberNumber": "PS01", "package": "Unallocated", "level": "",
        "subject": DESCRIPTOR["defaultSubject"],
        "checks": dict(schema()["alwaysOn"]),
    }
    layout = schema()
    for group in layout["groups"]:
        for field in group["fields"]:
            values[field["id"]] = field["default"]
    for option in layout["optional"]:
        values["checks"][option["id"]] = False
        for field in option["fields"]:
            values[field["id"]] = field["default"]
    return values


def compute(inputs: dict[str, Any]) -> dict[str, Any]:
    return engine.compute(inputs)


def render(inputs: dict[str, Any], result: dict[str, Any], *, standalone: bool = False,
           appendix: list[str] | None = None, anchor_prefix: str = "",
           contents_href: str = "") -> str:
    return report.render(inputs, result, standalone=standalone, appendix=appendix,
                         anchor_prefix=anchor_prefix, contents_href=contents_href)


def summarise(result: dict[str, Any]) -> dict[str, Any]:
    util = result["util"]
    key = max(util, key=lambda name: util[name])
    ratio = util[key]
    status = "OK" if math.isfinite(ratio) and ratio <= 1.0 else "FAIL"
    return {"worstUtil": result["worstUtil"], "criticalCheck": CHECK_LABELS[key],
            "status": status, "headline": f"{ratio * 100:.1f}% - {CHECK_LABELS[key]}"
            if math.isfinite(ratio) else f"Unattainable - {CHECK_LABELS[key]}"}


def identity(inputs: dict[str, Any]) -> dict[str, Any]:
    member_type = str(inputs.get("memberType") or "Slab")
    number = str(inputs.get("memberNumber") or "")
    circular = str(inputs.get("col") or "").strip().upper() == "Y"
    column = (f"D{_plain(inputs.get('pL'))}" if circular
              else f"{_plain(inputs.get('pL'))} x {_plain(inputs.get('pW'))}")
    size = f"{column} column, Ds {_plain(inputs.get('Ds'))}"
    return {"memberType": member_type, "memberNumber": number,
            "package": str(inputs.get("package") or "Unallocated"),
            "level": str(inputs.get("level") or ""), "calcType": DESCRIPTOR["calcType"],
            "title": f"{member_type} {number} - {size}".strip()}


def _plain(value: Any) -> str:
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return "?"


def validate(cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    from .validation import validate as run_validation
    return run_validation(cases)
