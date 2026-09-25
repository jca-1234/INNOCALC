"""Calculation-pad presentation for the strut-and-tie module, in the column-module layout.

Only formatting happens here; every engineering value comes from
:func:`ic_concrete_strut_tie.engine.compute`.
"""

from __future__ import annotations

import math
from html import escape
from typing import Any

import calcpad

from .engine import AREA_MODES, BEARING_MODES, DZ_MODES, FC_DEVELOPMENT_MAX, TIE_HEIGHT_MODES
from .version import VERSION

DATA_ID = "concrete-strut-tie-inputs"
DEFAULT_SUBJECT = "Strut-and-tie design"
num = calcpad.number
kN = calcpad.force

CHECK_ROWS = [
    ("strut", "Compression strut", "C* / phiC", "Cl 7.2.3"),
    ("supportLength", "Support length for the strut", "Lrg / Lr", "Fig 7.2.4(A)"),
    ("strutAngle", "Strut angle not less than 30 deg", "30 / theta", "Cl 7.1"),
    ("angleCompatibility", "Strut angle compatible with the nodes", "|theta - theta_az| <= 0.001",
     "Fig 7.2.2"),
    ("bottleLength", "Strut depth less than strut length", "dc / Ls", "Eq 7.2.4(4)"),
    ("burstingStrength", "Bursting reinforcement, strength", "Tb* / phiTb", "Cl 7.2.4(b)"),
    ("burstingService", "Bursting reinforcement, serviceability", "Tb.s / Tbs", "Cl 7.2.4(a)"),
    ("burstingCracking", "Bursting reinforcement, cracking", "Tb.cr / Tbsc", "Eq 7.2.4(1)"),
    ("burstingThreshold", "Bursting reinforcement not required", "Tbb* / (0.5 Tb.cr)",
     "Cl 7.2.4"),
    ("oneWayAngle", "One-way reinforcement angle", "40 / gamma", "Workbook rule"),
    ("verticalLoadSteel", "Vertical steel for Vr*", "max(Asvr, Asvr.s) / Asi1", "Cl 7.2.4"),
    ("tie", "Tension tie", "T* / phiT", "Cl 7.3.2"),
    ("node", "Nodal stress", "sigma_o / sigma3", "Cl 7.4.2"),
    ("bearing", "Bearing", "B* / phiB", "Cl 12.6"),
    ("nodeStrutFace", "Node, strut face", "sigma.s / sigma3", "Cl 7.4.2"),
    ("nodeBearingFace", "Node, bearing face", "sigma.b / sigma3", "Cl 7.4.2"),
    ("nodeTieFace", "Node, tie face", "sigma.t / sigma3", "Cl 7.4.2"),
]


def render(inputs: dict[str, Any], result: dict[str, Any], *, standalone: bool = False,
           appendix: list[str] | None = None, anchor_prefix: str = "",
           contents_href: str = "") -> str:
    blocks = [
        _summary(result),
        *_inputs(inputs),
        _model_figure(result),
        _geometry(result),
        _strut(result),
        *_anchorage(result),
        _reinforcement(result),
        _strength(result),
        _service(result),
        _cracking(result),
        _spacing(result),
        _tie(result),
        _node(result),
        _bearing(result),
        _faces(result),
        _basis(result),
    ]
    title = (f"{inputs.get('memberType', 'Strut and Tie')}-{inputs.get('memberNumber', '')} "
             f"- Concrete Strut-and-Tie Design {VERSION}")
    return calcpad.render(inputs, blocks, standalone=standalone, appendix=appendix,
                          anchor_prefix=anchor_prefix, contents_href=contents_href,
                          default_subject=DEFAULT_SUBJECT, data_id=DATA_ID, title=title)


def _badge_rows(result: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    rows = []
    for key, label, expression, reference in CHECK_ROWS:
        if key in keys and key in result["util"]:
            rows.append(calcpad.row(label, expression, calcpad.badge(result["util"][key]),
                                    reference))
    return rows


def _summary(result: dict[str, Any]) -> str:
    values, geometry, strut = result["inputs"], result["geometry"], result["strut"]
    cracking, tie = result["cracking"], result["tie"]
    rows = [
        calcpad.row("Strut-and-tie panel", "Lstrut x D x bc, f'c",
                    f"{num(values['Lstrut'], 0)} x {num(values['D'], 0)} x "
                    f"{num(values['bc'], 0)} mm, f'c = {num(values['fc'], 0)} MPa"),
        calcpad.row("Strut compression", "C* / Cserv",
                    f"{kN(strut['Cstar'], 0)} / {kN(strut['Cserv'], 0)} kN", "Cl 7.2"),
        calcpad.row("Strut angle", "theta, with theta_az = atan(z / a)",
                    f"{num(geometry['theta'], 2)} deg", "Fig 7.2.2"),
        calcpad.row("Strut depth and capacity", "dc / phiC = phi betas 0.9 f'c bc dc",
                    f"{num(strut['dc'], 0)} mm / {kN(strut['Cmax'], 0)} kN", "Cl 7.2.3"),
        calcpad.row("Support length required", "Lrg = dc.max sin(theta) + dz",
                    f"{num(geometry['Lrg'], 0)} mm, Lr = {num(geometry['Lr'], 0)} mm",
                    "Fig 7.2.4(A)"),
        calcpad.row("Bursting forces", "Tb* / Tb.s / Tb.cr",
                    f"{kN(result['strength']['Tb'], 0)} / {kN(result['service']['Tb'], 0)} / "
                    f"{kN(cracking['Tbcr'], 0)} kN", "Cl 7.2.4"),
        calcpad.row("Tension tie", "T* / phiT",
                    f"{kN(tie['Tstar'], 0)} / {kN(tie['phiT'], 0)} kN", "Cl 7.3.2"),
    ]
    rows += _badge_rows(result, tuple(key for key, *_ in CHECK_ROWS))
    rows.append(calcpad.row("Governing", "Maximum utilisation", calcpad.badge(result["worstUtil"])))
    if result["unattainable"]:
        rows.append(calcpad.row("Unattainable", "See design basis",
                                calcpad.badge(math.inf)))
    return calcpad.table("Design Summary", rows)


def _inputs(inputs: dict[str, Any]) -> list[str]:
    def manual(mode: str, key: str, label: str, unit: str = "") -> list[tuple[str, str, str]]:
        return [(label, key, unit)] if str(inputs.get(mode, "")).upper() == "M" else []

    groups = [
        ("Actions", [
            ("Strut compression C*", "Cstar", "kN"),
            ("Strut compression, serviceability", "Cserv", "kN"),
            ("Tie tension T*", "Tstar", "kN"), ("Additional vertical load Vr*", "Vrstar", "kN"),
            ("Additional vertical load, serviceability", "Vrserv", "kN")]),
        ("Geometry", [
            ("Concrete strength f'c", "fc", "MPa"), ("Horizontal length of strut", "Lstrut", "mm"),
            ("Depth of panel", "D", "mm"), ("Width of strut", "bc", "mm"),
            ("Horizontal reaction length", "Lr", "mm"), ("Strut angle mode", "thetaMode", ""),
            *manual("thetaMode", "theta", "Manual strut angle", "deg"),
            ("Horizontal distance a", "aMode", ""), *manual("aMode", "aManual", "Manual a", "mm"),
            ("Vertical distance z", "zMode", ""), *manual("zMode", "zManual", "Manual z", "mm"),
            ("Depth of strut dc", "dcMode", ""), *manual("dcMode", "dcManual", "Manual dc", "mm"),
            ("Bursting length lb", "lbMode", ""), *manual("lbMode", "lbManual", "Manual lb", "mm")]),
        ("Strut Efficiency and Divergence", [
            ("Strut efficiency factor", "betasMode", ""),
            *manual("betasMode", "betasManual", "Manual betas"),
            ("Strength tan alpha", "tanAlphaMode", ""),
            *manual("tanAlphaMode", "tanAlphaManual", "Manual strength tan alpha"),
            ("Serviceability tan alpha", "tanAlphaServMode", ""),
            *manual("tanAlphaServMode", "tanAlphaServManual", "Manual serviceability tan alpha")]),
        ("Bursting Reinforcement", [
            ("Crack control", "crack", ""), *manual_crack(inputs),
            ("Vertical bar size", "bar1", "mm"), ("Vertical bar centres", "cts1", "mm"),
            ("Vertical bar layers", "layer1", ""), ("Vertical bar yield", "fsy1", "MPa"),
            ("Horizontal bar size", "bar2", "mm"), ("Horizontal bar centres", "cts2", "mm"),
            ("Horizontal bar layers", "layer2", ""), ("Horizontal bar yield", "fsy2", "MPa"),
            ("Cracking capacity at phi fsy", "useRef2", "")]),
        ("Tension Tie and Anchorage", [
            ("Tie bar size", "tieBar", "mm"), ("Tie bars per layer", "tieBars", ""),
            ("Tie layers", "tieLayers", ""), ("Tie yield strength", "fsy", "MPa"),
            ("Epoxy coated", "ek", ""), ("Lightweight concrete", "lk", ""),
            ("Slip formed", "sk", ""), ("Cogged bars", "cogged", ""),
            ("Concrete cast below bars", "below", "mm"), ("Bars in bundle", "bundle", ""),
            ("Minimum cover", "cover", "mm"), ("Clear distance between bars", "covera", "mm"),
            ("Development zone", "dzMode", ""), *manual("dzMode", "dzManual", "Manual dz", "mm")]),
        ("Nodes and Bearing", [
            ("Node type", "ntype", ""), ("Nodal stress", "stresso", "MPa"),
            ("Bearing force", "bearingMode", ""),
            *manual("bearingMode", "Bstar", "Manual bearing B*", "kN"),
            ("Bearing areas", "areaMode", ""),
            *manual("areaMode", "A1", "Bearing area A1", "mm2"),
            *manual("areaMode", "A2", "Supporting area A2", "mm2")]),
    ]
    if (inputs.get("checks") or {}).get("nodeFaces"):
        groups.append(("Nodal Face Stresses", [
            ("Tie face height mode", "tieHeightMode", ""),
            *manual("tieHeightMode", "tieHeight", "Manual tie face height u", "mm")]))
    return [calcpad.matrix(f"Design Inputs - {title}",
                           [(label, key, inputs.get(key, ""), unit) for label, key, unit in fields
                            if str(inputs.get(key, "")).strip() != ""])
            for title, fields in groups]


def manual_crack(inputs: dict[str, Any]) -> list[tuple[str, str, str]]:
    if str(inputs.get("crack", "")).upper() == "C":
        return [("Custom steel stress limit", "fsic", "MPa")]
    return []


# ---------------------------------------------------------------------------
#  Strut-and-tie model drawing
# ---------------------------------------------------------------------------
def model_drawing(result: dict[str, Any], width_target: float = 112.0,
                  height_target: float = 100.0) -> str:
    """Elevation of the panel with the strut band, bottle outline, tie, nodes and support."""
    g, strut = result["geometry"], result["strut"]
    L, D, Lr = g["Lstrut"], g["D"], g["Lr"]
    a, z, dc, Ls = g["a"], g["z"], strut["dc"], g["Ls"]
    s = min(width_target / L, height_target / D)
    left, top, right_pad, bottom_pad = 16.0, 13.0, 16.0, 20.0
    width, height = L * s + left + right_pad, D * s + top + bottom_pad

    def X(x: float) -> float:
        return left + x * s

    def Y(y: float) -> float:
        return top + (D - y) * s

    def text(x: float, y: float, value: str, anchor: str = "middle", colour: str = "#111",
             rotate: float = 0.0) -> str:
        spin = f' transform="rotate({rotate:.2f} {x:.2f} {y:.2f})"' if rotate else ""
        return (f'<text x="{x:.2f}" y="{y:.2f}" font-size="2.7" text-anchor="{anchor}" '
                f'fill="{colour}"{spin}>{escape(value)}</text>')

    n1 = ((L - a) / 2.0, (D - z) / 2.0)
    n2 = (n1[0] + a, n1[1] + z)
    ux, uy = a / Ls, z / Ls
    nx, ny = -uy, ux

    def along(t: float, offset: float) -> tuple[float, float]:
        return n1[0] + ux * t + nx * offset, n1[1] + uy * t + ny * offset

    def poly(points: list[tuple[float, float]]) -> str:
        return " ".join(f"{X(px):.2f},{Y(py):.2f}" for px, py in points)

    band = [along(0, dc / 2), along(Ls, dc / 2), along(Ls, -dc / 2), along(0, -dc / 2)]
    samples = [Ls * index / 24 for index in range(25)]
    spread = [dc / 2 + 0.5 * min(t, Ls - t, Ls / 4) for t in samples]
    bottle = ([along(t, h) for t, h in zip(samples, spread)]
              + [along(t, -h) for t, h in reversed(list(zip(samples, spread)))])
    clip = (f'<clipPath id="st-panel"><rect x="{X(0):.2f}" y="{Y(D):.2f}" '
            f'width="{L * s:.2f}" height="{D * s:.2f}"/></clipPath>')
    parts = [
        f"<defs>{clip}"
        '<marker id="st-arrow" viewBox="0 0 6 6" refX="5" refY="3" markerWidth="4" '
        'markerHeight="4" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="#1c4fa1"/></marker>'
        "</defs>",
        f'<rect x="{X(0):.2f}" y="{Y(D):.2f}" width="{L * s:.2f}" height="{D * s:.2f}" '
        'fill="#f1f2f0" stroke="#111" stroke-width="0.5"/>',
        f'<g clip-path="url(#st-panel)"><polygon points="{poly(bottle)}" fill="none" '
        'stroke="#1c4fa1" stroke-width="0.3" stroke-dasharray="1.2,0.9"/>'
        f'<polygon points="{poly(band)}" fill="#c9d6ea" stroke="#1c4fa1" stroke-width="0.35"/>'
        "</g>",
        f'<line x1="{X(0):.2f}" y1="{Y(n1[1]):.2f}" x2="{X(L):.2f}" y2="{Y(n1[1]):.2f}" '
        'stroke="#b1257a" stroke-width="1.0"/>',
        f'<line x1="{X(n1[0]):.2f}" y1="{Y(n1[1]):.2f}" x2="{X(n2[0]):.2f}" y2="{Y(n2[1]):.2f}" '
        'stroke="#1c4fa1" stroke-width="0.3" stroke-dasharray="3,1,0.6,1"/>',
    ]
    for node in (n1, n2):
        parts.append(f'<circle cx="{X(node[0]):.2f}" cy="{Y(node[1]):.2f}" r="1.1" '
                     'fill="#fff" stroke="#111" stroke-width="0.4"/>')
    support_w = min(Lr, L) * s
    parts.append(f'<rect x="{X(0):.2f}" y="{Y(0):.2f}" width="{support_w:.2f}" height="2.2" '
                 'fill="#777"/>')
    for index in range(int(support_w / 2.0) + 1):
        x0 = X(0) + index * 2.0
        if x0 > X(0) + support_w:
            break
        parts.append(f'<line x1="{x0:.2f}" y1="{Y(0) + 2.2:.2f}" x2="{x0 - 1.4:.2f}" '
                     f'y2="{Y(0) + 3.8:.2f}" stroke="#555" stroke-width="0.2"/>')
    tip = (X(n2[0]), Y(n2[1]))
    tail = (tip[0] + ux * 11.0, tip[1] - uy * 11.0)
    parts.append(f'<line x1="{tail[0]:.2f}" y1="{tail[1]:.2f}" x2="{tip[0] + ux * 1.6:.2f}" '
                 f'y2="{tip[1] - uy * 1.6:.2f}" stroke="#1c4fa1" stroke-width="0.6" '
                 'marker-end="url(#st-arrow)"/>')
    angle = math.degrees(math.atan2(z, a))
    mid = along(Ls * 0.5, dc / 2)
    mx, my = X(mid[0]) + nx * 2.2, Y(mid[1]) - ny * 2.2
    radius = 9.0
    arc_end = (X(n1[0]) + radius * math.cos(math.radians(angle)),
               Y(n1[1]) - radius * math.sin(math.radians(angle)))
    parts += [
        f'<path d="M{X(n1[0]) + radius:.2f},{Y(n1[1]):.2f} A{radius},{radius} 0 0 0 '
        f'{arc_end[0]:.2f},{arc_end[1]:.2f}" fill="none" stroke="#111" stroke-width="0.3"/>',
        text(X(n1[0]) + radius + 1.5, Y(n1[1]) - 2.2, f"\u03b8 = {g['theta']:.1f}\u00b0", "start"),
        text(mx, my, f"C* = {strut['Cstar'] / 1e3:,.0f} kN", colour="#1c4fa1", rotate=-angle),
        text(X(L) - 1.5, Y(n1[1]) - 1.6, f"T* = {result['tie']['Tstar'] / 1e3:,.0f} kN", "end",
             colour="#b1257a"),
        text(X(0) + support_w / 2, Y(0) + 7.0, f"Lr = {Lr:,.0f}"),
        text(X(L / 2), Y(0) + 13.5, f"Lstrut = {L:,.0f} mm"),
        f'<line x1="{X(0):.2f}" y1="{Y(0) + 10.0:.2f}" x2="{X(L):.2f}" y2="{Y(0) + 10.0:.2f}" '
        'stroke="#555" stroke-width="0.25"/>',
        text(X(0) - 5.0, Y(D / 2), f"D = {D:,.0f} mm", rotate=-90.0),
        text(X(L) + 6.0, Y(n1[1] + z / 2), f"z = {z:,.0f}", rotate=-90.0),
        text(X(n1[0] + a / 2), Y(D) - 4.5, f"a = {a:,.0f}"),
        f'<line x1="{X(n1[0]):.2f}" y1="{Y(D) - 2.5:.2f}" x2="{X(n2[0]):.2f}" '
        f'y2="{Y(D) - 2.5:.2f}" stroke="#555" stroke-width="0.25"/>',
        f'<line x1="{X(L) + 3.0:.2f}" y1="{Y(n1[1]):.2f}" x2="{X(L) + 3.0:.2f}" '
        f'y2="{Y(n2[1]):.2f}" stroke="#555" stroke-width="0.25"/>',
    ]
    return (f'<svg viewBox="0 0 {width:.2f} {height:.2f}" width="{width:.2f}mm" '
            f'height="{height:.2f}mm" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="Strut-and-tie model">{"".join(parts)}</svg>')


def _model_figure(result: dict[str, Any]) -> str:
    g, strut = result["geometry"], result["strut"]
    caption = (f"Strut of depth dc = {strut['dc']:,.0f} mm between the support node "
               f"(bottom left, on the tie) and the loaded node. The dashed outline is the bottle "
               f"spreading at tan alpha = 0.5; bursting length lb = {g['lb']:,.0f} mm. The "
               f"support length is Lr = {g['Lr']:,.0f} mm, of which dz = "
               f"{result['anchorage']['dz']:,.0f} mm is the development zone.")
    svg = model_drawing(result)
    height = float(svg.split('height="', 1)[1].split("mm", 1)[0])
    return calcpad.figure("Strut-and-Tie Model", svg, caption, weight=int(height / 5.2) + 3)


# ---------------------------------------------------------------------------
#  Check tables
# ---------------------------------------------------------------------------
def _geometry(result: dict[str, Any]) -> str:
    g = result["geometry"]
    mode = g["thetaMode"]
    basis = {"S": f"Solved, theta = theta_az ({g['solver']['method']})",
             "G": "theta = atan(D / Lstrut)", "M": "Manual theta"}[mode]
    a_note = " (manual)" if g["aManual"] else ""
    z_note = " (manual)" if g["zManual"] else ""
    lb_note = " (manual)" if g["lbManual"] else ""
    rows = [
        calcpad.row("Geometric angle", "atan(D / Lstrut)", f"{num(g['thetaGeometric'], 3)} deg"),
        calcpad.row("Adopted strut angle", basis, f"{num(g['theta'], 3)} deg", "Fig 7.2.2"),
        calcpad.row("Angles to bursting bars", "gamma1 = 90 - theta, gamma2 = theta",
                    f"{num(g['gamma1'], 2)} / {num(g['gamma2'], 2)} deg", "Fig 7.2.4(B)"),
        calcpad.row("Strut projections", "w = dc sin(theta), Ω = dc cos(theta)",
                    f"{num(g['w'], 1)} / {num(g['omega'], 1)} mm"),
        calcpad.row("Node offsets", "w2 = dc / (2 sin(theta)), w1 = w2 - w / 2",
                    f"{num(g['w2'], 1)} / {num(g['w1'], 1)} mm"),
        calcpad.row("Strut horizontal distance", "a = Lstrut - 2 w1",
                    f"{num(g['a'], 1)} mm{a_note}", f"calc. {num(g['aCalc'], 1)}"),
        calcpad.row("Strut vertical distance", "z = D - Ω",
                    f"{num(g['z'], 1)} mm{z_note}", f"calc. {num(g['zCalc'], 1)}"),
        calcpad.row("Strut length", "Ls = sqrt(a^2 + z^2)", f"{num(g['Ls'], 1)} mm"),
        calcpad.row("Length of bursting zone", "lb = Ls - dc",
                    f"{num(g['lb'], 1)} mm{lb_note}", "Eq 7.2.4(4)"),
        calcpad.row("Bursting zone projections", "lb.1 = lb sin(gamma1), lb.2 = lb sin(gamma2)",
                    f"{num(g['lb1'], 1)} / {num(g['lb2'], 1)} mm"),
        calcpad.row("Angle between strut and tie", "theta_az = atan(z / a)",
                    f"{num(g['thetaAz'], 3)} deg", "Fig 7.2.2"),
    ]
    rows += _badge_rows(result, ("angleCompatibility", "strutAngle", "bottleLength"))
    return calcpad.table("Strut Geometry - Fig 7.2.4(A)", rows)


def _strut(result: dict[str, Any]) -> str:
    strut, g = result["strut"], result["geometry"]
    dc_note = "manual" if g["dcManual"] else "dc = dc.max"
    rows = [
        calcpad.row("Strut components", "Cv* = C* sin(theta), Ch* = C* cos(theta)",
                    f"{kN(strut['Cvstar'], 1)} / {kN(strut['Chstar'], 1)} kN"),
        calcpad.row("Strut efficiency factor", "betas = 1 / (1 + 0.66 cot^2 theta)",
                    num(strut["betasCalc"], 4), "Eq 7.2.2, 0.3 to 1.0"),
        calcpad.row("Adopted efficiency factor", "manual" if strut["betasManual"] else "calculated",
                    num(strut["betas"], 4)),
        calcpad.row("Capacity reduction factor", "phi.st", num(strut["phi"], 2), "Table 2.2.4"),
        calcpad.row("Design stress of strut", "phi fcu = phi betas 0.9 f'c",
                    f"{num(strut['Ca'], 3)} MPa", "Cl 7.2.3"),
        calcpad.row("Depth for full capacity", "dc.max = C* / (phi fcu bc)",
                    f"{num(strut['dcmax'], 1)} mm"),
        calcpad.row("Adopted strut depth", dc_note, f"{num(strut['dc'], 1)} mm"),
        calcpad.row("Strut capacity", "phiC = phi fcu bc dc", f"{kN(strut['Cmax'], 1)} kN",
                    "Cl 7.2.3"),
        *_badge_rows(result, ("strut",)),
        calcpad.row("Support length required", "Lrg = dc.max sin(theta) + dz",
                    f"{num(g['Lrg'], 1)} mm", "Fig 7.2.4(A)"),
        calcpad.row("Geometric strut depth at support", "dcg = (Lr - dz) / sin(theta)",
                    f"{num(g['dcg'], 1)} mm"),
        *_badge_rows(result, ("supportLength",)),
    ]
    if not g["dcManual"]:
        rows.append(calcpad.row("Note", "dc = dc.max", "φC = C* by construction",
                                "verified by Lrg &le; Lr"))
    return calcpad.table("Compression Strut - Cl 7.2", rows)


def _anchorage(result: dict[str, Any]) -> tuple[str, str]:
    data = result["anchorage"]
    h, t = data["horizontal"], data["tie"]
    factors = [("ek", "epoxy x1.5"), ("lk", "lightweight x1.3"), ("sk", "slip formed x1.3"),
               ("cogged", "cogged x0.5")]
    applied = ", ".join(label for key, label in factors if data[key]) or "none"

    def pair(key: str, digits: int = 1, unit: str = " mm") -> str:
        return f"{num(h[key], digits)} / {num(t[key], digits)}{unit}"

    rows = [
        calcpad.row("Bars, horizontal / tie", "db, fsy",
                    f"{num(h['db'], 2)} / {num(t['db'], 2)} mm, {num(h['fsy'], 0)} / "
                    f"{num(t['fsy'], 0)} MPa"),
        calcpad.row("Cover for development", "cd = min(a / 2, c)", f"{num(data['cd'], 1)} mm",
                    "Fig 13.1.2.2"),
        calcpad.row("Bar position factor", "k1 = 1.3 if more than 300 mm cast below",
                    num(data["k1"], 2)),
        calcpad.row("Bar size factor", "k2 = (132 - db) / 100", pair("k2", 4, "")),
        calcpad.row("Cover factor", "k3 = 1 - 0.15 (cd - db) / db, 0.7 to 1.0", pair("k3", 4, "")),
        calcpad.row("Basic development length", "Lsy.tb = 0.5 k1 k3 fsy db / (k2 sqrt(f'c))",
                    pair("basic"), f"Eq 13.1.2.2, f'c &le; {num(FC_DEVELOPMENT_MAX, 0)}"),
        calcpad.row("Minimum length", "0.058 fsy k1 db", pair("minimum"), "Eq 13.1.2.2"),
        calcpad.row("Development length", f"{num(data['percent'], 0)}% x max x modifiers",
                    pair("full"), "Cl 13.1.7"),
        calcpad.row("Modifiers applied", "Cl 13.1.2.2, Cl 13.1.2.6", escape(applied)),
        calcpad.row("Development length adopted", "x 0.5 for a cog", pair("developed")),
        calcpad.row("50% development length", "0.5 Lsy.t", pair("half"), "Cl 13.1.2.6"),
    ]
    zone = [
        calcpad.row("Calculated zone", "max(50% Lsy.h, 50% Lsy.t)", f"{num(data['dzCalc'], 1)} mm",
                    "Cl 7.3.3"),
        calcpad.row("Adopted development zone", escape(DZ_MODES[data["dzMode"]]),
                    f"{num(data['dz'], 1)} mm", "Cl 7.3.3"),
    ]
    return (calcpad.table("Development Lengths - Cl 13.1.2.2", rows),
            calcpad.table("Development Zone - Cl 7.3.3", zone))


def _reinforcement(result: dict[str, Any]) -> str:
    r = result["reinforcement"]

    def pair(key: str, digits: int = 1, unit: str = "") -> str:
        return f"{num(r[key + '1'], digits)} / {num(r[key + '2'], digits)}{unit}"

    rows = [
        calcpad.row("Crack control", escape(r["crackLabel"]), f"fsi = {num(r['fsi'], 0)} MPa",
                    "Cl 12.7"),
        calcpad.row("Vertical bars (1)", "db at cts x layers",
                    f"{r['class1']}{num(r['bar1'], 2)} at {num(r['cts1'], 0)} x "
                    f"{num(r['layer1'], 0)}"),
        calcpad.row("Horizontal bars (2)", "db at cts x layers",
                    f"{r['class2']}{num(r['bar2'], 2)} at {num(r['cts2'], 0)} x "
                    f"{num(r['layer2'], 0)}"),
        calcpad.row("Bar areas, 1 / 2", "As = pi db^2 / 4 x layers", pair("As", 1, " mm2")),
        calcpad.row("Area per metre, 1 / 2", "Am = As 1000 / cts", pair("Am", 1, " mm2/m")),
        calcpad.row("Bursting length, 1 / 2", "lb.1, lb.2", pair("lb", 1, " mm")),
        calcpad.row("Bars across the strut, 1 / 2", "lb.i / cts x layers", pair("bars", 2)),
        calcpad.row("Crossing area, 1 / 2", "Asi = Am lb.i / 1000", pair("Asi", 1, " mm2"),
                    "Cl 7.2.4"),
        calcpad.row("Angle to strut, 1 / 2", "gamma1 = 90 - theta, gamma2 = theta",
                    pair("gamma", 2, " deg"), "Fig 7.2.4(B)"),
        calcpad.row("Crack control met by spacing", "200 strong, 300 moderate, 350 minor",
                    f"{r['spacingClass1']} / {r['spacingClass2']}", "Cl 12.7"),
        calcpad.row("Direction of reinforcement", "Asi1 > 0 and Asi2 > 0",
                    "one direction only" if r["oneWay"] else "orthogonal"),
    ]
    return calcpad.table("Bursting Reinforcement - Cl 7.2.4", rows)


def _not_required(result: dict[str, Any]) -> list[str]:
    if result["cracking"]["required"]:
        return []
    return [calcpad.row("Reinforcement required", "Tbb* > 0.5 Tb.cr", "No"),
            *_badge_rows(result, ("burstingThreshold",))]


def _strength(result: dict[str, Any]) -> str:
    s = result["strength"]
    rows = [
        calcpad.row("Divergence", "tan alpha* >= 0.2", num(s["tanAlpha"], 3), "Cl 7.2.4(b)"),
        calcpad.row("Bursting force", "Tb* = C* tan alpha*", f"{kN(s['Tb'], 1)} kN"),
        calcpad.row("Vertical share", "Tb.1* = Tb* sin(gamma1) + Vr*", f"{kN(s['Tb1'], 1)} kN"),
        calcpad.row("Horizontal share", "Tb.2* = Tb* sin(gamma2)", f"{kN(s['Tb2'], 1)} kN"),
        calcpad.row("Steel for Vr*", "Asvr = Vr* / (phi fsy1)", f"{num(s['Asvr'], 1)} mm2"),
        calcpad.row("Vertical capacity", "phiTb1 = phi (Asi1 - Asvr) fsy1 sin(gamma1)",
                    f"{kN(s['phiTb1'], 1)} kN", "Table 2.2.4"),
        calcpad.row("Horizontal capacity", "phiTb2 = phi Asi2 fsy2 sin(gamma2)",
                    f"{kN(s['phiTb2'], 1)} kN"),
        calcpad.row("Bursting capacity", "phiTb = phiTb1 + phiTb2", f"{kN(s['phiTb'], 1)} kN"),
        *_badge_rows(result, ("burstingStrength",)),
        *_not_required(result),
    ]
    return calcpad.table("Bursting Strength - Cl 7.2.4(b)", rows)


def _service(result: dict[str, Any]) -> str:
    s = result["service"]
    rows = [
        calcpad.row("Divergence", "tan alpha.s >= 0.5", num(s["tanAlpha"], 3), "Cl 7.2.4(a)"),
        calcpad.row("Steel stress limit", "fsi", f"{num(s['fsi'], 0)} MPa", "Cl 12.7"),
        calcpad.row("Bursting force", "Tb.s = Cserv tan alpha.s", f"{kN(s['Tb'], 1)} kN"),
        calcpad.row("Vertical share", "Tb.s.1 = Tb.s sin(gamma1) + Vr.serv",
                    f"{kN(s['Tb1'], 1)} kN"),
        calcpad.row("Horizontal share", "Tb.s.2 = Tb.s sin(gamma2)", f"{kN(s['Tb2'], 1)} kN"),
        calcpad.row("Steel for Vr.serv", "Asvr.s = Vr.serv / fsi", f"{num(s['Asvr'], 1)} mm2"),
        calcpad.row("Vertical capacity", "Tbs1 = (Asi1 - Asvr.s) fsi sin(gamma1)",
                    f"{kN(s['Tbs1'], 1)} kN"),
        calcpad.row("Horizontal capacity", "Tbs2 = Asi2 fsi sin(gamma2)", f"{kN(s['Tbs2'], 1)} kN"),
        calcpad.row("Serviceability capacity", "Tbs = Tbs1 + Tbs2",
                    f"{kN(s['TbsCapacity'], 1)} kN"),
        *_badge_rows(result, ("burstingService",)),
    ]
    return calcpad.table("Bursting Serviceability - Cl 7.2.4(a)", rows)


def _cracking(result: dict[str, Any]) -> str:
    c = result["cracking"]
    stress = "φ fsy (reference 2)" if c["useRef2"] else "fsi"
    rows = [
        calcpad.row("Tensile strength", "f'ct = 0.36 sqrt(f'c)", f"{num(c['fct'], 3)} MPa",
                    "Cl 3.1.1.3"),
        calcpad.row("Cracking force", "Tb.cr = 0.7 bc lb f'ct", f"{kN(c['Tbcr'], 1)} kN",
                    "Eq 7.2.4(1)"),
        calcpad.row("Vertical share", "Tb.cr.1 = Tb.cr sin(gamma1) + Vr*",
                    f"{kN(c['Tbcr1'], 1)} kN"),
        calcpad.row("Horizontal share", "Tb.cr.2 = Tb.cr sin(gamma2)", f"{kN(c['Tbcr2'], 1)} kN"),
        calcpad.row("Force for the reinforcement test", "Tbb* = C* x 0.5", f"{kN(c['Tbb'], 1)} kN"),
        calcpad.row("Threshold", "0.5 Tb.cr", f"{kN(c['limit'], 1)} kN"),
        calcpad.row("Reinforcement required", "Tbb* > 0.5 Tb.cr", "Yes" if c["required"] else "No"),
        calcpad.row("Steel stress basis", "Reference 2 or AS 3600 stress limit", stress),
        calcpad.row("Vertical capacity", "Tbsc1 = fs (Asi1 - Asvr) sin(gamma1)",
                    f"{kN(c['Tbsc1'], 1)} kN"),
        calcpad.row("Horizontal capacity", "Tbsc2 = fs Asi2 sin(gamma2)", f"{kN(c['Tbsc2'], 1)} kN"),
        calcpad.row("Cracking capacity", "Tbsc = Tbsc1 + Tbsc2", f"{kN(c['TbscCapacity'], 1)} kN"),
        *_badge_rows(result, ("burstingCracking", "burstingThreshold", "oneWayAngle",
                              "verticalLoadSteel")),
    ]
    return calcpad.table("Bursting at Cracking - Eq 7.2.4(1)", rows)


def _spacing(result: dict[str, Any]) -> str:
    r = result["reinforcement"]
    rows = []
    for key, label in (("strength", "strength"), ("service", "serviceability"),
                       ("cracking", "cracking")):
        data = result[key]
        rows += [
            calcpad.row(f"Area required, {label}", "Am.req = As.i / lb.i",
                        f"{num(data['Am1'], 0)} / {num(data['Am2'], 0)} mm2/m"),
            calcpad.row(f"Maximum centres, {label}", "cts = As / Am.req",
                        f"{num(data['cts1'], 0)} / {num(data['cts2'], 0)} mm"),
        ]
    rows += [
        calcpad.row("Centres provided", "cts1 / cts2",
                    f"{num(r['cts1'], 0)} / {num(r['cts2'], 0)} mm"),
        calcpad.row("Governing requirement", "vertical / horizontal",
                    f"{r['governing1']} / {r['governing2']}", "Informative"),
    ]
    return calcpad.table("Required Bursting Reinforcement Spacing - Cl 7.2.4", rows)


def _tie(result: dict[str, Any]) -> str:
    t = result["tie"]
    rows = [
        calcpad.row("Tie tension", "T*", f"{kN(t['Tstar'], 1)} kN"),
        calcpad.row("Steel area required", "Ast.req = T* / (phi fsy)",
                    f"{num(t['AstRequired'], 1)} mm2"),
        calcpad.row("Bar group area", "As3 = pi db^2 / 4 x layers", f"{num(t['As3'], 1)} mm2"),
        calcpad.row("Bars required per layer", "Ast.req / As3", num(t["barsRequired"], 2)),
        calcpad.row("Steel area provided", "Ast = n As3",
                    f"{num(t['bars'], 0)} x {t['class']}{num(t['bar'], 0)} x "
                    f"{num(t['layers'], 0)} = {num(t['Ast'], 1)} mm2"),
        calcpad.row("Design tie stress", "phi fsy", f"{num(t['Ta'], 1)} MPa", "Table 2.2.4"),
        calcpad.row("Tie capacity", "phiT = phi fsy Ast", f"{kN(t['phiT'], 1)} kN", "Cl 7.3.2"),
        *_badge_rows(result, ("tie",)),
    ]
    return calcpad.table("Tension Tie - Cl 7.3", rows)


def _node(result: dict[str, Any]) -> str:
    n = result["node"]
    rows = [
        calcpad.row("Node type", n["type"], escape(n["label"])),
        calcpad.row("Node efficiency factor", "beta_n = 1.0 CCC, 0.8 CCT, 0.6 CTT",
                    num(n["betan"], 2), "Cl 7.4.2"),
        calcpad.row("Nodal stress limit", "sigma3 = phi beta_n 0.9 f'c",
                    f"{num(n['sigma3'], 3)} MPa", "Cl 7.4.2"),
        calcpad.row("Nodal stress entered", "sigma_o = user input", f"{num(n['stresso'], 3)} MPa"),
        *_badge_rows(result, ("node",)),
    ]
    return calcpad.table("Nodes - Cl 7.4.2", rows)


def _bearing(result: dict[str, Any]) -> str:
    b = result["bearing"]
    rows = [
        calcpad.row("Bearing force", escape(BEARING_MODES[b["mode"]]), f"{kN(b['Bstar'], 1)} kN"),
        calcpad.row("Bearing area", escape(AREA_MODES[b["areaMode"]]), f"{num(b['A1'], 0)} mm2"),
        calcpad.row("Largest similar supporting area", "A2 >= A1", f"{num(b['A2'], 0)} mm2"),
        calcpad.row("Bearing stress", "B* / A1", f"{num(b['Bs'], 3)} MPa"),
        calcpad.row("Upper limit", "phi 1.8 f'c", f"{num(b['fBmax'], 2)} MPa", "Table 2.2.2"),
        calcpad.row("Confined limit", "phi 0.9 f'c sqrt(A2 / A1)", f"{num(b['fBa'], 2)} MPa"),
        calcpad.row("Design bearing stress", "min of the above", f"{num(b['fB'], 2)} MPa"),
        calcpad.row("Bearing capacity", "phiB = phi fb A1", f"{kN(b['phiB'], 1)} kN"),
        *_badge_rows(result, ("bearing",)),
    ]
    return calcpad.table("Bearing Surfaces - Cl 12.6", rows)


def _faces(result: dict[str, Any]) -> str:
    f = result["nodeFaces"]
    if not f:
        return ""
    rows = [
        calcpad.row("Strut face", "sigma.s = C* / (bc dc)", f"{num(f['sigmaStrut'], 3)} MPa"),
        calcpad.row("Bearing face", "sigma.b = Cv* / (bc Lr)", f"{num(f['sigmaBearing'], 3)} MPa"),
        calcpad.row("Tie face height", escape(TIE_HEIGHT_MODES[f["tieHeightMode"]]),
                    f"u = {num(f['tieHeight'], 1)} mm"),
        calcpad.row("Tie face", "sigma.t = T* / (bc u)", f"{num(f['sigmaTie'], 3)} MPa"),
        calcpad.row("Nodal stress limit", "sigma3 = phi beta_n 0.9 f'c", f"{num(f['sigma3'], 3)} MPa"),
        *_badge_rows(result, ("nodeStrutFace", "nodeBearingFace", "nodeTieFace")),
    ]
    return calcpad.table("Nodal Face Stresses - Cl 7.4.2", rows)


def _basis(result: dict[str, Any]) -> str:
    def items(values: list[str]) -> str:
        return "<ul>" + "".join(f"<li>{escape(value)}</li>" for value in values) + "</ul>"

    body = ("<h3>Assumptions</h3>" + items(result["assumptions"])
            + "<h3>Limitations and exclusions</h3>" + items(result["limitations"]))
    if result["unattainable"]:
        body += "<h3>Unattainable checks</h3>" + items(result["unattainable"])
    if result["warnings"]:
        body += "<h3>Warnings</h3>" + items(result["warnings"])
    count = (len(result["assumptions"]) + len(result["limitations"]) + len(result["warnings"])
             + len(result["unattainable"]))
    return calcpad.prose("Design Basis, Assumptions and Limitations", body, weight=6 + 2 * count)
