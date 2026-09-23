"""Calculation-pad presentation for the deep beam module."""

from __future__ import annotations

from html import escape
from typing import Any

import calcpad

from .engine import CRACK_CLASSES, SPAN_TYPES

DATA_ID = "concrete-deep-beam-inputs"
DEFAULT_SUBJECT = "Concrete deep beam design"

CHECK_ROWS = [
    ("diagonalCompression", "Diagonal compressive stress", "V* / phiVu.max", "WRHF Eq 24.24"),
    ("externalSupport", "External support zone bearing", "R* / phiRe", "WRHF Eq 24.26"),
    ("internalSupport", "Internal support zone bearing", "R* / phiRi", "WRHF Eq 24.27"),
    ("spanDepthLimit", "CEB span to depth limit", "L/D / limit", "CEB applicability"),
    ("supportWidthLimit", "Support width limit", "c / (L/5)", "CEB detailing limit"),
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
        _actions(result),
        _tie(result),
        _distribution(result),
        _diagonal(result),
        _web(result),
        _support(result),
    ]
    notes = list(result.get("unattainable") or []) + list(result.get("warnings") or [])
    if notes:
        blocks.append(calcpad.prose("Warnings", _paragraphs(notes), weight=2 + 2 * len(notes)))
    return calcpad.render(inputs, blocks, standalone=standalone, appendix=appendix,
                          anchor_prefix=anchor_prefix, contents_href=contents_href,
                          default_subject=DEFAULT_SUBJECT, data_id=DATA_ID)


def _basis(result: dict[str, Any]) -> str:
    body = ("<p><strong>SUPERSEDED METHOD - INFORMATIVE ONLY.</strong> The source workbook "
            "states that this CEB approach is superseded. AS 3600:2018 Section 12 "
            "strut-and-tie is the current method.</p>"
            "<p><strong>Assumptions</strong></p>" + _paragraphs(result["assumptions"])
            + "<p><strong>Limitations and exclusions</strong></p>"
            + _paragraphs(result["limitations"]))
    return calcpad.prose("Design basis", body,
                         weight=8 + len(result["assumptions"]) + len(result["limitations"]))


def _summary(result: dict[str, Any]) -> str:
    geometry, material = result["geometry"], result["material"]
    rows = [
        calcpad.row("Deep beam", "L x D x bw",
                    f"{calcpad.number(geometry['L'], 0)} x {calcpad.number(geometry['D'], 0)} x "
                    f"{calcpad.number(geometry['bw'], 0)} mm, "
                    f"f'c = {calcpad.number(material['fc'], 0)} MPa"),
        calcpad.row("Span type", escape(SPAN_TYPES[geometry["spanType"]]["label"]),
                    f"L/D = {calcpad.number(geometry['ldActual'], 3)}"),
    ]
    for key, label, expression, reference in CHECK_ROWS:
        if key in result["util"]:
            rows.append(calcpad.row(label, expression, calcpad.badge(result["util"][key]),
                                    reference))
        else:
            rows.append(calcpad.row(label, expression, "not applicable to this span type",
                                    reference))
    rows.append(calcpad.row("Governing", "Maximum finite utilisation",
                            calcpad.badge(result["worstUtil"])))
    return calcpad.table("Design summary", rows)


def _geometry(result: dict[str, Any]) -> str:
    geometry, material = result["geometry"], result["material"]
    rows = [
        calcpad.row("Span or cantilever length", "L", f"{calcpad.number(geometry['L'], 0)} mm"),
        calcpad.row("Depth", "D", f"{calcpad.number(geometry['D'], 0)} mm"),
        calcpad.row("Thickness", "bw", f"{calcpad.number(geometry['bw'], 0)} mm"),
        calcpad.row("Span to depth ratio", "L / D", calcpad.number(geometry["ldActual"], 3)),
        calcpad.row("CEB limit for this span type", "L / D limit",
                    calcpad.number(geometry["ldLimit"], 2), "CEB applicability"),
        calcpad.row("Support width", "c", f"{calcpad.number(geometry['support'], 0)} mm"),
        calcpad.row("Support width limit", "L / 5",
                    f"{calcpad.number(geometry['supportLimit'], 0)} mm"),
        calcpad.row("Depth of slab", "Df", f"{calcpad.number(geometry['Df'], 0)} mm"),
        calcpad.row("Effective lever arm", "z", f"{calcpad.number(geometry['z'], 0)} mm",
                    "WRHF Eq 24.20 to Eq 24.23"),
        calcpad.row("Concrete strength", "f'c", f"{calcpad.number(material['fc'], 0)} MPa",
                    "Cl 1.1.2, 20 to 120 MPa"),
        calcpad.row("Design concrete strength", "f'cd = f'c / gamma_c",
                    f"{calcpad.number(material['fcd'], 2)} MPa"),
    ]
    return calcpad.table("Geometry and materials", rows)


def _actions(result: dict[str, Any]) -> str:
    loads = result["loads"]
    rows = [
        calcpad.row("Design positive moment", "Mp*", f"{calcpad.moment(loads['Mstar'])} kNm"),
        calcpad.row("Design negative moment", "Mn*", f"{calcpad.moment(loads['Mstarn'])} kNm"),
        calcpad.row("Design shear", "V*", f"{calcpad.force(loads['Vstar'])} kN"),
        calcpad.row("Design reaction", "R*", f"{calcpad.force(loads['Rstar'])} kN"),
        calcpad.row("Point load", "P*", f"{calcpad.force(loads['Pstar'])} kN",
                    "Indicative only"),
        calcpad.row("Uniform load", "w*", f"{calcpad.number(loads['wstar'], 3)} kN/m",
                    "Indicative only"),
        calcpad.row("Indicative moment from P* and w*", "M",
                    f"{calcpad.moment(loads['indicativeM'])} kNm", "Not used in the design"),
        calcpad.row("Indicative shear from P* and w*", "V",
                    f"{calcpad.force(loads['indicativeV'])} kN", "Not used in the design"),
    ]
    return calcpad.table("Design actions", rows)


def _tie(result: dict[str, Any]) -> str:
    service, reo, material = result["serviceability"], result["reinforcement"], result["material"]
    rows = [
        calcpad.row("Crack control class", escape(CRACK_CLASSES[service["crack"]]["label"]),
                    f"fsi = {calcpad.number(service['fsi'], 0)} MPa", "Cl 12.7"),
        calcpad.row("Material safety factor", "gamma_s",
                    calcpad.number(material["gammaS"], 3)),
        calcpad.row("Effective design stress", "fsy.d = min(fsy / gamma_s, fsi)",
                    f"{calcpad.number(service['fsyd'], 1)} MPa", "WRHF Eq 24.19"),
        calcpad.row("Bar size", "db", f"{calcpad.number(reo['bar'], 0)} mm"),
        calcpad.row("Bar area", "Abar = pi db^2 / 4", f"{calcpad.number(reo['Abar'], 2)} mm2"),
        calcpad.row("Positive tie area", "Ast+ = Mp* / (fsy.d z)",
                    f"{calcpad.number(reo['AstPositive'], 1)} mm2", "WRHF Eq 24.20 to 24.23"),
        calcpad.row("Positive tie bars", "Ast+ / Abar",
                    calcpad.number(reo["barsPositive"], 2)),
        calcpad.row("Negative tie area", "Ast- = Mn* / (fsy.d z)",
                    f"{calcpad.number(reo['AstNegative'], 1)} mm2", "WRHF Eq 24.20 to 24.23"),
        calcpad.row("Negative tie bars", "Ast- / Abar",
                    calcpad.number(reo["barsNegative"], 2)),
    ]
    return calcpad.table("Tension tie reinforcement", rows)


def _distribution(result: dict[str, Any]) -> str:
    positive, distribution = result["positiveRegion"], result["distribution"]
    rows = [
        calcpad.row("Positive region fraction in the outer zone", "reodiste",
                    calcpad.number(positive["fraction"], 2)),
        calcpad.row("Positive region zone depth", "0.2 D",
                    f"{calcpad.number(positive['depth'], 0)} mm"),
        calcpad.row("Positive region bars in the outer zone", "bars x reodiste",
                    calcpad.number(positive["bars"], 2)),
        calcpad.row("Distribution fraction", "reodist = 0 if L/D <= 1, else min(0.5 (L/D - 1), 1)",
                    calcpad.number(distribution["fraction"], 3)),
        calcpad.row("Outer zone depth", "0.2 D",
                    f"{calcpad.number(distribution['outerDepth'], 0)} mm"),
        calcpad.row("Positive bars in the outer zone", "bars+ x reodist",
                    calcpad.number(distribution["barsOuterPositive"], 2)),
        calcpad.row("Negative bars in the outer zone", "bars- x reodist",
                    calcpad.number(distribution["barsOuterNegative"], 2)),
        calcpad.row("Middle zone depth", "0.6 D",
                    f"{calcpad.number(distribution['middleDepth'], 0)} mm"),
        calcpad.row("Positive bars in the middle zone", "bars+ x (1 - reodist)",
                    calcpad.number(distribution["barsMiddlePositive"], 2)),
        calcpad.row("Negative bars in the middle zone", "bars- x (1 - reodist)",
                    calcpad.number(distribution["barsMiddleNegative"], 2)),
    ]
    return calcpad.table("Reinforcement distribution", rows)


def _diagonal(result: dict[str, Any]) -> str:
    shear, loads = result["shear"], result["loads"]
    rows = [
        calcpad.row("Capacity from the depth", "phiVu.max(D) = 0.1 bw D f'cd",
                    f"{calcpad.force(shear['phiVuDepth'])} kN", "WRHF Eq 24.24"),
        calcpad.row("Capacity from the span", "phiVu.max(L) = 0.1 bw L f'cd",
                    f"{calcpad.force(shear['phiVuSpan'])} kN", "WRHF Eq 24.24"),
        calcpad.row("Governing capacity", "phiVu.max = min of the two",
                    f"{calcpad.force(shear['phiVu'])} kN", "WRHF Eq 24.24"),
        calcpad.row("Design shear", "V*", f"{calcpad.force(loads['Vstar'])} kN"),
        calcpad.row("Utilisation", "V* / phiVu.max",
                    calcpad.badge(result["util"]["diagonalCompression"])),
    ]
    return calcpad.table("Diagonal compressive stress", rows)


def _web(result: dict[str, Any]) -> str:
    web = result["web"]
    rows = [
        calcpad.row("Panel mesh wire diameter", "d", f"{calcpad.number(web['mesh'], 2)} mm"),
        calcpad.row("Wire area", "Asw = pi d^2 / 4", f"{calcpad.number(web['Asw'], 2)} mm2"),
        calcpad.row("Maximum mesh centres", "s = Asw / (0.0025 bw)",
                    f"{calcpad.number(web['meshSpacing'], 1)} mm", "WRHF Eq 24.25"),
        calcpad.row("Maximum bar centres", "s = Asw / (0.002 bw)",
                    f"{calcpad.number(web['barSpacing'], 1)} mm", "WRHF Eq 24.25"),
    ]
    return calcpad.table("Web reinforcement", rows)


def _support(result: dict[str, Any]) -> str:
    support, loads = result["support"], result["loads"]
    rows = [
        calcpad.row("Design reaction", "R*", f"{calcpad.force(loads['Rstar'])} kN"),
        calcpad.row("External support capacity", "phiRe = 0.8 bw (c + Df) f'cd",
                    f"{calcpad.force(support['phiRe'])} kN", "WRHF Eq 24.26"),
        calcpad.row("External support utilisation", "R* / phiRe",
                    calcpad.badge(result["util"]["externalSupport"])
                    if support["externalApplies"]
                    else "not applicable to a cantilever"),
        calcpad.row("Internal support capacity", "phiRi = 1.2 bw (c + 2 Df) f'cd",
                    f"{calcpad.force(support['phiRi'])} kN", "WRHF Eq 24.27"),
        calcpad.row("Internal support utilisation", "R* / phiRi",
                    calcpad.badge(result["util"]["internalSupport"])
                    if support["internalApplies"]
                    else "not applicable to a simple span"),
        calcpad.row("Support width", "c / (L/5)",
                    calcpad.badge(result["util"]["supportWidthLimit"])),
    ]
    return calcpad.table("Support zone capacity", rows)
