"""Adapter between InnoCalc Manager and the plain concrete engine."""

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
    "bending": "Footing bending",
    "oneWayShear": "Footing one-way shear",
    "punchingShear": "Footing two-way punching shear",
    "pedestalCompression": "Pedestal compressive stress",
    "pedestalTension": "Pedestal tensile stress",
    "minimumDepth": "Minimum nominal depth",
}


def descriptor() -> dict[str, Any]:
    return deepcopy(DESCRIPTOR)


def schema() -> dict[str, Any]:
    return {
        **descriptor(),
        "identity": {"typeLabel": "Member type", "numberLabel": "Member number",
                     "typeOptions": ["Footing", "Pedestal", "Pad"]},
        "groups": [
            {"id": "footing", "title": "Footing geometry and material", "fields": [
                {"id": "fc", "label": "Concrete strength f'c", "type": "number", "unit": "MPa",
                 "default": 32.0, "help": "20 to 120 MPa, Cl 1.1.2"},
                {"id": "Dt", "label": "Nominal depth Dt", "type": "number", "unit": "mm",
                 "default": 400.0, "help": "200 mm minimum, Cl 20.4.1. Design depth D = Dt - 50"},
                {"id": "B", "label": "Breadth b", "type": "number", "unit": "mm",
                 "default": 1000.0},
            ]},
            {"id": "punching", "title": "Punching shear", "fields": [
                {"id": "L", "label": "Column length L", "type": "number", "unit": "mm",
                 "default": 300.0},
                {"id": "W", "label": "Column width W", "type": "number", "unit": "mm",
                 "default": 300.0},
                {"id": "uMode", "label": "Shear perimeter", "type": "select",
                 "default": "calculated", "width": "full",
                 "options": [{"value": "calculated", "label": "Calculated from aL and aW"},
                             {"value": "manual", "label": "Manually entered"}],
                 "help": "Use a manual perimeter for edge, corner or interrupted perimeters"},
                {"id": "um", "label": "Manual perimeter u", "type": "number", "unit": "mm",
                 "default": 1000.0, "showWhen": {"uMode": ["manual"]}},
                {"id": "Dir", "label": "Moment direction", "type": "select", "default": "L",
                 "options": [{"value": "L", "label": "L - parallel to the column length"},
                             {"value": "W", "label": "W - parallel to the column width"}],
                 "help": "Selects aL or aW in Eq 20.4.3(2)"},
            ]},
            {"id": "footingActions", "title": "Footing design actions", "fields": [
                {"id": "Mstar", "label": "Design moment M*", "type": "number", "unit": "kNm",
                 "default": 0.0},
                {"id": "Vstar", "label": "Design shear V*", "type": "number", "unit": "kN",
                 "default": 0.0},
            ]},
            {"id": "pedestal", "title": "Unreinforced pedestal", "fields": [
                {"id": "Lpx", "label": "Plan length Lpx", "type": "number", "unit": "mm",
                 "default": 400.0},
                {"id": "Wpy", "label": "Plan width Wpy", "type": "number", "unit": "mm",
                 "default": 400.0},
                {"id": "Pstar", "label": "Ultimate reaction P*", "type": "number", "unit": "kN",
                 "default": 500.0, "help": "Positive in compression"},
                {"id": "Mxstar", "label": "Applied moment Mx*", "type": "number", "unit": "kNm",
                 "default": 0.0},
                {"id": "Mystar", "label": "Applied moment My*", "type": "number", "unit": "kNm",
                 "default": 0.0},
                {"id": "eccx", "label": "Eccentricity eccx", "type": "number", "unit": "mm",
                 "default": 0.0},
                {"id": "eccy", "label": "Eccentricity eccy", "type": "number", "unit": "mm",
                 "default": 0.0},
                {"id": "ignoreEcc", "label": "Ignore minimum eccentricity", "type": "select",
                 "default": "N", "width": "full",
                 "options": [{"value": "N", "label": "N - apply Cl 20.3 minimum eccentricity"},
                             {"value": "Y", "label": "Y - override, minimum eccentricity ignored"}]},
            ]},
        ],
        "optional": [],
        "alwaysOn": {key: True for key in CHECK_LABELS},
        "actions": [],
    }


def defaults() -> dict[str, Any]:
    values: dict[str, Any] = {
        "memberType": "Footing", "memberNumber": "0001", "package": "Unallocated", "level": "",
        "subject": DESCRIPTOR["defaultSubject"],
        "checks": dict(schema()["alwaysOn"]),
    }
    for group in schema()["groups"]:
        for field in group["fields"]:
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
    unattainable = result.get("unattainable") or []
    if unattainable:
        critical = next((CHECK_LABELS[key] for key, value in util.items()
                         if not math.isfinite(value)), "Plain concrete capacity")
        return {"worstUtil": result["worstUtil"], "criticalCheck": critical, "status": "FAIL",
                "headline": f"Capacity unattainable - {critical.lower()}"}
    key = max(util, key=lambda name: util[name])
    ratio = util[key]
    return {"worstUtil": result["worstUtil"], "criticalCheck": CHECK_LABELS[key],
            "status": "OK" if ratio <= 1.0 else "FAIL",
            "headline": f"{ratio * 100:.1f}% - {CHECK_LABELS[key]}"}


def identity(inputs: dict[str, Any]) -> dict[str, Any]:
    member_type = str(inputs.get("memberType") or "Footing")
    number = str(inputs.get("memberNumber") or "")
    size = f"{_plain(inputs.get('Lpx'))} x {_plain(inputs.get('Wpy'))}"
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
