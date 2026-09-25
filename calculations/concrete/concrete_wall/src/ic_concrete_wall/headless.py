"""Adapter between InnoCalc Manager and the concrete wall engine."""

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
    "designMethod": "Wall design method applicable",
    "axial": "Design axial strength",
    "slenderness": "Slenderness limit Hwe/tw",
    "singleLayer": "Single layer of reinforcement permitted",
    "verticalSteel": "Minimum vertical reinforcement",
    "horizontalSteel": "Minimum horizontal reinforcement",
    "verticalSpacing": "Vertical bar spacing",
    "horizontalSpacing": "Horizontal bar spacing",
    "barGap": "Minimum clear gap between bars",
    "inPlaneShear": "In-plane shear",
    "ductileWall": "Limited ductile wall reinforcement",
    "fireResistance": "Fire resistance level",
    "crackControl": "Horizontal crack control reinforcement",
    "cover": "Cover for exposure classification",
}
ALWAYS_ON = ("designMethod", "axial", "slenderness", "verticalSteel", "horizontalSteel",
             "verticalSpacing", "horizontalSpacing", "barGap", "inPlaneShear")

YES_NO = [{"value": "Y", "label": "Yes"}, {"value": "N", "label": "No"}]
BARS = [{"value": f"{size:g}", "label": f"{size:g} mm"} for size in engine.BAR_SIZES]


def descriptor() -> dict[str, Any]:
    return deepcopy(DESCRIPTOR)


def schema() -> dict[str, Any]:
    return {
        **descriptor(),
        "identity": {"typeLabel": "Member type", "numberLabel": "Member number",
                     "typeOptions": ["Wall", "Shear wall", "Core wall", "Blade wall"]},
        "groups": [
            {"id": "geometry", "title": "Geometry and material", "fields": [
                {"id": "fc", "label": "Concrete strength f'c", "type": "number", "unit": "MPa",
                 "default": 32.0, "help": "20 to 120 MPa, Cl 1.1.2"},
                {"id": "tw", "label": "Wall thickness tw", "type": "number", "unit": "mm",
                 "default": 200.0},
                {"id": "Hw", "label": "Wall height Hw", "type": "number", "unit": "mm",
                 "default": 3000.0, "help": "Floor-to-floor unsupported height"},
                {"id": "Lw", "label": "Wall length Lw", "type": "number", "unit": "mm",
                 "default": 4000.0, "help": "Also L1 for Cl 11.4"},
                {"id": "cover", "label": "Cover to outer bars", "type": "number", "unit": "mm",
                 "default": 30.0, "help": "Excluding ligatures"},
                {"id": "formwork", "label": "Formwork and compaction", "type": "select",
                 "default": "S", "options": [{"value": "S", "label": "S - Standard"},
                                             {"value": "R", "label": "R - Rigid/intense"}]},
                {"id": "braced", "label": "Wall braced (Cl 11.3)", "type": "select",
                 "default": "Y", "options": YES_NO},
                {"id": "designAsWall", "label": "Design as wall when a slab is permitted",
                 "type": "select", "default": "Y", "options": YES_NO,
                 "help": "Cl 11.1(b)(i); No designs as a slab for axial stress"},
                {"id": "dwall", "label": "Limited ductile shear wall", "type": "select",
                 "default": "N", "options": YES_NO, "help": "Cl 14.6"},
            ]},
            {"id": "height", "title": "Effective height - Cl 11.4", "fields": [
                {"id": "rotRestraint", "label": "Restrained against rotation top and bottom",
                 "type": "select", "default": "Y", "options": YES_NO},
                {"id": "wallIntersect", "label": "Sides supported by intersecting walls",
                 "type": "select", "default": "0",
                 "options": [{"value": "0", "label": "0 - top and bottom only"},
                             {"value": "1", "label": "1 - three sides"},
                             {"value": "2", "label": "2 - four sides"}],
                 "help": "Return walls at least 0.2 Hw long"},
                {"id": "kMode", "label": "Effective height factor", "type": "select",
                 "default": "CALC", "options": [{"value": "CALC", "label": "Calculated, Cl 11.4"},
                                                {"value": "USER", "label": "User value"}]},
                {"id": "k", "label": "User effective height factor k", "type": "number",
                 "default": 1.0, "showWhen": {"kMode": ["USER"]}},
                {"id": "openings", "label": "Openings in wall", "type": "select", "default": "N",
                 "options": YES_NO},
                {"id": "Aopen", "label": "Area of openings Ao", "type": "number", "unit": "m2",
                 "default": 0.0, "showWhen": {"openings": ["Y"]}},
                {"id": "Sopen", "label": "Total height of openings Ho", "type": "number",
                 "unit": "mm", "default": 0.0, "showWhen": {"openings": ["Y"]}},
            ]},
            {"id": "loading", "title": "Design actions", "fields": [
                {"id": "Ndl", "label": "Dead load Ndl = G", "type": "number", "unit": "kN/m",
                 "default": 200.0},
                {"id": "Nll", "label": "Live load Nll = Q", "type": "number", "unit": "kN/m",
                 "default": 60.0},
                {"id": "Neu", "label": "Ultimate earthquake axial load Neu", "type": "number",
                 "unit": "kN/m", "default": 0.0},
                {"id": "includeSW", "label": "Include mid-height self weight", "type": "select",
                 "default": "Y", "options": YES_NO},
                {"id": "loadType", "label": "Load type", "type": "select", "default": "F",
                 "options": [{"value": key, "label": f"{key} - {label}"}
                             for key, label in engine.LOAD_TYPES.items()],
                 "help": "AS/NZS 1170.0 Table 4.1 factors"},
                {"id": "psiLOther", "label": "Long-term factor psi_l (other)", "type": "number",
                 "default": 1.0, "showWhen": {"loadType": ["O"]}},
                {"id": "psiEOther", "label": "Earthquake factor psi_E (other)", "type": "number",
                 "default": 1.0, "showWhen": {"loadType": ["O"]}},
                {"id": "wallecc", "label": "Load eccentricity e", "type": "number", "unit": "mm",
                 "default": 33.3, "help": "Cl 11.5.4; tw/6 for a discontinuous slab"},
                {"id": "Mstar", "label": "Out-of-plane moment Mo*", "type": "number",
                 "unit": "kNm/m", "default": 0.0, "help": "Not from the load eccentricity"},
                {"id": "Mstari", "label": "In-plane moment Mi*", "type": "number", "unit": "kNm",
                 "default": 0.0},
                {"id": "Vstar", "label": "In-plane shear V*", "type": "number", "unit": "kN",
                 "default": 0.0},
                {"id": "H", "label": "Overall wall height H for shear", "type": "number",
                 "unit": "mm", "default": 3000.0, "help": "Base to top, Cl 11.6"},
            ]},
            {"id": "reinforcement", "title": "Reinforcement - Cl 11.7", "fields": [
                {"id": "layers", "label": "Reinforcement layers", "type": "select", "default": "2",
                 "options": [{"value": "1", "label": "1 - central"},
                             {"value": "2", "label": "2 - each face"}]},
                {"id": "reoClass", "label": "Reinforcement ductility class", "type": "select",
                 "default": "N", "options": [{"value": "N", "label": "N - Normal"},
                                             {"value": "L", "label": "L - Low"}]},
                {"id": "fsy", "label": "Yield strength fsy", "type": "select", "default": "500",
                 "options": [{"value": f"{grade:g}", "label": f"{grade:g} MPa"}
                             for grade in engine.YIELD_STRENGTHS]},
                {"id": "dbv", "label": "Vertical bar size", "type": "select", "default": "12",
                 "options": BARS},
                {"id": "sv", "label": "Vertical bar spacing", "type": "number", "unit": "mm",
                 "default": 300.0},
                {"id": "dbh", "label": "Horizontal bar size", "type": "select", "default": "12",
                 "options": BARS},
                {"id": "sh", "label": "Horizontal bar spacing", "type": "number", "unit": "mm",
                 "default": 300.0},
                {"id": "unrest", "label": "Unrestrained against horizontal shrinkage",
                 "type": "select", "default": "N", "options": YES_NO, "help": "Cl 11.7.1(b)"},
            ]},
        ],
        "optional": [
            {"id": "fire", "label": "Fire resistance (Cl 5.7)", "fields": [
                {"id": "frlRequired", "label": "Required FRL", "type": "number", "unit": "min",
                 "default": 90.0},
                {"id": "exposed1side", "label": "Fire exposed on one side only", "type": "select",
                 "default": "Y", "options": YES_NO},
                {"id": "lat1side", "label": "Lateral support on one side only", "type": "select",
                 "default": "N", "options": YES_NO},
                {"id": "frlTop", "label": "Top lateral support requires an FRL", "type": "select",
                 "default": "Y", "options": YES_NO},
                {"id": "ll07", "label": "Adopt load level Nf*/phiNu = 0.7", "type": "select",
                 "default": "N", "options": YES_NO},
            ]},
            {"id": "crackControl", "label": "Horizontal crack control (Cl 11.7.2)", "fields": [
                {"id": "crackDegree", "label": "Degree of crack control", "type": "select",
                 "default": "MINOR",
                 "options": [{"value": key, "label": label}
                             for key, (_, label) in engine.CRACK_CONTROL.items()]},
            ]},
            {"id": "durability", "label": "Cover for exposure (Section 4)", "fields": [
                {"id": "exposureClass", "label": "Exposure classification", "type": "select",
                 "default": "A2", "options": list(engine.EXPOSURE_CLASSES)},
            ]},
        ],
        "alwaysOn": {key: True for key in ALWAYS_ON},
        "actions": [],
    }


def defaults() -> dict[str, Any]:
    values: dict[str, Any] = {
        "memberType": "Wall", "memberNumber": "W01", "package": "Unallocated", "level": "",
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
    if math.isfinite(ratio):
        headline = f"{ratio * 100:.1f}% - {CHECK_LABELS[key]}"
    elif key == "designMethod":
        headline = f"Not applicable - {result['method']['reason']}"
    else:
        headline = f"Unattainable - {CHECK_LABELS[key]}"
    return {"worstUtil": result["worstUtil"], "criticalCheck": CHECK_LABELS[key],
            "status": status, "headline": headline}


def identity(inputs: dict[str, Any]) -> dict[str, Any]:
    member_type = str(inputs.get("memberType") or "Wall")
    number = str(inputs.get("memberNumber") or "")
    size = f"{_plain(inputs.get('tw'))} thick x {_plain(inputs.get('Hw'))} high"
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
