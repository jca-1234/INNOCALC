"""Adapter between InnoCalc Manager and the deep beam engine."""

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
    "diagonalCompression": "Diagonal compressive stress",
    "externalSupport": "External support zone bearing",
    "internalSupport": "Internal support zone bearing",
    "spanDepthLimit": "CEB span to depth limit",
    "supportWidthLimit": "Support width limit c <= L/5",
}


def descriptor() -> dict[str, Any]:
    return deepcopy(DESCRIPTOR)


def schema() -> dict[str, Any]:
    return {
        **descriptor(),
        "identity": {"typeLabel": "Member type", "numberLabel": "Member number",
                     "typeOptions": ["Deep beam", "Transfer beam", "Wall beam"]},
        "groups": [
            {"id": "geometry", "title": "Geometry", "fields": [
                {"id": "spanType", "label": "Span type", "type": "select", "default": "S",
                 "width": "full",
                 "options": [{"value": key, "label": f"{key} - {value['label']} "
                                                     f"(L/D limit {value['ldLimit']:g})"}
                             for key, value in engine.SPAN_TYPES.items()]},
                {"id": "L", "label": "Span or cantilever length L", "type": "number",
                 "unit": "mm", "default": 8000.0},
                {"id": "D", "label": "Depth D", "type": "number", "unit": "mm",
                 "default": 4000.0},
                {"id": "bw", "label": "Thickness bw", "type": "number", "unit": "mm",
                 "default": 300.0},
                {"id": "support", "label": "Support width c", "type": "number", "unit": "mm",
                 "default": 500.0, "help": "Must not exceed L/5"},
                {"id": "Df", "label": "Depth of slab Df", "type": "number", "unit": "mm",
                 "default": 0.0, "help": "Zero when there is no slab stiffening the support"},
            ]},
            {"id": "material", "title": "Materials", "fields": [
                {"id": "fc", "label": "Concrete strength f'c", "type": "number", "unit": "MPa",
                 "default": 32.0, "help": "20 to 120 MPa, Cl 1.1.2"},
                {"id": "fsy", "label": "Yield strength fsy", "type": "select", "default": "500",
                 "options": [{"value": f"{grade:g}", "label": f"{grade:g} MPa"}
                             for grade in engine.YIELD_STRENGTHS]},
                {"id": "bar", "label": "Additional bar size", "type": "select", "default": "20",
                 "options": [{"value": f"{size:g}", "label": f"N{size:g}"}
                             for size in engine.BAR_SIZES]},
                {"id": "mesh", "label": "Panel mesh wire diameter", "type": "number",
                 "unit": "mm", "default": 10.0,
                 "help": "Standard wires are 6.75, 7.6, 8.55, 9.5, 10.65, 11.9 and 12 mm"},
                {"id": "gs", "label": "Material safety factor gamma_s", "type": "number",
                 "default": 1.15},
                {"id": "gc", "label": "Material safety factor gamma_c", "type": "number",
                 "default": 1.5},
            ]},
            {"id": "serviceability", "title": "Crack control", "fields": [
                {"id": "crack", "label": "Crack control", "type": "select", "default": "W",
                 "width": "full",
                 "options": [{"value": key, "label": f"{key} - {value['label']}"
                                                     + (f" ({value['fsi']:g} MPa)"
                                                        if value["fsi"] else "")}
                             for key, value in engine.CRACK_CLASSES.items()]},
                {"id": "fsic", "label": "Custom serviceability stress fsi", "type": "number",
                 "unit": "MPa", "default": 350.0, "showWhen": {"crack": ["C"]}},
            ]},
            {"id": "actions", "title": "Design actions", "fields": [
                {"id": "Mstar", "label": "Design positive moment Mp*", "type": "number",
                 "unit": "kNm", "default": 1670.0},
                {"id": "Mstarn", "label": "Design negative moment Mn*", "type": "number",
                 "unit": "kNm", "default": 0.0},
                {"id": "Vstar", "label": "Design shear V*", "type": "number", "unit": "kN",
                 "default": 900.0},
                {"id": "Rstar", "label": "Design reaction R*", "type": "number", "unit": "kN",
                 "default": 900.0},
                {"id": "reodiste", "label": "Positive steel fraction in the outer 0.2 D",
                 "type": "number", "default": 1.0, "help": "Between 0 and 1"},
            ]},
            {"id": "indicative", "title": "Indicative actions only", "fields": [
                {"id": "Pstar", "label": "Point load P*", "type": "number", "unit": "kN",
                 "default": 1000.0,
                 "help": "Prints an indicative moment and shear; does not drive the design"},
                {"id": "wstar", "label": "Uniform load w*", "type": "number", "unit": "kN/m",
                 "default": 100.0,
                 "help": "Prints an indicative moment and shear; does not drive the design"},
            ]},
        ],
        "optional": [],
        "alwaysOn": {"diagonalCompression": True, "spanDepthLimit": True,
                     "supportWidthLimit": True},
        "actions": [],
    }


def defaults() -> dict[str, Any]:
    values: dict[str, Any] = {
        "memberType": "Deep beam", "memberNumber": "0001", "package": "Unallocated", "level": "",
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
                         if not math.isfinite(value)), "Deep beam capacity")
        return {"worstUtil": result["worstUtil"], "criticalCheck": critical, "status": "FAIL",
                "headline": f"Capacity unattainable - {critical.lower()}"}
    key = max(util, key=lambda name: util[name])
    ratio = util[key]
    return {"worstUtil": result["worstUtil"], "criticalCheck": CHECK_LABELS[key],
            "status": "OK" if ratio <= 1.0 else "FAIL",
            "headline": f"Superseded CEB method: {ratio * 100:.1f}% - {CHECK_LABELS[key]}"}


def identity(inputs: dict[str, Any]) -> dict[str, Any]:
    member_type = str(inputs.get("memberType") or "Deep beam")
    number = str(inputs.get("memberNumber") or "")
    size = f"{_plain(inputs.get('L'))} x {_plain(inputs.get('D'))}"
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
