"""Adapter between InnoCalc Manager and the reinforcement tables engine."""

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
                     "typeOptions": ["Reinforcement", "Table"]},
        "groups": [
            {"id": "selection", "title": "Selected reinforcement", "fields": [
                {"id": "db", "label": "Bar diameter", "type": "number", "unit": "mm",
                 "default": 16.0,
                 "help": "Tabulated sizes are 12, 16, 20, 24, 28, 32 and 40 mm"},
                {"id": "count", "label": "Number of bars", "type": "number", "default": 4.0},
                {"id": "centres", "label": "Bar centres", "type": "number", "unit": "mm",
                 "default": 200.0},
                {"id": "rounding", "label": "Table rounding", "type": "select",
                 "default": "-1", "width": "full",
                 "options": [{"value": key, "label": label}
                             for key, label in engine.ROUNDINGS.items()]},
            ]},
            {"id": "fabric", "title": "Fabric", "fields": [
                {"id": "mesh", "label": "Fabric designation", "type": "select",
                 "default": "SL82", "width": "full",
                 "options": [{"value": entry["name"],
                              "label": f"{entry['name']} ({entry['family'].lower()})"}
                             for entry in engine.FABRIC]},
            ]},
        ],
        "optional": [],
        "alwaysOn": {},
        "actions": [],
    }


def defaults() -> dict[str, Any]:
    values: dict[str, Any] = {
        "memberType": "Reinforcement", "memberNumber": "0001", "package": "Unallocated",
        "level": "", "subject": DESCRIPTOR["defaultSubject"], "checks": {},
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
    selected = result["selected"]
    return {"worstUtil": 0.0,
            "criticalCheck": "Not applicable - reference tables",
            "status": "OK",
            "headline": f"N{selected['db']:g}: {selected['count']:g} bars = "
                        f"{selected['countArea']:.0f} mm2, at "
                        f"{selected['centres']:.0f} centres = "
                        f"{selected['centresArea']:.0f} mm2/m; no design check performed"}


def identity(inputs: dict[str, Any]) -> dict[str, Any]:
    member_type = str(inputs.get("memberType") or "Reinforcement")
    number = str(inputs.get("memberNumber") or "")
    size = _plain(inputs.get("db"))
    return {"memberType": member_type, "memberNumber": number,
            "package": str(inputs.get("package") or "Unallocated"),
            "level": str(inputs.get("level") or ""), "calcType": DESCRIPTOR["calcType"],
            "title": f"{member_type} {number} - {size} mm bar".strip()}


def _plain(value: Any) -> str:
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return "?"


def validate(cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    from .validation import validate as run_validation
    return run_validation(cases)
