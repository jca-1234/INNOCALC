"""Adapter between InnoCalc Manager and the strut-and-tie engine."""

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
    "strut": "Compression strut capacity",
    "supportLength": "Support length for the strut",
    "strutAngle": "Strut angle not less than 30 degrees",
    "angleCompatibility": "Strut angle compatible with the node geometry",
    "bottleLength": "Strut depth less than the strut length",
    "burstingStrength": "Bursting reinforcement, strength",
    "burstingService": "Bursting reinforcement, serviceability",
    "burstingCracking": "Bursting reinforcement, transfer at cracking",
    "burstingThreshold": "Bursting force below the cracking threshold",
    "oneWayAngle": "One-way bursting reinforcement angle",
    "verticalLoadSteel": "Vertical steel for the additional vertical load",
    "tie": "Tension tie capacity",
    "node": "Nodal stress",
    "bearing": "Bearing stress",
    "nodeStrutFace": "Node face stress, strut face",
    "nodeBearingFace": "Node face stress, bearing face",
    "nodeTieFace": "Node face stress, tie face",
}
ALWAYS_ON = ("strut", "supportLength", "strutAngle", "angleCompatibility", "bottleLength",
             "verticalLoadSteel", "tie", "node", "bearing")

YES_NO = [{"value": "Y", "label": "Yes"}, {"value": "N", "label": "No"}]
CALC_MANUAL = [{"value": "C", "label": "Calculated"}, {"value": "M", "label": "Manual"}]
GRADES = [{"value": f"{grade:g}", "label": f"{grade:g} MPa"} for grade in engine.YIELD_STRENGTHS]


def _options(mapping: dict[str, Any]) -> list[dict[str, str]]:
    return [{"value": key, "label": f"{key} - {value if isinstance(value, str) else value[0]}"}
            for key, value in mapping.items()]


def _manual(mode: str, value: str, label: str, default: float, unit: str = "") -> list[dict]:
    fields = [{"id": mode, "label": label, "type": "select", "default": "C",
               "options": CALC_MANUAL},
              {"id": value, "label": f"Manual {label[0].lower()}{label[1:]}", "type": "number",
               "default": default, "showWhen": {mode: ["M"]}}]
    if unit:
        fields[1]["unit"] = unit
    return fields


def descriptor() -> dict[str, Any]:
    return deepcopy(DESCRIPTOR)


def schema() -> dict[str, Any]:
    return {
        **descriptor(),
        "identity": {"typeLabel": "Member type", "numberLabel": "Member number",
                     "typeOptions": ["Strut and Tie", "Deep beam", "Transfer wall", "Pile cap",
                                     "Corbel", "Nib"]},
        "groups": [
            {"id": "actions", "title": "Strut-and-tie actions", "fields": [
                {"id": "Cstar", "label": "Strut compression C*", "type": "number", "unit": "kN",
                 "default": 3000.0},
                {"id": "Cserv", "label": "Strut compression, serviceability Cserv",
                 "type": "number", "unit": "kN", "default": 2000.0},
                {"id": "Tstar", "label": "Tie tension T*", "type": "number", "unit": "kN",
                 "default": 2200.0},
                {"id": "Vrstar", "label": "Additional vertical load Vr*", "type": "number",
                 "unit": "kN", "default": 0.0,
                 "help": "Acts with the strut, for example a uniform load"},
                {"id": "Vrserv", "label": "Additional vertical load, serviceability Vr.serv",
                 "type": "number", "unit": "kN", "default": 0.0},
            ]},
            {"id": "geometry", "title": "Strut geometry - Fig 7.2.4(A)", "fields": [
                {"id": "fc", "label": "Concrete strength f'c", "type": "number", "unit": "MPa",
                 "default": 40.0, "help": "20 to 120 MPa, Cl 1.1.2"},
                {"id": "Lstrut", "label": "Horizontal length of strut Lstrut", "type": "number",
                 "unit": "mm", "default": 3000.0},
                {"id": "D", "label": "Depth of panel D", "type": "number", "unit": "mm",
                 "default": 3000.0},
                {"id": "bc", "label": "Width of strut or wall bc", "type": "number", "unit": "mm",
                 "default": 400.0},
                {"id": "Lr", "label": "Horizontal reaction length Lr", "type": "number",
                 "unit": "mm", "default": 800.0},
                {"id": "thetaMode", "label": "Strut angle theta", "type": "select", "default": "S",
                 "options": _options(engine.THETA_MODES)},
                {"id": "theta", "label": "Manual strut angle theta", "type": "number",
                 "unit": "deg", "default": 45.0, "showWhen": {"thetaMode": ["M"]}},
                *_manual("aMode", "aManual", "Strut horizontal distance a", 2500.0, "mm"),
                *_manual("zMode", "zManual", "Strut vertical distance z", 2500.0, "mm"),
                *_manual("dcMode", "dcManual", "Depth of strut dc", 500.0, "mm"),
                *_manual("lbMode", "lbManual", "Length of bursting zone lb", 3000.0, "mm"),
            ]},
            {"id": "strut", "title": "Strut efficiency and divergence - Cl 7.2", "fields": [
                *_manual("betasMode", "betasManual", "Strut efficiency factor betas", 0.5),
                *_manual("tanAlphaMode", "tanAlphaManual", "Strength tan alpha", 0.2),
                *_manual("tanAlphaServMode", "tanAlphaServManual", "Serviceability tan alpha",
                         0.5),
            ]},
            {"id": "bursting", "title": "Bursting reinforcement - Cl 7.2.4", "fields": [
                {"id": "crack", "label": "Crack control", "type": "select", "default": "O",
                 "options": _options(engine.CRACK_CLASSES), "help": "Steel stress limit fsi"},
                {"id": "fsic", "label": "Custom steel stress limit fsi", "type": "number",
                 "unit": "MPa", "default": 250.0, "showWhen": {"crack": ["C"]}},
                {"id": "bar1", "label": "Vertical bar size", "type": "number", "unit": "mm",
                 "default": 16.0, "help": "0 for no vertical bars"},
                {"id": "cts1", "label": "Vertical bar centres", "type": "number", "unit": "mm",
                 "default": 200.0},
                {"id": "layer1", "label": "Vertical bar layers", "type": "number", "default": 2.0},
                {"id": "fsy1", "label": "Vertical bar yield strength", "type": "select",
                 "default": "500", "options": GRADES},
                {"id": "bar2", "label": "Horizontal bar size", "type": "number", "unit": "mm",
                 "default": 16.0, "help": "0 for no horizontal bars"},
                {"id": "cts2", "label": "Horizontal bar centres", "type": "number", "unit": "mm",
                 "default": 200.0},
                {"id": "layer2", "label": "Horizontal bar layers", "type": "number",
                 "default": 2.0},
                {"id": "fsy2", "label": "Horizontal bar yield strength", "type": "select",
                 "default": "500", "options": GRADES},
                {"id": "useRef2", "label": "Cracking capacity at phi fsy (reference 2)",
                 "type": "select", "default": "Y", "options": YES_NO,
                 "help": "No uses the stress limit fsi"},
            ]},
            {"id": "tie", "title": "Tension tie - Cl 7.3", "fields": [
                {"id": "tieBar", "label": "Tie bar size", "type": "number", "unit": "mm",
                 "default": 28.0},
                {"id": "tieBars", "label": "Number of tie bars per layer", "type": "number",
                 "default": 6.0},
                {"id": "tieLayers", "label": "Tie bar layers", "type": "number", "default": 2.0},
                {"id": "fsy", "label": "Tie yield strength", "type": "select", "default": "500",
                 "options": GRADES},
            ]},
            {"id": "anchorage", "title": "Anchorage of ties - Cl 7.3.3", "fields": [
                {"id": "ek", "label": "Epoxy coated bars", "type": "select", "default": "N",
                 "options": YES_NO},
                {"id": "lk", "label": "Lightweight concrete", "type": "select", "default": "N",
                 "options": YES_NO},
                {"id": "sk", "label": "Slip formed element", "type": "select", "default": "N",
                 "options": YES_NO},
                {"id": "cogged", "label": "Cogged bars", "type": "select", "default": "Y",
                 "options": YES_NO},
                {"id": "below", "label": "Concrete cast below horizontal and tie bars",
                 "type": "number", "unit": "mm", "default": 350.0},
                {"id": "bundle", "label": "Bars in bundle", "type": "select", "default": "1",
                 "options": [{"value": str(count), "label": str(count)} for count in range(1, 5)]},
                {"id": "cover", "label": "Minimum cover c", "type": "number", "unit": "mm",
                 "default": 40.0},
                {"id": "covera", "label": "Clear distance between bars a", "type": "number",
                 "unit": "mm", "default": 100.0},
                {"id": "dzMode", "label": "Development zone dz", "type": "select",
                 "default": "C", "options": _options(engine.DZ_MODES)},
                {"id": "dzManual", "label": "Manual development zone dz", "type": "number",
                 "unit": "mm", "default": 300.0, "showWhen": {"dzMode": ["M"]}},
            ]},
            {"id": "nodes", "title": "Nodes and bearing - Cl 7.4.2 and Cl 12.6", "fields": [
                {"id": "ntype", "label": "Node type", "type": "select", "default": "CCT",
                 "options": [{"value": key, "label": key} for key in engine.NODE_TYPES]},
                {"id": "stresso", "label": "Nodal stress sigma_o", "type": "number",
                 "unit": "MPa", "default": 0.0},
                {"id": "bearingMode", "label": "Bearing force B*", "type": "select",
                 "default": "C", "options": _options(engine.BEARING_MODES)},
                {"id": "Bstar", "label": "Manual bearing B*", "type": "number", "unit": "kN",
                 "default": 0.0, "showWhen": {"bearingMode": ["M"]}},
                {"id": "areaMode", "label": "Bearing areas", "type": "select", "default": "D",
                 "options": _options(engine.AREA_MODES)},
                {"id": "A1", "label": "Bearing area A1", "type": "number", "unit": "mm2",
                 "default": 320000.0, "showWhen": {"areaMode": ["M"]}},
                {"id": "A2", "label": "Largest similar supporting area A2", "type": "number",
                 "unit": "mm2", "default": 320000.0, "showWhen": {"areaMode": ["M"]}},
            ]},
        ],
        "optional": [
            {"id": "nodeFaces", "label": "Nodal face stresses from the model forces (Cl 7.4.2)",
             "fields": [
                 {"id": "tieHeightMode", "label": "Tie face height u", "type": "select",
                  "default": "H", "options": _options(engine.TIE_HEIGHT_MODES)},
                 {"id": "tieHeight", "label": "Manual tie face height u", "type": "number",
                  "unit": "mm", "default": 300.0, "showWhen": {"tieHeightMode": ["M"]},
                  "help": "Depth of concrete engaged by the tie at the node"},
             ]},
        ],
        "alwaysOn": {key: True for key in ALWAYS_ON},
        "actions": [],
    }


def defaults() -> dict[str, Any]:
    values: dict[str, Any] = {
        "memberType": "Strut and Tie", "memberNumber": "ST01", "package": "Unallocated",
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
    member_type = str(inputs.get("memberType") or "Strut and Tie")
    number = str(inputs.get("memberNumber") or "")
    size = f"{_plain(inputs.get('Lstrut'))} x {_plain(inputs.get('D'))} x {_plain(inputs.get('bc'))}"
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
