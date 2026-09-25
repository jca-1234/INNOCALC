"""Adapter between InnoCalc Manager and the concrete beam and slab engine."""

from __future__ import annotations

import math
import tomllib
from copy import deepcopy
from importlib.resources import files
from typing import Any

from . import deflection, detailing, engine, flexure, materials, report
from .version import VERSION

DESCRIPTOR = {**tomllib.loads(files(__package__).joinpath("module.toml").read_text(encoding="utf-8")),
              "version": VERSION}

CHECK_LABELS = engine.CHECK_LABELS
ALWAYS_ON = engine.ALWAYS_ON

YES_NO = [{"value": "Y", "label": "Yes"}, {"value": "N", "label": "No"}]
CLASSES = [{"value": "N", "label": "N - Normal ductility"}, {"value": "L", "label": "L - Low ductility"}]
MODES = [{"value": "N", "label": "Number of bars"}, {"value": "S", "label": "Bar centres (mm)"},
         {"value": "A", "label": "Area (mm2)"}]
CALC_MANUAL = [{"value": "C", "label": "Calculated"}, {"value": "M", "label": "Manual"}]


def _bars(key: str, label: str, default: str) -> dict[str, Any]:
    return {"id": key, "label": label, "type": "select", "default": default,
            "options": [{"value": f"{size:g}", "label": f"{size:g} mm"} for size in engine.BAR_SIZES]}


def _grades(key: str, label: str) -> dict[str, Any]:
    return {"id": key, "label": label, "type": "select", "default": "500",
            "options": [{"value": f"{grade:g}", "label": f"{grade:g} MPa"}
                        for grade in engine.YIELD_STRENGTHS]}


def _yes_no(key: str, label: str, default: str, help_text: str = "") -> dict[str, Any]:
    field = {"id": key, "label": label, "type": "select", "default": default, "options": YES_NO}
    if help_text:
        field["help"] = help_text
    return field


def _num(key: str, label: str, default: float, unit: str = "", help_text: str = "",
         show: dict[str, list[str]] | None = None) -> dict[str, Any]:
    field: dict[str, Any] = {"id": key, "label": label, "type": "number", "default": default}
    if unit:
        field["unit"] = unit
    if help_text:
        field["help"] = help_text
    if show:
        field["showWhen"] = show
    return field


def descriptor() -> dict[str, Any]:
    return deepcopy(DESCRIPTOR)


def schema() -> dict[str, Any]:
    flanged = {"sectionType": ["F"]}
    beam = {"sectionType": ["R", "F"]}
    return {
        **descriptor(),
        "identity": {"typeLabel": "Member type", "numberLabel": "Member number",
                     "typeOptions": ["Beam", "Band beam", "Slab", "Transfer beam"]},
        "groups": [
            {"id": "geometry", "title": "Section and material", "fields": [
                {"id": "sectionType", "label": "Section type", "type": "select", "default": "R",
                 "options": [{"value": "S", "label": "Slab (1 m strip)"},
                             {"value": "R", "label": "Rectangular beam"},
                             {"value": "F", "label": "Flanged T or L beam"}]},
                _num("fc", "Concrete strength f'c", 32.0, "MPa", "20 to 120 MPa, Cl 1.1.2"),
                _num("D", "Overall depth D", 600.0, "mm"),
                _num("W", "Web width W", 400.0, "mm", show=beam),
                _num("Bf", "Flange width Bf", 1200.0, "mm", "Actual flange; bef limits it",
                     show=flanged),
                _num("Tf", "Flange thickness Tf", 150.0, "mm", show=flanged),
                {"id": "btype", "label": "Flanged beam type", "type": "select", "default": "T",
                 "options": [{"value": "T", "label": "T-beam"}, {"value": "L", "label": "L-beam"}],
                 "showWhen": flanged},
                _num("Lm", "Span L", 6000.0, "mm", "Effective span; also used for bef and deflection"),
                {"id": "supportType", "label": "Support for zero-moment length a", "type": "select",
                 "default": "S", "options": [{"value": "S", "label": "Simple, a = L"},
                                             {"value": "C", "label": "Continuous, a = 0.7 L"},
                                             {"value": "M", "label": "Manual factor"}],
                 "showWhen": flanged},
                _num("mke", "Manual a / L", 0.7, "", show={"supportType": ["M"]}),
                {"id": "slabType", "label": "Slab type (alpha.b)", "type": "select", "default": "O",
                 "options": [{"value": key, "label": label}
                             for key, label in flexure.SLAB_TYPES.items()],
                 "help": "Cl 8.1.6.1 and Cl 9.1.1", "showWhen": {"sectionType": ["S"]}},
                _num("density", "Concrete density", 2400.0, "kg/m3", "Cl 3.1.3"),
                _yes_no("useFcmi", "Use fcmi for Ec", "N", "No uses fcmi = f'c"),
            ]},
            {"id": "reinforcement", "title": "Reinforcement", "fields": [
                _bars("barBot", "Bottom bar size", "20"),
                {"id": "botMode", "label": "Bottom bars given as", "type": "select", "default": "N",
                 "options": MODES},
                _num("botValue", "Bottom number, centres or area", 4.0, "",
                     "Bars, mm centres or mm2 as selected"),
                _bars("barTop", "Top bar size", "12"),
                {"id": "topMode", "label": "Top bars given as", "type": "select", "default": "N",
                 "options": MODES},
                _num("topValue", "Top number, centres or area", 2.0),
                _grades("fsy", "Yield strength fsy"),
                {"id": "classBot", "label": "Bottom ductility class", "type": "select",
                 "default": "N", "options": CLASSES},
                {"id": "classTop", "label": "Top ductility class", "type": "select",
                 "default": "N", "options": CLASSES},
                _num("cover", "Bottom cover", 30.0, "mm", "To fitments for beams, to bars for slabs"),
                _num("coverTop", "Top cover", 30.0, "mm"),
                _num("coverSide", "Side cover", 30.0, "mm", show=beam),
                {"id": "ligs", "label": "Fitment bar size", "type": "select", "default": "10",
                 "options": [{"value": f"{size:g}", "label": "None" if size == 0 else f"{size:g} mm"}
                             for size in engine.FITMENT_SIZES]},
                _num("clearBot", "Bottom horizontal clear gap", 50.0, "mm"),
                _num("vclearBot", "Bottom vertical clear gap", 50.0, "mm"),
                _num("clearTop", "Top horizontal clear gap", 50.0, "mm"),
                _num("vclearTop", "Top vertical clear gap", 50.0, "mm"),
                _yes_no("extend", "Top bars extend into bef", "N", "Flanged beams, Cl 8.6.1(b)"),
            ]},
            {"id": "actions", "title": "Bending actions", "fields": [
                _num("Mstar", "Design moment M*", 170.0, "kNm", "+ve bottom tension; kNm/m for slabs"),
                {"id": "ms1Mode", "label": "Ms1* (psi.s = 1)", "type": "select", "default": "D",
                 "options": [{"value": "D", "label": "Estimate 0.75 M*"},
                             {"value": "M", "label": "Enter value"}]},
                _num("Ms1", "Service moment Ms1*", 187.5, "kNm", show={"ms1Mode": ["M"]}),
                {"id": "msMode", "label": "Ms* (psi.s)", "type": "select", "default": "D",
                 "options": [{"value": "D", "label": "Estimate 0.65 M*"},
                             {"value": "M", "label": "Enter value"}]},
                _num("Ms", "Service moment Ms*", 162.5, "kNm", show={"msMode": ["M"]}),
                {"id": "astMinBasis", "label": "Minimum steel basis", "type": "select",
                 "default": "M", "options": [{"value": "D", "label": "Deemed-to-comply"},
                                             {"value": "A", "label": "Actual (Muo)min"},
                                             {"value": "M", "label": "Lesser of the two"}]},
            ]},
            {"id": "serviceability", "title": "Crack control, creep and shrinkage", "fields": [
                _yes_no("enclosed", "Fully enclosed, wider cracks tolerated", "N"),
                {"id": "wmax", "label": "Maximum crack width w'max", "type": "select",
                 "default": "0.3", "options": [{"value": f"{w:g}", "label": f"{w:g} mm"}
                                               for w in (0.2, 0.3, 0.4)]},
                _yes_no("withSteel", "Include reinforcement in Iuncr", "Y"),
                _yes_no("useBef", "Use bef for gross properties", "Y", "No uses Bf"),
                {"id": "environment", "label": "Environment", "type": "select", "default": "T",
                 "options": [{"value": key, "label": label}
                             for key, label in materials.ENVIRONMENTS.items()],
                 "help": "Cl 3.1.7.2"},
                {"id": "shrinkageMode", "label": "Basic drying shrinkage", "type": "select",
                 "default": "S", "options": [{"value": "S", "label": "Standard, 800 x 1e-6"},
                                             {"value": "T", "label": "Tested value"}]},
                _num("ecsdbTested", "Tested eps.csd.b*", 800.0, "x1e-6",
                     show={"shrinkageMode": ["T"]}),
                _num("tDays", "Time after drying t", 10950.0, "days"),
                _num("tauDays", "Age at loading tau", 28.0, "days"),
                {"id": "thMode", "label": "Hypothetical thickness", "type": "select",
                 "default": "C", "options": CALC_MANUAL},
                _num("thManual", "Manual th", 100.0, "mm", show={"thMode": ["M"]}),
                {"id": "ecsMode", "label": "Design shrinkage strain", "type": "select",
                 "default": "C", "options": CALC_MANUAL},
                _num("ecsManual", "Manual eps.cs", 655.0, "x1e-6", show={"ecsMode": ["M"]}),
                {"id": "fccMode", "label": "Creep coefficient", "type": "select", "default": "C",
                 "options": CALC_MANUAL},
                _num("fccManual", "Manual phi.cc", 2.5, "", show={"fccMode": ["M"]}),
                _num("sigmaO", "Sustained stress sigma.o", 0.0, "MPa", "Cl 3.1.8.3 k6"),
            ]},
            {"id": "shear", "title": "Shear and torsion", "fields": [
                _num("Vstar", "Design shear V*", 110.0, "kN"),
                _num("MstarV", "Coexisting moment M*", 85.0, "kNm", "+ve bottom tension"),
                _num("MmaxV", "Section maximum moment Mmax*", 0.0, "kNm", "0 uses M*"),
                _num("NstarV", "Axial force N*", 0.0, "kN", "Compression positive"),
                _num("Tstar", "Design torsion T*", 0.0, "kNm"),
                {"id": "shearMethod", "label": "kv and theta.v method", "type": "select",
                 "default": "G", "options": [{"value": "G", "label": "General, Cl 8.2.4.2"},
                                             {"value": "S", "label": "Simplified, Cl 8.2.4.3"}]},
                _num("dg", "Maximum aggregate size dg", 20.0, "mm"),
                _yes_no("lightweight", "Lightweight concrete", "N"),
                _yes_no("compCracked", "Cracking in compression zone", "N", "Cl 8.2.4.5"),
                _yes_no("ignoreLigs", "Ignore fitments", "N"),
                _num("s", "Fitment spacing s", 200.0, "mm"),
                _num("legs", "Fitment legs", 2.0, "", "Per cross-section; per metre for slabs"),
                _grades("fsyf", "Fitment yield strength fsy.f"),
                {"id": "classFit", "label": "Fitment ductility class", "type": "select",
                 "default": "N", "options": CLASSES},
                _num("alphaV", "Fitment angle alpha.v", 90.0, "deg"),
                _yes_no("increaseSpacing", "Allow 0.75 D / 500 mm spacing", "Y",
                        "Applied only where V* <= phi.Vu.min, Cl 8.3.2.2"),
                _yes_no("waiveSpacing", "Waive maximum spacing", "N"),
                _yes_no("waiveTransverse", "Waive transverse spacing", "N"),
                _yes_no("waiveDeep", "Waive D >= 750 mm fitments", "N"),
                {"id": "actDefinition", "label": "Act for eps.x", "type": "select",
                 "default": "AS3600", "options": [
                     {"value": "AS3600", "label": "AS 3600: mid-depth to tension face"},
                     {"value": "AS5100", "label": "AS 5100.5: uncracked tension zone"}]},
                _yes_no("limitTtd", "Limit Ttd to Mmax* requirement", "N"),
                _num("AstManual", "Manual tension steel", 0.0, "mm2", "0 uses the design steel"),
                _num("AscManual", "Manual compression steel", 0.0, "mm2", "0 uses the design steel"),
            ]},
            {"id": "deemed", "title": "Deemed-to-comply deflection", "fields": [
                {"id": "spanType", "label": "Span type", "type": "select", "default": "S",
                 "options": [{"value": key, "label": label}
                             for key, label in deflection.SPAN_TYPES.items()]},
                {"id": "spans", "label": "Number of spans", "type": "select", "default": "2",
                 "options": [{"value": "2", "label": "2"}, {"value": "3", "label": "More than 2"}]},
                _num("wsdl", "Superimposed dead load", 10.0, "kN/m", "kPa for slabs"),
                _num("wll", "Live load", 12.0, "kN/m", "kPa for slabs"),
                {"id": "loadTypeDefl", "label": "Live load type", "type": "select", "default": "N",
                 "options": [{"value": "N", "label": "N - Normal"}, {"value": "S", "label": "S - Storage"}],
                 "help": "AS/NZS 1170.0 Table 4.1"},
                _num("lefDelta", "Total deflection limit Lef/Delta", 250.0, "", "Table 2.3.2"),
                _num("lefDeltaInc", "Incremental deflection limit Lef/Delta", 500.0, "",
                     "Table 2.3.2"),
                _num("k3", "Slab factor k3", 1.0, "", "1.0 for one-way slabs",
                     show={"sectionType": ["S"]}),
            ]},
        ],
        "optional": [
            {"id": "crackWidth", "label": "Calculated crack width (Cl 8.6.2.3)", "fields": [
                {"id": "barShapeBot", "label": "Bottom bar shape", "type": "select",
                 "default": "D", "options": [{"value": "D", "label": "Deformed"},
                                             {"value": "P", "label": "Plain"}]},
                {"id": "barShapeTop", "label": "Top bar shape", "type": "select", "default": "D",
                 "options": [{"value": "D", "label": "Deformed"}, {"value": "P", "label": "Plain"}]},
                _num("NstarCrack", "Axial force N*", 0.0, "kN", "Tension negative"),
            ]},
            {"id": "calcDeflection", "label": "Calculated deflection (Cl 8.5.3)", "fields": [
                *[_num(f"m{key}", f"M* at {name}", value, "kNm")
                  for key, name, value in (("L", "left", 0.0), ("X", "position x", 170.0),
                                           ("R", "right", 0.0))],
                *[_num(f"ms{key}", f"Ms* at {name}", value, "kNm")
                  for key, name, value in (("L", "left", 0.0), ("X", "position x", 110.0),
                                           ("R", "right", 0.0))],
                *[_num(f"topAs{key}", f"Top steel at {key}", 0.0, "mm2",
                       "0 uses the steel required; negative sets zero")
                  for key in deflection.POSITIONS],
                *[_num(f"botAs{key}", f"Bottom steel at {key}", 0.0, "mm2",
                       "0 uses the steel required; negative sets zero")
                  for key in deflection.POSITIONS],
                _num("deltaDL", "Gross dead load deflection", 1.3, "mm", "Elastic, from analysis"),
                _num("deltaLL", "Gross live load deflection", 1.0, "mm", "Elastic, from analysis"),
                _num("psiSDefl", "Short-term factor psi.s", 0.7),
                _num("psiLDefl", "Long-term factor psi.l", 0.4),
                _yes_no("useFcs", "Include shrinkage stress sigma.cs", "Y", "Cl 8.5.3.1"),
                _num("limDL", "Dead load limit span /", 300.0),
                _num("absDL", "Dead load absolute limit", 0.0, "mm", "0 for none"),
                _num("limLL", "Live load limit span /", 300.0),
                _num("absLL", "Live load absolute limit", 0.0, "mm", "0 for none"),
                _num("limInc", "Incremental limit span /", 500.0),
                _num("absInc", "Incremental absolute limit", 0.0, "mm", "0 for none"),
                _num("limTotal", "Total limit span /", 250.0),
                _num("absTotal", "Total absolute limit", 0.0, "mm", "0 for none"),
                _num("cutoff", "End moment cut-off", 15.0, "%"),
                {"id": "creepSpanType", "label": "Span type for WRH creep and shrinkage",
                 "type": "select", "default": "S",
                 "options": [{"value": key, "label": label}
                             for key, label in deflection.CREEP_SPAN_TYPES.items()]},
            ]},
            {"id": "slenderness", "label": "Lateral restraint (Cl 8.9)", "fields": [
                _num("restraintSpacing", "Lateral restraint spacing", 6000.0, "mm"),
                _yes_no("cantilever", "Cantilever", "N"),
            ]},
            {"id": "secondary", "label": "Slab shrinkage and temperature steel (Cl 9.5.3)",
             "fields": [
                 {"id": "restraint", "label": "Restraint condition", "type": "select",
                  "default": "IMOD", "options": [{"value": key, "label": label}
                                                 for key, (label, _) in detailing.RESTRAINT.items()]},
                 _num("sigmaCp", "Average prestress sigma.cp", 0.0, "MPa"),
                 _num("AsSecondary", "Secondary steel provided", 0.0, "mm2/m",
                      "Each face when D > 500 mm"),
             ]},
        ],
        "alwaysOn": {key: True for key in ALWAYS_ON},
        "actions": [],
    }


def defaults() -> dict[str, Any]:
    values: dict[str, Any] = {
        "memberType": "Beam", "memberNumber": "B01", "package": "Unallocated", "level": "",
        "subject": DESCRIPTOR["defaultSubject"],
        "checks": dict(schema()["alwaysOn"]),
    }
    layout = schema()
    for group in layout["groups"]:
        for field in group["fields"]:
            values[field["id"]] = field["default"]
    for group in layout["optional"]:
        values["checks"][group["id"]] = False
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
    util = result["util"]
    key = max(util, key=lambda name: util[name])
    ratio = util[key]
    status = "OK" if math.isfinite(ratio) and ratio <= 1.0 else "FAIL"
    return {"worstUtil": result["worstUtil"], "criticalCheck": CHECK_LABELS[key],
            "status": status, "headline": f"{ratio * 100:.1f}% - {CHECK_LABELS[key]}"
            if math.isfinite(ratio) else f"Unattainable - {CHECK_LABELS[key]}"}


def identity(inputs: dict[str, Any]) -> dict[str, Any]:
    member_type = str(inputs.get("memberType") or "Beam")
    number = str(inputs.get("memberNumber") or "")
    kind = str(inputs.get("sectionType") or "R").strip().upper()
    if kind == "S":
        size = f"{_plain(inputs.get('D'))} thick slab"
    else:
        size = f"{_plain(inputs.get('D'))} x {_plain(inputs.get('W'))}"
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
