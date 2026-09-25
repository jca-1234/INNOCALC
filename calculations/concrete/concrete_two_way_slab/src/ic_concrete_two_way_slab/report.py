"""Calculation-pad presentation for the two-way slab module, in the column-module layout.

Only formatting happens here; every engineering value comes from
:func:`ic_concrete_two_way_slab.engine.compute`.
"""

from __future__ import annotations

from html import escape
from typing import Any

import calcpad

from .engine import FLEXURE_LAYERS, LOAD_TYPES
from .version import VERSION

DATA_ID = "concrete-two-way-slab-inputs"
DEFAULT_SUBJECT = "Two-way slab design"
num = calcpad.number

CHECK_ROWS = [
    ("deflectionTotal", "Deemed-to-comply depth, total", "d.min / ds", "Cl 9.4.4.2"),
    ("deflectionIncremental", "Deemed-to-comply depth, incremental", "d.min.inc / ds",
     "Cl 9.4.4.2"),
    ("minimumSteel", "Minimum strength reinforcement", "Ast.min / Ast", "Cl 9.1.1(b)"),
    ("liveLoadLimit", "Live load not exceeding dead load", "wll / wdl", "Cl 9.4.4.2"),
    ("flexure", "Flexural capacity, governing location", "M* / phiMu", "Cl 8.1"),
    ("ductility", "Ductility, governing location", "ku / 0.36", "Cl 8.1.5"),
    ("flexuralMinimum", "Minimum reinforcement, governing location", "As.min / As",
     "Cl 9.1.1, Cl 9.4.3"),
    ("barSpacing", "Bar spacing, governing location", "s / min(300, 2D)", "Cl 9.4.1"),
    ("shrinkage", "Shrinkage and temperature reinforcement", "As.cs / Ast", "Cl 9.4.3"),
]

SOURCE_LABELS = {"A": "Table 6.10.3.2(A) - Class N with redistribution",
                 "B": "Table 6.10.3.2(B) - Class L and/or no redistribution",
                 "formula": "Closed-form coefficients (WRH) - Class N with redistribution"}


def render(inputs: dict[str, Any], result: dict[str, Any], *, standalone: bool = False,
           appendix: list[str] | None = None, anchor_prefix: str = "",
           contents_href: str = "") -> str:
    blocks = [
        _summary(result),
        *_inputs(inputs),
        _panel_figure(result),
        _material(result),
        _actions(result),
        *_coefficients(result),
        *_moments(result),
        _minimum(result),
        _deflection(result),
        _shrinkage(result),
        *_flexure(result),
        _basis(result),
    ]
    title = (f"{inputs.get('memberType', 'Slab')}-{inputs.get('memberNumber', '')} "
             f"- Concrete Two-Way Slab Design {VERSION}")
    return calcpad.render(inputs, blocks, standalone=standalone, appendix=appendix,
                          anchor_prefix=anchor_prefix, contents_href=contents_href,
                          default_subject=DEFAULT_SUBJECT, data_id=DATA_ID, title=title)


def _summary(result: dict[str, Any]) -> str:
    values, analysis, moments = result["inputs"], result["analysis"], result["moments"]
    deflection = result["deflection"]
    rows = [
        calcpad.row("Slab panel", "Ly x Lx x th, f'c",
                    f"{num(values['Ly'], 0)} x {num(values['Lx'], 0)} x {num(values['th'], 0)} mm, "
                    f"f'c = {num(values['fc'], 0)} MPa"),
        calcpad.row("Edge condition", f"Edge code {analysis['code']}",
                    escape(analysis["edgeLabel"]), "Table 6.10.3.2"),
        calcpad.row("Design load", f"Fd = {result['loads']['case']}",
                    f"{num(result['loads']['Fd'], 2)} kPa", "AS/NZS 1170.0 Cl 4.2.2"),
        calcpad.row("Positive moment, short span", "Mx* = betax Fd Lx^2",
                    f"{num(moments['Mx'], 1)} kNm/m", "Cl 6.10.3.2(a)"),
        calcpad.row("Positive moment, long span", "My* = betay Fd Lx^2",
                    f"{num(moments['My'], 1)} kNm/m", "Cl 6.10.3.2(a)"),
        calcpad.row("Minimum effective depth", "d.min / d.min.inc",
                    f"{num(deflection['dmin'], 0)} / {num(deflection['dmini'], 0)} mm",
                    "Cl 9.4.4.2"),
        calcpad.row("Effective depth provided", "ds = th - cover - db / 2",
                    f"{num(deflection['ds'], 0)} mm"),
    ]
    for key, label, expression, reference in CHECK_ROWS:
        if key in result["util"]:
            rows.append(calcpad.row(label, expression, calcpad.badge(result["util"][key]),
                                    reference))
    rows.append(calcpad.row("Governing", "Maximum utilisation", calcpad.badge(result["worstUtil"])))
    return calcpad.table("Design Summary", rows)


def _inputs(inputs: dict[str, Any]) -> list[str]:
    groups = [
        ("Geometry and Material", [
            ("Concrete strength f'c", "fc", "MPa"), ("Slab thickness", "th", "mm"),
            ("Long edge length", "Ly", "mm"), ("Short edge length", "Lx", "mm"),
            ("Continuous long edges", "contLong", ""), ("Continuous short edges", "contShort", ""),
            ("Reinforcement ductility class", "reo", ""), ("Allow redistribution", "redist", ""),
            ("Closed-form coefficients", "useFormula", "")]),
        ("Loading", [
            ("Include self weight", "includeSW", ""), ("Superimposed dead load", "wsdl", "kPa"),
            ("Live load", "wll", "kPa"), ("Live load type", "loadType", "")]),
        ("Reinforcement and Deflection", [
            ("Tensile steel", "Ast", "mm2/m"), ("Yield strength", "fsy", "MPa"),
            ("Cover to bottom steel", "cover", "mm"), ("Bar size", "dia", "mm"),
            ("Compression steel", "Asc", "mm2/m"), ("Depth to compression steel", "dc", "mm"),
            ("Use fcmi for Ec", "useFcmi", ""), ("Concrete density", "density", "kg/m3"),
            ("Total deflection limit Lef/Delta", "lefDelta", ""),
            ("Incremental deflection limit Lef/Delta", "lefDeltaInc", "")]),
    ]
    checks = inputs.get("checks") or {}
    if checks.get("flexure"):
        fields = [("Cover to top steel", "coverTop", "mm")]
        for key, label in FLEXURE_LAYERS.items():
            fields += [(f"{label} bar", f"bar{key}", "mm"), (f"{label} spacing", f"s{key}", "mm")]
        groups.append(("Flexural Reinforcement", fields))
    if checks.get("shrinkage"):
        groups.append(("Shrinkage and Temperature", [("Degree of restraint", "restraint", "")]))
    return [calcpad.matrix(f"Design Inputs - {title}",
                           [(label, key, inputs.get(key, ""), unit) for label, key, unit in fields
                            if str(inputs.get(key, "")).strip() != ""])
            for title, fields in groups]


def _hatch(x1: float, y1: float, x2: float, y2: float, outward: tuple[float, float]) -> str:
    """Short diagonal ticks along a continuous edge, drawn on the outside of the panel."""
    length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    count = max(2, int(length / 3.0))
    ox, oy = outward
    ticks = []
    for index in range(count + 1):
        t = index / count
        x, y = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
        ticks.append(f'<line x1="{x:.2f}" y1="{y:.2f}" x2="{x + ox * 2.2 + oy * 1.2:.2f}" '
                     f'y2="{y + oy * 2.2 + ox * 1.2:.2f}" stroke="#555" stroke-width="0.2"/>')
    return "".join(ticks)


def panel_drawing(result: dict[str, Any], target: float = 90.0) -> str:
    """Plan of the panel with continuous edges hatched and the design moments labelled."""
    analysis, edges, moments = result["analysis"], result["edges"], result["moments"]
    Ly, Lx = analysis["Ly"], analysis["Lx"]
    aspect = min(Ly / Lx, 3.0)
    body_w = target
    body_h = max(target / aspect, 22.0)
    left, top = 16.0, 12.0
    width, height = body_w + 2 * left, body_h + 2 * top
    right, bottom = left + body_w, top + body_h
    parts = [f'<rect x="{left}" y="{top}" width="{body_w:.2f}" height="{body_h:.2f}" '
             'fill="#f1f2f0" stroke="#111" stroke-width="0.55"/>']
    if edges["longTopContinuous"]:
        parts.append(_hatch(left, top, right, top, (0.0, -1.0)))
    if edges["longBottomContinuous"]:
        parts.append(_hatch(left, bottom, right, bottom, (0.0, 1.0)))
    if edges["shortLeftContinuous"]:
        parts.append(_hatch(left, top, left, bottom, (-1.0, 0.0)))
    if edges["shortRightContinuous"]:
        parts.append(_hatch(right, top, right, bottom, (1.0, 0.0)))
    cx, cy = left + body_w / 2, top + body_h / 2

    def text(x: float, y: float, value: str, anchor: str = "middle", rotate: bool = False,
             colour: str = "#111") -> str:
        spin = f' transform="rotate(-90 {x:.2f} {y:.2f})"' if rotate else ""
        return (f'<text x="{x:.2f}" y="{y:.2f}" font-size="2.6" text-anchor="{anchor}" '
                f'fill="{colour}"{spin}>{escape(value)}</text>')

    parts += [
        text(cx, top - 4.5, f"Mx* = {edges['longTop']:.1f} kNm/m", colour="#1c4fa1"),
        text(cx, bottom + 6.5, f"Mx* = {edges['longBottom']:.1f} kNm/m", colour="#1c4fa1"),
        text(left - 4.5, cy, f"My* = {edges['shortLeft']:.1f}", rotate=True, colour="#1c4fa1"),
        text(right + 6.0, cy, f"My* = {edges['shortRight']:.1f}", rotate=True, colour="#1c4fa1"),
        f'<line x1="{cx:.2f}" y1="{top + 3:.2f}" x2="{cx:.2f}" y2="{bottom - 3:.2f}" '
        'stroke="#b1257a" stroke-width="0.3" stroke-dasharray="1.4,1"/>',
        f'<line x1="{left + 3:.2f}" y1="{cy:.2f}" x2="{right - 3:.2f}" y2="{cy:.2f}" '
        'stroke="#b1257a" stroke-width="0.3" stroke-dasharray="1.4,1"/>',
        text(cx + 1.5, cy - 2.0, f"Mx* = {moments['Mx']:.1f} kNm/m", "start", colour="#b1257a"),
        text(cx - 1.5, cy + 4.0, f"My* = {moments['My']:.1f} kNm/m", "end", colour="#b1257a"),
        text(cx, bottom + 10.5, f"Ly = {Ly:,.0f} mm"),
        text(right + 10.5, cy, f"Lx = {Lx:,.0f} mm", rotate=True),
    ]
    return (f'<svg viewBox="0 0 {width:.2f} {height:.2f}" width="{width:.2f}mm" '
            f'height="{height:.2f}mm" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="Two-way slab panel">{"".join(parts)}</svg>')


def _panel_figure(result: dict[str, Any]) -> str:
    caption = (f"{result['analysis']['edgeLabel']}. Hatched edges are continuous. Edge values are "
               "negative design moments; centre values are positive midspan moments. Mx* spans "
               "the short direction Lx and My* the long direction Ly. Corners are held down.")
    return calcpad.figure("Slab Panel and Design Moments", panel_drawing(result), caption,
                          weight=24)


def _material(result: dict[str, Any]) -> str:
    deflection, minimum = result["deflection"], result["minimum"]
    fcmi_basis = ("fcmi = -0.0015 f'c^2 + 1.1429 f'c - 0.0614" if deflection["useFcmi"]
                  else "fcmi taken as f'c")
    ec_basis = ("Ec = rho^1.5 (0.043 sqrt(fcmi))" if deflection["fcmi"] <= 40
                else "Ec = rho^1.5 (0.024 sqrt(fcmi) + 0.12)")
    rows = [
        calcpad.row("Concrete strength", "f'c", f"{num(result['inputs']['fc'], 0)} MPa",
                    "Cl 1.1.2, 20 to 120 MPa"),
        calcpad.row("Mean in-situ strength", fcmi_basis,
                    f"{num(deflection['fcmi'], 2)} MPa", "Table 3.1.2"),
        calcpad.row("Density", "rho", f"{num(deflection['density'], 0)} kg/m3", "Cl 3.1.3"),
        calcpad.row("Modulus of elasticity", ec_basis, f"{num(deflection['Ec'], 0)} MPa +/- 20%",
                    "Cl 3.1.2"),
        calcpad.row("Modular ratio", "n = Es / Ec", num(deflection["n"], 3), "Es = 200 GPa"),
        calcpad.row("Flexural tensile strength", "f'ct.f = 0.6 sqrt(f'c)",
                    f"{num(minimum['fctf'], 3)} MPa", "Cl 3.1.1.3"),
        calcpad.row("Yield strength", "fsy", f"{num(result['inputs']['fsy'], 0)} MPa"),
    ]
    return calcpad.table("Material Properties - Section 3", rows)


def _actions(result: dict[str, Any]) -> str:
    loads = result["loads"]
    sw = (f"{num(loads['swt'], 2)} kPa" if loads["includeSW"] else "excluded")
    rows = [
        calcpad.row("Self weight", "S.Wt = 25 th / 1000", sw),
        calcpad.row("Superimposed dead load", "wsdl", f"{num(loads['wsdl'], 2)} kPa"),
        calcpad.row("Dead load", "wdl = S.Wt + wsdl", f"{num(loads['wdl'], 2)} kPa"),
        calcpad.row("Live load", "wll", f"{num(loads['wll'], 2)} kPa"),
        calcpad.row("Strength combination", "Fd = max(1.35 wdl, 1.2 wdl + 1.5 wll)",
                    f"{num(loads['Fd'], 2)} kPa", f"AS/NZS 1170.0 Cl 4.2.2, {escape(loads['case'])}"),
        calcpad.row("Live load use", LOAD_TYPES[loads["loadType"]],
                    f"psi_s = {num(loads['psiS'], 2)}, psi_l = {num(loads['psiL'], 2)}",
                    "AS/NZS 1170.0 Table 4.1"),
        calcpad.row("Live to dead load ratio", "wll / wdl <= 1",
                    calcpad.badge(result["util"]["liveLoadLimit"]), "Cl 9.4.4.2"),
    ]
    return calcpad.table("Design Actions - AS/NZS 1170.0", rows)


def _coefficients(result: dict[str, Any]) -> tuple[str, str]:
    analysis = result["analysis"]
    rows = [
        calcpad.row("Edge code", "discont. long + 3 discont. short + 1",
                    f"{analysis['code']} - {escape(analysis['edgeLabel'])}"),
        calcpad.row("Design class", "L if Class L or no redistribution",
                    f"Class {analysis['class']}", "Cl 6.10.3.2"),
        calcpad.row("Coefficient source", "Cl 6.10.3.2", escape(SOURCE_LABELS[analysis["source"]])),
        calcpad.row("Span ratio", "Ly / Lx", num(analysis["yx"], 3)),
        calcpad.row("Edge factors", "deltax / deltay",
                    f"{num(analysis['deltaX'], 1)} / {num(analysis['deltaY'], 1)}", "WRH"),
        calcpad.row("Short span coefficient", "betax", num(analysis["betaX"], 4), "Table 6.10.3.2"),
        calcpad.row("Long span coefficient", "betay", num(analysis["betaY"], 4), "Table 6.10.3.2"),
    ]
    if analysis["class"] == "L":
        rows += [calcpad.row("Negative factor, short span", "alphax", num(analysis["alphaX"], 3),
                             "Table 6.10.3.2(B)"),
                 calcpad.row("Negative factor, long span", "alphay", num(analysis["alphaY"], 3),
                             "Table 6.10.3.2(B)")]
    comparison = calcpad.grid(
        "Coefficient Comparison", ["Source", "betax", "betay"],
        [["Closed form (WRH)", num(analysis["formulaBx"], 4), num(analysis["formulaBy"], 4)],
         ["Table 6.10.3.2(A)", num(analysis["tableABx"], 4), num(analysis["tableABy"], 4)],
         ["Table 6.10.3.2(B)", num(analysis["tableBBx"], 4), num(analysis["tableBBy"], 4)]],
        "Interpolated linearly in Ly/Lx between 1.0 and 2.0; the '> 2' column applies above 2.0.")
    return calcpad.table("Moment Coefficients - Cl 6.10.3.2", rows), comparison


def _moments(result: dict[str, Any]) -> tuple[str, str]:
    moments, analysis = result["moments"], result["analysis"]
    klass = analysis["class"]
    cont_x = "1.33" if klass == "N" else "alphax"
    cont_y = "1.33" if klass == "N" else "alphay"
    disc = num(moments["discFactor"], 1)
    rows = [
        calcpad.row("Positive moment, short span", "Mx* = betax Fd Lx^2",
                    f"{num(moments['Mx'], 2)} kNm/m", "Cl 6.10.3.2(a)"),
        calcpad.row("Positive moment, long span", "My* = betay Fd Lx^2",
                    f"{num(moments['My'], 2)} kNm/m", "Cl 6.10.3.2(a)"),
        calcpad.row("Negative at continuous long edge", f"{cont_x} Mx*",
                    f"{num(moments['MxCont'], 2)} kNm/m", "Cl 6.10.3.2(b)"),
        calcpad.row("Negative at continuous short edge", f"{cont_y} My*",
                    f"{num(moments['MyCont'], 2)} kNm/m", "Cl 6.10.3.2(b)"),
        calcpad.row("Negative at discontinuous long edge", f"{disc} Mx*",
                    f"{num(moments['MxDisc'], 2)} kNm/m", "Cl 6.10.3.2(c)"),
        calcpad.row("Negative at discontinuous short edge", f"{disc} My*",
                    f"{num(moments['MyDisc'], 2)} kNm/m", "Cl 6.10.3.2(c)"),
    ]
    table = calcpad.table("Design Bending Moments - Cl 6.10.3.2", rows)
    if result["flexure"]:
        return table, ""
    note = ("Flexural capacity is not checked unless the optional flexure group is enabled. "
            "Otherwise design the positive and negative regions for these moments separately.")
    return table, calcpad.prose("", f"<p>{escape(note)}</p>", weight=2)


def _minimum(result: dict[str, Any]) -> str:
    minimum = result["minimum"]
    rows = [
        calcpad.row("Effective depth", "ds = th - cover - db / 2", f"{num(minimum['ds'], 1)} mm"),
        calcpad.row("Minimum reinforcement", "Ast.min = 0.19 (D/d)^2 f'ct.f / fsy b d",
                    f"{num(minimum['Astmin'], 1)} mm2/m", "Cl 9.1.1(b)"),
        calcpad.row("Tensile steel provided", "Ast", f"{num(result['deflection']['Ast'], 1)} mm2/m"),
        calcpad.row("Minimum strength check", "Ast.min / Ast",
                    calcpad.badge(result["util"]["minimumSteel"]), "Cl 9.1.1"),
        calcpad.row("For comparison, one-way", "0.20 (D/d)^2 f'ct.f / fsy b d",
                    f"{num(minimum['AstminOneWay'], 1)} mm2/m", "Eq 8.1.6.1(2)"),
        calcpad.row("For comparison, column supported", "0.24 (D/d)^2 f'ct.f / fsy b d",
                    f"{num(minimum['AstminColumns'], 1)} mm2/m", "Cl 9.1.1(a)"),
    ]
    return calcpad.table("Minimum Strength Requirements - Cl 9.1.1", rows)


def _deflection(result: dict[str, Any]) -> str:
    d = result["deflection"]
    asc = "ignored, in tension zone" if d["ascIgnored"] else f"{num(d['Asc'], 0)} mm2/m"
    rows = [
        calcpad.row("Tension steel ratio", "p = Ast / (b ds)", num(d["p"], 5)),
        calcpad.row("Compression steel ratio", "pc = Asc / (b ds)", num(d["pc"], 5)),
        calcpad.row("Neutral axis parameter",
                    "ku = sqrt[(np + (n-1)pc)^2 + 2(np + (n-1)pc dc/ds)] - (np + (n-1)pc)",
                    num(d["ku"], 4), "WRH Eq 5.22"),
        calcpad.row("Cracked neutral axis depth", "kud = ku ds", f"{num(d['NA'], 1)} mm"),
        calcpad.row("Compression steel for kcs", "Asc used when kud - db/2 >= dc", asc),
        calcpad.row("Long-term factor", "kcs = 2 - 1.2 Asc / Ast >= 0.8", num(d["kcs"], 3),
                    "Cl 8.5.3.2"),
        calcpad.row("Effective load, total", "Fd.ef = (1 + kcs) g + (psi_s + kcs psi_l) q",
                    f"{num(d['Fdef'], 2)} kPa", "Cl 9.4.4.1(a)"),
        calcpad.row("Effective load, incremental", "Fd.ef.inc = kcs g + (psi_s + kcs psi_l) q",
                    f"{num(d['Fdefi'], 2)} kPa", "Cl 9.4.4.1(b)"),
        calcpad.row("Slab factors", "k3 / k4", f"{num(d['k3'], 1)} / {num(d['k4'], 3)}",
                    "Table 9.4.4.2"),
        calcpad.row("Deflection limits", "Lef / Delta, total / incremental",
                    f"{num(d['lefDelta'], 0)} / {num(d['lefDeltaInc'], 0)}", "Table 2.3.2"),
        calcpad.row("Minimum depth, total", "d.min = Lx / (k3 k4 [(Delta/Lef) Ec / Fd.ef]^(1/3))",
                    f"{num(d['dmin'], 1)} mm", "Cl 9.4.4.2"),
        calcpad.row("Minimum depth, incremental", "same with Fd.ef.inc",
                    f"{num(d['dmini'], 1)} mm", "Cl 9.4.4.2"),
        calcpad.row("Equivalent thickness", "th.min = db/2 + cover + d.min",
                    f"{num(d['thmin'], 0)} / {num(d['thmininc'], 0)} mm"),
        calcpad.row("Total deflection check", "d.min / ds",
                    calcpad.badge(result["util"]["deflectionTotal"])),
        calcpad.row("Incremental deflection check", "d.min.inc / ds",
                    calcpad.badge(result["util"]["deflectionIncremental"])),
    ]
    return calcpad.table("Deflection by Deemed-to-Comply Span-to-Depth - Cl 9.4.4.2", rows)


def _shrinkage(result: dict[str, Any]) -> str:
    data = result["shrinkage"]
    if not data:
        return ""
    rows = [
        calcpad.row("Restraint condition", "Cl 9.4.3", escape(data["label"])),
        calcpad.row("Reinforcement ratio", "p", num(data["p"], 5), "Cl 9.4.3.4"),
        calcpad.row("Two-way slab, each direction", "As.cs = 0.75 p b D",
                    f"{num(data['AsCrack'], 0)} mm2/m", "Cl 9.4.3.3"),
    ]
    if "shrinkage" in result["util"]:
        rows.append(calcpad.row("Shrinkage reinforcement check", "As.cs / Ast",
                                calcpad.badge(result["util"]["shrinkage"])))
    else:
        rows.append(calcpad.row("Application", "As.min = max(As.cs, 0.19 (D/d)^2 f'ct.f/fsy b d)",
                                "at every flexure location"))
    return calcpad.table("Shrinkage and Temperature Reinforcement - Cl 9.4.3", rows)


def _flexure(result: dict[str, Any]) -> list[str]:
    data = result["flexure"]
    if not data:
        return []
    first = data["locations"][0]
    rows = [
        calcpad.row("Stress block factors", "alpha2 = 0.85 - 0.0015 f'c >= 0.67; "
                    "gamma = 0.97 - 0.0025 f'c >= 0.67",
                    f"{num(first['alpha2'], 3)} / {num(first['gamma'], 3)}", "Cl 8.1.3"),
        calcpad.row("Neutral axis parameter", "ku = As fsy / (alpha2 f'c gamma b d)", "per location",
                    "Cl 8.1.5"),
        calcpad.row("Capacity reduction factor",
                    "Class N: phi = 1.24 - 13 ku / 12, 0.65 to 0.85; Class L: 0.65",
                    "per location", "Table 2.2.2"),
        calcpad.row("Moment capacity", "phiMu = phi As fsy d (1 - As fsy / (2 alpha2 f'c b d))",
                    "per location", "Cl 8.1"),
        calcpad.row("Maximum bar spacing", "smax = min(300, 2D)", f"{num(data['sMax'], 0)} mm",
                    "Cl 9.4.1"),
    ]
    grid = calcpad.grid(
        "Flexural Capacity by Location",
        ["Location", "Bars", "As", "d", "ku", "phi", "M*", "phiMu", "M*/phiMu", "As.min"],
        [[escape(item["label"]), f"N{num(item['bar'], 0)}-{num(item['spacing'], 0)}",
          num(item["As"], 0), num(item["d"], 0), num(item["ku"], 3), num(item["phi"], 3),
          num(item["Mstar"], 1), num(item["phiMu"], 1), calcpad.badge(item["ratioMoment"]),
          num(item["AsMin"], 0)] for item in data["locations"]],
        "As and As.min in mm2/m, d in mm, moments in kNm/m. Short-span bars are the outer layer.")
    return [calcpad.table("Flexural Capacity - Cl 8.1", rows), grid]


def _basis(result: dict[str, Any]) -> str:
    def items(values: list[str]) -> str:
        return "<ul>" + "".join(f"<li>{escape(value)}</li>" for value in values) + "</ul>"

    body = ("<h3>Assumptions</h3>" + items(result["assumptions"])
            + "<h3>Limitations and exclusions</h3>" + items(result["limitations"]))
    if result["warnings"]:
        body += "<h3>Warnings</h3>" + items(result["warnings"])
    weight = 6 + 2 * (len(result["assumptions"]) + len(result["limitations"])
                      + len(result["warnings"]))
    return calcpad.prose("Design Basis, Assumptions and Limitations", body, weight=weight)
