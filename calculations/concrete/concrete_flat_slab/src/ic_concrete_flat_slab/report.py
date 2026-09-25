"""Calculation-pad presentation for the flat slab module, in the column-module layout.

Only formatting happens here; every engineering value comes from
:func:`ic_concrete_flat_slab.engine.compute`.
"""

from __future__ import annotations

from html import escape
from typing import Any

import calcpad

from .engine import (CUSTOM_SUPPORT_FIELDS, DISTRIBUTION_RANGES, FLEXURE_LAYERS, LOAD_TYPES,
                     POSITION_KIND, POSITIONS, SPAN_TYPES, SUPPORT_LABELS)
from .version import VERSION

DATA_ID = "concrete-flat-slab-inputs"
DEFAULT_SUBJECT = "Flat slab design"
num = calcpad.number

CHECK_ROWS = [
    ("spanRatio", "Span ratio not exceeding 2", "(Ly / Lx) / 2", "Cl 6.10.4.1(c)"),
    ("liveLoadRatio", "Live load not exceeding twice the dead load", "wll / (2 g)",
     "Cl 6.10.4.1(g)"),
    ("ductilityClass", "Class N flexural reinforcement", "Class L not permitted",
     "Cl 6.10.4.1(i)"),
    ("distributionRange", "Custom column strip factors", "within Table 6.9.5.3 ranges",
     "Table 6.9.5.3"),
    ("minimumSteel", "Minimum strength reinforcement", "Ast.min / Ast", "Cl 9.1.1(a)"),
    ("liveLoadDeflection", "Live load not exceeding dead load", "wll / g", "Cl 9.4.4.1"),
    ("deflectionTotal", "Deemed-to-comply depth, total", "d.min / ds", "Cl 9.4.4.1"),
    ("deflectionIncremental", "Deemed-to-comply depth, incremental", "d.min.inc / ds",
     "Cl 9.4.4.1"),
    ("flexure", "Flexural capacity, governing strip", "M* / phiMu", "Cl 8.1"),
    ("ductility", "Ductility, governing strip", "ku / 0.36", "Cl 8.1.5"),
    ("flexuralMinimum", "Minimum reinforcement, governing strip", "As.min / As",
     "Cl 9.1.1, Cl 9.4.3"),
    ("barSpacing", "Bar spacing, governing strip", "s / min(300, 2D)", "Cl 9.4.1"),
    ("shrinkage", "Shrinkage and temperature reinforcement", "As.cs / Ast", "Cl 9.4.3"),
]
SHORT_POSITIONS = ("End -ve", "End span +ve", "1st int. -ve (end)", "1st int. -ve (int.)",
                   "Interior +ve", "Interior -ve")
KIND_LABELS = {"negExt": "Negative, exterior", "negInt": "Negative, interior",
               "pos": "Positive"}


def render(inputs: dict[str, Any], result: dict[str, Any], *, standalone: bool = False,
           appendix: list[str] | None = None, anchor_prefix: str = "",
           contents_href: str = "") -> str:
    blocks = [
        _summary(result),
        *_inputs(inputs),
        _plan_figure(result),
        _moment_figure(result),
        _applicability(result),
        _actions(result),
        *_spans(result),
        _static(result),
        *_coefficients(result),
        *_strips(result),
        _transfer(result),
        _minimum(result),
        _deflection(result),
        _shrinkage(result),
        *_flexure(result),
        _basis(result),
    ]
    title = (f"{inputs.get('memberType', 'Flat slab')}-{inputs.get('memberNumber', '')} "
             f"- Concrete Flat Slab Design {VERSION}")
    return calcpad.render(inputs, blocks, standalone=standalone, appendix=appendix,
                          anchor_prefix=anchor_prefix, contents_href=contents_href,
                          default_subject=DEFAULT_SUBJECT, data_id=DATA_ID, title=title)


def _extreme(values: list[float], sign: int) -> float:
    return max((sign * value for value in values), default=0.0) * sign


def _grid(*args: Any) -> str:
    """calcpad.grid kept left of the sheet's reference-column rule."""
    return f'<div style="margin-right:37mm">{calcpad.grid(*args)}</div>'


def _summary(result: dict[str, Any]) -> str:
    values, analysis, static = result["inputs"], result["analysis"], result["static"]
    strips, deflection = result["strips"], result["deflection"]
    column = strips["y"]["csPerM"] + strips["x"]["csPerM"]
    drop = "with drop panels" if values["hasDrop"] else "no drop panels"
    rows = [
        calcpad.row("Slab system", "Ly x Lx x th, f'c",
                    f"{num(values['Ly'], 0)} x {num(values['Lx'], 0)} x {num(values['th'], 0)} mm, "
                    f"f'c = {num(values['fc'], 0)} MPa"),
        calcpad.row("Exterior edge", f"Type {escape(analysis['slabType'])}",
                    f"{escape(analysis['typeLabel'])}, {drop}", "Table 6.10.4.3"),
        calcpad.row("Design load", f"Fd = {result['loads']['case']}",
                    f"{num(result['loads']['Fd'], 2)} kPa", "AS/NZS 1170.0 Cl 4.2.2"),
        calcpad.row("Total static moment, span Ly", "Mo = Fd Lt Lo^2 / 8, end / interior",
                    f"{num(static['Moy1'], 1)} / {num(static['Moy'], 1)} kNm", "Cl 6.10.4.2"),
        calcpad.row("Total static moment, span Lx", "Mo = Fd Lt Lo^2 / 8, end / interior",
                    f"{num(static['Mox1'], 1)} / {num(static['Mox'], 1)} kNm", "Cl 6.10.4.2"),
        calcpad.row("Column strip moment, peak", "M* negative / positive",
                    f"{num(_extreme(column, -1), 1)} / {num(_extreme(column, 1), 1)} kNm/m",
                    "Table 6.9.5.3"),
        calcpad.row("Minimum effective depth", "d.min / d.min.inc",
                    f"{num(deflection['dmin'], 0)} / {num(deflection['dmini'], 0)} mm",
                    "Cl 9.4.4.1"),
        calcpad.row("Effective depth provided", "ds = th - cover - db.inner - db / 2"
                    if values["insideLayer"] else "ds = th - cover - db / 2",
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
            ("Longer span", "Ly", "mm"), ("Shorter span", "Lx", "mm"),
            ("Edge overhang, Ly direction", "Oy", "mm"), ("Edge overhang, Lx direction", "Ox", "mm"),
            ("Column dimension, parallel to Ly", "Cy", "mm"),
            ("Column dimension, parallel to Lx", "Cx", "mm"),
            ("Slab thickness", "th", "mm"), ("Drop panels", "hasDrop", ""),
            ("Exterior edge condition", "slabType", ""),
            ("Limit interior column strip to L/2", "limitStrip", ""),
            ("Reinforcement ductility class", "reo", ""), ("Concrete strength f'c", "fc", "MPa")]),
        ("Loading", [
            ("Dead load incl. self weight", "wdl", "kPa"),
            ("Superimposed dead load", "wsdl", "kPa"), ("Live load", "wll", "kPa"),
            ("Live load type", "loadType", "")]),
        ("Reinforcement and Deflection", [
            ("Span type for deflection", "spanType", ""), ("Nominal bar size", "bar", "mm"),
            ("Cover to bottom steel", "cover", "mm"), ("Base ds on inside layer", "insideLayer", ""),
            ("Tensile steel", "Ast", "mm2/m"), ("Yield strength", "fsy", "MPa"),
            ("Compression steel", "Asc", "mm2/m"), ("Depth to compression steel", "dc", "mm"),
            ("Use fcmi for Ec", "useFcmi", ""), ("Concrete density", "density", "kg/m3"),
            ("Total deflection limit Lef/Delta", "lefDelta", ""),
            ("Incremental deflection limit Lef/Delta", "lefDeltaInc", "")]),
    ]
    checks = inputs.get("checks") or {}
    if checks.get("customSupports"):
        groups.append(("Custom Support Lengths", [
            (f"Sum of a_sup, {label.lower()}", CUSTOM_SUPPORT_FIELDS[key], "mm")
            for key, label in SUPPORT_LABELS.items()]))
    if checks.get("customDistribution"):
        fields = [(f"Column strip factor, {position.lower()}", f"cf{index}", "")
                  for index, position in enumerate(POSITIONS, start=1)]
        fields += [(f"Edge column strip factor, {position.lower()}", f"ef{index}", "")
                   for index, position in enumerate(POSITIONS, start=1)]
        groups.append(("Custom Distribution", fields))
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


# ---------------------------------------------------------------------------
#  Drawings
# ---------------------------------------------------------------------------
def _text(x: float, y: float, value: str, anchor: str = "middle", size: float = 2.4,
          colour: str = "#111", rotate: bool = False) -> str:
    spin = f' transform="rotate(-90 {x:.2f} {y:.2f})"' if rotate else ""
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" text-anchor="{anchor}" '
            f'fill="{colour}"{spin}>{escape(value)}</text>')


def plan_drawing(result: dict[str, Any], width: float = 120.0, height: float = 68.0) -> str:
    """Plan of the corner of the slab: column grid, drops, edge support and My* design strips."""
    g, strips = result["geometry"], result["strips"]
    fstype = result["analysis"]["fstype"]
    Lx, Ly, Ox, Oy = g["Lx"], g["Ly"], g["Ox"], g["Oy"]
    reach = 2.45
    extent_x, extent_y = reach * Lx + Ox, reach * Ly + Oy
    scale = min(width / extent_x, height / extent_y)
    left, top, bottom_margin = 16.0, 9.0, 15.0
    body_w, body_h = extent_x * scale, extent_y * scale
    view_w, view_h = left + body_w + 8.0, top + body_h + bottom_margin

    def px(x: float) -> float:
        return left + (x + Ox) * scale

    def py(y: float) -> float:
        return top + body_h - (y + Oy) * scale

    parts = []

    def band(x0: float, x1: float, fill: str) -> None:
        parts.append(f'<rect x="{px(x0):.2f}" y="{top:.2f}" width="{(x1 - x0) * scale:.2f}" '
                     f'height="{body_h:.2f}" fill="{fill}" stroke="none"/>')

    cs, ecs = strips["y"]["csWidth"], strips["edgeY"]["csWidth"]
    band(-Ox, -Ox + ecs, "#cfdcf2")
    band(-Ox + ecs, Lx / 2, "#f4ead8")
    band(Lx / 2, Lx - cs / 2, "#f4ead8")
    band(Lx - cs / 2, Lx + cs / 2, "#cfdcf2")
    band(Lx + cs / 2, 1.5 * Lx, "#f4ead8")
    x_end, y_foot = left + body_w, top + body_h
    # Slab edges solid; the slab continues beyond the dashed sides.
    parts.append(f'<path d="M{left:.2f},{top:.2f} L{left:.2f},{y_foot:.2f} L{x_end:.2f},{y_foot:.2f}" '
                 'fill="none" stroke="#111" stroke-width="0.5"/>'
                 f'<path d="M{left:.2f},{top:.2f} L{x_end:.2f},{top:.2f} L{x_end:.2f},{y_foot:.2f}" '
                 'fill="none" stroke="#111" stroke-width="0.3" stroke-dasharray="1.6,1"/>')
    for index in range(3):
        parts.append(f'<line x1="{px(index * Lx):.2f}" y1="{top:.2f}" x2="{px(index * Lx):.2f}" '
                     f'y2="{top + body_h:.2f}" stroke="#777" stroke-width="0.15" '
                     'stroke-dasharray="3,0.8,0.6,0.8"/>'
                     f'<line x1="{left:.2f}" y1="{py(index * Ly):.2f}" x2="{left + body_w:.2f}" '
                     f'y2="{py(index * Ly):.2f}" stroke="#777" stroke-width="0.15" '
                     'stroke-dasharray="3,0.8,0.6,0.8"/>')
    if fstype == 3:
        for x0, y0, x1, y1 in ((0, 0, reach * Lx, 0), (0, 0, 0, reach * Ly)):
            parts.append(f'<line x1="{px(x0):.2f}" y1="{py(y0):.2f}" x2="{px(x1):.2f}" '
                         f'y2="{py(y1):.2f}" stroke="#555" stroke-width="1.6" opacity="0.55"/>')
    for i in range(3):
        for j in range(3):
            edge = i == 0 or j == 0
            if fstype == 4 and edge:
                continue
            if g["hasDrop"] and not (fstype == 3 and edge):
                dx, dy = g["dropX"] * scale, g["dropY"] * scale
                parts.append(f'<rect x="{px(i * Lx) - dx:.2f}" y="{py(j * Ly) - dy:.2f}" '
                             f'width="{2 * dx:.2f}" height="{2 * dy:.2f}" fill="none" '
                             'stroke="#333" stroke-width="0.25" stroke-dasharray="1,0.7"/>')
            cw, ch = max(g["Cx"] * scale, 1.2), max(g["Cy"] * scale, 1.2)
            parts.append(f'<rect x="{px(i * Lx) - cw / 2:.2f}" y="{py(j * Ly) - ch / 2:.2f}" '
                         f'width="{cw:.2f}" height="{ch:.2f}" fill="#222"/>')
    if fstype == 4:
        wall = 1.4
        parts.append(f'<rect x="{px(0) - wall / 2:.2f}" y="{top:.2f}" width="{wall:.2f}" '
                     f'height="{py(0) - top + wall / 2:.2f}" fill="#444"/>'
                     f'<rect x="{px(0) - wall / 2:.2f}" y="{py(0) - wall / 2:.2f}" '
                     f'width="{left + body_w - px(0) + wall / 2:.2f}" height="{wall:.2f}" '
                     'fill="#444"/>')
    label_y = top + 3.6
    parts += [
        _text((px(-Ox) + px(-Ox + ecs)) / 2, label_y, "ECS", size=2.2, colour="#1c4fa1"),
        _text((px(-Ox + ecs) + px(Lx / 2)) / 2, label_y, "MS", size=2.2, colour="#8a5a14"),
        _text(px(Lx), label_y, "CS", size=2.2, colour="#1c4fa1"),
        _text((px(Lx + cs / 2) + px(1.5 * Lx)) / 2, label_y, "MS", size=2.2, colour="#8a5a14"),
    ]
    dim_y = top + body_h + 5.0
    parts += [
        f'<line x1="{px(0):.2f}" y1="{dim_y:.2f}" x2="{px(Lx):.2f}" y2="{dim_y:.2f}" '
        'stroke="#111" stroke-width="0.2"/>',
        _text((px(0) + px(Lx)) / 2, dim_y - 1.0, f"Lx = {Lx:,.0f}"),
        _text((px(Lx / 2) + px(1.5 * Lx)) / 2, dim_y + 5.5,
              f"Interior design strip Lt = Lx, CS = {cs:,.0f}", size=2.2),
        _text(px(-Ox), dim_y + 2.6, f"Ox = {Ox:,.0f}", anchor="start", size=2.1),
        f'<line x1="{left - 5:.2f}" y1="{py(0):.2f}" x2="{left - 5:.2f}" y2="{py(Ly):.2f}" '
        'stroke="#111" stroke-width="0.2"/>',
        _text(left - 6.2, (py(0) + py(Ly)) / 2, f"Ly = {Ly:,.0f}", rotate=True),
        _text(left - 2.2, py(-Oy) - 0.6, f"Oy = {Oy:,.0f}", anchor="start", size=2.1, rotate=True),
    ]
    return (f'<svg viewBox="0 0 {view_w:.2f} {view_h:.2f}" width="{view_w:.2f}mm" '
            f'height="{view_h:.2f}mm" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="Flat slab plan">{"".join(parts)}</svg>')


def _plan_figure(result: dict[str, Any]) -> str:
    fstype = result["analysis"]["fstype"]
    support = {1: "Columns at an unrestrained edge.", 2: "Edge columns without edge beams.",
               3: "Edge beams (grey) along both edges; no drops at edge columns.",
               4: "Walls along both edges replace the edge columns."}[fstype]
    drop = " Dashed squares are drop panels (L/6 each way)." if result["geometry"]["hasDrop"] else ""
    caption = (f"Corner of the slab to scale. Shaded bands are the design strips for My* (spanning "
               f"Ly): column strips (blue) and middle strips (buff); Mx* strips are the same "
               f"turned through 90 degrees. {support}{drop}")
    return calcpad.figure("Slab Plan and Design Strips", plan_drawing(result), caption, weight=20)


def _curve(ends: tuple[float, float], mid: float, samples: int = 16) -> list[tuple[float, float]]:
    """Parabola through the end moments with the positive moment at midspan."""
    a, b = ends
    rise = mid - (a + b) / 2
    return [(t, a * (1 - t) + b * t + 4 * rise * t * (1 - t))
            for t in (index / samples for index in range(samples + 1))]


def moment_drawing(result: dict[str, Any]) -> str:
    """Column and middle strip moments per metre along the end and first interior spans."""
    strips = result["strips"]
    panels = (("My* interior design strip (span Ly)", strips["y"]),
              ("Mx* interior design strip (span Lx)", strips["x"]))
    peak = max(abs(value) for _, strip in panels for key in ("csPerM", "msPerM")
               for value in strip[key]) or 1.0
    width, panel_h, left = 120.0, 38.0, 10.0
    span_w = (width - left - 6.0) / 2
    k = 11.0 / peak
    parts = []
    for row, (title, strip) in enumerate(panels):
        axis = 8.0 + row * panel_h + 19.0
        parts.append(_text(left, 8.0 + row * panel_h + 1.5, title, anchor="start", size=2.5))
        parts.append(f'<line x1="{left:.2f}" y1="{axis:.2f}" x2="{left + 2 * span_w:.2f}" '
                     f'y2="{axis:.2f}" stroke="#111" stroke-width="0.35"/>')
        for index in range(3):
            x = left + index * span_w
            parts.append(f'<path d="M{x - 1.3:.2f},{axis + 2.2:.2f} L{x:.2f},{axis:.2f} '
                         f'L{x + 1.3:.2f},{axis + 2.2:.2f} Z" fill="#fff" stroke="#111" '
                         'stroke-width="0.25"/>')
        for series, colour, dash in (("csPerM", "#1c4fa1", ""), ("msPerM", "#b1257a", "1.2,0.8")):
            v = strip[series]
            points = [(t, m) for t, m in _curve((v[0], v[2]), v[1])]
            points += [(1 + t, m) for t, m in _curve((v[3], v[5]), v[4])]
            path = " ".join(f"{'M' if i == 0 else 'L'}{left + t * span_w:.2f},{axis + m * k:.2f}"
                            for i, (t, m) in enumerate(points))
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
            parts.append(f'<path d="{path}" fill="none" stroke="{colour}" stroke-width="0.45"'
                         f'{dash_attr}/>')
        # Column strip label above the middle strip label, clear of both curves.
        cs, ms = strip["csPerM"], strip["msPerM"]
        placements = ((0.0, 1.2, "start"), (0.5, 0.0, "middle"), (1.0, -1.2, "end"),
                      (1.0, 1.2, "start"), (1.5, 0.0, "middle"), (2.0, -1.2, "end"))
        for (t, shift, anchor), a, b in zip(placements, cs, ms):
            if a == 0 and b == 0:
                continue
            hogging = min(a, b) < 0
            base = (axis + min(a, b) * k - 3.2) if hogging else (axis + max(a, b) * k + 2.8)
            x = left + t * span_w + shift
            parts.append(_text(x, base, f"{a:.1f}", anchor, size=2.0, colour="#1c4fa1"))
            parts.append(_text(x, base + 2.3, f"{b:.1f}", anchor, size=2.0, colour="#b1257a"))
        parts.append(_text(left + span_w / 2, axis - 1.6, "End span", size=2.1, colour="#555"))
        parts.append(_text(left + 1.5 * span_w, axis - 1.6, "Interior span", size=2.1,
                           colour="#555"))
    height = 8.0 + 2 * panel_h
    return (f'<svg viewBox="0 0 {width:.2f} {height:.2f}" width="{width:.2f}mm" '
            f'height="{height:.2f}mm" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="Design strip moments">{"".join(parts)}</svg>')


def _moment_figure(result: dict[str, Any]) -> str:
    caption = ("Moments per metre width in kNm/m: column strip solid blue, half middle strip "
               "dashed magenta. Hogging (negative) moments are drawn above the axis, on the "
               "tension face. Curves are schematic parabolas through the design values.")
    return calcpad.figure("Design Strip Moments", moment_drawing(result), caption, weight=18)


# ---------------------------------------------------------------------------
#  Check tables
# ---------------------------------------------------------------------------
def _applicability(result: dict[str, Any]) -> str:
    util, analysis, loads = result["util"], result["analysis"], result["loads"]
    rows = [
        calcpad.row("Continuous spans", "at least 2 in each direction", "assumed",
                    "Cl 6.10.4.1(a)"),
        calcpad.row("Support grid", "rectangular, offsets <= 10 % of span", "assumed",
                    "Cl 6.10.4.1(b)"),
        calcpad.row("Span ratio", "Ly / Lx <= 2", num(analysis["spanRatio"], 3), "Cl 6.10.4.1(c)"),
        calcpad.row("Span ratio check", "(Ly / Lx) / 2", calcpad.badge(util["spanRatio"])),
        calcpad.row("Successive spans", "differ by <= 1/3 of the longer; end span <= interior",
                    "equal spans assumed", "Cl 6.10.4.1(d), (e)"),
        calcpad.row("Live to dead load ratio", "wll <= 2 (wdl + wsdl)",
                    f"{num(loads['wll'], 2)} / {num(2 * loads['g'], 2)} kPa", "Cl 6.10.4.1(g)"),
        calcpad.row("Live load check", "wll / (2 g)", calcpad.badge(util["liveLoadRatio"])),
        calcpad.row("Flexural reinforcement", "Ductility Class N",
                    f"Class {escape(result['inputs']['reo'])}", "Cl 6.10.4.1(i)"),
        calcpad.row("Reinforcement class check", "Class L not permitted",
                    calcpad.badge(util["ductilityClass"])),
    ]
    return calcpad.table("Applicability of the Simplified Method - Cl 6.10.4.1", rows)


def _actions(result: dict[str, Any]) -> str:
    loads = result["loads"]
    rows = [
        calcpad.row("Dead load, incl. self weight", "wdl", f"{num(loads['wdl'], 2)} kPa",
                    f"S.Wt = 25 th = {num(loads['selfWeight'], 2)} kPa"),
        calcpad.row("Superimposed dead load", "wsdl", f"{num(loads['wsdl'], 2)} kPa"),
        calcpad.row("Permanent action", "g = wdl + wsdl", f"{num(loads['g'], 2)} kPa"),
        calcpad.row("Live load", "wll", f"{num(loads['wll'], 2)} kPa"),
        calcpad.row("Strength combination", "Fd = max(1.35 g, 1.2 g + 1.5 wll)",
                    f"{num(loads['Fd'], 2)} kPa", f"AS/NZS 1170.0 Cl 4.2.2, {escape(loads['case'])}"),
        calcpad.row("Live load use", LOAD_TYPES[loads["loadType"]],
                    f"psi_s = {num(loads['psiS'], 2)}, psi_l = {num(loads['psiL'], 2)}",
                    "AS/NZS 1170.0 Table 4.1"),
    ]
    return calcpad.table("Design Actions - AS/NZS 1170.0", rows)


def _spans(result: dict[str, Any]) -> tuple[str, str]:
    g, spans, supports = result["geometry"], result["spans"], result["supports"]
    rows = []
    for key, label in SUPPORT_LABELS.items():
        span = g["Ly"] if key[2] == "y" else g["Lx"]
        lo_key = "Lo" + key[2:]
        rows.append([escape(label), num(span, 0), num(supports[key], 1),
                     num(spans["raw"][lo_key], 1), num(0.65 * span, 0), num(spans[lo_key], 1)])
    note = ("Lengths in mm. a_sup1 + a_sup2 from the workbook's support table"
            + (" (custom values)." if result["analysis"]["customSupports"] else ".")
            + (" Wall-supported edge strips carry no span moment (Lo = 0)."
               if spans["wallEdge"] else ""))
    grid = _grid("Support Lengths and Effective Spans - Cl 6.10.4.2",
                        ["Strip and span", "L", "a.sup1 + a.sup2", "L - 0.7 sum", "0.65 L", "Lo"],
                        rows, note)
    drop_rows = [
        calcpad.row("Drop panel depth", "thd = 0.3 th", f"{num(g['thd'], 1)} mm",
                    "Cl 9.4.4.1, overall 1.3 D"),
        calcpad.row("Drop panel extent", "DLy, DLx = roundup(L / 6, 10)",
                    f"{num(g['dropY'], 0)} / {num(g['dropX'], 0)} mm each side", "Cl 9.4.4.1"),
        calcpad.row("Span to depth", "max(Lo.x, Lo.y) / th", num(result["analysis"]["spanDepth"], 2)),
    ] if g["hasDrop"] else [
        calcpad.row("Drop panels", "none", "-"),
        calcpad.row("Span to depth", "max(Lo.x, Lo.y) / th", num(result["analysis"]["spanDepth"], 2)),
    ]
    return grid, calcpad.table("Drop Panels and Slenderness", drop_rows)


def _static(result: dict[str, Any]) -> str:
    static, spans = result["static"], result["spans"]
    rows = [
        calcpad.row("Interior strip, end span, Ly", "Mo.y1 = Fd Lx Lo.y1^2 / 8",
                    f"{num(static['Moy1'], 2)} kNm", "Eq 6.10.4.2"),
        calcpad.row("Interior strip, interior span, Ly", "Mo.y = Fd Lx Lo.y^2 / 8",
                    f"{num(static['Moy'], 2)} kNm", "Eq 6.10.4.2"),
        calcpad.row("Interior strip, end span, Lx", "Mo.x1 = Fd Ly Lo.x1^2 / 8",
                    f"{num(static['Mox1'], 2)} kNm", "Eq 6.10.4.2"),
        calcpad.row("Interior strip, interior span, Lx", "Mo.x = Fd Ly Lo.x^2 / 8",
                    f"{num(static['Mox'], 2)} kNm", "Eq 6.10.4.2"),
        calcpad.row("Edge strip widths", "Lt.e = L / 2 + O",
                    f"{num(static['Ltxe'], 0)} / {num(static['Ltye'], 0)} mm", "My* / Mx*"),
        calcpad.row("Edge strip, end span, Ly", "Mo.y1e = Fd Lt.xe Lo.y1e^2 / 8",
                    f"{num(static['Moy1e'], 2)} kNm", "Eq 6.10.4.2"),
        calcpad.row("Edge strip, interior span, Ly", "Mo.ye = Fd Lt.xe Lo.ye^2 / 8",
                    f"{num(static['Moye'], 2)} kNm", "Eq 6.10.4.2"),
        calcpad.row("Edge strip, end span, Lx", "Mo.x1e = Fd Lt.ye Lo.x1e^2 / 8",
                    f"{num(static['Mox1e'], 2)} kNm", "Eq 6.10.4.2"),
        calcpad.row("Edge strip, interior span, Lx", "Mo.xe = Fd Lt.ye Lo.xe^2 / 8",
                    f"{num(static['Moxe'], 2)} kNm", "Eq 6.10.4.2"),
    ]
    if spans["floorApplied"]:
        rows.append(calcpad.row("Lower limit applied", "Lo >= 0.65 L",
                                escape(", ".join(spans["floorApplied"])), "Cl 6.10.4.2"))
    return calcpad.table("Total Static Moments - Cl 6.10.4.2", rows)


def _coefficients(result: dict[str, Any]) -> tuple[str, str]:
    analysis, strips = result["analysis"], result["strips"]
    rows = []
    for index, position in enumerate(POSITIONS):
        low, high = DISTRIBUTION_RANGES[POSITION_KIND[index]]
        rows.append([escape(position), num(analysis["coefficients"][index], 2),
                     num(strips["y"]["factor"][index], 2), num(strips["y"]["msFactor"][index], 2),
                     num(strips["edgeY"]["factor"][index], 2), f"{low:.2f} - {high:.2f}"])
    source = "custom values" if analysis["customDistribution"] else "workbook defaults"
    grid = _grid(
        "Moment Coefficients and Strip Shares - Table 6.10.4.3 and Table 6.9.5.3",
        ["Position", "M*/Mo", "CS share", "MS share", "Edge CS share", "Table 6.9.5.3"], rows,
        f"Exterior edge {analysis['typeLabel'].lower()}; strip shares are {source}. Interior "
        "spans use -0.65 / +0.35 / -0.65. WRH and RCB recommend 0.5 for the positive moment.")
    if "distributionRange" not in result["util"]:
        return grid, ""
    check = calcpad.table("Custom Distribution - Table 6.9.5.3", [
        calcpad.row("Column strip shares", "max(low / f, f / high)",
                    calcpad.badge(result["util"]["distributionRange"]), "Table 6.9.5.3")])
    return grid, check


def _strip_grid(title: str, strip: dict[str, Any], edge: bool) -> str:
    rows = [[escape(SHORT_POSITIONS[index]), num(strip["total"][index], 1),
             num(strip["factor"][index], 2), num(strip["cs"][index], 1),
             num(strip["csPerM"][index], 1), num(strip["ms"][index], 1),
             num(strip["msPerM"][index], 1)] for index in range(6)]
    cs_label, ms_label = ("Edge CS" if edge else "CS"), "Half MS"
    note = (f"Strip moment M* in kNm; per metre in kNm/m. Design strip Lt = {strip['width']:,.0f} mm, "
            f"{cs_label} width {strip['csWidth']:,.0f} mm, {ms_label} width "
            f"{strip['msWidth']:,.0f} mm. "
            + ("First interior support governed by the end span." if strip["firstInteriorGoverns"]
               else "First interior support governed by the interior span."))
    return _grid(title, ["Position", "M*", "Share", f"{cs_label} M*", f"{cs_label} /m",
                         f"{ms_label} M*", f"{ms_label} /m"], rows, note)


def _strips(result: dict[str, Any]) -> list[str]:
    strips = result["strips"]
    return [
        _strip_grid("Interior Design Strip Moments, Span Ly - Cl 6.10.4.4", strips["y"], False),
        _strip_grid("Interior Design Strip Moments, Span Lx - Cl 6.10.4.4", strips["x"], False),
        _strip_grid("Edge Design Strip Moments, Span Ly - Cl 6.10.4.4", strips["edgeY"], True),
        _strip_grid("Edge Design Strip Moments, Span Lx - Cl 6.10.4.4", strips["edgeX"], True),
    ]


def _transfer(result: dict[str, Any]) -> str:
    moments = result["transfer"]
    basis = "M*v = 0.06 [(1.2 g + 0.75 q) Lt Lo^2 - 1.2 g Lt Lo.min^2]"
    rows = [
        calcpad.row("First interior column, span Ly", basis, f"{num(moments['firstY'], 1)} kNm",
                    "Cl 6.10.4.5"),
        calcpad.row("Typical interior column, span Ly", "Lo.min = Lo",
                    f"{num(moments['interiorY'], 1)} kNm", "Cl 6.10.4.5"),
        calcpad.row("First interior column, span Lx", basis, f"{num(moments['firstX'], 1)} kNm",
                    "Cl 6.10.4.5"),
        calcpad.row("Typical interior column, span Lx", "Lo.min = Lo",
                    f"{num(moments['interiorX'], 1)} kNm", "Cl 6.10.4.5"),
        calcpad.row("Use", "minimum Mv* for punching shear",
                    "concrete-punching-shear", "Cl 9.3.4"),
    ]
    return calcpad.table("Moment Transfer to Interior Columns - Cl 6.10.4.5", rows)


def _minimum(result: dict[str, Any]) -> str:
    minimum = result["minimum"]
    rows = [
        calcpad.row("Effective depth", "ds", f"{num(minimum['ds'], 1)} mm"),
        calcpad.row("Flexural tensile strength", "f'ct.f = 0.6 sqrt(f'c)",
                    f"{num(minimum['fctf'], 3)} MPa", "Cl 3.1.1.3"),
        calcpad.row("Minimum reinforcement", "Ast.min = 0.24 (D/d)^2 f'ct.f / fsy b d",
                    f"{num(minimum['Astmin'], 1)} mm2/m", "Cl 9.1.1(a)"),
        calcpad.row("Tensile steel provided", "Ast", f"{num(minimum['Ast'], 1)} mm2/m"),
        calcpad.row("Minimum strength check", "Ast.min / Ast",
                    calcpad.badge(result["util"]["minimumSteel"]), "Cl 9.1.1"),
    ]
    return calcpad.table("Minimum Strength Requirements - Cl 9.1.1", rows)


def _deflection(result: dict[str, Any]) -> str:
    d, util = result["deflection"], result["util"]
    wb = d["workbook"]
    asc = "ignored, in tension zone" if d["ascIgnored"] else f"{num(d['Asc'], 0)} mm2/m"
    ec_basis = ("Ec = rho^1.5 (0.043 sqrt(fcmi))" if d["fcmi"] <= 40
                else "Ec = rho^1.5 (0.024 sqrt(fcmi) + 0.12)")
    fcmi_basis = ("fcmi = -0.0015 f'c^2 + 1.1429 f'c - 0.0614" if d["useFcmi"]
                  else "fcmi taken as f'c")
    drop = result["geometry"]["hasDrop"]
    rows = [
        calcpad.row("Live to dead load ratio", "wll / g <= 1",
                    calcpad.badge(util["liveLoadDeflection"]), "Cl 9.4.4.1"),
        calcpad.row("Mean in-situ strength", fcmi_basis, f"{num(d['fcmi'], 2)} MPa", "Table 3.1.2"),
        calcpad.row("Modulus of elasticity", ec_basis, f"{num(d['Ec'], 0)} MPa", "Cl 3.1.2"),
        calcpad.row("Modular ratio", "n = Es / Ec", num(d["n"], 3), "Es = 200 GPa"),
        calcpad.row("Steel ratios", "p = Ast / (b ds); pc = Asc / (b ds)",
                    f"{num(d['p'], 5)} / {num(d['pc'], 5)}"),
        calcpad.row("Neutral axis parameter",
                    "ku = sqrt[(np + (n-1)pc)^2 + 2(np + (n-1)pc dc/ds)] - (np + (n-1)pc)",
                    f"{num(d['ku'], 4)}, kud = {num(d['NA'], 1)} mm", "WRH Eq 5.22"),
        calcpad.row("Compression steel for kcs", "Asc used when kud - db/2 - db.inner >= dc", asc),
        calcpad.row("Long-term factor", "kcs = 2 - 1.2 Asc / Ast >= 0.8", num(d["kcs"], 3),
                    "Cl 8.5.3.2"),
        calcpad.row("Effective load, total", "Fd.ef = (1 + kcs) g + (psi_s + kcs psi_l) q",
                    f"{num(d['Fdef'], 2)} kPa", "Cl 9.4.4.1(a)"),
        calcpad.row("Effective load, incremental", "Fd.ef.inc = kcs g + (psi_s + kcs psi_l) q",
                    f"{num(d['Fdefi'], 2)} kPa", "Cl 9.4.4.1(b)"),
        calcpad.row("Slab factors", "k3 / k4",
                    f"{num(d['k3'], 2)} / {num(d['k4'], 2)}, "
                    f"{'drop panels' if drop else 'no drops'}, {SPAN_TYPES[d['spanType']].lower()}",
                    "Cl 9.4.4.1"),
        calcpad.row("Effective span", "Lef = max over spans of min(L - c + D, L)",
                    f"{num(d['Lef'], 0)} mm", "Lef definition, longer span"),
        calcpad.row("Deflection limits", "Lef / Delta, total / incremental",
                    f"{num(d['lefDelta'], 0)} / {num(d['lefDeltaInc'], 0)}", "Table 2.3.2"),
        calcpad.row("Minimum depth, total", "d.min = Lef / (k3 k4 [(Delta/Lef) Ec / Fd.ef]^(1/3))",
                    f"{num(d['dmin'], 1)} mm", "Cl 9.4.4.1"),
        calcpad.row("Minimum depth, incremental", "same with Fd.ef.inc",
                    f"{num(d['dmini'], 1)} mm", "Cl 9.4.4.1"),
        calcpad.row("Equivalent thickness", "th.min = cover + db.inner + db/2 + d.min",
                    f"{num(d['thmin'], 0)} / {num(d['thmini'], 0)} mm"),
        calcpad.row("Workbook basis, Lo in place of Lef",
                    f"Lo = {num(d['LoWorkbook'], 0)} mm, d.min / d.min.inc",
                    f"{num(wb['dminDrop'] if drop else wb['dmin'], 1)} / "
                    f"{num(wb['dminiDrop'] if drop else wb['dmini'], 1)} mm", "for comparison"),
        calcpad.row("Total deflection check", "d.min / ds", calcpad.badge(util["deflectionTotal"])),
        calcpad.row("Incremental deflection check", "d.min.inc / ds",
                    calcpad.badge(util["deflectionIncremental"])),
    ]
    return calcpad.table("Deflection by Deemed-to-Comply Span-to-Depth - Cl 9.4.4.1", rows)


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
        rows.append(calcpad.row("Application", "As.min = max(As.cs, 0.24 (D/d)^2 f'ct.f/fsy b d)",
                                "at every strip"))
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
        calcpad.row("Neutral axis parameter", "ku = As fsy / (alpha2 f'c gamma b d)", "per strip",
                    "Cl 8.1.5"),
        calcpad.row("Capacity reduction factor", "phi = 1.24 - 13 ku / 12, 0.65 to 0.85",
                    "per strip", "Table 2.2.2"),
        calcpad.row("Moment capacity", "phiMu = phi As fsy d (1 - As fsy / (2 alpha2 f'c b d))",
                    "per strip", "Cl 8.1"),
        calcpad.row("Maximum bar spacing", "smax = min(300, 2D)", f"{num(data['sMax'], 0)} mm",
                    "Cl 9.4.1"),
    ]
    grid = _grid(
        "Flexural Capacity by Strip",
        ["Strip", "Bars", "As", "d", "ku", "phi", "M*", "phiMu", "M*/phiMu", "As.min"],
        [[escape(item["label"]), f"N{num(item['bar'], 0)}-{num(item['spacing'], 0)}",
          num(item["As"], 0), num(item["d"], 0), num(item["ku"], 3), num(item["phi"], 3),
          num(item["Mstar"], 1), num(item["phiMu"], 1), calcpad.badge(item["ratioMoment"]),
          num(item["AsMin"], 0)] for item in data["locations"]],
        "As and As.min in mm2/m, d in mm, moments in kNm/m. M* is the peak per metre over both "
        "directions; d uses the inner layer when ds is based on the inside layer; drop panel "
        "depth is ignored.")
    governs = calcpad.table("Governing Strip Moments", [
        calcpad.row(escape(item["label"]), "governing position", escape(item["governs"]))
        for item in data["locations"]])
    return [calcpad.table("Flexural Capacity - Cl 8.1", rows), grid, governs]


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
