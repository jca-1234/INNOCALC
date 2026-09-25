"""Adapter between InnoCalc Manager and the industrial pavement engine."""

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
    "rackBearing": "Rack post bearing",
    "rackPunching": "Rack post punching shear",
    "rackFlexure": "Rack post flexural stress",
    "wheelFlexure": "Wheel flexural stress",
    "uniformVariable": "Uniform load, variable layout",
    "uniformAisle": "Uniform load, patterned at the actual aisle",
    "uniformCritical": "Uniform load, patterned at the critical aisle",
    "abrasionGrade": "Concrete grade for abrasion and exposure",
    "customFlexure": "Custom load flexural stress",
    "positionApplicability": "Load position applicability",
}
ALWAYS_ON = ("rackBearing", "rackPunching", "rackFlexure", "wheelFlexure", "uniformVariable",
             "uniformAisle", "uniformCritical", "abrasionGrade")

YES_NO = [{"value": "Y", "label": "Yes"}, {"value": "N", "label": "No"}]
DIRECTION_OPTIONS = [{"value": "T", "label": "T - Tangential"},
                     {"value": "R", "label": "R - Radial"},
                     {"value": "C", "label": "C - Critical of both"}]


def _options(mapping: dict[str, str]) -> list[dict[str, str]]:
    return [{"value": key, "label": f"{key} - {label}"} for key, label in mapping.items()]


def _custom_fields() -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = [
        {"id": "CPL", "label": "Point G load", "type": "number", "unit": "kN", "default": 20.0},
        {"id": "CFl", "label": "Foot length", "type": "number", "unit": "mm", "default": 140.0},
        {"id": "CFw", "label": "Foot width", "type": "number", "unit": "mm", "default": 80.0},
        {"id": "ltype", "label": "Loading type", "type": "select", "default": "W",
         "options": [{"value": "P", "label": "P - Post"}, {"value": "W", "label": "W - Wheel"}]},
        {"id": "CLife", "label": "Design life", "type": "number", "unit": "years", "default": 25.0},
        {"id": "CReps", "label": "Daily cycles", "type": "number", "default": 50.0},
        {"id": "customLoads", "label": "Adjacent point loads", "type": "select",
         "default": "SAME", "options": [{"value": "SAME", "label": "Equal to the point G load"},
                                        {"value": "LIST", "label": "Entered for each point"}]},
    ]
    for name in engine.CUSTOM_POINTS:
        distance, direction = engine.CUSTOM_DEFAULTS[name]
        fields += [
            {"id": f"load{name}", "label": f"Point {name} load", "type": "number", "unit": "kN",
             "default": 20.0, "showWhen": {"customLoads": ["LIST"]}},
            {"id": f"dist{name}", "label": f"Point {name} distance from G", "type": "number",
             "unit": "mm", "default": distance, "help": "0 for no load"},
            {"id": f"dir{name}", "label": f"Point {name} direction in X", "type": "select",
             "default": direction, "options": DIRECTION_OPTIONS,
             "help": "Y is the other direction; C in both"},
        ]
    return fields


def descriptor() -> dict[str, Any]:
    return deepcopy(DESCRIPTOR)


def schema() -> dict[str, Any]:
    return {
        **descriptor(),
        "identity": {"typeLabel": "Member type", "numberLabel": "Member number",
                     "typeOptions": ["Floor slab", "Pavement", "Hardstand"]},
        "groups": [
            {"id": "concrete", "title": "Concrete and slab", "fields": [
                {"id": "fc", "label": "Concrete strength f'c", "type": "number", "unit": "MPa",
                 "default": 32.0, "help": "20 to 120 MPa, AS 3600 Cl 1.1.2"},
                {"id": "h", "label": "Slab thickness h", "type": "number", "unit": "mm",
                 "default": 150.0},
                {"id": "density", "label": "Concrete density", "type": "number", "unit": "kg/m3",
                 "default": 2400.0},
                {"id": "useFcmi", "label": "Use fcmi for Ec", "type": "select", "default": "Y",
                 "options": YES_NO, "help": "No uses fcmi = f'c"},
                {"id": "fmethod", "label": "Method for flexural strength", "type": "select",
                 "default": "A", "options": _options(engine.FLEXURAL_METHODS)},
                {"id": "fcfo", "label": "Other manual flexural strength", "type": "number",
                 "unit": "MPa", "default": 4.16, "showWhen": {"fmethod": ["O"]}},
                {"id": "u", "label": "Poisson's ratio", "type": "number", "default": 0.15},
                {"id": "whereinput", "label": "Point under consideration", "type": "select",
                 "default": "I", "options": _options(engine.POSITIONS)},
                {"id": "Transfer", "label": "Load transfer between slabs at a joint",
                 "type": "select", "default": "N", "options": YES_NO,
                 "help": "Edge and corner only; Chandler 0.85 edge and 0.7 corner"},
                {"id": "consider", "label": "Reduce distances by the loaded radius",
                 "type": "select", "default": "N", "options": YES_NO},
                {"id": "Includeneg", "label": "Include negative chart values", "type": "select",
                 "default": "N", "options": YES_NO,
                 "help": "Yes lets adjacent loads reduce the stress"},
                {"id": "overlapwhere", "label": "Check load overlap at", "type": "select",
                 "default": "M", "options": [{"value": "T", "label": "T - Top of slab"},
                                             {"value": "M", "label": "M - Mid-depth"},
                                             {"value": "B", "label": "B - Bottom of slab"}]},
            ]},
            {"id": "subgrade", "title": "Subgrade", "fields": [
                {"id": "K", "label": "Modulus of subgrade reaction K", "type": "number",
                 "unit": "kPa/mm", "default": 40.0, "help": "Design value"},
                {"id": "CBRValue", "label": "CBR for conversion", "type": "number", "unit": "%",
                 "default": 5.0, "help": "Valid for CBR 2 to 30"},
                {"id": "MSRValue", "label": "K for conversion", "type": "number",
                 "unit": "kPa/mm", "default": 40.0},
                {"id": "bt", "label": "Bound sub-base thickness", "type": "select",
                 "default": "150", "options": [{"value": f"{value:g}", "label": f"{value:g} mm"}
                                              for value in engine.BOUND_THICKNESSES]},
                {"id": "T48_2009", "label": "Use T48 2009 charts", "type": "select",
                 "default": "Y", "options": YES_NO, "help": "No uses T48 1999"},
            ]},
            {"id": "racking", "title": "Rack loading", "fields": [
                {"id": "PRNo", "label": "Above ground rack levels", "type": "number",
                 "default": 3.0},
                {"id": "PRwt", "label": "Rack pallet weight", "type": "number", "unit": "kg",
                 "default": 1000.0, "help": "2 pallets per rack"},
                {"id": "PGwt", "label": "Ground pallet weight", "type": "number", "unit": "kg",
                 "default": 1000.0},
                {"id": "PRl", "label": "Pallet side length", "type": "number", "unit": "mm",
                 "default": 1000.0},
                {"id": "PRe", "label": "Pallet side width", "type": "number", "unit": "mm",
                 "default": 1000.0},
                {"id": "Isle", "label": "Aisle width", "type": "number", "unit": "mm",
                 "default": 1680.0, "help": "Chandler Fig 3, 1500 to 4500 mm"},
                {"id": "Fl", "label": "Foot length Fl", "type": "number", "unit": "mm",
                 "default": 140.0},
                {"id": "Fw", "label": "Foot width Fw", "type": "number", "unit": "mm",
                 "default": 80.0},
                {"id": "Rk1", "label": "Material factor Rk1", "type": "number", "default": 0.85,
                 "help": "T48 Table 1.16, 0.75 to 0.85"},
                {"id": "Rk2", "label": "Repetition factor Rk2", "type": "number", "default": 1.0,
                 "help": "T48 Cl 3.3.6"},
                {"id": "Dexian", "label": "Standard Dexian racking", "type": "select",
                 "default": "Y", "options": YES_NO},
                {"id": "dAB", "label": "Distance A - B", "type": "number", "unit": "mm",
                 "default": 838.0},
                {"id": "dAE", "label": "Distance A - E", "type": "number", "unit": "mm",
                 "default": 2591.0},
                {"id": "dBC", "label": "Distance B - C", "type": "number", "unit": "mm",
                 "default": 381.0},
            ]},
            {"id": "wheels", "title": "Wheel loading", "fields": [
                {"id": "Fork", "label": "Vehicle description", "type": "text",
                 "default": "Standard Forklift"},
                {"id": "AxleP", "label": "Maximum single axle load", "type": "number",
                 "unit": "t", "default": 3.5, "help": "Approximately 2.45 x capacity"},
                {"id": "WheelsPerAxle", "label": "Wheels per axle", "type": "select",
                 "default": "2", "options": [{"value": "2", "label": "2"},
                                             {"value": "4", "label": "4"}]},
                {"id": "WheelPairCentres", "label": "Wheel pair spacing (4 per axle)",
                 "type": "number", "unit": "mm", "default": 500.0},
                {"id": "Wcts", "label": "Distance between wheels across the axle",
                 "type": "number", "unit": "mm", "default": 2600.0},
                {"id": "Bogie", "label": "Distance between axles", "type": "number",
                 "unit": "mm", "default": 0.0, "help": "0 for a single axle"},
                {"id": "Pr", "label": "Tyre pressure", "type": "number", "unit": "kPa",
                 "default": 700.0},
                {"id": "Wk1", "label": "Material factor Wk1", "type": "number", "default": 0.95,
                 "help": "T48 Table 1.16, 0.85 to 0.95"},
                {"id": "Life", "label": "Design life", "type": "number", "unit": "years",
                 "default": 25.0},
                {"id": "Reps", "label": "Daily cycles", "type": "number", "default": 50.0},
                {"id": "showDistWarning", "label": "Warn when loaded areas overlap",
                 "type": "select", "default": "Y", "options": YES_NO},
            ]},
            {"id": "uniform", "title": "Uniform floor loading", "fields": [
                {"id": "PFno", "label": "Number of pallets on the floor", "type": "number",
                 "default": 1.0},
                {"id": "PFwt", "label": "Ground pallet weight", "type": "number", "unit": "kg",
                 "default": 1000.0},
                {"id": "PFl", "label": "Pallet side length", "type": "number", "unit": "mm",
                 "default": 1000.0},
                {"id": "PFe", "label": "Pallet end length", "type": "number", "unit": "mm",
                 "default": 1000.0},
                {"id": "IsleUDL", "label": "Aisle width", "type": "number", "unit": "mm",
                 "default": 2000.0},
                {"id": "Uk1", "label": "Material factor Uk1", "type": "number", "default": 0.85,
                 "help": "T48 Table 1.16, 0.75 to 0.85"},
                {"id": "Uk2", "label": "Repetition factor Uk2", "type": "number", "default": 0.75,
                 "help": "T48 Cl 3.3.6"},
                {"id": "useFOS", "label": "Use a factor of safety (C&CA)", "type": "select",
                 "default": "N", "options": YES_NO, "help": "No uses Uk1 x Uk2"},
                {"id": "fos", "label": "Factor of safety", "type": "number", "default": 2.0,
                 "help": "C&CA Cl 5.6.3"},
            ]},
            {"id": "reinforcement", "title": "Shrinkage reinforcement", "fields": [
                {"id": "cjlen", "label": "Length between untied joints", "type": "number",
                 "unit": "mm", "default": 16000.0},
                {"id": "dragu", "label": "Subgrade drag coefficient", "type": "number",
                 "default": 1.5, "help": "T48 Fig 1.31, Austroads Fig 9.10"},
                {"id": "fsy", "label": "Steel yield strength fsy", "type": "select",
                 "default": "500", "options": [{"value": f"{grade:g}", "label": f"{grade:g} MPa"}
                                               for grade in engine.YIELD_STRENGTHS]},
                {"id": "reom", "label": "Method for reinforcement", "type": "select",
                 "default": "A", "options": _options(engine.REINFORCEMENT_METHODS)},
            ]},
        ],
        "optional": [
            {"id": "custom", "label": "Custom point load layout (workbook Custom tab)",
             "fields": _custom_fields()},
            {"id": "location", "label": "Load position applicability (generic, after Tedds)",
             "fields": [
                 {"id": "edgeDistX", "label": "Load centre to nearest edge or joint",
                  "type": "number", "unit": "mm", "default": 3000.0},
                 {"id": "edgeDistY", "label": "Load centre to second edge or joint",
                  "type": "number", "unit": "mm", "default": 3000.0},
             ]},
        ],
        "alwaysOn": {key: True for key in ALWAYS_ON},
        "actions": [],
    }


def defaults() -> dict[str, Any]:
    values: dict[str, Any] = {
        "memberType": "Floor slab", "memberNumber": "SL01", "package": "Unallocated",
        "level": "", "subject": DESCRIPTOR["defaultSubject"],
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
    member_type = str(inputs.get("memberType") or "Floor slab")
    number = str(inputs.get("memberNumber") or "")
    size = f"{_plain(inputs.get('h'))} mm, f'c {_plain(inputs.get('fc'))} MPa"
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
