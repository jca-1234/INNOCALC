"""Adapter between InnoCalc Manager and the concrete stair engine."""

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
    "bending": "Bending",
    "minimumSteel": "Minimum reinforcement",
    "ductility": "Section ductility kuo",
    "deflection": "Minimum thickness for total deflection",
    "deflectionIncremental": "Minimum thickness for incremental deflection",
}


def descriptor() -> dict[str, Any]:
    return deepcopy(DESCRIPTOR)


def schema() -> dict[str, Any]:
    return {
        **descriptor(),
        "identity": {"typeLabel": "Member type", "numberLabel": "Member number",
                     "typeOptions": ["Stair", "Flight", "Landing"]},
        "groups": [
            {"id": "geometry", "title": "Geometry", "fields": [
                {"id": "L", "label": "Horizontal span L", "type": "number", "unit": "mm",
                 "default": 3800.0},
                {"id": "W", "label": "Flight width W", "type": "number", "unit": "mm",
                 "default": 1000.0},
                {"id": "th", "label": "Throat thickness th", "type": "number", "unit": "mm",
                 "default": 150.0, "help": "Measured perpendicular to the soffit"},
                {"id": "riser", "label": "Riser", "type": "number", "unit": "mm",
                 "default": 190.0},
                {"id": "going", "label": "Going", "type": "number", "unit": "mm",
                 "default": 250.0},
                {"id": "cover", "label": "Bottom cover", "type": "number", "unit": "mm",
                 "default": 20.0},
                {"id": "spanType", "label": "Span type", "type": "select", "default": "S",
                 "width": "full",
                 "options": [{"value": key, "label": f"{key} - {value['label']} "
                                                     f"(k4 = {value['k4']:g})"}
                             for key, value in engine.SPAN_TYPES.items()]},
            ]},
            {"id": "material", "title": "Materials", "fields": [
                {"id": "fc", "label": "Concrete strength f'c", "type": "number", "unit": "MPa",
                 "default": 32.0, "help": "20 to 120 MPa, Cl 1.1.2"},
                {"id": "conc", "label": "Concrete unit weight", "type": "number", "unit": "kN/m3",
                 "default": 25.0},
                {"id": "density", "label": "Concrete density", "type": "number", "unit": "kg/m3",
                 "default": 2400.0, "help": "Used for the Cl 3.1.2 modulus of elasticity"},
                {"id": "usefcmi", "label": "Use the mean in-situ strength for Ec",
                 "type": "select", "default": "N", "width": "full",
                 "options": [{"value": "N", "label": "N - use f'c"},
                             {"value": "Y", "label": "Y - use the fcmi curve fit"}]},
            ]},
            {"id": "loading", "title": "Loading", "fields": [
                {"id": "wsdl", "label": "Superimposed dead load", "type": "number", "unit": "kPa",
                 "default": 0.0},
                {"id": "wll", "label": "Live load", "type": "number", "unit": "kPa",
                 "default": 4.0},
                {"id": "loadtype", "label": "Live load type", "type": "select", "default": "FLOOR",
                 "options": [{"value": key, "label": f"{value['label']} "
                                                     f"(psi_s {value['psiS']:g}, "
                                                     f"psi_l {value['psiL']:g})"}
                             for key, value in engine.LOAD_TYPES.items()],
                 "help": "AS/NZS 1170.0 Table 4.1"},
            ]},
            {"id": "reinforcement", "title": "Main reinforcement", "fields": [
                {"id": "bar", "label": "Bar size", "type": "select", "default": "16",
                 "options": [{"value": f"{size:g}", "label": f"{size:g} mm"}
                             for size in engine.BAR_SIZES]},
                {"id": "fsy", "label": "Yield strength fsy", "type": "select", "default": "500",
                 "options": [{"value": f"{grade:g}", "label": f"{grade:g} MPa"}
                             for grade in engine.YIELD_STRENGTHS]},
                {"id": "ductilityClass", "label": "Ductility class", "type": "select",
                 "default": "N", "width": "full",
                 "options": [{"value": key, "label": label}
                             for key, label in engine.DUCTILITY_CLASSES.items()]},
                {"id": "reoMode", "label": "Reinforcement entered as", "type": "select",
                 "default": "centres", "width": "full",
                 "options": [{"value": "count", "label": "Total number of bars"},
                             {"value": "centres", "label": "Bar centres (mm)"},
                             {"value": "area", "label": "Steel area (mm2/m)"}]},
                {"id": "reoValue", "label": "Reinforcement quantity", "type": "number",
                 "default": 150.0, "help": "Bars, centres in mm or area in mm2/m to suit the mode"},
                {"id": "useVertM", "label": "Use the vertical depth for bending",
                 "type": "select", "default": "N", "width": "full",
                 "options": [{"value": "N", "label": "N - depth perpendicular to the soffit"},
                             {"value": "Y", "label": "Y - vertical depth, f x ds"}]},
            ]},
            {"id": "deflection", "title": "Deflection, Cl 9.4.4", "fields": [
                {"id": "Asc", "label": "Compression steel area Asc", "type": "number",
                 "unit": "mm2/m", "default": 0.0},
                {"id": "dc", "label": "Depth to the compression steel dc", "type": "number",
                 "unit": "mm", "default": 20.0},
                {"id": "spanOverDeflection", "label": "Span to deflection ratio L/d",
                 "type": "number", "default": 250.0},
                {"id": "spanOverDeflectionIncremental",
                 "label": "Incremental span to deflection ratio", "type": "number",
                 "default": 500.0},
                {"id": "k3", "label": "Deflection constant k3", "type": "number", "default": 1.0,
                 "help": "Table 2.3.2; 1.0 for a one-way member"},
                {"id": "useVertD", "label": "Use the vertical depth for deflection",
                 "type": "select", "default": "Y", "width": "full",
                 "options": [{"value": "Y", "label": "Y - vertical depth"},
                             {"value": "N", "label": "N - divide by f for the throat"}]},
                {"id": "deflectionBasis", "label": "Vertical deflection basis", "type": "select",
                 "default": "L", "width": "full",
                 "options": [{"value": key, "label": label}
                             for key, label in engine.DEFLECTION_BASIS.items()]},
            ]},
        ],
        "optional": [],
        "alwaysOn": {key: True for key in CHECK_LABELS},
        "actions": [],
    }


def defaults() -> dict[str, Any]:
    values: dict[str, Any] = {
        "memberType": "Stair", "memberNumber": "0001", "package": "Unallocated", "level": "",
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
                         if not math.isfinite(value)), "Stair capacity")
        return {"worstUtil": result["worstUtil"], "criticalCheck": critical, "status": "FAIL",
                "headline": f"Capacity unattainable - {critical.lower()}"}
    key = max(util, key=lambda name: util[name])
    ratio = util[key]
    return {"worstUtil": result["worstUtil"], "criticalCheck": CHECK_LABELS[key],
            "status": "OK" if ratio <= 1.0 else "FAIL",
            "headline": f"{ratio * 100:.1f}% - {CHECK_LABELS[key]}"}


def identity(inputs: dict[str, Any]) -> dict[str, Any]:
    member_type = str(inputs.get("memberType") or "Stair")
    number = str(inputs.get("memberNumber") or "")
    size = f"{_plain(inputs.get('L'))} span, {_plain(inputs.get('th'))} throat"
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
