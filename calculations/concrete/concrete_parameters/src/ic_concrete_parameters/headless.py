"""Adapter between InnoCalc Manager and the concrete parameter engine."""

from __future__ import annotations

import tomllib
from copy import deepcopy
from importlib.resources import files
from typing import Any

from . import engine, report
from .version import VERSION

DESCRIPTOR = {**tomllib.loads(files(__package__).joinpath("module.toml").read_text(encoding="utf-8")),
              "version": VERSION}


def descriptor() -> dict[str, Any]:
    return deepcopy(DESCRIPTOR)


def schema() -> dict[str, Any]:
    return {
        **descriptor(),
        "identity": {"typeLabel": "Item type", "numberLabel": "Item number",
                     "typeOptions": ["Concrete", "Grade", "Mix"]},
        "groups": [
            {"id": "concrete", "title": "Concrete", "fields": [
                {"id": "fc", "label": "Concrete strength f'c", "type": "number", "unit": "MPa",
                 "default": 32.0, "help": "20 to 120 MPa, Cl 1.1.2"},
                {"id": "density", "label": "Density", "type": "number", "unit": "kg/m3",
                 "default": 2400.0, "help": "Cl 3.1.3, typical normal weight concrete"},
                {"id": "fcmiSource", "label": "Mean in-situ strength fcmi from", "type": "select",
                 "default": "table", "width": "full",
                 "options": [{"value": key, "label": label}
                             for key, label in engine.FCMI_SOURCES.items()]},
            ]},
            {"id": "age", "title": "Strength gain with age", "fields": [
                {"id": "cement", "label": "Cement type", "type": "select", "default": "N",
                 "options": [{"value": key, "label": label}
                             for key, label in engine.CEMENTS.items()]},
                {"id": "age", "label": "Age", "type": "select", "default": "28", "unit": "days",
                 "options": [{"value": str(entry["day"]), "label": f"{entry['day']} days"}
                             for entry in engine.STRENGTH_GAIN]},
            ]},
        ],
        "optional": [
            {"id": "minimumSteel", "label": "Minimum flexural reinforcement", "fields": [
                {"id": "sectionType", "label": "Section", "type": "select", "default": "rect",
                 "width": "full",
                 "options": [{"value": key, "label": label}
                             for key, label in engine.SECTION_TYPES.items()]},
                {"id": "bw", "label": "Web width bw", "type": "number", "unit": "mm",
                 "default": 300.0},
                {"id": "D", "label": "Overall depth D", "type": "number", "unit": "mm",
                 "default": 600.0},
                {"id": "ds", "label": "Depth to tensile steel ds", "type": "number", "unit": "mm",
                 "default": 550.0},
                {"id": "fsy", "label": "Yield strength fsy", "type": "number", "unit": "MPa",
                 "default": 500.0},
                {"id": "bef", "label": "Effective flange width bef", "type": "number",
                 "unit": "mm", "default": 900.0,
                 "showWhen": {"sectionType": ["TLweb", "TLflange"]}},
                {"id": "Ds", "label": "Flange thickness Ds", "type": "number", "unit": "mm",
                 "default": 150.0, "showWhen": {"sectionType": ["TLweb", "TLflange"]}},
            ]},
            {"id": "cracking", "label": "Minimum cracking moment", "fields": [
                {"id": "Zt", "label": "Section modulus Zt", "type": "number", "unit": "mm3",
                 "default": 1.8e7},
                {"id": "Zb", "label": "Section modulus Zb", "type": "number", "unit": "mm3",
                 "default": 1.8e7},
            ]},
        ],
        "alwaysOn": {},
        "actions": [],
    }


def defaults() -> dict[str, Any]:
    layout = schema()
    values: dict[str, Any] = {
        "memberType": "Concrete", "memberNumber": "0001", "package": "Unallocated", "level": "",
        "subject": DESCRIPTOR["defaultSubject"], "checks": {},
    }
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
    fc = result["material"]["fc"]
    return {"worstUtil": 0.0,
            "criticalCheck": "Not applicable - parameter calculation",
            "status": "OK",
            "headline": f"Parameters for f'c = {fc:g} MPa; no design check performed"}


def identity(inputs: dict[str, Any]) -> dict[str, Any]:
    member_type = str(inputs.get("memberType") or "Concrete")
    number = str(inputs.get("memberNumber") or "")
    grade = _plain(inputs.get("fc"))
    return {"memberType": member_type, "memberNumber": number,
            "package": str(inputs.get("package") or "Unallocated"),
            "level": str(inputs.get("level") or ""), "calcType": DESCRIPTOR["calcType"],
            "title": f"{member_type} {number} - f'c = {grade} MPa".strip()}


def _plain(value: Any) -> str:
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return "?"


def validate(cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    from .validation import validate as run_validation
    return run_validation(cases)
