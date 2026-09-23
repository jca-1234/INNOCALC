"""Adapter between InnoCalc Manager and the reinforcement rate engine."""

from __future__ import annotations

import tomllib
from copy import deepcopy
from importlib.resources import files
from typing import Any

from . import engine, report
from .version import VERSION

DESCRIPTOR = {**tomllib.loads(files(__package__).joinpath("module.toml").read_text(encoding="utf-8")),
              "version": VERSION}

DEFAULT_SCHEDULE = (
    "# type, number or centres, bar size, length (mm), description\n"
    "B, 200, 12, 1000, Bottom bars main direction\n"
    "B, 400, 12, 1000, Top bars main direction"
)


def descriptor() -> dict[str, Any]:
    return deepcopy(DESCRIPTOR)


def schema() -> dict[str, Any]:
    return {
        **descriptor(),
        "identity": {"typeLabel": "Member type", "numberLabel": "Member number",
                     "typeOptions": ["Slab", "Beam", "Band beam", "Wall", "Column"]},
        "groups": [
            {"id": "member", "title": "Member", "fields": [
                {"id": "title", "label": "Description", "type": "text", "default": "Default",
                 "width": "full"},
                {"id": "L", "label": "Length", "type": "number", "unit": "mm",
                 "default": 1000.0},
                {"id": "rb", "label": "Width", "type": "number", "unit": "mm",
                 "default": 1000.0},
                {"id": "rd", "label": "Depth", "type": "number", "unit": "mm",
                 "default": 150.0},
                {"id": "cover", "label": "Cover", "type": "number", "unit": "mm",
                 "default": 30.0},
                {"id": "ligs", "label": "Ligature size", "type": "number", "unit": "mm",
                 "default": 8.0, "help": "Hook length is tabulated for 8, 10, 12, 16 and 20 mm"},
                {"id": "density", "label": "Reinforcement density", "type": "number",
                 "unit": "kg/m3", "default": 7860.0},
            ]},
            {"id": "schedule", "title": "Reinforcement schedule", "fields": [
                {"id": "schedule", "label": "Schedule", "type": "textarea",
                 "default": DEFAULT_SCHEDULE, "width": "full",
                 "help": "One row per line: type (B bar, L ligature, T transverse set), "
                         "number or centres, bar size, length in mm, description. "
                         "A number of 100 or more is read as centres. Maximum 21 rows."},
            ]},
        ],
        "optional": [],
        "alwaysOn": {},
        "actions": [],
    }


def defaults() -> dict[str, Any]:
    values: dict[str, Any] = {
        "memberType": "Slab", "memberNumber": "0001", "package": "Unallocated", "level": "",
        "subject": DESCRIPTOR["defaultSubject"], "checks": {},
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
    totals = result["totals"]
    return {"worstUtil": 0.0,
            "criticalCheck": "Not applicable - quantity calculation",
            "status": "OK",
            "headline": f"{totals['rate']:.1f} kg/m3 from {totals['weight']:.1f} kg of steel; "
                        "no design check performed"}


def identity(inputs: dict[str, Any]) -> dict[str, Any]:
    member_type = str(inputs.get("memberType") or "Slab")
    number = str(inputs.get("memberNumber") or "")
    title = str(inputs.get("title") or "").strip()
    described = f"{member_type} {number} - {title}" if title else f"{member_type} {number}"
    return {"memberType": member_type, "memberNumber": number,
            "package": str(inputs.get("package") or "Unallocated"),
            "level": str(inputs.get("level") or ""), "calcType": DESCRIPTOR["calcType"],
            "title": described.strip()}


def validate(cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    from .validation import validate as run_validation
    return run_validation(cases)
