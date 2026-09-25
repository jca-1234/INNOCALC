"""Adapter between InnoCalc Manager and the two-way slab engine."""

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
    "deflectionTotal": "Deemed-to-comply depth, total deflection",
    "deflectionIncremental": "Deemed-to-comply depth, incremental deflection",
    "minimumSteel": "Minimum strength reinforcement",
    "liveLoadLimit": "Live load not exceeding dead load",
    "flexure": "Flexural capacity",
    "ductility": "Ductility ku <= 0.36",
    "flexuralMinimum": "Minimum reinforcement at each location",
    "barSpacing": "Maximum bar spacing",
    "shrinkage": "Shrinkage and temperature reinforcement",
}
ALWAYS_ON = ("deflectionTotal", "deflectionIncremental", "minimumSteel", "liveLoadLimit")


def _layer_fields(key: str, label: str, bar: str, spacing: float) -> list[dict[str, Any]]:
    return [
        {"id": f"bar{key}", "label": f"{label} bar", "type": "select", "default": bar,
         "options": [{"value": f"{size:g}", "label": f"{size:g} mm"} for size in engine.BAR_SIZES]},
        {"id": f"s{key}", "label": f"{label} spacing", "type": "number", "unit": "mm",
         "default": spacing},
    ]

YES_NO = [{"value": "Y", "label": "Yes"}, {"value": "N", "label": "No"}]
EDGES = [{"value": "0", "label": "0"}, {"value": "1", "label": "1"}, {"value": "2", "label": "2"}]


def descriptor() -> dict[str, Any]:
    return deepcopy(DESCRIPTOR)


def schema() -> dict[str, Any]:
    return {
        **descriptor(),
        "identity": {"typeLabel": "Member type", "numberLabel": "Member number",
                     "typeOptions": ["Slab", "Slab panel", "Transfer slab"]},
        "groups": [
            {"id": "geometry", "title": "Geometry and material", "fields": [
                {"id": "fc", "label": "Concrete strength f'c", "type": "number", "unit": "MPa",
                 "default": 25.0, "help": "20 to 120 MPa, Cl 1.1.2"},
                {"id": "th", "label": "Slab thickness th", "type": "number", "unit": "mm",
                 "default": 150.0},
                {"id": "Ly", "label": "Long edge length Ly", "type": "number", "unit": "mm",
                 "default": 7000.0, "help": "Effective span"},
                {"id": "Lx", "label": "Short edge length Lx", "type": "number", "unit": "mm",
                 "default": 6000.0, "help": "Effective span; also Lef for deflection"},
                {"id": "contLong", "label": "Continuous long edges", "type": "select",
                 "default": "0", "options": EDGES},
                {"id": "contShort", "label": "Continuous short edges", "type": "select",
                 "default": "0", "options": EDGES},
                {"id": "reo", "label": "Reinforcement ductility class", "type": "select",
                 "default": "L", "options": [{"value": "N", "label": "N - Normal"},
                                             {"value": "L", "label": "L - Low"}]},
                {"id": "redist", "label": "Allow moment redistribution", "type": "select",
                 "default": "Y", "options": YES_NO},
                {"id": "useFormula", "label": "Use closed-form coefficients", "type": "select",
                 "default": "N", "options": YES_NO,
                 "help": "Class N with redistribution only (Warner, Rangan and Hall)"},
            ]},
            {"id": "loading", "title": "Service actions", "fields": [
                {"id": "includeSW", "label": "Include self weight", "type": "select",
                 "default": "Y", "options": YES_NO},
                {"id": "wsdl", "label": "Superimposed dead load wsdl", "type": "number",
                 "unit": "kPa", "default": 0.0,
                 "help": "Total dead load when self weight is excluded"},
                {"id": "wll", "label": "Live load wll", "type": "number", "unit": "kPa",
                 "default": 3.0},
                {"id": "loadType", "label": "Live load type", "type": "select", "default": "N",
                 "options": [{"value": key, "label": f"{key} - {label}"}
                             for key, label in engine.LOAD_TYPES.items()],
                 "help": "AS/NZS 1170.0 Table 4.1"},
            ]},
            {"id": "serviceability", "title": "Reinforcement and deflection", "fields": [
                {"id": "Ast", "label": "Tensile steel Ast", "type": "number", "unit": "mm2/m",
                 "default": 454.0, "help": "Bottom steel in the positive moment region"},
                {"id": "fsy", "label": "Yield strength fsy", "type": "select", "default": "500",
                 "options": [{"value": f"{grade:g}", "label": f"{grade:g} MPa"}
                             for grade in engine.YIELD_STRENGTHS]},
                {"id": "cover", "label": "Cover to bottom steel", "type": "number", "unit": "mm",
                 "default": 25.0},
                {"id": "dia", "label": "Bar size", "type": "select", "default": "12",
                 "options": [{"value": f"{size:g}", "label": f"{size:g} mm"}
                             for size in engine.BAR_SIZES]},
                {"id": "Asc", "label": "Compression steel Asc", "type": "number", "unit": "mm2/m",
                 "default": 0.0},
                {"id": "dc", "label": "Depth to compression steel dc", "type": "number",
                 "unit": "mm", "default": 30.0, "help": "Measured from the top face"},
                {"id": "useFcmi", "label": "Use fcmi for Ec", "type": "select", "default": "N",
                 "options": YES_NO, "help": "No uses fcmi = f'c"},
                {"id": "density", "label": "Concrete density", "type": "number", "unit": "kg/m3",
                 "default": 2400.0, "help": "Cl 3.1.3"},
                {"id": "lefDelta", "label": "Total deflection limit Lef/Delta", "type": "number",
                 "default": 300.0, "help": "Table 2.3.2"},
                {"id": "lefDeltaInc", "label": "Incremental deflection limit Lef/Delta",
                 "type": "number", "default": 500.0, "help": "Table 2.3.2"},
            ]},
        ],
        "optional": [
            {"id": "flexure", "label": "Flexural capacity at each location", "fields": [
                {"id": "coverTop", "label": "Cover to top steel", "type": "number", "unit": "mm",
                 "default": 25.0},
                *_layer_fields("Xb", "Short span bottom (outer)", "12", 200.0),
                *_layer_fields("Yb", "Long span bottom (inner)", "12", 250.0),
                *_layer_fields("Xtc", "Short span top, continuous edge", "12", 150.0),
                *_layer_fields("Xtd", "Short span top, discontinuous edge", "12", 300.0),
                *_layer_fields("Ytc", "Long span top, continuous edge", "12", 200.0),
                *_layer_fields("Ytd", "Long span top, discontinuous edge", "12", 300.0),
            ]},
            {"id": "shrinkage", "label": "Shrinkage and temperature (Cl 9.4.3)", "fields": [
                {"id": "restraint", "label": "Degree of restraint", "type": "select",
                 "default": "MODERATE",
                 "options": [{"value": key, "label": label}
                             for key, label in engine.SHRINKAGE_LABELS.items()]},
            ]},
        ],
        "alwaysOn": {key: True for key in ALWAYS_ON},
        "actions": [],
    }


def defaults() -> dict[str, Any]:
    values: dict[str, Any] = {
        "memberType": "Slab", "memberNumber": "SL01", "package": "Unallocated", "level": "",
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
    size = f"{_plain(inputs.get('Ly'))} x {_plain(inputs.get('Lx'))} x {_plain(inputs.get('th'))}"
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
