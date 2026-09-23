"""Calculation-pad presentation for the concrete stair module."""

from __future__ import annotations

from html import escape
from typing import Any

import calcpad

from .engine import DEFLECTION_BASIS, DUCTILITY_CLASSES, LOAD_TYPES, REINFORCEMENT_MODES

DATA_ID = "concrete-stair-inputs"
DEFAULT_SUBJECT = "Concrete stair design"

CHECK_ROWS = [
    ("bending", "Bending", "M* / phiMuo", "Cl 9.1"),
    ("minimumSteel", "Minimum reinforcement", "Ast.min / Ast", "Cl 9.1.1, Eq 8.1.6.1(2)"),
    ("ductility", "Section ductility", "kuo / 0.36", "Cl 8.1.5"),
    ("deflection", "Minimum thickness, total deflection", "th.min / ath", "Cl 9.4.4"),
    ("deflectionIncremental", "Minimum thickness, incremental deflection",
     "th.min.inc / ath", "Cl 9.4.4"),
]


def _paragraphs(items: list[str]) -> str:
    return "".join(f"<p>{escape(str(item))}</p>" for item in items)


def render(inputs: dict[str, Any], result: dict[str, Any], *, standalone: bool = False,
           appendix: list[str] | None = None, anchor_prefix: str = "",
           contents_href: str = "") -> str:
    blocks = [
        _basis(result),
        _summary(result),
        _geometry(result),
        _loading(result),
        _reinforcement(result),
        _bending(result),
        _service(result),
        _thickness(result),
    ]
    notes = list(result.get("unattainable") or []) + list(result.get("warnings") or [])
    if notes:
        blocks.append(calcpad.prose("Warnings", _paragraphs(notes), weight=2 + 2 * len(notes)))
    return calcpad.render(inputs, blocks, standalone=standalone, appendix=appendix,
                          anchor_prefix=anchor_prefix, contents_href=contents_href,
                          default_subject=DEFAULT_SUBJECT, data_id=DATA_ID)


def _basis(result: dict[str, Any]) -> str:
    body = ("<p><strong>Every area, load, moment and capacity below is per metre width of "
            "flight.</strong></p>"
            "<p><strong>Assumptions</strong></p>" + _paragraphs(result["assumptions"])
            + "<p><strong>Limitations and exclusions</strong></p>"
            + _paragraphs(result["limitations"]))
    return calcpad.prose("Design basis", body,
                         weight=8 + len(result["assumptions"]) + len(result["limitations"]))


def _summary(result: dict[str, Any]) -> str:
    geometry, reo = result["geometry"], result["reinforcement"]
    rows = [
        calcpad.row("Stair", "Span, throat, f'c",
                    f"{escape(geometry['label'])}, span {calcpad.number(geometry['L'], 0)} mm, "
                    f"throat {calcpad.number(geometry['th'], 0)} mm, "
                    f"f'c = {calcpad.number(result['material']['fc'], 0)} MPa"),
        calcpad.row("Main reinforcement", "Bar and spacing",
                    f"{escape(reo['class'])}{calcpad.number(reo['bar'], 0)} at "
                    f"{calcpad.number(reo['cts'], 0)} centres, "
                    f"{calcpad.number(reo['Ast'], 0)} mm2/m"),
    ]
    for key, label, expression, reference in CHECK_ROWS:
        rows.append(calcpad.row(label, expression, calcpad.badge(result["util"][key]), reference))
    rows.append(calcpad.row("Governing", "Maximum finite utilisation",
                            calcpad.badge(result["worstUtil"])))
    return calcpad.table("Design summary", rows)


def _geometry(result: dict[str, Any]) -> str:
    geometry = result["geometry"]
    rows = [
        calcpad.row("Horizontal span", "L", f"{calcpad.number(geometry['L'], 0)} mm"),
        calcpad.row("Flight width", "W", f"{calcpad.number(geometry['W'], 0)} mm"),
        calcpad.row("Throat thickness", "th", f"{calcpad.number(geometry['th'], 0)} mm",
                    "Perpendicular to the soffit"),
        calcpad.row("Riser", "riser", f"{calcpad.number(geometry['riser'], 0)} mm"),
        calcpad.row("Going", "going", f"{calcpad.number(geometry['going'], 0)} mm"),
        calcpad.row("Hypotenuse of the step", "ang = sqrt(riser^2 + going^2)",
                    f"{calcpad.number(geometry['ang'], 3)} mm"),
        calcpad.row("Vertical average thickness factor", "f = ang / going",
                    calcpad.number(geometry["f"], 6)),
        calcpad.row("Incline", "theta = atan(riser / going)",
                    f"{calcpad.number(geometry['incline'], 3)} deg"),
        calcpad.row("Average thickness", "ath = th + going/ang x riser/2",
                    f"{calcpad.number(geometry['ath'], 2)} mm"),
        calcpad.row("Depth to the steel", "ds = th - cover - db/2",
                    f"{calcpad.number(geometry['ds'], 1)} mm"),
        calcpad.row("Effective depth for bending", "eds",
                    f"{calcpad.number(geometry['eds'], 1)} mm",
                    "Vertical f x ds, or perpendicular ds"),
        calcpad.row("Depth for minimum steel", "D",
                    f"{calcpad.number(geometry['D'], 1)} mm"),
    ]
    return calcpad.table("Geometry", rows)


def _loading(result: dict[str, Any]) -> str:
    loads, material = result["loads"], result["material"]
    rows = [
        calcpad.row("Concrete unit weight", "gamma.c",
                    f"{calcpad.number(result['inputs']['conc'], 1)} kN/m3"),
        calcpad.row("Self weight", "wdl = gamma.c x ath / 1000 x f",
                    f"{calcpad.number(loads['wdl'], 4)} kPa"),
        calcpad.row("Superimposed dead load", "wsdl",
                    f"{calcpad.number(loads['wsdl'], 3)} kPa"),
        calcpad.row("Live load", "wll", f"{calcpad.number(loads['wll'], 3)} kPa"),
        calcpad.row("Design load", "w* = max(1.35 G, 1.2 G + 1.5 Q)",
                    f"{calcpad.number(loads['wstar'], 4)} kPa",
                    f"AS/NZS 1170.0, {escape(loads['case'])}"),
        calcpad.row("Design moment", "M* = w* L^2 / 8",
                    f"{calcpad.moment(loads['Mstar'])} kNm/m"),
        calcpad.row("Live load type",
                    escape(LOAD_TYPES[result["inputs"]["loadtype"]]["label"]),
                    f"psi_s = {calcpad.number(loads['psiS'], 2)}, "
                    f"psi_l = {calcpad.number(loads['psiL'], 2)}",
                    "AS/NZS 1170.0 Table 4.1"),
        calcpad.row("Concrete strength", "f'c", f"{calcpad.number(material['fc'], 0)} MPa",
                    "Cl 1.1.2, 20 to 120 MPa"),
    ]
    return calcpad.table("Loading", rows)


def _reinforcement(result: dict[str, Any]) -> str:
    reo = result["reinforcement"]
    rows = [
        calcpad.row("Entry mode", escape(REINFORCEMENT_MODES[reo["mode"]]),
                    calcpad.number(result["inputs"]["reoValue"], 1)),
        calcpad.row("Bar size", "db", f"{calcpad.number(reo['bar'], 0)} mm"),
        calcpad.row("Yield strength", "fsy", f"{calcpad.number(reo['fsy'], 0)} MPa"),
        calcpad.row("Ductility class", escape(DUCTILITY_CLASSES[reo["ductility"]]), ""),
        calcpad.row("Bars per metre", "nbars", calcpad.number(reo["nbars"], 3)),
        calcpad.row("Bar centres", "cts = 1000 / nbars",
                    f"{calcpad.number(reo['cts'], 1)} mm"),
        calcpad.row("Steel area", "Ast", f"{calcpad.number(reo['Ast'], 1)} mm2/m"),
        calcpad.row("Minimum steel", "Ast.min = 0.2 (D/eds)^2 x 0.6 sqrt(f'c) / fsy x 1000 eds",
                    f"{calcpad.number(reo['Astmin'], 1)} mm2/m", "Eq 8.1.6.1(2)"),
        calcpad.row("Utilisation", "Ast.min / Ast",
                    calcpad.badge(result["util"]["minimumSteel"])),
    ]
    return calcpad.table("Main reinforcement", rows)


def _bending(result: dict[str, Any]) -> str:
    bending = result["bending"]
    rows = [
        calcpad.row("Stress block intensity", "alpha2 = 0.85 - 0.0015 f'c",
                    calcpad.number(bending["alpha2"], 4), "Eq 8.1.3(1), not less than 0.67"),
        calcpad.row("Stress block depth ratio", "gamma = 0.97 - 0.0025 f'c",
                    calcpad.number(bending["gamma"], 4), "Eq 8.1.3(2), not less than 0.67"),
        calcpad.row("Neutral axis parameter",
                    "kuo = fsy Ast / (alpha2 f'c gamma 1000 ds)",
                    calcpad.number(bending["kuo"], 6)),
        calcpad.row("Ductility utilisation", "kuo / 0.36",
                    calcpad.badge(result["util"]["ductility"]), "Cl 8.1.5"),
        calcpad.row("Capacity reduction factor", "phi",
                    calcpad.number(bending["phi"], 4), "Table 2.2.2(b)"),
        calcpad.row("Design capacity",
                    "phiMuo = phi fsy Ast eds [1 - fsy Ast / (2 alpha2 f'c 1000 eds)]",
                    f"{calcpad.moment(bending['phiMuo'])} kNm/m", "Cl 9.1"),
        calcpad.row("Design moment", "M*", f"{calcpad.moment(bending['Mstar'])} kNm/m"),
        calcpad.row("Utilisation", "M* / phiMuo", calcpad.badge(result["util"]["bending"])),
    ]
    return calcpad.table("Bending - Section 9.1", rows)


def _service(result: dict[str, Any]) -> str:
    deflection, material = result["deflection"], result["material"]
    rows = [
        calcpad.row("Mean in-situ strength", "fcmi",
                    f"{calcpad.number(material['fcmi'], 3)} MPa", "Table 3.1.2"),
        calcpad.row("Modulus of elasticity", "Ec",
                    f"{calcpad.number(material['Ec'], 0)} MPa", "Cl 3.1.2"),
        calcpad.row("Modular ratio", "n = Es / Ec", calcpad.number(material["n"], 5)),
        calcpad.row("Tension steel ratio", "p = Ast / (1000 ds)",
                    calcpad.number(deflection["p"], 6)),
        calcpad.row("Compression steel ratio", "pc = Asc / (1000 ds)",
                    calcpad.number(deflection["pc"], 6)),
        calcpad.row("Depth ratio", "dc / ds", calcpad.number(deflection["dcOverDs"], 4)),
        calcpad.row("Cracked neutral axis parameter",
                    "ku = sqrt(B^2 + 2(n p + (n-1) pc dc/ds)) - B, B = n p + (n-1) pc",
                    calcpad.number(deflection["ku"], 6)),
        calcpad.row("Cracked neutral axis", "NA = ku ds",
                    f"{calcpad.number(deflection['NA'], 2)} mm"),
        calcpad.row("Compression steel used for kcs", "Asc effective",
                    f"{calcpad.number(deflection['effectiveAsc'], 1)} mm2/m", "Cl 8.5.3.2"),
        calcpad.row("Long term factor", "kcs = max(0.8, 2 - 1.2 Asc/Ast)",
                    calcpad.number(deflection["kcs"], 4), "Cl 8.5.3.2"),
        calcpad.row("Effective service load",
                    "Fd.ef = (1 + kcs)(wdl + wsdl) + (psi_s + kcs psi_l) wll",
                    f"{calcpad.number(deflection['fdef'], 4)} kPa"),
        calcpad.row("Incremental service load",
                    "Fd.ef.inc = kcs (wdl + wsdl) + (psi_s + kcs psi_l) wll",
                    f"{calcpad.number(deflection['fdefIncremental'], 4)} kPa"),
    ]
    return calcpad.table("Serviceability parameters", rows)


def _thickness(result: dict[str, Any]) -> str:
    deflection = result["deflection"]
    inputs = result["inputs"]
    rows = [
        calcpad.row("Vertical deflection basis",
                    escape(DEFLECTION_BASIS[deflection["basis"]]),
                    calcpad.number(deflection["inclineModifier"], 6)),
        calcpad.row("Deflection constants", "k3, k4",
                    f"{calcpad.number(deflection['k3'], 2)}, "
                    f"{calcpad.number(deflection['k4'], 2)}", "Table 2.3.2"),
        calcpad.row("Minimum effective depth",
                    "d.min = mod x L / [k3 k4 (Ec / (L/d) / (Fd.ef/1000))^(1/3)]",
                    f"{calcpad.number(deflection['dmin'], 2)} mm", "Cl 9.4.4, Table 2.3.2"),
        calcpad.row("Minimum throat", "th.min = d.min / divisor + db/2 + cover",
                    f"{calcpad.number(deflection['thmin'], 2)} mm",
                    f"L/{calcpad.number(inputs['spanOverDeflection'], 0)}"),
        calcpad.row("Average thickness provided", "ath",
                    f"{calcpad.number(deflection['ath'], 2)} mm"),
        calcpad.row("Utilisation", "th.min / ath", calcpad.badge(result["util"]["deflection"])),
        calcpad.row("Incremental minimum effective depth", "d.min.inc",
                    f"{calcpad.number(deflection['dminIncremental'], 2)} mm", "Cl 9.4.4"),
        calcpad.row("Incremental minimum throat", "th.min.inc",
                    f"{calcpad.number(deflection['thminIncremental'], 2)} mm",
                    f"L/{calcpad.number(inputs['spanOverDeflectionIncremental'], 0)}"),
        calcpad.row("Utilisation", "th.min.inc / ath",
                    calcpad.badge(result["util"]["deflectionIncremental"])),
    ]
    return calcpad.table("Deflection, deemed to comply - Cl 9.4.4", rows)
