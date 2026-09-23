"""Headless entry point for the Steel Member Design module.

The module is usable three ways and behaves identically in all of them:

* standalone, through ``server.py`` in this folder;
* headless, by importing this file (no HTTP, no browser, no global state);
* hosted, by InnoCalc Manager which discovers this file through the shared
  module contract documented in ``docs/MODULE-SPECIFICATION.md``.

Every function is pure: give it an input document, get a result document back.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from . import catalogue
from .engine import compute_design
from .report import render_report
from .store import CHECK_NAMES
from .version import VERSION

MODULE_DIR = Path(__file__).resolve().parent.parent
MODULE_ID = "steel-member"

DESCRIPTOR: dict[str, Any] = {
    "id": MODULE_ID,
    "name": "Steel Member Design",
    "short": "Steel Member",
    "standard": "AS 4100:2020",
    "folder": "01 - STEEL MEMBER",
    "status": "available",
    "version": VERSION,
    "defaultSubject": "Steel member design",
    "calcType": "Steel member",
    "description": ("Bending, shear, compression, tension, combined actions, torsion, "
                    "bearing and fire checks for open steel sections."),
    "capabilities": ["compute", "render", "validate", "optimise", "exchange"],
    "entry": "smd.headless",
}

MEMBER_TYPES = ["Rafter", "Floor Beam", "Bearer", "Column", "Wind Beam", "Purlin",
                "Batten", "Primary beam", "Secondary beam", "Tertiary beam",
                "Window header", "Dropper", "Brace", "Lintel"]

RESTRAINT = [{"value": "F", "label": "F - Fully restrained"},
             {"value": "P", "label": "P - Partially restrained"},
             {"value": "L", "label": "L - Laterally restrained"},
             {"value": "U", "label": "U - Unrestrained"}]


def descriptor() -> dict[str, Any]:
    return dict(DESCRIPTOR)


# ---------------------------------------------------------------------------
#  Input schema - the manager builds its whole form from this
# ---------------------------------------------------------------------------
def schema() -> dict[str, Any]:
    catalogues = {"sections": {family: catalogue.names(family)
                               for family in catalogue.sections()}}
    families = [{"value": item["value"], "label": item["label"]}
                for item in catalogue.families()]
    return {
        **descriptor(),
        "identity": {"typeLabel": "Member type", "numberLabel": "Member number",
                     "typeOptions": MEMBER_TYPES},
        "catalogues": catalogues,
        "groups": [
            {"id": "section", "title": "Section", "fields": [
                {"id": "secType", "label": "Family", "type": "select", "options": families,
                 "default": "UB"},
                {"id": "section", "label": "Designation", "type": "catalogue",
                 "catalogue": "sections", "optionsBy": "secType", "default": "310UB40.4"},
                {"id": "grade", "label": "Grade", "type": "select", "default": "300",
                 "options": [{"value": "300", "label": "300"}, {"value": "350", "label": "350"},
                             {"value": "400", "label": "400"}]},
                {"id": "legOrient", "label": "Angle orientation", "type": "select",
                 "default": "down", "showWhen": {"secType": ["EA", "UA"]},
                 "options": [{"value": "down", "label": "Leg down"},
                             {"value": "up", "label": "Leg up"}]},
            ]},
            {"id": "actions", "title": "Design Actions", "fields": [
                {"id": "Mx", "label": "M*x", "unit": "kNm", "type": "number", "default": 0},
                {"id": "My", "label": "M*y", "unit": "kNm", "type": "number", "default": 0},
                {"id": "Vx", "label": "V*x", "unit": "kN", "type": "number", "default": 0},
                {"id": "Vy", "label": "V*y", "unit": "kN", "type": "number", "default": 0},
                {"id": "Mz", "label": "M*z", "unit": "kNm", "type": "number", "default": 0},
            ]},
            {"id": "restraint", "title": "Bending and Restraint", "fields": [
                {"id": "L", "label": "Segment length", "unit": "mm", "type": "number", "default": 4500},
                {"id": "end1", "label": "End 1 restraint", "type": "select",
                 "options": RESTRAINT, "default": "F"},
                {"id": "end2", "label": "End 2 restraint", "type": "select",
                 "options": RESTRAINT, "default": "F"},
                {"id": "loadpos", "label": "Load position", "type": "select", "default": "E",
                 "options": [{"value": "E", "label": "At segment end"},
                             {"value": "W", "label": "Within segment"}]},
                {"id": "loadht", "label": "Load height", "type": "select", "default": "S",
                 "options": [{"value": "S", "label": "Shear centre"},
                             {"value": "T", "label": "Top flange"}]},
                {"id": "latrot", "label": "Lateral rotation restraints", "type": "select",
                 "default": "0", "options": [{"value": "0", "label": "0"},
                                             {"value": "1", "label": "1"},
                                             {"value": "2", "label": "2"}]},
                {"id": "amMode", "label": "alpha-m basis", "type": "select", "default": "manual",
                 "options": [{"value": "manual", "label": "Manual"},
                             {"value": "quarter", "label": "Quarter-point"}]},
                {"id": "am", "label": "alpha-m", "type": "number", "default": 1},
                {"id": "Mmax", "label": "M max", "unit": "kNm", "type": "number", "default": 0,
                 "showWhen": {"amMode": ["quarter"]}},
                {"id": "M14", "label": "M at 1/4", "unit": "kNm", "type": "number", "default": 0,
                 "showWhen": {"amMode": ["quarter"]}},
                {"id": "M12", "label": "M at 1/2", "unit": "kNm", "type": "number", "default": 0,
                 "showWhen": {"amMode": ["quarter"]}},
                {"id": "M34", "label": "M at 3/4", "unit": "kNm", "type": "number", "default": 0,
                 "showWhen": {"amMode": ["quarter"]}},
                {"id": "flr", "label": "Full lateral restraint", "type": "checkbox",
                 "default": False, "width": "full"},
            ]},
        ],
        "optional": [
            {"id": "compression", "label": "Compression", "fields": [
                {"id": "Nc", "label": "N*c", "unit": "kN", "type": "number", "default": 0},
                {"id": "Lx", "label": "Lx", "unit": "mm", "type": "number", "default": 4000},
                {"id": "Ly", "label": "Ly", "unit": "mm", "type": "number", "default": 4000},
                {"id": "kex", "label": "kex", "type": "number", "default": 1},
                {"id": "key", "label": "key", "type": "number", "default": 1},
            ]},
            {"id": "tension", "label": "Tension", "fields": [
                {"id": "Nt", "label": "N*t", "unit": "kN", "type": "number", "default": 0},
                {"id": "kt", "label": "kt", "type": "number", "default": 1},
                {"id": "An", "label": "An", "unit": "mm2", "type": "number", "default": 0},
            ]},
            {"id": "torsion", "label": "Torsion", "fields": [
                {"id": "tload", "label": "Load type", "type": "select", "default": "U",
                 "options": [{"value": "U", "label": "UDL"}, {"value": "P", "label": "Point"}]},
                {"id": "tspan", "label": "Span type", "type": "select", "default": "S",
                 "options": [{"value": "S", "label": "Simple"}, {"value": "C", "label": "Cantilever"}]},
            ]},
            {"id": "bearing", "label": "Bearing", "fields": [
                {"id": "R", "label": "R*", "unit": "kN", "type": "number", "default": 0},
                {"id": "bs", "label": "Stiff bearing bs", "unit": "mm", "type": "number", "default": 150},
                {"id": "boc", "label": "Edge distance boc", "unit": "mm", "type": "number", "default": 75},
            ]},
            {"id": "momentAmplification", "label": "Moment Amplification", "fields": [
                {"id": "frame", "label": "Frame", "type": "select", "default": "B",
                 "options": [{"value": "B", "label": "Braced"}, {"value": "S", "label": "Sway"}]},
                {"id": "Mend1", "label": "M end 1", "unit": "kNm", "type": "number", "default": 0},
                {"id": "Mend2", "label": "M end 2", "unit": "kNm", "type": "number", "default": 0},
            ]},
            {"id": "fire", "label": "Fire", "fields": [
                {"id": "G", "label": "G", "unit": "kN", "type": "number", "default": 0},
                {"id": "Q", "label": "Q", "unit": "kN", "type": "number", "default": 0},
                {"id": "fireload", "label": "Load type", "type": "select", "default": "F",
                 "options": [{"value": "F", "label": "Floor"}, {"value": "S", "label": "Storage"},
                             {"value": "R", "label": "Roof"}]},
                {"id": "ksm", "label": "ksm", "unit": "1/m", "type": "number", "default": 25},
            ]},
        ],
        "actions": [
            {"id": "optimise-weight", "label": "Find lightest satisfactory section"},
            {"id": "optimise-depth", "label": "Find shallowest satisfactory section"},
        ],
    }


def defaults() -> dict[str, Any]:
    """Blank input document consistent with the schema."""
    values: dict[str, Any] = {"memberType": "Rafter", "memberNumber": "0001",
                              "package": "Unallocated", "level": "",
                              "subject": DESCRIPTOR["defaultSubject"], "checks": {}}
    for group in schema()["groups"]:
        for field in group["fields"]:
            values[field["id"]] = field.get("default", "")
    for option in schema()["optional"]:
        values["checks"][option["id"]] = False
        for field in option["fields"]:
            values[field["id"]] = field.get("default", "")
    return values


# ---------------------------------------------------------------------------
#  Calculation
# ---------------------------------------------------------------------------
def compute(inputs: dict[str, Any]) -> dict[str, Any]:
    """Design result for one input document. Raises ValueError on bad input."""
    section = catalogue.resolve(inputs)
    return compute_design(section, inputs)


def render(inputs: dict[str, Any], result: dict[str, Any], *, standalone: bool = False,
           appendix: list[str] | None = None, anchor_prefix: str = "",
           contents_href: str = "") -> str:
    section = catalogue.resolve(inputs)
    return render_report(inputs, section, result, standalone=standalone, appendix=appendix,
                         anchor_prefix=anchor_prefix, contents_href=contents_href)


def summarise(result: dict[str, Any]) -> dict[str, Any]:
    utilisation = {key: value for key, value in (result.get("util") or {}).items()
                   if isinstance(value, (int, float)) and math.isfinite(value)}
    worst = max(utilisation.values(), default=0.0)
    governing = max(utilisation, key=lambda key: utilisation[key]) if utilisation else ""
    unattainable = [key for key, value in (result.get("util") or {}).items()
                   if not isinstance(value, (int, float)) or not math.isfinite(value)]
    if unattainable:
        label = CHECK_NAMES.get(unattainable[0], unattainable[0])
        return {"worstUtil": worst, "criticalCheck": label, "status": "FAIL",
                "headline": f"Capacity not attainable: {label}"}
    return {"worstUtil": worst, "criticalCheck": CHECK_NAMES.get(governing, governing),
            "status": "OK" if worst <= 1.0 else "FAIL",
            "headline": f"{worst * 100:.1f}% - {CHECK_NAMES.get(governing, governing)}"}


def identity(inputs: dict[str, Any]) -> dict[str, Any]:
    section = str(inputs.get("section") or "")
    return {"memberType": str(inputs.get("memberType") or "Member"),
            "memberNumber": str(inputs.get("memberNumber") or ""),
            "package": str(inputs.get("package") or "Unallocated"),
            "level": str(inputs.get("level") or ""),
            "calcType": DESCRIPTOR["calcType"],
            "title": f"{inputs.get('memberType', 'Member')} "
                     f"{inputs.get('memberNumber', '')} - {section}".strip()}


# ---------------------------------------------------------------------------
#  Inter-module data exchange
# ---------------------------------------------------------------------------
def exchange(inputs: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Values this calculation can pass to another module (see the module spec)."""
    section = catalogue.resolve(inputs)
    reactions = {"Vx": float(inputs.get("Vx") or 0.0), "Vy": float(inputs.get("Vy") or 0.0)}
    return {
        "schema": "innocalc.exchange/1",
        "source": {"module": MODULE_ID, "version": VERSION, **identity(inputs)},
        "axial": {"compression_kN": float(inputs.get("Nc") or 0.0),
                  "tension_kN": float(inputs.get("Nt") or 0.0)},
        "moments": {"Mx_kNm": float(inputs.get("Mx") or 0.0),
                    "My_kNm": float(inputs.get("My") or 0.0)},
        "reactions": {"support_kN": max(reactions.values(), default=0.0), **reactions},
        "geometry": {"length_mm": float(inputs.get("L") or 0.0),
                     "depth_mm": float(section.get("d") or section.get("b1") or 0.0),
                     "width_mm": float(section.get("bf") or section.get("b2") or 0.0)},
        "material": {"grade": str(inputs.get("grade") or "300"),
                     "fy_MPa": float(result.get("props", {}).get("fy") or 0.0)},
        "utilisation": summarise(result),
    }


ACCEPTS = ["axial", "moments", "reactions", "geometry"]


def accepts() -> list[str]:
    return list(ACCEPTS)


def apply_exchange(inputs: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Merge another module's exchange payload into this module's inputs."""
    values = dict(inputs)
    axial = payload.get("axial") or {}
    moments = payload.get("moments") or {}
    reactions = payload.get("reactions") or {}
    geometry = payload.get("geometry") or {}
    mapping = {"Nc": axial.get("compression_kN"), "Nt": axial.get("tension_kN"),
               "Mx": moments.get("Mx_kNm"), "My": moments.get("My_kNm"),
               "R": reactions.get("support_kN"), "L": geometry.get("length_mm")}
    for key, value in mapping.items():
        if value not in (None, ""):
            values[key] = value
    values.setdefault("linkedFrom", []).append(payload.get("source", {}))
    return values


# ---------------------------------------------------------------------------
#  Module actions and self-validation
# ---------------------------------------------------------------------------
def optimise(inputs: dict[str, Any], mode: str = "weight") -> dict[str, Any]:
    """Lightest or shallowest section in the selected family that passes every check."""
    family = str(inputs.get("secType") or "UB")
    satisfactory = []
    for record in catalogue.sections().get(family, []):
        try:
            result = compute_design(record, inputs)
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            continue
        if result.get("worstUtil", math.inf) <= 1.0:
            satisfactory.append((record, result))
    if not satisfactory:
        raise ValueError(f"No satisfactory {family} section for these actions")
    if mode == "depth":
        satisfactory.sort(key=lambda item: item[0].get("d") or item[0].get("b1") or 0.0)
    else:
        satisfactory.sort(key=lambda item: item[1]["props"]["weight"])
    record, result = satisfactory[0]
    return {"section": record["name"], "worstUtil": result["worstUtil"],
            "mode": mode, "considered": len(satisfactory)}


def run_action(action_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    if action_id in {"optimise-weight", "optimise-depth"}:
        outcome = optimise(inputs, "depth" if action_id.endswith("depth") else "weight")
        return {"inputs": {**inputs, "section": outcome["section"]}, "message":
                f"{outcome['section']} selected ({outcome['worstUtil'] * 100:.1f}% utilised)"}
    raise ValueError(f"Unknown action '{action_id}'")


def validate(cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Self-validation used during module refinement only.

    Without supplied cases the module checks internal consistency: every section
    in the catalogue computes, every utilisation is finite, and the reported
    governing check matches the largest utilisation.
    """
    if cases:
        return _validate_cases(cases)
    base = defaults()
    base.update({"Mx": 50.0, "Vx": 60.0, "L": 4000.0, "checks": {"compression": True}})
    failures = []
    tested = 0
    for family, records in catalogue.sections().items():
        for record in records:
            tested += 1
            trial = {**base, "secType": family, "section": record["name"]}
            try:
                result = compute_design(record, trial)
            except Exception as exc:  # noqa: BLE001 - report, do not mask
                failures.append({"section": record["name"], "error": repr(exc)})
                continue
            utilisation = result.get("util") or {}
            if not utilisation:
                failures.append({"section": record["name"], "error": "no utilisation returned"})
                continue
            worst = max(value for value in utilisation.values() if math.isfinite(value))
            if abs(worst - result["worstUtil"]) > 1e-9:
                failures.append({"section": record["name"],
                                 "error": f"worstUtil {result['worstUtil']} != {worst}"})
    return {"ok": not failures, "mode": "self-consistency", "module": MODULE_ID,
            "version": VERSION, "tested": tested, "failures": failures}


def _validate_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare computed values against expected values supplied by the caller.

    Each case is ``{"name", "inputs", "expect": {"dotted.path": value}, "tolerance"}``.
    """
    rows = []
    for case in cases:
        tolerance = float(case.get("tolerance", 0.01))
        try:
            result = compute(case["inputs"])
        except Exception as exc:  # noqa: BLE001 - report, do not mask
            rows.append({"name": case.get("name", ""), "ok": False, "error": repr(exc)})
            continue
        checks = []
        for path, expected in (case.get("expect") or {}).items():
            actual = _dig(result, path)
            deviation = (abs(actual - expected) / abs(expected)) if expected else abs(actual)
            checks.append({"path": path, "expected": expected, "actual": actual,
                           "deviation": deviation, "ok": deviation <= tolerance})
        rows.append({"name": case.get("name", ""), "ok": all(item["ok"] for item in checks),
                     "checks": checks})
    return {"ok": all(row["ok"] for row in rows), "mode": "worked-examples",
            "module": MODULE_ID, "version": VERSION, "tested": len(rows), "cases": rows}


def _dig(data: Any, path: str) -> float:
    for key in path.split("."):
        data = data[int(key)] if isinstance(data, list) else data[key]
    return float(data)
