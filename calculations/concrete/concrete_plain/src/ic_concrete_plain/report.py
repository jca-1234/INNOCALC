"""Calculation-pad presentation for the plain concrete module.

Only formatting and display-unit conversion happen here.  Every engineering
value is read from the result document produced by
:func:`ic_concrete_plain.engine.compute`.
"""

from __future__ import annotations

from html import escape
from typing import Any

import calcpad

from .engine import DIRECTIONS, PERIMETER_MODES

DATA_ID = "concrete-plain-inputs"
DEFAULT_SUBJECT = "Plain concrete design"

CHECK_ROWS = [
    ("bending", "Footing bending", "M* / phiMuo", "Cl 20.4.2"),
    ("oneWayShear", "Footing one-way shear", "V* / phiVu", "Eq 20.4.3(1)"),
    ("punchingShear", "Footing two-way punching shear", "V* / phiVum", "Cl 20.4.3(b)"),
    ("pedestalCompression", "Pedestal compressive stress", "sigma.tc / sigma.c.max", "Cl 20.3"),
    ("pedestalTension", "Pedestal tensile stress", "|sigma.tt| / sigma.t.max", "Cl 20.3"),
    ("minimumDepth", "Minimum nominal depth", "200 / Dt", "Cl 20.4.1"),
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
        _bending(result),
        _one_way(result),
        _punching(result),
        _pedestal_geometry(result),
        _pedestal_stress(result),
    ]
    notes = list(result.get("unattainable") or []) + list(result.get("warnings") or [])
    if notes:
        blocks.append(calcpad.prose("Warnings", _paragraphs(notes), weight=2 + len(notes)))
    return calcpad.render(inputs, blocks, standalone=standalone, appendix=appendix,
                          anchor_prefix=anchor_prefix, contents_href=contents_href,
                          default_subject=DEFAULT_SUBJECT, data_id=DATA_ID)


def _basis(result: dict[str, Any]) -> str:
    body = ("<p><strong>Assumptions</strong></p>" + _paragraphs(result["assumptions"])
            + "<p><strong>Limitations and exclusions</strong></p>"
            + _paragraphs(result["limitations"]))
    return calcpad.prose("Design basis", body,
                         weight=6 + len(result["assumptions"]) + len(result["limitations"]))


def _summary(result: dict[str, Any]) -> str:
    values = result["inputs"]
    rows = [
        calcpad.row("Footing", "b x Dt, f'c",
                    f"{calcpad.number(values['B'], 0)} x {calcpad.number(values['Dt'], 0)} mm, "
                    f"f'c = {calcpad.number(values['fc'], 0)} MPa"),
        calcpad.row("Pedestal", "Lpx x Wpy",
                    f"{calcpad.number(values['Lpx'], 0)} x {calcpad.number(values['Wpy'], 0)} mm"),
    ]
    for key, label, expression, reference in CHECK_ROWS:
        rows.append(calcpad.row(label, expression, calcpad.badge(result["util"][key]), reference))
    rows.append(calcpad.row("Governing", "Maximum finite utilisation",
                            calcpad.badge(result["worstUtil"])))
    return calcpad.table("Design summary", rows)


def _geometry(result: dict[str, Any]) -> str:
    geometry, material = result["geometry"], result["material"]
    rows = [
        calcpad.row("Concrete strength", "f'c", f"{calcpad.number(material['fc'], 0)} MPa",
                    "Cl 1.1.2, 20 to 120 MPa"),
        calcpad.row("Nominal depth", "Dt", f"{calcpad.number(geometry['Dt'], 0)} mm",
                    "Cl 20.4.1, 200 mm minimum"),
        calcpad.row("Design depth", "D = Dt - 50", f"{calcpad.number(geometry['D'], 0)} mm",
                    "Cl 20.4.1"),
        calcpad.row("Breadth", "b", f"{calcpad.number(geometry['B'], 0)} mm"),
        calcpad.row("Capacity reduction factor", "phi",
                    calcpad.number(result["factors"]["phi"], 2), "Table 2.2.2(g)"),
        calcpad.row("Characteristic flexural tensile strength", "f'ct.f = 0.6 sqrt(f'c)",
                    f"{calcpad.number(material['fcf'], 4)} MPa", "Cl 3.1.1.3"),
    ]
    return calcpad.table("Footing geometry and material", rows)


def _bending(result: dict[str, Any]) -> str:
    footing, loads = result["footing"], result["loads"]
    rows = [
        calcpad.row("Design moment", "M*", f"{calcpad.moment(loads['Mstar'])} kNm"),
        calcpad.row("Bending capacity", "phiMuo = phi f'ct.f b D^2 / 6",
                    f"{calcpad.moment(footing['phiMuo'])} kNm", "Cl 20.4.2"),
        calcpad.row("Utilisation", "M* / phiMuo", calcpad.badge(result["util"]["bending"])),
    ]
    return calcpad.table("Strength in bending - Cl 20.4.2", rows)


def _one_way(result: dict[str, Any]) -> str:
    footing, loads = result["footing"], result["loads"]
    rows = [
        calcpad.row("Critical section from the support face", "0.5 D",
                    f"{calcpad.number(footing['critical'], 0)} mm", "Cl 20.4.3(a)"),
        calcpad.row("Design shear", "V*", f"{calcpad.force(loads['Vstar'])} kN"),
        calcpad.row("Shear capacity", "phiVu = phi 0.15 b D f'c^(1/3)",
                    f"{calcpad.force(footing['phiVu1'])} kN", "Eq 20.4.3(1)"),
        calcpad.row("Utilisation", "V* / phiVu", calcpad.badge(result["util"]["oneWayShear"])),
    ]
    return calcpad.table("One-way shear - Cl 20.4.3(a)", rows)


def _punching(result: dict[str, Any]) -> str:
    punching, loads = result["punching"], result["loads"]
    rows = [
        calcpad.row("Perimeter dimension", "aL = L + D",
                    f"{calcpad.number(punching['aL'], 0)} mm", "Fig 9.3(A)"),
        calcpad.row("Perimeter dimension", "aW = W + D",
                    f"{calcpad.number(punching['aW'], 0)} mm", "Fig 9.3(A)"),
        calcpad.row("Calculated shear perimeter", "uc = 2 aL + 2 aW",
                    f"{calcpad.number(punching['uc'], 0)} mm", "Fig 9.3(A)"),
        calcpad.row("Design shear perimeter",
                    escape(PERIMETER_MODES[punching["mode"]]),
                    f"u = {calcpad.number(punching['u'], 0)} mm", "Cl 20.4.3(b)"),
        calcpad.row("Aspect ratio", "beta.h = max(L, W) / min(L, W)",
                    calcpad.number(punching["bh"], 3)),
        calcpad.row("Upper limit", "phiVu.max = phi 0.2 u D sqrt(f'c)",
                    f"{calcpad.force(punching['phiVumax'])} kN", "Cl 20.4.3(b)"),
        calcpad.row("Unreinforced capacity", "phiVu.u = phi 0.1 u D (1 + 2/beta.h) sqrt(f'c)",
                    f"{calcpad.force(punching['phiVuu'])} kN", "Cl 20.4.3(b)"),
        calcpad.row("Punching capacity", "phiVu = min(phiVu.max, phiVu.u)",
                    f"{calcpad.force(punching['phiVu'])} kN", "Cl 20.4.3(b)"),
        calcpad.row("Moment direction",
                    escape(DIRECTIONS[punching["direction"]]),
                    f"a = {calcpad.number(punching['a'], 0)} mm", "Eq 20.4.3(2)"),
        calcpad.row("Reduced capacity", "phiVum = phiVu / [1 + u M* / (8 V* a D)]",
                    f"{calcpad.force(punching['phiVum'])} kN", "Eq 20.4.3(2)"),
        calcpad.row("Utilisation", "V* / phiVum", calcpad.badge(result["util"]["punchingShear"])),
    ]
    return calcpad.table("Two-way punching shear - Cl 20.4.3(b)", rows)


def _pedestal_geometry(result: dict[str, Any]) -> str:
    pedestal = result["pedestal"]
    rows = [
        calcpad.row("Plan length", "Lpx", f"{calcpad.number(pedestal['Lpx'], 0)} mm"),
        calcpad.row("Plan width", "Wpy", f"{calcpad.number(pedestal['Wpy'], 0)} mm"),
        calcpad.row("Cross sectional area", "Ag = Lpx Wpy",
                    f"{calcpad.number(pedestal['Ag'], 0)} mm2"),
        calcpad.row("Maximum permitted height", "3 min(Lpx, Wpy)",
                    f"{calcpad.number(pedestal['maxHeight'], 0)} mm", "Cl 20.1(a)"),
        calcpad.row("Minimum eccentricity", "ax = 0.1 Lpx",
                    f"{calcpad.number(pedestal['ax'], 1)} mm", "Cl 20.3"),
        calcpad.row("Minimum eccentricity", "ay = 0.1 Wpy",
                    f"{calcpad.number(pedestal['ay'], 1)} mm", "Cl 20.3"),
        calcpad.row("Design eccentricity", "dax = max(eccx, ax)",
                    f"{calcpad.number(pedestal['dax'], 1)} mm", "Cl 20.3"),
        calcpad.row("Design eccentricity", "day = max(eccy, ay)",
                    f"{calcpad.number(pedestal['day'], 1)} mm", "Cl 20.3"),
    ]
    return calcpad.table("Unreinforced pedestal geometry - Cl 20.3", rows)


def _pedestal_stress(result: dict[str, Any]) -> str:
    pedestal, loads = result["pedestal"], result["loads"]
    rows = [
        calcpad.row("Ultimate reaction", "P*", f"{calcpad.force(loads['Pstar'])} kN",
                    "Positive in compression"),
        calcpad.row("Axial stress", "sigma.a = P* / Ag",
                    f"{calcpad.number(pedestal['sigmaA'], 4)} MPa", "Cl 20.3"),
        calcpad.row("Eccentric moment about x", "|P*| dax",
                    f"{calcpad.moment(pedestal['Mxecc'])} kNm", "Cl 20.3"),
        calcpad.row("Eccentric moment about y", "|P*| day",
                    f"{calcpad.moment(pedestal['Myecc'])} kNm", "Cl 20.3"),
        calcpad.row("Bending stress", "sigma.bxc = 6 (|Mx*| + |P*| dax) / (Wpy Lpx^2)",
                    f"{calcpad.number(pedestal['sigmaBx'], 4)} MPa", "Cl 20.3"),
        calcpad.row("Bending stress", "sigma.byc = 6 (|My*| + |P*| day) / (Lpx Wpy^2)",
                    f"{calcpad.number(pedestal['sigmaBy'], 4)} MPa", "Cl 20.3"),
        calcpad.row("Total compressive stress", "sigma.tc = max(0, sigma.a + sigma.bxc + sigma.byc)",
                    f"{calcpad.number(pedestal['sigmaTc'], 4)} MPa", "Cl 20.3"),
        calcpad.row("Total tensile stress", "sigma.tt = min(0, sigma.a - sigma.bxc - sigma.byc)",
                    f"{calcpad.number(pedestal['sigmaTt'], 4)} MPa", "Cl 20.3"),
        calcpad.row("Compressive limit", "sigma.c.max = phi 0.4 f'c",
                    f"{calcpad.number(pedestal['sigmaCmax'], 4)} MPa", "Cl 20.3"),
        calcpad.row("Tensile limit", "sigma.t.max = phi 0.45 sqrt(f'c)",
                    f"{calcpad.number(pedestal['sigmaTmax'], 4)} MPa", "Cl 20.3"),
        calcpad.row("Limiting compressive capacity", "phiNuo = sigma.c.max Ag",
                    f"{calcpad.force(pedestal['phiNuoC'])} kN", "Cl 20.3"),
        calcpad.row("Limiting tensile capacity", "phiNuo = sigma.t.max Ag",
                    f"{calcpad.force(pedestal['phiNuoT'])} kN", "Cl 20.3"),
        calcpad.row("Compression utilisation", "sigma.tc / sigma.c.max",
                    calcpad.badge(result["util"]["pedestalCompression"])),
        calcpad.row("Tension utilisation", "|sigma.tt| / sigma.t.max",
                    calcpad.badge(result["util"]["pedestalTension"])),
    ]
    return calcpad.table("Unreinforced pedestal stresses - Cl 20.3", rows)
