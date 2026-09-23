"""Calculation-pad presentation for the concrete corbel module.

Only formatting and display-unit conversion happen here.  Every engineering
value is read from the result document produced by
:func:`ic_concrete_corbel.engine.compute`.
"""

from __future__ import annotations

import math
from html import escape
from typing import Any

import calcpad

from .engine import LOAD_TYPE_LABELS, REINFORCEMENT_MODES

DATA_ID = "concrete-corbel-inputs"
DEFAULT_SUBJECT = "Concrete corbel design"

CHECK_ROWS = [
    ("bearing", "Bearing at the corbel node", "B* / phiB", "Cl 7.4.2"),
    ("shearFriction", "Shear friction on the vertical face", "V* / phiVu", "Cl 8.4.3"),
    ("tensileTie", "Horizontal tensile tie", "Ft* / phiFt", "Cl 7.3.2"),
    ("minimumSteel", "Minimum flexural reinforcement", "Ast.min / As", "Eq 8.1.6.1(2)"),
    ("depthLimit", "Minimum overall depth", "1.7 av / D", "Corbel proportions"),
    ("wallThickness", "Strut width across the wall", "w / th", "Geometry limit"),
]


def _paragraphs(items: list[str]) -> str:
    return "".join(f"<p>{escape(str(item))}</p>" for item in items)


def _degrees(radians: float) -> str:
    return f"{calcpad.number(math.degrees(radians), 1)} deg"


def render(inputs: dict[str, Any], result: dict[str, Any], *, standalone: bool = False,
           appendix: list[str] | None = None, anchor_prefix: str = "",
           contents_href: str = "") -> str:
    blocks = [
        _basis(result),
        _summary(result),
        _geometry(result),
        _actions(result),
        _reinforcement(result),
        _bearing(result),
        _shear_friction(result),
        _strut(result),
        _tie(result),
    ]
    notes = list(result.get("unattainable") or []) + list(result.get("warnings") or [])
    if notes:
        blocks.append(calcpad.prose("Warnings and unattainable checks", _paragraphs(notes),
                                    weight=2 + len(notes)))
    return calcpad.render(inputs, blocks, standalone=standalone, appendix=appendix,
                          anchor_prefix=anchor_prefix, contents_href=contents_href,
                          default_subject=DEFAULT_SUBJECT, data_id=DATA_ID)


def _basis(result: dict[str, Any]) -> str:
    body = ("<p><strong>Assumptions</strong></p>" + _paragraphs(result["assumptions"])
            + "<p><strong>Limitations and exclusions</strong></p>"
            + _paragraphs(result["limitations"]))
    return calcpad.prose("Design basis", body,
                         weight=4 + len(result["assumptions"]) + len(result["limitations"]))


def _summary(result: dict[str, Any]) -> str:
    util = result["util"]
    geometry, material = result["geometry"], result["material"]
    rows = [
        calcpad.row("Corbel", "b x D, f'c",
                    f"{calcpad.number(result['inputs']['b'], 0)} x "
                    f"{calcpad.number(result['inputs']['D'], 0)} mm, "
                    f"f'c = {calcpad.number(material['fc'], 0)} MPa"),
        calcpad.row("Design shear", f"V* = {escape(result['loads']['Vcase'])}",
                    f"{calcpad.force(result['loads']['Vstar'])} {_force_unit(geometry)}",
                    "AS/NZS 1170.0 Cl 4.2.2"),
        calcpad.row("Design horizontal action", "Nd* = max(N*, 0.2 V*)",
                    f"{calcpad.force(result['loads']['Ndstar'])} {_force_unit(geometry)}",
                    "Cl 12.3(b)"),
    ]
    for key, label, expression, reference in CHECK_ROWS:
        rows.append(calcpad.row(label, expression, calcpad.badge(util[key]), reference))
    rows.append(calcpad.row("Governing", "Maximum finite utilisation",
                            calcpad.badge(result["worstUtil"])))
    return calcpad.table("Design summary", rows)


def _force_unit(geometry: dict[str, Any]) -> str:
    return "kN/m" if geometry["perMetre"] else "kN"


def _area_unit(geometry: dict[str, Any]) -> str:
    return "mm2/m" if geometry["perMetre"] else "mm2"


def _geometry(result: dict[str, Any]) -> str:
    values, geometry = result["inputs"], result["geometry"]
    interface = result["interface"]
    rows = [
        calcpad.row("Concrete strength", "f'c", f"{calcpad.number(values['fc'], 0)} MPa",
                    "Cl 1.1.2, 20 to 120 MPa"),
        calcpad.row("Corbel length", "b", f"{calcpad.number(values['b'], 0)} mm"),
        calcpad.row("Corbel depth", "df", f"{calcpad.number(values['df'], 0)} mm"),
        calcpad.row("Overall depth", "D", f"{calcpad.number(values['D'], 0)} mm"),
        calcpad.row("Eccentricity", "av", f"{calcpad.number(values['av'], 0)} mm"),
        calcpad.row("Minimum overall depth", "Dmin = 1.7 av",
                    f"{calcpad.number(geometry['Dmin'], 1)} mm", "Corbel proportions"),
        calcpad.row("Bearing strip", "bw x bl",
                    f"{calcpad.number(values['bw'], 0)} x {calcpad.number(geometry['bl'], 0)} mm"),
        calcpad.row("Bearing area", "Ab = bw bl",
                    f"{calcpad.number(geometry['Ab'], 0)} mm2"),
        calcpad.row("Supporting wall thickness", "th", f"{calcpad.number(values['th'], 0)} mm"),
        calcpad.row("Casting condition", escape(interface["label"]),
                    f"mu = {calcpad.number(interface['mu'], 2)}, "
                    f"kco = {calcpad.number(interface['kco'], 2)}", "Table 8.4.3"),
        calcpad.row("Characteristic flexural tensile strength", "f'ct.f = 0.6 sqrt(f'c)",
                    f"{calcpad.number(result['material']['fctf'], 3)} MPa", "Cl 3.1.1.3"),
        calcpad.row("Characteristic principal tensile strength", "f'ct = 0.36 sqrt(f'c)",
                    f"{calcpad.number(result['material']['fct'], 3)} MPa", "Cl 3.1.1.3"),
    ]
    return calcpad.table("Geometry and material", rows)


def _actions(result: dict[str, Any]) -> str:
    loads, geometry = result["loads"], result["geometry"]
    unit = _force_unit(geometry)
    rows = [
        calcpad.row("Vertical dead load", "Vdl", f"{calcpad.force(loads['Vdl'])} {unit}"),
        calcpad.row("Vertical live load", "Vll", f"{calcpad.force(loads['Vll'])} {unit}"),
        calcpad.row("Horizontal dead load", "Ndl", f"{calcpad.force(loads['Ndl'])} {unit}"),
        calcpad.row("Horizontal live load", "Nll", f"{calcpad.force(loads['Nll'])} {unit}"),
        calcpad.row("Design shear", "V* = max(1.35 G, 1.2 G + 1.5 Q)",
                    f"{calcpad.force(loads['Vstar'])} {unit}",
                    f"AS/NZS 1170.0, {escape(loads['Vcase'])}"),
        calcpad.row("Design horizontal action", "N* = max(1.35 G, 1.2 G + 1.5 Q)",
                    f"{calcpad.force(loads['Nstar'])} {unit}",
                    f"AS/NZS 1170.0, {escape(loads['Ncase'])}"),
        calcpad.row("Horizontal action for the tie", "Nd* = max(N*, 0.2 V*)",
                    f"{calcpad.force(loads['Ndstar'])} {unit}", "Cl 12.3(b)"),
        calcpad.row("Load type", escape(LOAD_TYPE_LABELS.get(result["inputs"]["loadtype"], "")),
                    f"psi_l = {calcpad.number(loads['psiL'], 2)}", "AS/NZS 1170.0 Table 4.1"),
        calcpad.row("Permanent clamping action",
                    "gpt = -max(Ndl + psi_l Nll, 0.2 (Vdl + psi_l Vll))",
                    f"{calcpad.force(loads['gpt'])} {unit}"),
        calcpad.row("Permanent clamping action per unit length", "gp = gpt / b",
                    f"{calcpad.number(loads['gp'], 3)} N/mm"),
    ]
    return calcpad.table("Design actions", rows)


def _reinforcement(result: dict[str, Any]) -> str:
    reo, geometry = result["reinforcement"], result["geometry"]
    rows = [
        calcpad.row("Entry mode", escape(REINFORCEMENT_MODES[reo["mode"]]),
                    f"{calcpad.number(result['inputs']['reoValue'], 1)}"),
        calcpad.row("Bar size", "db", f"{calcpad.number(reo['bar'], 0)} mm"),
        calcpad.row("Bar area", "Abar = pi db^2 / 4", f"{calcpad.number(reo['Abar'], 2)} mm2"),
        calcpad.row("Number of bars", "nbars", calcpad.number(reo["nbars"], 2)),
        calcpad.row("Bar centres", "cts", f"{calcpad.number(reo['cts'], 1)} mm"),
        calcpad.row("Cover", "c", f"{calcpad.number(reo['cover'], 0)} mm"),
        calcpad.row("Yield strength", "fsy", f"{calcpad.number(result['material']['fsy'], 0)} MPa"),
        calcpad.row("Horizontal steel area", "As",
                    f"{calcpad.number(reo['As'], 1)} {_area_unit(geometry)}"),
        calcpad.row("Depth to the tie", "d = D - c - db/2",
                    f"{calcpad.number(geometry['lever'], 1)} mm"),
        calcpad.row("Minimum flexural reinforcement",
                    "Ast.min = 0.2 (D/d)^2 f'ct.f / fsy d b",
                    f"{calcpad.number(reo['Asmin'], 1)} {_area_unit(geometry)}",
                    "Eq 8.1.6.1(2)"),
        calcpad.row("Minimum steel check", "Ast.min / As",
                    calcpad.badge(result["util"]["minimumSteel"]), "Cl 8.1.6.1"),
    ]
    return calcpad.table("Horizontal tie reinforcement", rows)


def _bearing(result: dict[str, Any]) -> str:
    bearing, geometry = result["bearing"], result["geometry"]
    rows = [
        calcpad.row("Capacity reduction factor", "phi.st.c",
                    calcpad.number(bearing["phist"], 2), "Table 2.2.4"),
        calcpad.row("Bearing stress", "B* = V* / Ab",
                    f"{calcpad.number(bearing['Bstar'], 2)} MPa"),
        calcpad.row("Node coefficient", "beta.n", calcpad.number(bearing["betan"], 2),
                    "Cl 7.4.2(b), CCT node"),
        calcpad.row("Bearing limit", "phiB.max = phi.st.c 1.8 f'c",
                    f"{calcpad.number(bearing['phiBmax'], 2)} MPa", "Cl 7.4.2"),
        calcpad.row("Node limit", "phiBa = phi.st.c beta.n 0.9 f'c",
                    f"{calcpad.number(bearing['phiBa'], 2)} MPa", "Cl 7.4.2"),
        calcpad.row("Bearing capacity", "phiB = min(phiB.max, phiBa)",
                    f"{calcpad.number(bearing['phiB'], 2)} MPa", "Cl 7.4.2"),
        calcpad.row("Utilisation", "B* / phiB", calcpad.badge(result["util"]["bearing"])),
    ]
    return calcpad.table("Bearing - Cl 7.4.2", rows)


def _shear_friction(result: dict[str, Any]) -> str:
    shear, geometry = result["shearFriction"], result["geometry"]
    unit = _force_unit(geometry)
    rows = [
        calcpad.row("Capacity reduction factor", "phi.v", calcpad.number(shear["phiv"], 2),
                    "Table 2.2.2(e)"),
        calcpad.row("Anchored steel crossing the interface", "Asf = 2 Abar",
                    f"{calcpad.number(shear['Asf'], 1)} mm2"),
        calcpad.row("Width of the shear plane", "bf = D", f"{calcpad.number(shear['bf'], 0)} mm"),
        calcpad.row("Spacing of the anchored steel", "s = cts",
                    f"{calcpad.number(shear['s'], 1)} mm"),
        calcpad.row("Interface shear stress",
                    "tau.u = mu [Asf fsy / (s bf) + gp / bf] + kco f'ct",
                    f"{calcpad.number(shear['tauCalc'], 3)} MPa", "Cl 8.4.3"),
        calcpad.row("Stress limit", "tau.u.max = min(0.2 f'c, 10 MPa)",
                    f"{calcpad.number(min(shear['tauMax'], 10.0), 3)} MPa", "Cl 8.4.3"),
        calcpad.row("Governing interface shear stress", "tau.u",
                    f"{calcpad.number(shear['tau'], 3)} MPa", "Cl 8.4.3"),
        calcpad.row("Shear capacity", "phiVu = phi.v tau.u b D",
                    f"{calcpad.force(shear['phiVu'])} {unit}", "Cl 8.4.3"),
        calcpad.row("Utilisation", "V* / phiVu", calcpad.badge(result["util"]["shearFriction"])),
    ]
    return calcpad.table("Shear friction on the vertical face - Cl 8.4.3", rows)


def _strut(result: dict[str, Any]) -> str:
    strut, geometry = result["strut"], result["geometry"]
    unit = _force_unit(geometry)
    if not strut["converged"]:
        body = (f"<p>The strut width could not be solved. {escape(strut['reason'])}</p>"
                f"<p>Search bracket: {calcpad.number(strut['bracket'][0], 3)} mm to "
                f"{calcpad.number(strut['bracket'][1], 3)} mm.</p>")
        return calcpad.prose("Compression strut - Cl 7.2.3", body, weight=6)
    rows = [
        calcpad.row("Diagonal length", "H = sqrt(d^2 + av^2)",
                    f"{calcpad.number(strut['H'], 1)} mm"),
        calcpad.row("Strut width", "dc solved so Cf* = phiCa - 0.01 kN",
                    f"{calcpad.number(strut['dc'], 3)} mm",
                    f"Bisection, {strut['iterations']} steps"),
        calcpad.row("Geometric strut length", "lg = sqrt(H^2 - (dc/2)^2)",
                    f"{calcpad.number(strut['lg'], 1)} mm"),
        calcpad.row("Angle to the vertical face", "ang1 = atan(av / d)",
                    _degrees(strut["ang1"])),
        calcpad.row("Angle subtended by the strut", "ang2 = atan((dc/2) / lg)",
                    _degrees(strut["ang2"])),
        calcpad.row("Strut inclination", "theta = pi/2 - (ang1 + ang2)",
                    _degrees(strut["theta"])),
        calcpad.row("Strut efficiency factor", "beta.s = 1 / [1 + 0.66 cot(theta)^2]",
                    calcpad.number(strut["betas"], 3), "Cl 7.2.2, 0.3 <= beta.s <= 1.0"),
        calcpad.row("Strut depth", "x = dc / cos(theta)", f"{calcpad.number(strut['x'], 2)} mm"),
        calcpad.row("Maximum strut stress", "sigma.st.max = phi.st.c beta.s 0.9 f'c",
                    f"{calcpad.number(strut['sigmaMax'], 2)} MPa", "Cl 7.2.3"),
        calcpad.row("Strut capacity", "phiCa = sigma.st.max b dc",
                    f"{calcpad.force(strut['phiCa'])} {unit}", "Cl 7.2.3"),
        calcpad.row("Strut lever length", "dl = d - sin(pi/2 - theta) dc/2",
                    f"{calcpad.number(strut['dl'], 1)} mm"),
        calcpad.row("Strut compression force", "Cf* = lg / dl V*",
                    f"{calcpad.force(strut['Cf'])} {unit}"),
        calcpad.row("Strut width across the wall", "w = dc sin(theta)",
                    f"{calcpad.number(strut['w'], 2)} mm"),
        calcpad.row("Wall thickness check", "w / th",
                    calcpad.badge(result["util"]["wallThickness"])),
    ]
    note = ("The strut width dc is solved so that the strut is fully utilised, which fixes the "
            "strut depth x used by the tie below. The strut is therefore not reported as an "
            "independent utilisation.")
    return calcpad.table("Compression strut - Cl 7.2.3", rows) + calcpad.prose(
        "Compression strut basis", f"<p>{escape(note)}</p>", weight=3)


def _tie(result: dict[str, Any]) -> str:
    tie, geometry = result["tie"], result["geometry"]
    unit = _force_unit(geometry)
    demand = (f"{calcpad.force(tie['Ftstar'])} {unit}" if math.isfinite(tie["Ftstar"])
              else "not attainable")
    lever = (f"{calcpad.number(tie['lever'], 1)} mm" if math.isfinite(tie["lever"])
             else "not attainable")
    rows = [
        calcpad.row("Capacity reduction factor", "phi.st.t", calcpad.number(tie["phis"], 2),
                    "Table 2.2.4"),
        calcpad.row("Tie lever arm", "d - x/2", lever),
        calcpad.row("Tie force", "Ft* = V* av / (d - x/2) + Nd*", demand, "Cl 7.3.2"),
        calcpad.row("Tie capacity", "phiFt = phi.st.t fsy As",
                    f"{calcpad.force(tie['phiFt'])} {unit}", "Cl 7.3.2"),
        calcpad.row("Utilisation", "Ft* / phiFt", calcpad.badge(result["util"]["tensileTie"])),
    ]
    return calcpad.table("Horizontal tensile tie - Cl 7.3.2", rows)