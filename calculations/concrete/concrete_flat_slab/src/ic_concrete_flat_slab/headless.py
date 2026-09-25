"""Adapter between InnoCalc Manager and the flat slab engine."""

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
    "spanRatio": "Span ratio Ly/Lx not exceeding 2",
    "liveLoadRatio": "Live load not exceeding twice the dead load",
    "liveLoadDeflection": "Live load not exceeding dead load (deflection)",
    "ductilityClass": "Class N flexural reinforcement",
    "distributionRange": "Column strip factors within Table 6.9.5.3",
    "flexure": "Flexural capacity",
    "ductility": "Ductility ku <= 0.36",
    "flexuralMinimum": "Minimum reinforcement at each location",
    "barSpacing": "Maximum bar spacing",
    "shrinkage": "Shrinkage and temperature reinforcement",
}
ALWAYS_ON = ("deflectionTotal", "deflectionIncremental", "minimumSteel", "spanRatio",
             "liveLoadRatio", "liveLoadDeflection", "ductilityClass")

YES_NO = [{"value": "Y", "label": "Yes"}, {"value": "N", "label": "No"}]
BARS = [{"value": f"{size:g}", "label": f"{size:g} mm"} for size in engine.BAR_SIZES]


def _layer_fields(key: str, label: str, bar: str, spacing: float) -> list[dict[str, Any]]:
    return [
        {"id": f"bar{key}", "label": f"{label} bar", "type": "select", "default": bar,
         "options": BARS},
        {"id": f"s{key}", "label": f"{label} spacing", "type": "number", "unit": "mm",
         "default": spacing},
    ]


def _factor_fields(prefix: str, label: str, factors: tuple[float, ...]) -> list[dict[str, Any]]:
    return [{"id": f"{prefix}{index}", "label": f"{label}, {position.lower()}",
             "type": "number", "default": factor, "help": "Share of the strip moment, 0 to 1"}
            for index, (position, factor) in enumerate(zip(engine.POSITIONS, factors), start=1)]


def descriptor() -> dict[str, Any]:
    return deepcopy(DESCRIPTOR)


def schema() -> dict[str, Any]:
    return {
        **descriptor(),
        "identity": {"typeLabel": "Member type", "numberLabel": "Member number",
                     "typeOptions": ["Flat slab", "Flat plate", "Slab"]},
        "groups": [
            {"id": "geometry", "title": "Geometry and material", "fields": [
                {"id": "Ly", "label": "Longer span Ly", "type": "number", "unit": "mm",
                 "default": 7000.0, "help": "Column centreline spacing"},
                {"id": "Lx", "label": "Shorter span Lx", "type": "number", "unit": "mm",
                 "default": 6000.0, "help": "Column centreline spacing"},
                {"id": "Oy", "label": "Edge overhang Oy", "type": "number", "unit": "mm",
                 "default": 200.0, "help": "Slab beyond the edge column line, Ly direction"},
                {"id": "Ox", "label": "Edge overhang Ox", "type": "number", "unit": "mm",
                 "default": 200.0, "help": "Slab beyond the edge column line, Lx direction"},
                {"id": "Cy", "label": "Column dimension Cy", "type": "number", "unit": "mm",
                 "default": 400.0, "help": "Parallel to Ly"},
                {"id": "Cx", "label": "Column dimension Cx", "type": "number", "unit": "mm",
                 "default": 400.0, "help": "Parallel to Lx"},
                {"id": "th", "label": "Slab thickness th", "type": "number", "unit": "mm",
                 "default": 250.0, "help": "Excluding drop panels"},
                {"id": "hasDrop", "label": "Drop panels", "type": "select", "default": "Y",
                 "options": YES_NO, "help": "L/6 each way, 0.3 th deep"},
                {"id": "slabType", "label": "Exterior edge condition", "type": "select",
                 "default": "I", "options": [
                     {"value": "S", "label": "S - Unrestrained (simple)"},
                     {"value": "I", "label": "I - Integral columns"},
                     {"value": "C", "label": "C - Columns and edge beam"},
                     {"value": "F", "label": "F - Fully restrained (walls)"}],
                 "help": "Table 6.10.4.3"},
                {"id": "limitStrip", "label": "Limit interior column strip to L/2",
                 "type": "select", "default": "N", "options": YES_NO, "help": "WRH"},
                {"id": "reo", "label": "Reinforcement ductility class", "type": "select",
                 "default": "N", "options": [{"value": "N", "label": "N - Normal"},
                                             {"value": "L", "label": "L - Low"}],
                 "help": "Class L not permitted, Cl 6.10.4.1(i)"},
                {"id": "fc", "label": "Concrete strength f'c", "type": "number", "unit": "MPa",
                 "default": 32.0, "help": "20 to 120 MPa, Cl 1.1.2"},
            ]},
            {"id": "loading", "title": "Service actions", "fields": [
                {"id": "wdl", "label": "Dead load wdl", "type": "number", "unit": "kPa",
                 "default": 6.25, "help": "Including slab self weight (25 kN/m3)"},
                {"id": "wsdl", "label": "Superimposed dead load wsdl", "type": "number",
                 "unit": "kPa", "default": 1.0},
                {"id": "wll", "label": "Live load wll", "type": "number", "unit": "kPa",
                 "default": 3.0},
                {"id": "loadType", "label": "Live load type", "type": "select", "default": "N",
                 "options": [{"value": key, "label": f"{key} - {label}"}
                             for key, label in engine.LOAD_TYPES.items()],
                 "help": "AS/NZS 1170.0 Table 4.1"},
            ]},
            {"id": "serviceability", "title": "Reinforcement and deflection", "fields": [
                {"id": "spanType", "label": "Span type for deflection", "type": "select",
                 "default": "E", "options": [{"value": key, "label": label}
                                             for key, label in engine.SPAN_TYPES.items()],
                 "help": "k4 = 2.1 interior, 1.75 end span"},
                {"id": "bar", "label": "Nominal bar size", "type": "select", "default": "16",
                 "options": BARS},
                {"id": "cover", "label": "Cover to bottom steel", "type": "number", "unit": "mm",
                 "default": 25.0},
                {"id": "insideLayer", "label": "Base ds on inside layer", "type": "select",
                 "default": "Y", "options": YES_NO},
                {"id": "Ast", "label": "Tensile steel Ast", "type": "number", "unit": "mm2/m",
                 "default": 1000.0, "help": "Bottom steel in the positive moment region"},
                {"id": "fsy", "label": "Yield strength fsy", "type": "select", "default": "500",
                 "options": [{"value": f"{grade:g}", "label": f"{grade:g} MPa"}
                             for grade in engine.YIELD_STRENGTHS]},
                {"id": "Asc", "label": "Compression steel Asc", "type": "number", "unit": "mm2/m",
                 "default": 0.0},
                {"id": "dc", "label": "Depth to compression steel dc", "type": "number",
                 "unit": "mm", "default": 44.0, "help": "Measured from the top face"},
                {"id": "useFcmi", "label": "Use fcmi for Ec", "type": "select", "default": "Y",
                 "options": YES_NO, "help": "No uses fcmi = f'c"},
                {"id": "density", "label": "Concrete density", "type": "number", "unit": "kg/m3",
                 "default": 2400.0, "help": "Cl 3.1.3"},
                {"id": "lefDelta", "label": "Total deflection limit Lef/Delta", "type": "number",
                 "default": 250.0, "help": "Table 2.3.2"},
                {"id": "lefDeltaInc", "label": "Incremental deflection limit Lef/Delta",
                 "type": "number", "default": 500.0, "help": "Table 2.3.2"},
            ]},
        ],
        "optional": [
            {"id": "customSupports", "label": "Custom support lengths (sum of a_sup)", "fields": [
                {"id": field, "label": f"Sum of a_sup, {engine.SUPPORT_LABELS[key].lower()}",
                 "type": "number", "unit": "mm", "default": 400.0}
                for key, field in engine.CUSTOM_SUPPORT_FIELDS.items()]},
            {"id": "customDistribution", "label": "Custom column strip distribution", "fields": [
                *_factor_fields("cf", "Column strip factor", engine.COEFF_COLUMN[2]),
                *_factor_fields("ef", "Edge column strip factor", engine.COEFF_EDGE[2]),
            ]},
            {"id": "flexure", "label": "Flexural capacity of each strip", "fields": [
                {"id": "coverTop", "label": "Cover to top steel", "type": "number", "unit": "mm",
                 "default": 25.0},
                *_layer_fields("Ct", "Column strip top", "16", 150.0),
                *_layer_fields("Cb", "Column strip bottom", "12", 200.0),
                *_layer_fields("Mt", "Middle strip top", "12", 300.0),
                *_layer_fields("Mb", "Middle strip bottom", "12", 250.0),
                *_layer_fields("Et", "Edge column strip top", "16", 200.0),
                *_layer_fields("Eb", "Edge column strip bottom", "12", 200.0),
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
        "memberType": "Flat slab", "memberNumber": "FS01", "package": "Unallocated", "level": "",
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
            if math.isfinite(ratio) else f"Not satisfied - {CHECK_LABELS[key]}"}


def identity(inputs: dict[str, Any]) -> dict[str, Any]:
    member_type = str(inputs.get("memberType") or "Flat slab")
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
