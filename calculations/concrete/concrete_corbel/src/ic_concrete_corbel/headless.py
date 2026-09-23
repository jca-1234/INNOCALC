"""Adapter between InnoCalc Manager and the concrete corbel engine.

Everything here is presentation of the module contract.  Design decisions belong
in :mod:`ic_concrete_corbel.engine` and sheet layout in
:mod:`ic_concrete_corbel.report`.
"""

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
    "bearing": "Bearing at the corbel node",
    "shearFriction": "Shear friction on the vertical face",
    "tensileTie": "Horizontal tensile tie",
    "minimumSteel": "Minimum flexural reinforcement",
    "depthLimit": "Minimum overall depth D >= 1.7 av",
    "wallThickness": "Strut width across the supporting wall",
}


def descriptor() -> dict[str, Any]:
    return deepcopy(DESCRIPTOR)


def schema() -> dict[str, Any]:
    return {
        **descriptor(),
        "identity": {"typeLabel": "Member type", "numberLabel": "Member number",
                     "typeOptions": ["Corbel", "Nib", "Halving joint"]},
        "groups": [
            {"id": "geometry", "title": "Geometry and material", "fields": [
                {"id": "fc", "label": "Concrete strength f'c", "type": "number", "unit": "MPa",
                 "default": 32.0, "help": "20 to 120 MPa, Cl 1.1.2"},
                {"id": "b", "label": "Corbel length b", "type": "number", "unit": "mm",
                 "default": 600.0, "help": "Enter 1000 to design per metre run"},
                {"id": "df", "label": "Corbel depth df", "type": "number", "unit": "mm",
                 "default": 150.0},
                {"id": "D", "label": "Overall depth D", "type": "number", "unit": "mm",
                 "default": 300.0},
                {"id": "av", "label": "Eccentricity av", "type": "number", "unit": "mm",
                 "default": 105.0},
                {"id": "bw", "label": "Bearing strip width bw", "type": "number", "unit": "mm",
                 "default": 30.0},
                {"id": "th", "label": "Supporting wall thickness", "type": "number", "unit": "mm",
                 "default": 150.0},
            ]},
            {"id": "interface", "title": "Shear interface", "fields": [
                {"id": "scond", "label": "Corbel casting condition", "type": "select",
                 "default": "R", "width": "full",
                 "options": [{"value": key, "label": f"{key} - {value['label']}"}
                             for key, value in engine.SURFACE_CONDITIONS.items()]},
                {"id": "mu", "label": "Frictional constant mu", "type": "number", "default": 0.7,
                 "showWhen": {"scond": ["O"]}, "help": "Table 8.4.3, manually assessed"},
                {"id": "kco", "label": "Cohesion coefficient kco", "type": "number", "default": 0.4,
                 "showWhen": {"scond": ["O"]}, "help": "Table 8.4.3, manually assessed"},
            ]},
            {"id": "loading", "title": "Service actions", "fields": [
                {"id": "Vdl", "label": "Vertical dead load Vdl", "type": "number", "unit": "kN",
                 "default": 60.0},
                {"id": "Vll", "label": "Vertical live load Vll", "type": "number", "unit": "kN",
                 "default": 60.0},
                {"id": "Ndl", "label": "Horizontal dead load Ndl", "type": "number", "unit": "kN",
                 "default": 6.0},
                {"id": "Nll", "label": "Horizontal live load Nll", "type": "number", "unit": "kN",
                 "default": 6.0},
                {"id": "loadtype", "label": "Load type", "type": "select", "default": "N",
                 "options": [{"value": "N", "label": "N - Normal"},
                             {"value": "S", "label": "S - Storage"},
                             {"value": "M", "label": "M - Manual factor"}],
                 "help": "AS/NZS 1170.0 Table 4.1 long term factor"},
                {"id": "mlt", "label": "Long term factor psi_l", "type": "number", "default": 1.0,
                 "showWhen": {"loadtype": ["M"]}},
            ]},
            {"id": "reinforcement", "title": "Horizontal tie reinforcement", "fields": [
                {"id": "bar", "label": "Bar size", "type": "select", "default": "12",
                 "options": [{"value": f"{size:g}", "label": f"N{size:g}"}
                             for size in engine.BAR_SIZES]},
                {"id": "fsy", "label": "Yield strength fsy", "type": "select", "default": "500",
                 "options": [{"value": f"{grade:g}", "label": f"{grade:g} MPa"}
                             for grade in engine.YIELD_STRENGTHS]},
                {"id": "reoMode", "label": "Reinforcement entered as", "type": "select",
                 "default": "count", "width": "full",
                 "options": [{"value": "count", "label": "Number of bars"},
                             {"value": "centres", "label": "Bar centres (mm)"},
                             {"value": "area", "label": "Steel area (mm2)"}]},
                {"id": "reoValue", "label": "Reinforcement quantity", "type": "number",
                 "default": 6.0, "help": "Bars, centres in mm or area in mm2 to suit the mode"},
                {"id": "cover", "label": "Cover", "type": "number", "unit": "mm", "default": 40.0},
            ]},
        ],
        "optional": [],
        "alwaysOn": {key: True for key in
                     ("bearing", "shearFriction", "strut", "tensileTie", "minimumSteel",
                      "depthLimit", "wallThickness")},
        "actions": [],
    }


def defaults() -> dict[str, Any]:
    values: dict[str, Any] = {
        "memberType": "Corbel", "memberNumber": "0001", "package": "Unallocated", "level": "",
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
                         if not math.isfinite(value)), "Corbel capacity")
        return {"worstUtil": result["worstUtil"], "criticalCheck": critical, "status": "FAIL",
                "headline": f"Capacity unattainable - {critical.lower()}"}
    key = max(util, key=lambda name: util[name])
    ratio = util[key]
    return {"worstUtil": result["worstUtil"], "criticalCheck": CHECK_LABELS[key],
            "status": "OK" if ratio <= 1.0 else "FAIL",
            "headline": f"{ratio * 100:.1f}% - {CHECK_LABELS[key]}"}


def identity(inputs: dict[str, Any]) -> dict[str, Any]:
    member_type = str(inputs.get("memberType") or "Corbel")
    number = str(inputs.get("memberNumber") or "")
    size = f"{_plain(inputs.get('b'))} x {_plain(inputs.get('D'))}"
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