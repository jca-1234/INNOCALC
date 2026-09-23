"""Adapter between InnoCalc Manager and the development and lap length engine."""

from __future__ import annotations

import tomllib
from copy import deepcopy
from importlib.resources import files
from typing import Any

from . import engine, report
from .version import VERSION

DESCRIPTOR = {**tomllib.loads(files(__package__).joinpath("module.toml").read_text(encoding="utf-8")),
              "version": VERSION}

_YES_NO_OPTIONS = [{"value": "N", "label": "No"}, {"value": "Y", "label": "Yes"}]


def descriptor() -> dict[str, Any]:
    return deepcopy(DESCRIPTOR)


def schema() -> dict[str, Any]:
    return {
        **descriptor(),
        "identity": {"typeLabel": "Item type", "numberLabel": "Item number",
                     "typeOptions": ["Reinforcement", "Bar", "Splice"]},
        "groups": [
            {"id": "material", "title": "Materials and bar", "fields": [
                {"id": "fc", "label": "Concrete strength f'c", "type": "number", "unit": "MPa",
                 "default": 32.0, "help": "20 to 120 MPa, Cl 1.1.2. Tension development caps "
                                          "f'c at 65 MPa"},
                {"id": "db", "label": "Bar diameter db", "type": "number", "unit": "mm",
                 "default": 20.0, "help": "Standard sizes are 10 to 36 mm; others are allowed"},
                {"id": "fsy", "label": "Yield strength fsy", "type": "select", "default": "500",
                 "options": [{"value": f"{grade:g}", "label": f"{grade:g} MPa"}
                             for grade in engine.YIELD_STRENGTHS]},
                {"id": "plain", "label": "Plain bar", "type": "select", "default": "N",
                 "options": _YES_NO_OPTIONS},
                {"id": "lightweight", "label": "Lightweight concrete", "type": "select",
                 "default": "N", "options": _YES_NO_OPTIONS,
                 "help": "Cl 13.1.2.2(b), ml = 1.3"},
                {"id": "epoxy", "label": "Epoxy coated bars", "type": "select", "default": "N",
                 "options": _YES_NO_OPTIONS, "help": "Cl 13.1.2.2(a), me = 1.5"},
                {"id": "bundle", "label": "Bars in bundle", "type": "select", "default": "1",
                 "options": [{"value": f"{size:g}", "label": f"{size:g}"}
                             for size in engine.BUNDLE_SIZES], "help": "Cl 13.1.7"},
                {"id": "rounding", "label": "Round lengths", "type": "select", "default": "-1",
                 "width": "full",
                 "options": [{"value": key, "label": label}
                             for key, label in engine.ROUNDINGS.items()]},
            ]},
            {"id": "geometry", "title": "Cover and spacing", "fields": [
                {"id": "cover", "label": "Minimum cover", "type": "number", "unit": "mm",
                 "default": 50.0},
                {"id": "clear", "label": "Clear distance between bars a", "type": "number",
                 "unit": "mm", "default": 50.0, "help": "Fig 13.1.2.2, cd = min(a/2, cover)"},
                {"id": "below", "label": "Concrete cast below the bar", "type": "number",
                 "unit": "mm", "default": 350.0,
                 "help": "More than 300 mm gives k1 = 1.3, Cl 13.1.2.2"},
            ]},
            {"id": "stress", "title": "Bar stress", "fields": [
                {"id": "stress", "label": "Tension bar stress", "type": "number", "unit": "MPa",
                 "default": 500.0, "help": "Cl 13.1.2.4. Laps require the full yield stress"},
                {"id": "stressc", "label": "Compression bar stress", "type": "number",
                 "unit": "MPa", "default": 500.0,
                 "help": "Cl 13.1.5.4. Laps require the full yield stress"},
                {"id": "limitCompressionFc", "label": "Limit compression f'c to 65 MPa",
                 "type": "select", "default": "N", "width": "full",
                 "options": _YES_NO_OPTIONS},
            ]},
            {"id": "tensionLap", "title": "Tension lapped splice, Cl 13.2.2", "fields": [
                {"id": "element", "label": "Wide or narrow element", "type": "select",
                 "default": "W", "width": "full",
                 "options": [{"value": key, "label": label}
                             for key, label in engine.ELEMENTS.items()]},
                {"id": "sbb", "label": "Clear distance between spliced bars sb",
                 "type": "number", "unit": "mm", "default": 50.0,
                 "help": "Counted only when it is at least 3 db"},
                {"id": "twiceProvided", "label": "Twice the steel provided for tensile capacity",
                 "type": "select", "default": "N", "width": "full",
                 "options": _YES_NO_OPTIONS, "help": "Sets k7 to 1.0 rather than 1.25"},
            ]},
            {"id": "compressionLap", "title": "Compression lapped splice, Cl 13.2.4", "fields": [
                {"id": "fitment", "label": "Fitment diameter", "type": "number", "unit": "mm",
                 "default": 12.0},
                {"id": "fitmentSpacing", "label": "Fitment spacing", "type": "number",
                 "unit": "mm", "default": 200.0},
                {"id": "threeFitments", "label": "At least three fitments over the lap",
                 "type": "select", "default": "Y", "options": _YES_NO_OPTIONS},
                {"id": "helical", "label": "Helical fitments", "type": "select", "default": "N",
                 "options": _YES_NO_OPTIONS},
                {"id": "helixBars", "label": "Number of bars in the helix", "type": "number",
                 "default": 6.0},
            ]},
        ],
        "optional": [
            {"id": "hooksAndCogs", "label": "Hook and cog geometry, Cl 13.1.2.7", "fields": [
                {"id": "bendDb", "label": "Bar diameter at the bend", "type": "number",
                 "unit": "mm", "default": 20.0},
                {"id": "galvanised", "label": "Galvanised", "type": "select", "default": "N",
                 "options": _YES_NO_OPTIONS},
                {"id": "rebent", "label": "Bar to be rebent or straightened", "type": "select",
                 "default": "N", "options": _YES_NO_OPTIONS},
                {"id": "maxInternal", "label": "Maximum internal diameter", "type": "number",
                 "default": 8.0, "help": "As a multiple of db"},
            ]},
        ],
        "alwaysOn": {},
        "actions": [],
    }


def defaults() -> dict[str, Any]:
    layout = schema()
    values: dict[str, Any] = {
        "memberType": "Reinforcement", "memberNumber": "0001", "package": "Unallocated",
        "level": "", "subject": DESCRIPTOR["defaultSubject"], "checks": {},
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
    errors = result.get("errors") or []
    if errors:
        return {"worstUtil": 0.0, "criticalCheck": "Lapped splice validity",
                "status": "FAIL", "headline": errors[0]}
    db = result["inputs"]["db"]
    tension = result["tension"]["Lsyt" if result["inputs"]["plain"] == "N" else "Lsytp"]
    return {"worstUtil": 0.0,
            "criticalCheck": "Not applicable - length calculation",
            "status": "OK",
            "headline": f"N{db:g}: Lsy.t = {tension:.0f} mm, lap = "
                        f"{result['tensionLap']['Lsytlap']:.0f} mm; no design check performed"}


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
