"""Calculation-pad presentation for the punching shear module, in the column-module layout.

Only formatting happens here; every engineering value comes from
:func:`ic_concrete_punching_shear.engine.compute`.
"""

from __future__ import annotations

from html import escape
from typing import Any

import calcpad

from .version import VERSION

DATA_ID = "concrete-punching-shear-inputs"
DEFAULT_SUBJECT = "Punching shear design"
num = calcpad.number
force = calcpad.force
moment = calcpad.moment

CHECK_ROWS = [
    ("punching", "Punching shear strength", "V* / phiVu", "Cl 9.3.3, Cl 9.3.4"),
    ("fitmentArea", "Minimum closed fitment area", "Asw.min / Asw", "Cl 9.3.5"),
    ("fitmentSpacing", "Maximum closed fitment spacing", "s / s.max", "Cl 9.3.6"),
    ("fitmentWidth", "Fitment width within the torsion strip", "wcl / a", "Workbook Design!H13"),
    ("prestressDepth", "do for a prestressed slab", "0.8 Ds / do", "Cl 1.7 (workbook)"),
    ("integrity", "Integrity reinforcement", "As.min / As", "Cl 9.2.2 (workbook)"),
]


def render(inputs: dict[str, Any], result: dict[str, Any], *, standalone: bool = False,
           appendix: list[str] | None = None, anchor_prefix: str = "",
           contents_href: str = "") -> str:
    blocks = [
        _summary(result),
        *_inputs(inputs, result),
        _plan_figure(result),
        _perimeter(result),
        _strength_no_moment(result),
        _strength_moment(result),
        _fitments(result),
        *_governing(result),
        _moment_transfer(result),
        _integrity(result),
        _basis(result),
    ]
    title = (f"{inputs.get('memberType', 'Slab')}-{inputs.get('memberNumber', '')} "
             f"- Concrete Punching Shear Design {VERSION}")
    return calcpad.render(inputs, blocks, standalone=standalone, appendix=appendix,
                          anchor_prefix=anchor_prefix, contents_href=contents_href,
                          default_subject=DEFAULT_SUBJECT, data_id=DATA_ID, title=title)


def _column(geometry: dict[str, Any]) -> str:
    if geometry["circular"]:
        return f"D = {num(geometry['pL'], 0)} mm circular"
    return f"{num(geometry['pL'], 0)} x {num(geometry['pW'], 0)} mm rectangular"


def _summary(result: dict[str, Any]) -> str:
    g, s, m, gov = result["geometry"], result["strength"], result["moment"], result["governing"]
    place = g["positionTitle"].lower() + (", spandrel beam" if g["spandrel"] else "")
    rows = [
        calcpad.row("Column and position", "Loaded area", f"{_column(g)}, {escape(place)}",
                    "Cl 9.3.1"),
        calcpad.row("Slab", "Ds, dom, f'c",
                    f"Ds = {num(g['Ds'], 0)} mm, dom = {num(g['domc'], 1)} mm, "
                    f"f'c = {num(result['inputs']['fc'], 0)} MPa"),
        calcpad.row("Critical shear perimeter", "u at dom/2 from the face",
                    f"{num(g['u'], 0)} mm", "Cl 9.3.1.3"),
        calcpad.row("Design actions", "V*, Mv*",
                    f"{force(result['inputs']['Vstar'])} kN, {moment(m['Mdesign'], 2)} kNm"),
        calcpad.row("Strength without moment transfer", "phiVuo", f"{force(s['phiVuo'])} kN",
                    "Cl 9.3.3"),
        calcpad.row("Governing strength", escape(gov["label"]), f"{force(gov['capacity'])} kN",
                    f"{escape(gov['case'])}, {escape(gov['equation'])}"),
    ]
    for key, label, expression, reference in CHECK_ROWS:
        if key in result["util"]:
            rows.append(calcpad.row(label, expression, calcpad.badge(result["util"][key]),
                                    reference))
    rows.append(calcpad.row("Governing", "Maximum utilisation", calcpad.badge(result["worstUtil"])))
    return calcpad.table("Design Summary", rows)


def _inputs(inputs: dict[str, Any], result: dict[str, Any]) -> list[str]:
    g = result["geometry"]
    groups = [
        ("Slab and Column", [
            ("Concrete strength f'c", "fc", "MPa"), ("Slab depth", "Ds", "mm"),
            ("Slab distance do", "dom", "mm"), ("Circular column", "col", ""),
            ("Larger column dimension L", "pL", "mm"), ("Shorter column dimension W", "pW", "mm"),
            ("Position", "pPos", ""), ("Face on edge", "pface", ""),
            ("Spandrel both sides of corner", "spanbothsides", ""),
            ("Ineffective portion of perimeter", "ineffU", "mm")]),
        ("Actions", [
            ("Design shear V*", "Vstar", "kN"), ("Moment transferred Mv*", "Mvstar", "kNm"),
            ("Direction of moment", "pmDir", ""), ("Average prestress", "ps", "MPa"),
            ("Shear head", "shearhead", "")]),
        ("Spandrel Beam", [
            ("Spandrel beam", "span", ""), ("Ignore spandrel for dom", "ignorespan", ""),
            ("Spandrel depth Db", "Db", "mm"), ("Width of spandrel bw", "bw", "mm")]),
        ("Closed Fitments", [
            ("Fitment bar size", "dialp", "mm"), ("Fitment spacing s", "ctsp", "mm"),
            ("Fitment yield strength fsy.f", "fyp", "MPa"), ("Cover for y1", "cover", "mm"),
            ("Width of closed fitment (O/A)", "wcl", "mm")]),
        ("Integrity Reinforcement", [
            ("Column reaction N*", "Nstar", "kN"), ("Bar yield strength fsy", "fsy", "MPa"),
            ("Ductility class", "ductility", ""), ("Bar size", "ibar", "mm"),
            ("Bottom bars through the column", "nIntegrity", ""),
            ("Beams with shear reinforcement in all spans", "beams", "")]),
        ("Moment Transfer", [
            ("Slab designed by the simplified method", "simplifiedMethod", ""),
            ("Larger adjoining span Lo", "pLo", "mm"), ("Smaller adjoining span Lo'", "pLod", "mm"),
            ("Design strip width Lt", "pLt", "mm"), ("Dead load G", "Vdl", "kPa"),
            ("Live load Q", "Vll", "kPa")]),
    ]
    hidden = set()
    if g["circular"]:
        hidden |= {"pW", "pface"}
    if g["position"] == "I":
        hidden.add("pface")
    if g["position"] != "C":
        hidden.add("spanbothsides")
    if not g["spandrel"]:
        hidden.add("ignorespan")
    if result["layers"]:
        hidden.add("dom")
        groups.append(("Mean Depth from Bar Layers", [
            ("Cover to tension reinforcement", "domCover", "mm"),
            ("Outer layer bar size", "barOuter", "mm"), ("Inner layer bar size", "barInner", "mm")]))
    return [calcpad.matrix(f"Design Inputs - {title}",
                           [(label, key, inputs.get(key, ""), unit) for label, key, unit in fields
                            if key not in hidden and str(inputs.get(key, "")).strip() != ""])
            for title, fields in groups]


# ---------------------------------------------------------------------------
#  Plan drawing
# ---------------------------------------------------------------------------
def plan_drawing(result: dict[str, Any], target: float = 96.0, max_height: float = 84.0) -> str:
    """Scaled plan of the loaded area, free edges, spandrel and critical perimeter."""
    g = result["geometry"]
    d, pos, circular = g["domc"], g["position"], g["circular"]
    half = d / 2.0
    if circular:
        r = g["pL"] / 2.0
        rd = r + half
        centre = {"I": (0.0, 0.0), "E": (0.0, r), "C": (r, r)}[pos]
        x_min = {"I": -rd, "E": -rd, "C": 0.0}[pos]
        x_max = {"I": rd, "E": rd, "C": r + rd}[pos]
        y_min = {"I": -rd, "E": 0.0, "C": 0.0}[pos]
        y_max = {"I": rd, "E": r + rd, "C": r + rd}[pos]
    else:
        if pos == "I":
            w, h = g["pL"], g["pW"]
            box = (-w / 2.0, -h / 2.0, w / 2.0, h / 2.0)
        elif pos == "E":
            w, h = g["pX"], g["pY"]
            box = (-w / 2.0, 0.0, w / 2.0, h)
        else:
            w, h = g["pX"], g["pY"]
            box = (0.0, 0.0, w, h)
        x_min = box[0] - half if pos != "C" else 0.0
        x_max = box[2] + half
        y_min = box[1] - half if pos == "I" else 0.0
        y_max = box[3] + half
    extent = max(x_max - x_min, y_max - y_min)
    margin = 0.35 * extent
    slab = [x_min - margin if pos != "C" else 0.0, y_min - margin if pos == "I" else 0.0,
            x_max + margin, y_max + margin * 1.4]
    scale = min(target / (slab[2] - slab[0]), max_height / (slab[3] - slab[1]))
    left, top = 8.0, 9.0

    def px(x: float) -> float:
        return left + (x - slab[0]) * scale

    def py(y: float) -> float:
        return top + (y - slab[1]) * scale

    def text(x: float, y: float, value: str, anchor: str = "middle", colour: str = "#111",
             rotate: bool = False) -> str:
        spin = f' transform="rotate(-90 {x:.2f} {y:.2f})"' if rotate else ""
        return (f'<text x="{x:.2f}" y="{y:.2f}" font-size="2.5" text-anchor="{anchor}" '
                f'fill="{colour}"{spin}>{escape(value)}</text>')

    width = (slab[2] - slab[0]) * scale + 2 * left
    height = (slab[3] - slab[1]) * scale + top + 6.0
    parts = [f'<rect x="{px(slab[0]):.2f}" y="{py(slab[1]):.2f}" '
             f'width="{(slab[2] - slab[0]) * scale:.2f}" height="{(slab[3] - slab[1]) * scale:.2f}" '
             'fill="#f1f2f0" stroke="#999" stroke-width="0.25" stroke-dasharray="1.2,0.8"/>']
    if g["spandrel"] and pos != "I":
        band = min(g["bw"], slab[3] - slab[1])
        parts.append(f'<rect x="{px(slab[0]):.2f}" y="{py(0.0):.2f}" '
                     f'width="{(slab[2] - slab[0]) * scale:.2f}" height="{band * scale:.2f}" '
                     'fill="#d9e3f0" stroke="none"/>')
        if pos == "C" and g["bothSides"]:
            band_x = min(g["bw"], slab[2] - slab[0])
            parts.append(f'<rect x="{px(0.0):.2f}" y="{py(0.0):.2f}" width="{band_x * scale:.2f}" '
                         f'height="{(slab[3] - slab[1]) * scale:.2f}" fill="#d9e3f0" stroke="none"/>')
        beyond = " (beyond view)" if g["bw"] > slab[3] - slab[1] else ""
        parts.append(text(px(slab[0]) + 1.0, py(0.0) - 1.4,
                          f"Spandrel bw = {g['bw']:,.0f} mm{beyond}", "start", "#1c4fa1"))
    if pos in ("E", "C"):
        parts.append(f'<line x1="{px(slab[0]):.2f}" y1="{py(0.0):.2f}" x2="{px(slab[2]):.2f}" '
                     f'y2="{py(0.0):.2f}" stroke="#111" stroke-width="0.8"/>')
        parts.append(text(px(slab[2]) - 1.0, py(0.0) - 1.4, "Free edge", "end"))
    if pos == "C":
        parts.append(f'<line x1="{px(0.0):.2f}" y1="{py(slab[1]):.2f}" x2="{px(0.0):.2f}" '
                     f'y2="{py(slab[3]):.2f}" stroke="#111" stroke-width="0.8"/>')
        parts.append(text(px(0.0) - 1.4, py(slab[3]) - 1.0, "Free edge", "start", rotate=True))

    dash = 'fill="none" stroke="#b1257a" stroke-width="0.45" stroke-dasharray="1.6,1"'
    if circular:
        cx, cy = centre
        parts.append(f'<circle cx="{px(cx):.2f}" cy="{py(cy):.2f}" r="{r * scale:.2f}" '
                     'fill="#8a8f96" stroke="#111" stroke-width="0.4"/>')
        if pos == "I":
            parts.append(f'<circle cx="{px(cx):.2f}" cy="{py(cy):.2f}" r="{rd * scale:.2f}" {dash}/>')
        elif pos == "E":
            parts.append(f'<path d="M {px(-rd):.2f} {py(0):.2f} L {px(-rd):.2f} {py(r):.2f} '
                         f'A {rd * scale:.2f} {rd * scale:.2f} 0 0 0 {px(rd):.2f} {py(r):.2f} '
                         f'L {px(rd):.2f} {py(0):.2f}" {dash}/>')
        else:
            parts.append(f'<path d="M {px(r + rd):.2f} {py(0):.2f} L {px(r + rd):.2f} {py(r):.2f} '
                         f'A {rd * scale:.2f} {rd * scale:.2f} 0 0 1 {px(r):.2f} {py(r + rd):.2f} '
                         f'L {px(0):.2f} {py(r + rd):.2f}" {dash}/>')
        column_label = f"D = {g['pL']:,.0f}"
        label_at = (px(cx), py(cy) + 0.9)
    else:
        parts.append(f'<rect x="{px(box[0]):.2f}" y="{py(box[1]):.2f}" '
                     f'width="{(box[2] - box[0]) * scale:.2f}" height="{(box[3] - box[1]) * scale:.2f}" '
                     'fill="#8a8f96" stroke="#111" stroke-width="0.4"/>')
        if pos == "I":
            parts.append(f'<rect x="{px(x_min):.2f}" y="{py(y_min):.2f}" '
                         f'width="{(x_max - x_min) * scale:.2f}" height="{(y_max - y_min) * scale:.2f}" '
                         f'{dash}/>')
        elif pos == "E":
            parts.append(f'<path d="M {px(x_min):.2f} {py(0):.2f} L {px(x_min):.2f} {py(y_max):.2f} '
                         f'L {px(x_max):.2f} {py(y_max):.2f} L {px(x_max):.2f} {py(0):.2f}" {dash}/>')
        else:
            parts.append(f'<path d="M {px(x_max):.2f} {py(0):.2f} L {px(x_max):.2f} {py(y_max):.2f} '
                         f'L {px(0):.2f} {py(y_max):.2f}" {dash}/>')
        column_label = f"{w:,.0f} x {h:,.0f}"
        label_at = (px((box[0] + box[2]) / 2.0), py((box[1] + box[3]) / 2.0) + 0.9)
    parts.append(text(*label_at, column_label, colour="#fff"))

    l_horizontal = pos == "I" or circular or g["face"] == "L"
    horizontal = l_horizontal if g["pmDir"] == "L" else not l_horizontal
    arrow = 'stroke="#1c4fa1" stroke-width="0.35" marker-start="url(#ps-arrow)" marker-end="url(#ps-arrow)"'
    if horizontal:
        level = py(y_max) + margin * 0.55 * scale
        parts.append(f'<line x1="{px(x_min):.2f}" y1="{level:.2f}" x2="{px(x_max):.2f}" '
                     f'y2="{level:.2f}" {arrow}/>')
        parts.append(text((px(x_min) + px(x_max)) / 2.0, level + 3.4,
                          f"a = {g['a']:,.0f} mm, parallel to Mv*", colour="#1c4fa1"))
    else:
        level = px(x_max) + margin * 0.45 * scale
        parts.append(f'<line x1="{level:.2f}" y1="{py(y_min):.2f}" x2="{level:.2f}" '
                     f'y2="{py(y_max):.2f}" {arrow}/>')
        parts.append(text(level + 3.2, (py(y_min) + py(y_max)) / 2.0,
                          f"a = {g['a']:,.0f} mm, parallel to Mv*", colour="#1c4fa1", rotate=True))
    parts.append(text((px(x_min) + px(x_max)) / 2.0, py(y_max) + 3.0,
                      f"u = {g['u']:,.0f} mm at dom/2 = {half:,.1f} mm", colour="#b1257a"))
    marker = ('<defs><marker id="ps-arrow" viewBox="0 0 6 6" refX="3" refY="3" markerWidth="3" '
              'markerHeight="3" orient="auto-start-reverse"><path d="M0,0 L6,3 L0,6 z" '
              'fill="#1c4fa1"/></marker></defs>')
    return (f'<svg viewBox="0 0 {width:.2f} {height:.2f}" width="{width:.2f}mm" '
            f'height="{height:.2f}mm" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="Punching shear plan">{marker}{"".join(parts)}</svg>')


def _plan_figure(result: dict[str, Any]) -> str:
    g = result["geometry"]
    caption = (f"{g['udesc']}. The dashed line is the critical shear perimeter at dom/2 from the "
               "face of the support, with the ineffective portion deducted from u "
               f"({g['ineffU']:,.0f} mm).")
    if g["spandrel"] and g["position"] != "I":
        caption += " The shaded band is the spandrel beam."
    return calcpad.figure("Plan of Loaded Area and Critical Shear Perimeter", plan_drawing(result),
                          caption, weight=26)


# ---------------------------------------------------------------------------
#  Check tables
# ---------------------------------------------------------------------------
def _u_expression(g: dict[str, Any]) -> str:
    if g["circular"]:
        return {"I": "u = pi (D + dom)", "E": "u = pi (D + dom) / 2 + D",
                "C": "u = pi (D + dom) / 4 + D"}[g["position"]]
    return {"I": "u = 2 (L + dom + W + dom)", "E": "u = 2 (pY + dom/2) + pX + dom",
            "C": "u = pX + dom/2 + pY + dom/2"}[g["position"]]


def _a_expressions(g: dict[str, Any]) -> tuple[str, str]:
    if g["circular"]:
        return "aL = D + dom", "aW = aL"
    if g["position"] == "I":
        return "aL = L + dom", "aW = W + dom"
    if g["position"] == "C":
        return "aL = L + 0.5 dom", "aW = W + 0.5 dom"
    if g["face"] == "W":
        return "aL = L + 0.5 dom", "aW = W + dom"
    return "aL = L + dom", "aW = W + 0.5 dom"


def _perimeter(result: dict[str, Any]) -> str:
    g, layers = result["geometry"], result["layers"]
    rows = [
        calcpad.row("Loaded area", "Column", _column(g)),
        calcpad.row("Position", "Cl 9.3.1.3", escape(g["udesc"])),
    ]
    if not g["circular"] and g["position"] != "I":
        rows.append(calcpad.row("Faces", "pX parallel to the edge, pY away from it",
                                f"{num(g['pX'], 0)} / {num(g['pY'], 0)} mm"))
    if layers:
        rows += [
            calcpad.row("Outer and inner layer depths",
                        "do = Ds - c - db1/2; Ds - c - db1 - db2/2",
                        f"{num(layers['doOuter'], 1)} / {num(layers['doInner'], 1)} mm"),
            calcpad.row("Slab distance", "do = mean of the two layers",
                        f"{num(layers['dom'], 1)} mm", "Tedds"),
        ]
    else:
        rows.append(calcpad.row("Slab distance", "do", f"{num(g['domInput'], 1)} mm",
                                "Cl 9.3.1.4"))
    if g["spandrel"]:
        rows.append(calcpad.row("Spandrel", "bw x Db", f"{num(g['bw'], 0)} x {num(g['Db'], 0)} mm"))
        rows.append(calcpad.row("Spandrel distance", "dob = Db - (Ds - do)",
                                f"{num(g['doSpandrel'], 1)} mm"))
    if g["domRequired"]:
        solution = g["solution"]
        state = ("converged" if solution["exact"] else "no exact root; taken at the jump")
        rows += [
            calcpad.row("Mean depth around the perimeter", "dom = sum(do l) / u, solved for dom",
                        f"{num(g['domc'], 2)} mm", "Cl 9.3.1.4"),
            calcpad.row("Solution", "Bisection between do and dob",
                        f"{solution['iterations']} steps, {escape(state)}"),
        ]
    else:
        basis = "dom = do (spandrel ignored)" if g["spandrel"] and g["position"] != "I" else "dom = do"
        rows.append(calcpad.row("Mean depth", basis, f"{num(g['domc'], 1)} mm", "Cl 9.3.1.4"))
    aL_text, aW_text = _a_expressions(g)
    rows += [
        calcpad.row("Perimeter length", _u_expression(g), f"{num(g['uval'], 1)} mm", "Cl 9.3.1.3"),
        calcpad.row("Ineffective portion", "Critical openings", f"{num(g['ineffU'], 0)} mm",
                    "Fig 9.3(A)"),
        calcpad.row("Critical shear perimeter", "u = u.calc - u.ineff >= 0",
                    f"{num(g['u'], 1)} mm", "Cl 9.3.1.3"),
        calcpad.row("Dimension along L", aL_text, f"{num(g['aL'], 1)} mm"),
        calcpad.row("Dimension along W", aW_text, f"{num(g['aW'], 1)} mm"),
        calcpad.row("Dimension parallel to Mv*", f"a = a{g['pmDir']}", f"{num(g['a'], 1)} mm",
                    "Fig 9.3(B)"),
        calcpad.row("Loaded area ratio",
                    "betah = 1.0 for a circle" if g["circular"] else "betah = L / W",
                    num(g["betaH"], 3), "Cl 9.3.1.4"),
    ]
    if "prestressDepth" in result["util"]:
        rows.append(calcpad.row("Prestressed slab depth", "do >= 0.8 Ds",
                                calcpad.badge(result["util"]["prestressDepth"]), "Cl 1.7"))
    return calcpad.table("Critical Shear Perimeter - Cl 9.3.1", rows)


def _strength_no_moment(result: dict[str, Any]) -> str:
    s, m = result["strength"], result["moment"]
    rows = [
        calcpad.row("Capacity reduction factor", "phi", num(s["phi"], 2), "Table 2.2.2"),
        calcpad.row("Upper limit", "fcv.max = 0.34 sqrt(f'c)", f"{num(s['fcvMax'], 3)} MPa"),
        calcpad.row("Concrete shear stress", "fcv1 = 0.17 (1 + 2/betah) sqrt(f'c)",
                    f"{num(s['fcv1'], 3)} MPa"),
        calcpad.row("Design shear stress", "fcv = min(fcv1, fcv.max)", f"{num(s['fcv'], 3)} MPa",
                    "Cl 9.3.3(a)"),
        calcpad.row("No shear head", "phiVuo = phi u dom (fcv + 0.3 sigma.cp)",
                    f"{force(s['phiVuoPlain'], 2)} kN", "Eq 9.3.3(1)"),
        calcpad.row("Shear head, upper limit", "phiVuo.max = phi 0.2 u dom f'c",
                    f"{force(s['phiVuoMax'], 2)} kN", "Eq 9.3.3(2)"),
        calcpad.row("Shear head", "phiVuo1 = phi u dom (0.5 sqrt(f'c) + 0.3 sigma.cp)",
                    f"{force(s['phiVuo1'], 2)} kN", "Eq 9.3.3(2)"),
        calcpad.row("Shear head strength", "phiVuo = min(phiVuo1, phiVuo.max)",
                    f"{force(s['phiVuoHead'], 2)} kN", "Cl 9.3.3(b)"),
        calcpad.row("Strength used", "shear head" if s["shearHead"] else "no shear head",
                    f"{force(s['phiVuo'], 2)} kN"),
    ]
    label = "Check where Mv* = 0" if m["zero"] else "V* / phiVuo (for information, Mv* > 0)"
    rows.append(calcpad.row(label, "V* / phiVuo",
                            calcpad.badge(result["governing"]["ratioNoMoment"]), "Cl 9.3.3"))
    return calcpad.table("Ultimate Shear Strength Where Mv* = 0 - Cl 9.3.3", rows)


def _strength_moment(result: dict[str, Any]) -> str:
    m, f, g = result["moment"], result["fitments"], result["geometry"]
    rows = [calcpad.row("Moment transferred", "Mv*", f"{moment(m['Mv'], 2)} kNm")]
    if m["simplified"] and g["position"] == "I":
        rows.append(calcpad.row("Design moment", "Mv* = max(Mv*, M.min*)",
                                f"{moment(m['Mdesign'], 2)} kNm", "Cl 6.10.4.5"))
    na = "not applicable"
    rows += [
        calcpad.row("(a) No closed fitments", "phiVu = phiVuo / [1 + u Mv* / (8 V* a dom)]",
                    f"{force(result['transfer']['phiVuA'], 2)} kN", "Eq 9.3.4(1)"),
        calcpad.row("(b) Minimum fitments, torsion strip",
                    "phiVu.min = 1.2 phiVuo / [1 + u Mv* / (2 V* a^2)]",
                    f"{force(f['phiVuB'], 2)} kN" if f["valid"] else escape(f["Asw0desc"] or na),
                    "Eq 9.3.4(2)"),
        calcpad.row("(c) Minimum fitments, spandrel",
                    "phiVu.min = 1.2 phiVuo (Db / Ds) / [1 + u Mv* / (2 V* a bw)]",
                    f"{force(f['phiVuC'], 2)} kN" if g["spandrel"] and f["valid"] else
                    ("no spandrel" if not g["spandrel"] else escape(f["Asw0desc"])),
                    "Eq 9.3.4(3)"),
        calcpad.row("Torsion strip or spandrel", "x / y, shorter / longer",
                    f"{num(f['x'], 0)} / {num(f['y'], 0)} mm", "Cl 9.3.4"),
        calcpad.row("(d) Upper limit", "phiVu.max = 3 phiVu.min sqrt(x/y)",
                    f"{force(f['phiVuMax'], 2)} kN", "Eq 9.3.4(5)"),
        calcpad.row("(d) Fitments provided",
                    "phiVu = phiVu.min sqrt((Asw/s) / (0.2 y1/fsy.f)) <= phiVu.max",
                    f"{force(f['phiVuD'], 2)} kN", "Eq 9.3.4(4)"),
        calcpad.row("Spacing for V*", "s = Asw / (0.2 y1/fsy.f (V*/phiVu.min)^2)",
                    f"{num(f['sForVstar'], 0)} mm" if f["phiVuMin"] > 0 else na),
    ]
    label = "Check where Mv* > 0" if not m["zero"] else "V* / phiVu (a) (for information)"
    rows.append(calcpad.row(label, "V* / phiVu, governing case" if not m["zero"] else "V* / phiVu",
                            calcpad.badge(result["util"]["punching"] if not m["zero"] else
                                          result["governing"]["ratioNoFitments"]),
                            "Cl 9.3.4"))
    return calcpad.table("Ultimate Shear Strength Where Mv* > 0 - Cl 9.3.4", rows)


def _fitments(result: dict[str, Any]) -> str:
    f, g, util = result["fitments"], result["geometry"], result["util"]
    if not f["provided"]:
        return calcpad.table("Closed Fitments - Cl 9.3.5 and Cl 9.3.6", [
            calcpad.row("Closed fitments", "Torsion strip or spandrel", "None"),
            calcpad.row("Strength basis", "No fitments", "Eq 9.3.4(1) applies", "Cl 9.3.4(a)"),
        ])
    y1_text = ("y1 = max(bw, Db) - 2 c - db.f" if g["spandrel"]
               else "y1 = min(a, max(wcl - db.f, Ds - 2 c - db.f))")
    rows = [
        calcpad.row("Closed fitments", "Size and spacing", escape(f["label"])),
        calcpad.row("Location", "Spandrel" if g["spandrel"] else "Torsion strip of width a",
                    f"{num(g['bw'], 0)} x {num(g['Db'], 0)} mm" if g["spandrel"]
                    else f"a = {num(g['a'], 0)} mm"),
        calcpad.row("Larger fitment dimension", y1_text, f"{num(f['y1'], 1)} mm", "Cl 9.3.4"),
        calcpad.row("Fitment area", "Asw = pi db.f^2 / 4", f"{num(f['AswActual'], 1)} mm2"),
        calcpad.row("Minimum area", "Asw.min = 0.2 y1 / fsy.f s", f"{num(f['AswMin'], 1)} mm2",
                    "Eq 9.3.5"),
        calcpad.row("Spacing at minimum area", "s = Asw / (0.2 y1 / fsy.f)",
                    f"{num(f['sMaxArea'], 0)} mm", "Eq 9.3.5"),
        calcpad.row("Maximum spacing", "s.max = min(Db, 300)" if g["spandrel"]
                    else "s.max = min(Ds, 300)", f"{num(f['maxcts'], 0)} mm", "Cl 9.3.6"),
        calcpad.row("Minimum area check", "Asw.min / Asw", calcpad.badge(util["fitmentArea"]),
                    "Cl 9.3.5"),
        calcpad.row("Spacing check", "s / s.max", calcpad.badge(util["fitmentSpacing"]),
                    "Cl 9.3.6"),
    ]
    if "fitmentWidth" in util:
        rows.append(calcpad.row("Fitment width check", "wcl / a", calcpad.badge(util["fitmentWidth"]),
                                "Workbook Design!H13"))
    return calcpad.table("Closed Fitments - Cl 9.3.5 and Cl 9.3.6", rows)


def _governing(result: dict[str, Any]) -> tuple[str, str]:
    gov, m = result["governing"], result["moment"]
    V = result["inputs"]["Vstar"]
    rows = [
        calcpad.row("Design moment", "Mv*", f"{moment(m['Mdesign'], 2)} kNm"),
        calcpad.row("Governing case", escape(gov["label"]),
                    f"{escape(gov['case'])}", escape(gov["equation"])),
        calcpad.row("Design strength", "phiVu", f"{force(gov['capacity'], 2)} kN"),
        calcpad.row("Design shear", "V*", f"{force(V, 2)} kN"),
        calcpad.row("Punching shear check", "V* / phiVu", calcpad.badge(result["util"]["punching"]),
                    "Cl 9.3"),
    ]
    grid = calcpad.grid(
        "Punching Strength by Case", ["Case", "Equation", "phiV (kN)", "V* / phiV", "Governs"],
        [[escape(case["label"]), case["equation"], force(case["capacity"], 2),
          "-" if case["ratio"] is None else num(case["ratio"], 3),
          "Yes" if case["governs"] else ""] for case in result["cases"]],
        "Zero strength means the case is not available for the reinforcement provided. The "
        "governing case follows Cl 9.3.3 when Mv* = 0 and otherwise the fitments provided.")
    return calcpad.table("Punching Shear Check - Cl 9.3", rows), grid


def _moment_transfer(result: dict[str, Any]) -> str:
    m, g = result["moment"], result["geometry"]
    if m["simplified"] and g["position"] == "I":
        status = "applied" if m["applied"] else "Mv* exceeds the minimum"
    elif m["simplified"]:
        status = "not applied, interior supports only"
    else:
        status = "reported only, simplified method not selected"
    rows = [
        calcpad.row("Load on the larger span", "V1* = 1.2 G + 0.75 Q", f"{num(m['v1'], 3)} kPa"),
        calcpad.row("Load on the smaller span", "V2* = 1.2 G", f"{num(m['v2'], 3)} kPa"),
        calcpad.row("Spans and strip", "Lo / Lo' / Lt",
                    f"{num(m['Lo'], 0)} / {num(m['Lod'], 0)} / {num(m['Lt'], 0)} mm",
                    "Cl 6.10.4.2"),
        calcpad.row("Minimum transferred moment", "M.min* = 0.06 (V1* Lt Lo^2 - V2* Lt Lo'^2)",
                    f"{moment(m['MvMin'], 2)} kNm", "Cl 6.10.4.5"),
        calcpad.row("Moment entered", "Mv*", f"{moment(m['Mv'], 2)} kNm"),
        calcpad.row("Design moment", escape(status), f"{moment(m['Mdesign'], 2)} kNm"),
    ]
    return calcpad.table("Moment Transfer for Shear in Flat Slabs - Cl 6.10.4.5", rows)


def _integrity(result: dict[str, Any]) -> str:
    i = result["integrity"]
    if not i["required"]:
        return calcpad.table("Integrity Reinforcement - Cl 9.2", [
            calcpad.row("Requirement", "Beams with shear reinforcement and 2 continuous bottom "
                        "bars in all spans", "Not required", "Cl 9.2.2 (workbook)")])
    rows = [
        calcpad.row("Column reaction", "N*", f"{force(i['N'])} kN"),
        calcpad.row("Bar yield strength", f"fsy, Class {i['barClass']}",
                    f"{num(i['fsy'], 0)} MPa"),
        calcpad.row("Capacity reduction factor", "phi", num(i["phi"], 2), "Table 2.2.2 (workbook)"),
        calcpad.row("Bottom connecting area", "As.min = 2 N* / (phi fsy)",
                    f"{num(i['AsMin'], 0)} mm2", "Eq 9.2.2 (workbook)"),
        calcpad.row("Bar area", "Ab = pi db^2 / 4", f"{num(i['Ab'], 1)} mm2"),
        calcpad.row("Bars required", "As.min / Ab", escape(i["desc"])),
        calcpad.row("Bars provided", "n Ab",
                    f"{i['provided']} bars, {num(i['AsProvided'], 0)} mm2"),
        calcpad.row("Integrity check", "As.min / As", calcpad.badge(result["util"]["integrity"]),
                    "Cl 9.2.2 (workbook)"),
    ]
    return calcpad.table("Integrity Reinforcement - Cl 9.2", rows)


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
