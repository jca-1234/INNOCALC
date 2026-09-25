"""Calculation-pad presentation for the industrial pavement module, in the column-module layout.

Only formatting happens here; every engineering value comes from
:func:`ic_concrete_industrial_pavement.engine.compute`.
"""

from __future__ import annotations

from html import escape
from typing import Any

import calcpad

from .engine import FLEXURAL_METHODS, POSITIONS
from .version import VERSION

DATA_ID = "concrete-industrial-pavement-inputs"
DEFAULT_SUBJECT = "Industrial pavement design"
num = calcpad.number

CHECK_ROWS = [
    ("rackBearing", "Rack post bearing", "1.5 RPL / Fa / (phi 0.9 f'c)", "AS 3600 Cl 12.6"),
    ("rackPunching", "Rack post punching shear", "V* / phiVuo", "AS 3600 Cl 9.3.3"),
    ("rackFlexure", "Rack post flexural stress", "(sigma_rf + sigma_uf) / f'ct.f",
     "Chandler; T48 Cl 3.3.6"),
    ("wheelFlexure", "Wheel flexural stress", "sigma_wf / f'ct.f", "Chandler; T48 Table 1.17"),
    ("uniformVariable", "Uniform load, variable layout", "q / W", "C&amp;CA Cl 5.6.3"),
    ("uniformAisle", "Uniform load, actual aisle", "sigma_uf / f'ct.f", "Hetenyi"),
    ("uniformCritical", "Uniform load, critical aisle", "sigma_uf / f'ct.f", "Hetenyi"),
    ("abrasionGrade", "Concrete grade for abrasion", "25 / f'c", "T48 Tables 1.6 and 1.7"),
    ("customFlexure", "Custom load flexural stress", "(sigma_cf + sigma_uf) / f'ct.f",
     "Chandler; T48 Cl 3.3.6"),
    ("positionApplicability", "Load position applicability", "(a + l) / distance",
     "Westergaard; Tedds"),
]


def render(inputs: dict[str, Any], result: dict[str, Any], *, standalone: bool = False,
           appendix: list[str] | None = None, anchor_prefix: str = "",
           contents_href: str = "") -> str:
    blocks = [
        _summary(result),
        *_inputs(inputs),
        _section_figure(result),
        _plan_figure(result),
        _wheel_figure(result),
        _material(result),
        _subgrade(result),
        _abrasion(result),
        _bearing(result),
        _punching(result),
        _rack_stresses(result),
        _grid_block(_increase_grid("Adjacent Rack Post Stress Increases - Chandler",
                                   result["racking"]["points"], result)),
        _rack_total(result),
        _wheel_stresses(result),
        _grid_block(_increase_grid(
            f"Adjacent Wheel Stress Increases - {result['wheels']['axleCase'].title()} Axle",
            result["wheels"][result["wheels"]["axleCase"]]["points"], result)),
        _wheel_total(result),
        _uniform_variable(result),
        _uniform_patterned(result),
        *_custom(result),
        _location(result),
        _reinforcement(result),
        _basis(result),
    ]
    title = (f"{inputs.get('memberType', 'Floor slab')}-{inputs.get('memberNumber', '')} "
             f"- Concrete Industrial Pavement Design {VERSION}")
    return calcpad.render(inputs, blocks, standalone=standalone, appendix=appendix,
                          anchor_prefix=anchor_prefix, contents_href=contents_href,
                          default_subject=DEFAULT_SUBJECT, data_id=DATA_ID, title=title)


def _grid_block(html: str) -> str:
    # Keeps wide grids, drawings and prose clear of the sheet's right-hand reference rule.
    return f'<div style="margin-right:37mm">{html}</div>' if html else ""


def _summary(result: dict[str, Any]) -> str:
    mat, sub = result["material"], result["subgrade"]
    rack, wheels, uniform = result["racking"], result["wheels"], result["uniform"]
    rows = [
        calcpad.row("Slab", "h, f'c", f"{num(mat['h'], 0)} mm, f'c = {num(mat['fc'], 0)} MPa",
                    "Unreinforced for flexure"),
        calcpad.row("Subgrade", "K (CBR)",
                    f"{num(mat['K'], 0)} kPa/mm ({num(sub['CBRofK'], 1)} % CBR)", "Chandler Fig 1"),
        calcpad.row("Flexural tensile strength", "f'ct.f", f"{num(mat['fcf'], 2)} MPa",
                    escape(FLEXURAL_METHODS[mat["fmethod"]])),
        calcpad.row("Radius of relative stiffness", "l = [E h^3 / (12 (1 - mu^2) K)]^0.25",
                    f"{num(mat['l'], 0)} mm", "Westergaard"),
        calcpad.row("Point under consideration", "Position",
                    escape(result["inputs"]["position"])),
        calcpad.row("Rack post load", "RPL = levels x pallet mass x g",
                    f"{num(rack['RPL'], 1)} kN"),
        calcpad.row("Wheel load", "WPL = axle load / wheels",
                    f"{num(wheels['WPL'], 3)} t ({num(wheels['WPL'] * 10, 1)} kN)"),
        calcpad.row("Floor uniform load", "q", f"{num(uniform['UDL'], 1)} kPa"),
    ]
    for key, label, expression, reference in CHECK_ROWS:
        if key in result["util"]:
            rows.append(calcpad.row(label, expression, calcpad.badge(result["util"][key]),
                                    reference))
    rows.append(calcpad.row("Governing", "Maximum utilisation", calcpad.badge(result["worstUtil"])))
    return calcpad.table("Design Summary", rows)


def _inputs(inputs: dict[str, Any]) -> list[str]:
    groups = [
        ("Concrete and Slab", [
            ("Concrete strength f'c", "fc", "MPa"), ("Slab thickness", "h", "mm"),
            ("Concrete density", "density", "kg/m3"), ("Use fcmi for Ec", "useFcmi", ""),
            ("Flexural strength method", "fmethod", ""),
            *([("Manual flexural strength", "fcfo", "MPa")]
              if str(inputs.get("fmethod", "")).upper() == "O" else []),
            ("Poisson's ratio", "u", ""), ("Point under consideration", "whereinput", ""),
            ("Load transfer at joint", "Transfer", ""),
            ("Reduce distances by loaded radius", "consider", ""),
            ("Include negative chart values", "Includeneg", ""),
            ("Check load overlap at", "overlapwhere", "")]),
        ("Subgrade", [
            ("Modulus of subgrade reaction", "K", "kPa/mm"), ("CBR for conversion", "CBRValue", "%"),
            ("K for conversion", "MSRValue", "kPa/mm"), ("Bound sub-base thickness", "bt", "mm"),
            ("Use T48 2009 charts", "T48_2009", "")]),
        ("Rack Loading", [
            ("Above ground rack levels", "PRNo", ""), ("Rack pallet weight", "PRwt", "kg"),
            ("Ground pallet weight", "PGwt", "kg"), ("Pallet side length", "PRl", "mm"),
            ("Pallet side width", "PRe", "mm"), ("Aisle width", "Isle", "mm"),
            ("Foot length", "Fl", "mm"), ("Foot width", "Fw", "mm"),
            ("Material factor Rk1", "Rk1", ""), ("Repetition factor Rk2", "Rk2", ""),
            ("Standard Dexian racking", "Dexian", ""), ("Distance A - B", "dAB", "mm"),
            ("Distance A - E", "dAE", "mm"), ("Distance B - C", "dBC", "mm")]),
        ("Wheel Loading", [
            ("Vehicle description", "Fork", ""), ("Maximum single axle load", "AxleP", "t"),
            ("Wheels per axle", "WheelsPerAxle", ""),
            ("Wheel pair spacing", "WheelPairCentres", "mm"),
            ("Distance between wheels", "Wcts", "mm"), ("Distance between axles", "Bogie", "mm"),
            ("Tyre pressure", "Pr", "kPa"), ("Material factor Wk1", "Wk1", ""),
            ("Design life", "Life", "years"), ("Daily cycles", "Reps", ""),
            ("Warn when loaded areas overlap", "showDistWarning", "")]),
        ("Uniform Floor Loading", [
            ("Number of pallets on the floor", "PFno", ""), ("Ground pallet weight", "PFwt", "kg"),
            ("Pallet side length", "PFl", "mm"), ("Pallet end length", "PFe", "mm"),
            ("Aisle width", "IsleUDL", "mm"), ("Material factor Uk1", "Uk1", ""),
            ("Repetition factor Uk2", "Uk2", ""), ("Use a factor of safety", "useFOS", ""),
            ("Factor of safety", "fos", "")]),
        ("Shrinkage Reinforcement", [
            ("Length between untied joints", "cjlen", "mm"), ("Subgrade drag coefficient", "dragu", ""),
            ("Steel yield strength", "fsy", "MPa"), ("Method", "reom", "")]),
    ]
    checks = inputs.get("checks") or {}
    if checks.get("custom"):
        groups.append(("Custom Point Load", [
            ("Point G load", "CPL", "kN"), ("Foot length", "CFl", "mm"), ("Foot width", "CFw", "mm"),
            ("Loading type", "ltype", ""), ("Design life", "CLife", "years"),
            ("Daily cycles", "CReps", ""), ("Adjacent point loads", "customLoads", "")]))
    if checks.get("location"):
        groups.append(("Load Position", [
            ("Load centre to nearest edge or joint", "edgeDistX", "mm"),
            ("Load centre to second edge or joint", "edgeDistY", "mm")]))
    return [calcpad.matrix(f"Design Inputs - {title}",
                           [(label, key, inputs.get(key, ""), unit) for label, key, unit in fields
                            if str(inputs.get(key, "")).strip() != ""])
            for title, fields in groups]


# ---------------------------------------------------------------------------
#  Drawings
# ---------------------------------------------------------------------------
def _text(x: float, y: float, value: str, *, size: float = 2.6, anchor: str = "middle",
          colour: str = "#111", rotate: bool = False, weight: str = "normal") -> str:
    spin = f' transform="rotate(-90 {x:.2f} {y:.2f})"' if rotate else ""
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" text-anchor="{anchor}" '
            f'font-weight="{weight}" fill="{colour}"{spin}>{escape(value)}</text>')


def _dimension(x1: float, y1: float, x2: float, y2: float, label: str, *,
               offset: float = 1.2, vertical: bool = False) -> str:
    line = (f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="#111" '
            'stroke-width="0.2" marker-start="url(#pvArrow)" marker-end="url(#pvArrow)"/>')
    if vertical:
        return line + _text(x1 + offset + 1.0, (y1 + y2) / 2 + 0.9, label, anchor="start")
    return line + _text((x1 + x2) / 2, y1 - offset, label)


ARROW_DEFS = ('<marker id="pvArrow" markerWidth="4" markerHeight="4" refX="2" refY="2" '
              'orient="auto-start-reverse"><path d="M0,0.8 L4,2 L0,3.2 Z" fill="#111"/></marker>')


def section_drawing(result: dict[str, Any]) -> str:
    """Scaled section through the pavement: slab, sub-base and subgrade under the loads."""
    mat, sub, rack, wheels = result["material"], result["subgrade"], result["racking"], result["wheels"]
    h, bt, l = mat["h"], sub["bt"], mat["l"]
    width = 128.0
    left, top = 10.0, 16.0
    body = 100.0
    span = max(2.4 * l + 800.0, 2000.0)
    scale = body / span
    slab_h = max(h * scale, 3.0)
    sub_h = max(bt * scale, 3.0) if bt else 0.0
    grade_h = 9.0
    base = top + slab_h
    height = base + sub_h + grade_h + 10.0
    parts = [
        '<defs>', ARROW_DEFS,
        '<pattern id="pvSub" width="2" height="2" patternUnits="userSpaceOnUse">'
        '<path d="M0,2 L2,0" stroke="#8d959a" stroke-width="0.2"/></pattern>',
        '<pattern id="pvGrade" width="3" height="3" patternUnits="userSpaceOnUse">'
        '<circle cx="1" cy="1" r="0.35" fill="#a58b62"/><circle cx="2.4" cy="2.2" r="0.25" '
        'fill="#a58b62"/></pattern></defs>',
        f'<rect x="{left}" y="{top}" width="{body}" height="{slab_h:.2f}" fill="#e4e6e3" '
        'stroke="#111" stroke-width="0.45"/>',
    ]
    if sub_h:
        parts.append(f'<rect x="{left}" y="{base:.2f}" width="{body}" height="{sub_h:.2f}" '
                     'fill="url(#pvSub)" stroke="#555" stroke-width="0.25"/>')
    grade_top = base + sub_h
    parts.append(f'<rect x="{left}" y="{grade_top:.2f}" width="{body}" height="{grade_h}" '
                 'fill="url(#pvGrade)" stroke="none"/>')
    parts.append(f'<line x1="{left}" y1="{grade_top:.2f}" x2="{left + body}" y2="{grade_top:.2f}" '
                 'stroke="#555" stroke-width="0.25"/>')
    post_x = left + 0.28 * body
    foot = max(rack["Fl"] * scale, 1.6)
    parts += [
        f'<rect x="{post_x - foot / 2:.2f}" y="{top - 1.0:.2f}" width="{foot:.2f}" height="1.0" '
        'fill="#111"/>',
        f'<rect x="{post_x - 0.6:.2f}" y="{top - 9.0:.2f}" width="1.2" height="8.0" fill="#555"/>',
        _text(post_x, top - 10.5, f"Post {num(rack['RPL'], 1)} kN", size=2.4),
    ]
    wheel_x = left + 0.8 * body
    tyre = 3.2
    parts += [
        f'<circle cx="{wheel_x:.2f}" cy="{top - tyre:.2f}" r="{tyre}" fill="#333"/>',
        f'<circle cx="{wheel_x:.2f}" cy="{top - tyre:.2f}" r="1.2" fill="#bbb"/>',
        _text(wheel_x, top - 2 * tyre - 1.5, f"Wheel {num(wheels['WPL'] * 10, 1)} kN", size=2.4),
    ]
    l_end = post_x + l * scale
    parts += [
        f'<line x1="{post_x:.2f}" y1="{top + slab_h / 2:.2f}" x2="{l_end:.2f}" '
        f'y2="{top + slab_h / 2:.2f}" stroke="#b1257a" stroke-width="0.25" '
        'stroke-dasharray="1.2,0.8" marker-end="url(#pvArrow)"/>',
        _text((post_x + l_end) / 2, top + slab_h / 2 - 0.8, f"l = {num(l, 0)}", size=2.2,
              colour="#b1257a"),
        _dimension(left + body + 3.0, top, left + body + 3.0, base, f"h = {num(h, 0)}",
                   vertical=True),
        _text(left + body - 2.0, top + slab_h / 2 + 0.9,
              f"Concrete slab, f'c = {num(mat['fc'], 0)} MPa", anchor="end", size=2.3),
    ]
    if sub_h:
        cbr_text = (f", equivalent CBR {num(sub['CBRbValue'], 1)} %"
                    if sub["CBRbValue"] is not None else "")
        parts += [_dimension(left + body + 3.0, base, left + body + 3.0, grade_top,
                             f"{num(bt, 0)}", vertical=True),
                  _text(left + 2.0, base + sub_h / 2 + 0.9,
                        f"Bound sub-base {num(bt, 0)} mm{cbr_text}", anchor="start", size=2.3)]
    parts.append(_text(left + 2.0, grade_top + grade_h / 2 + 1.0,
                       f"Subgrade K = {num(mat['K'], 0)} kPa/mm (CBR {num(sub['CBRofK'], 1)} %)",
                       anchor="start", size=2.3))
    parts.append(_text(left + body / 2, height - 2.0,
                       f"Horizontal scale 1:{num(1 / scale, 0)}; slab and sub-base depths drawn "
                       "to the same scale (minimum 3 mm)", size=2.0, colour="#555"))
    return (f'<svg viewBox="0 0 {width:.2f} {height:.2f}" width="{width:.2f}mm" '
            f'height="{height:.2f}mm" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="Pavement section">{"".join(parts)}</svg>')


def _section_figure(result: dict[str, Any]) -> str:
    caption = ("Section through the pavement. The rack post foot and a forklift wheel act on the "
               "top face; l is the radius of relative stiffness used by the Westergaard, Kelley "
               "and Pickett stress formulae.")
    return calcpad.figure("Pavement Section and Subgrade", _grid_block(section_drawing(result)),
                          caption, weight=12)


def plan_drawing(result: dict[str, Any]) -> str:
    """Plan of the rack post layout (points A to L) with a joint panel inset for position."""
    rack, mat = result["racking"], result["material"]
    aisle = rack["aisle"]
    xs = [pos[0] for pos in rack["positions"].values()]
    ys = [pos[1] for pos in rack["positions"].values()]
    x_min, x_max = min(xs) - aisle, max(xs) + aisle
    y_min, y_max = min(ys), max(ys)
    body_w = 86.0
    scale = body_w / (x_max - x_min)
    body_h = (y_max - y_min) * scale
    left, top = 4.0, 8.0

    def sx(value: float) -> float:
        return left + (value - x_min) * scale

    def sy(value: float) -> float:
        return top + (y_max - value) * scale

    parts = ['<defs>', ARROW_DEFS,
             '<pattern id="pvAisle" width="2.5" height="2.5" patternUnits="userSpaceOnUse">'
             '<path d="M0,2.5 L2.5,0" stroke="#c9d3dc" stroke-width="0.3"/></pattern></defs>']
    for x0, x1 in ((x_min, min(xs)), (max(xs), x_max)):
        parts.append(f'<rect x="{sx(x0):.2f}" y="{sy(y_max) - 2:.2f}" width="{(x1 - x0) * scale:.2f}" '
                     f'height="{body_h + 4:.2f}" fill="url(#pvAisle)" stroke="none"/>')
        parts.append(_text((sx(x0) + sx(x1)) / 2, sy(0) + 1.0, f"Aisle {num(aisle, 0)}", size=2.2,
                           colour="#1c4fa1", rotate=True))
    frames = sorted(set(xs))
    for pair in ((frames[0], frames[1]), (frames[2], frames[3])):
        parts.append(f'<rect x="{sx(pair[0]):.2f}" y="{sy(y_max):.2f}" '
                     f'width="{(pair[1] - pair[0]) * scale:.2f}" height="{body_h:.2f}" '
                     'fill="#f1f2f0" stroke="#8d959a" stroke-width="0.25"/>')
    for x in frames:
        parts.append(f'<line x1="{sx(x):.2f}" y1="{sy(y_max):.2f}" x2="{sx(x):.2f}" '
                     f'y2="{sy(y_min):.2f}" stroke="#555" stroke-width="0.35"/>')
    foot_l, foot_w = max(rack["Fl"] * scale, 1.2), max(rack["Fw"] * scale, 0.8)
    g_x, g_y = sx(0.0), sy(0.0)
    radius_l = mat["l"] * scale
    parts.append(f'<circle cx="{g_x:.2f}" cy="{g_y:.2f}" r="{radius_l:.2f}" fill="none" '
                 'stroke="#b1257a" stroke-width="0.25" stroke-dasharray="1,0.7"/>')
    for name, (x, y) in rack["positions"].items():
        colour = "#c0392b" if name == "G" else "#111"
        parts.append(f'<rect x="{sx(x) - foot_w / 2:.2f}" y="{sy(y) - foot_l / 2:.2f}" '
                     f'width="{foot_w:.2f}" height="{foot_l:.2f}" fill="{colour}"/>')
        parts.append(_text(sx(x) + 1.6, sy(y) - 1.4, name, size=2.4, anchor="start",
                           colour=colour, weight="bold" if name == "G" else "normal"))
    parts.append(_text(g_x + radius_l * 0.72, g_y + radius_l * 0.72 + 2.4, "l", size=2.4,
                       colour="#b1257a"))
    dim_y = sy(y_min) + 5.0
    e_x, h_x = sx(-(rack["dAB"] + rack["dBC"])), sx(rack["dAB"])
    parts += [
        _dimension(e_x, dim_y, sx(-rack["dBC"]), dim_y, num(rack["dAB"], 0)),
        _dimension(sx(-rack["dBC"]), dim_y, g_x, dim_y, num(rack["dBC"], 0)),
        _dimension(g_x, dim_y, h_x, dim_y, num(rack["dAB"], 0)),
        _dimension(sx(x_max) - 2.0, sy(rack["dAE"]), sx(x_max) - 2.0, g_y,
                   num(rack["dAE"], 0), vertical=True, offset=-5.0),
    ]
    # Joint panel inset showing the internal, edge and corner positions.
    inset_x, inset_y, inset = left + body_w + 8.0, top + 4.0, 26.0
    where = result["inputs"]["where"]
    parts += [
        f'<rect x="{inset_x:.2f}" y="{inset_y:.2f}" width="{inset}" height="{inset}" '
        'fill="#f1f2f0" stroke="#111" stroke-width="0.45"/>',
        f'<line x1="{inset_x + inset / 2:.2f}" y1="{inset_y:.2f}" x2="{inset_x + inset / 2:.2f}" '
        f'y2="{inset_y + inset:.2f}" stroke="#555" stroke-width="0.25" stroke-dasharray="1.5,0.8"/>',
        f'<line x1="{inset_x:.2f}" y1="{inset_y + inset / 2:.2f}" x2="{inset_x + inset:.2f}" '
        f'y2="{inset_y + inset / 2:.2f}" stroke="#555" stroke-width="0.25" stroke-dasharray="1.5,0.8"/>',
        _text(inset_x + inset / 2, inset_y - 2.0, "Joint panel", size=2.4),
    ]
    markers = {"I": (inset_x + inset * 0.25, inset_y + inset * 0.25),
               "E": (inset_x + inset * 0.25, inset_y + inset - 1.8),
               "C": (inset_x + inset - 1.8, inset_y + inset - 1.8)}
    for key, (x, y) in markers.items():
        chosen = key == where
        parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{1.6 if chosen else 1.1}" '
                     f'fill="{"#c0392b" if chosen else "#fff"}" stroke="#111" stroke-width="0.25"/>')
        parts.append(_text(x, y - 2.2 if key != "I" else y + 4.0, POSITIONS[key], size=2.2,
                           weight="bold" if chosen else "normal"))
    parts.append(_text(inset_x + inset / 2, inset_y + inset + 4.5, "Dashed: sawn joints",
                       size=2.0, colour="#555"))
    width = inset_x + inset + 4.0
    height = max(sy(y_min) + 9.0, inset_y + inset + 8.0)
    return (f'<svg viewBox="0 0 {width:.2f} {height:.2f}" width="{width:.2f}mm" '
            f'height="{height:.2f}mm" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="Rack post layout">{"".join(parts)}</svg>')


def _plan_figure(result: dict[str, Any]) -> str:
    rack = result["racking"]
    caption = (f"{'Standard Dexian' if rack['dexian'] else 'Custom'} back-to-back rack layout in "
               f"plan. Post G (red) is the point under consideration; A to L are the adjacent "
               f"posts and the dashed circle is the radius of relative stiffness. The inset marks "
               f"the {result['inputs']['position'].lower()} position used for the stresses.")
    return calcpad.figure("Rack Post Layout and Load Position", _grid_block(plan_drawing(result)),
                          caption, weight=25)


def wheel_drawing(result: dict[str, Any]) -> str:
    wheels, mat = result["wheels"], result["material"]
    positions = wheels["positions"]
    xs = [pos[0] for pos in positions.values()]
    ys = [pos[1] for pos in positions.values()]
    span_x = max(max(xs) - min(xs), 1.0)
    body_w = 80.0
    scale = body_w / span_x
    left, top = 16.0, 9.0
    body_h = (max(ys) - min(ys)) * scale

    def sx(value: float) -> float:
        return left + (value - min(xs)) * scale

    def sy(value: float) -> float:
        return top + (value - min(ys)) * scale

    radius = max(wheels["WRadius"] * scale, 1.0)
    parts = ['<defs>', ARROW_DEFS, '</defs>']
    for y in sorted(set(ys)):
        parts.append(f'<line x1="{sx(min(xs)):.2f}" y1="{sy(y):.2f}" x2="{sx(max(xs)):.2f}" '
                     f'y2="{sy(y):.2f}" stroke="#555" stroke-width="0.6"/>')
    l_end = sx(0) + mat["l"] * scale
    parts += [f'<line x1="{sx(0):.2f}" y1="{sy(0) + radius + 1.5:.2f}" x2="{l_end:.2f}" '
              f'y2="{sy(0) + radius + 1.5:.2f}" stroke="#b1257a" stroke-width="0.25" '
              'stroke-dasharray="1,0.7" marker-end="url(#pvArrow)"/>',
              _text((sx(0) + l_end) / 2, sy(0) + radius + 4.2, f"l = {num(mat['l'], 0)}",
                    size=2.2, colour="#b1257a")]
    for name, (x, y) in positions.items():
        colour = "#c0392b" if name == "B" else "#111"
        parts.append(f'<circle cx="{sx(x):.2f}" cy="{sy(y):.2f}" r="{radius:.2f}" fill="{colour}"/>')
        parts.append(_text(sx(x), sy(y) - radius - 1.2, name, size=2.4, colour=colour))
    dim_y = sy(max(ys)) + radius + 9.0
    parts.append(_dimension(sx(0), dim_y, sx(wheels["Wcts"]), dim_y,
                            f"w = {num(wheels['Wcts'], 0)}"))
    if wheels["WheelsPerAxle"] > 2:
        parts.append(_dimension(sx(-wheels["WheelPairCentres"]), dim_y + 5.0, sx(0), dim_y + 5.0,
                                f"y = {num(wheels['WheelPairCentres'], 0)}"))
    if wheels["Bogie"]:
        parts.append(_dimension(left - 6.0, sy(0), left - 6.0, sy(wheels["Bogie"]),
                                num(wheels["Bogie"], 0), vertical=True, offset=-9.0))
    width = left + body_w + 12.0
    height = dim_y + (10.0 if wheels["WheelsPerAxle"] > 2 else 5.0)
    return (f'<svg viewBox="0 0 {width:.2f} {height:.2f}" width="{width:.2f}mm" '
            f'height="{height:.2f}mm" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="Wheel layout">{"".join(parts)}</svg>')


def _wheel_figure(result: dict[str, Any]) -> str:
    wheels = result["wheels"]
    axles = "dual axle" if wheels["Bogie"] else "single axle"
    caption = (f"{wheels['Fork'] or 'Vehicle'}, {axles}, {wheels['WheelsPerAxle']} wheels per axle, "
               f"contact radius {num(wheels['WRadius'], 0)} mm drawn to scale. Wheel B (red) is "
               "the point under consideration.")
    rows = 12 if wheels["Bogie"] or wheels["WheelsPerAxle"] > 2 else 8
    return calcpad.figure("Wheel Layout", _grid_block(wheel_drawing(result)), caption, weight=rows)


# ---------------------------------------------------------------------------
#  Check tables
# ---------------------------------------------------------------------------
def _material(result: dict[str, Any]) -> str:
    mat, values = result["material"], result["inputs"]
    fcmi_basis = ("fcmi = -0.0015 f'c^2 + 1.1392 f'c + 0.3481" if mat["useFcmi"]
                  else "fcmi taken as f'c")
    ec_basis = ("Ec = rho^1.5 (0.043 sqrt(fcmi))" if mat["fcmi"] <= 40
                else "Ec = rho^1.5 (0.024 sqrt(fcmi) + 0.12)")
    rows = [
        calcpad.row("Concrete strength", "f'c", f"{num(mat['fc'], 0)} MPa", "AS 3600 Cl 1.1.2"),
        calcpad.row("Mean in-situ strength", fcmi_basis, f"{num(mat['fcmi'], 2)} MPa",
                    "AS 3600 Table 3.1.2"),
        calcpad.row("Modulus of elasticity", ec_basis, f"{num(mat['E'], 0)} MPa +/- 20%",
                    "AS 3600 Cl 3.1.2"),
        calcpad.row("Flexural strength, C&amp;CA", "0.438 f'c^(2/3)", f"{num(mat['fcfCCA'], 3)} MPa",
                    "C&amp;CA Figure 4"),
        calcpad.row("Flexural strength, T48 (display)", "0.7 sqrt(1.1 f'c)",
                    f"{num(mat['fcfT48'], 3)} MPa", "T48 Cl 3.3.6"),
        calcpad.row("Flexural strength, AS 3600", "0.6 sqrt(f'c)", f"{num(mat['fcfAS'], 3)} MPa",
                    "AS 3600 Cl 3.1.1.3"),
        calcpad.row("Adopted 90 day flexural strength", mat["fmethodLabel"],
                    f"<b>{num(mat['fcf'], 3)} MPa</b>", f"Method {mat['fmethod']}"),
        calcpad.row("Section modulus", "Z = h^2 b / 6", f"{num(mat['Z'], 0)} mm3/m"),
        calcpad.row("Poisson's ratio", "mu", num(mat["u"], 2)),
        calcpad.row("Radius of relative stiffness", "l = [E h^3 / (12 (1 - mu^2) K)]^0.25",
                    f"{num(mat['l'], 1)} mm", "Westergaard"),
        calcpad.row("Joint load transfer multipliers", "Te / Tc",
                    f"{num(values['Te'], 2)} / {num(values['Tc'], 2)}",
                    "Chandler" if values["transfer"] else "No transfer"),
    ]
    return calcpad.table("Material Properties - AS 3600 Section 3 and T48 Cl 3.3.6", rows)


def _subgrade(result: dict[str, Any]) -> str:
    sub = result["subgrade"]
    rows = [
        calcpad.row("Design modulus of subgrade reaction", "K", f"{num(sub['K'], 1)} kPa/mm"),
        calcpad.row("Equivalent CBR", "CBR = exp[(K - 0.7047) / 23.372]",
                    f"{num(sub['CBRofK'], 2)} %", "Chandler Fig 1 fit"),
        calcpad.row("Recommended nominal sub-base", "200 if CBR <= 2; 100 if CBR >= 10",
                    f"{num(sub['nominalSubbase'], 0)} mm", escape(sub["subbaseRef"])),
        calcpad.row("Conversion, CBR to K", "K = 23.372 ln(CBR) + 0.7047",
                    f"CBR {num(sub['CBRValue'], 1)} % : {num(sub['MSRofCBR'], 2)} kPa/mm",
                    "Valid 2 to 30 %"),
        calcpad.row("Conversion, K to CBR", "CBR = exp[(K - 0.7047) / 23.372]",
                    f"K {num(sub['MSRValue'], 1)} : {num(sub['CBRofMSR'], 2)} %"),
    ]
    if sub["CBRbValue"] is None:
        rows.append(calcpad.row("Bound sub-base", "bt = 0", "Not applicable"))
    else:
        rows += [
            calcpad.row("Subgrade CBR for sub-base chart", "min(12, CBR)", f"{num(sub['CBRb'], 1)} %"),
            calcpad.row(f"Equivalent design CBR, {num(sub['bt'], 0)} mm bound sub-base",
                        "chart fit, 35 % maximum", f"{num(sub['CBRbValue'], 2)} %",
                        escape(sub["boundRef"])),
            calcpad.row("Equivalent K on the bound sub-base", "K = 23.372 ln(CBR) + 0.7047",
                        f"{num(sub['Kbound'], 1)} kPa/mm", "Information only"),
        ]
    return calcpad.table("Subgrade and Sub-base - T48 Table 1.5 and Figure 1.26", rows)


def _abrasion(result: dict[str, Any]) -> str:
    mat = result["material"]
    rows = [calcpad.row("Exposure classification", "by f'c", escape(mat["exposure"]), "T48"),
            calcpad.row("Abrasion resistance", "by f'c", escape(mat["abrasion"]), "T48")]
    if mat["abrasion2"]:
        rows.append(calcpad.row("Abrasion, also suitable for", "by f'c", escape(mat["abrasion2"]),
                                "T48"))
    rows.append(calcpad.row("Minimum grade", "25 MPa / f'c",
                            calcpad.badge(result["util"]["abrasionGrade"]), "Unsuitable below 25"))
    return calcpad.table("Concrete Abrasion and Exposure - T48 Tables 1.6 and 1.7", rows)


def _bearing(result: dict[str, Any]) -> str:
    rack = result["racking"]
    rows = [
        calcpad.row("Working post load", "RPL = levels x pallet mass x 10 / 1000",
                    f"{num(rack['RPL'], 2)} kN"),
        calcpad.row("Ultimate post load", "V* = 1.5 RPL", f"{num(rack['VPstar'], 2)} kN",
                    "AS/NZS 1170.0"),
        calcpad.row("Foot area", "Fa = Fl Fw", f"{num(rack['Fa'], 0)} mm2"),
        calcpad.row("Ultimate bearing stress", "V* / Fa", f"{num(rack['bearings'], 3)} MPa"),
        calcpad.row("Capacity reduction factor", "phi", num(rack["phib"], 2), "AS 3600 Table 2.2.2"),
        calcpad.row("Bearing capacity", "phi 0.9 f'c", f"{num(rack['allowbs'], 2)} MPa",
                    "AS 3600 Cl 12.6"),
        calcpad.row("Bearing check", "(V* / Fa) / (phi 0.9 f'c)",
                    calcpad.badge(result["util"]["rackBearing"])),
    ]
    return calcpad.table("Rack Post Bearing - AS 3600 Cl 12.6", rows)


def _punching(result: dict[str, Any]) -> str:
    rack, where = result["racking"], result["inputs"]["where"]
    perimeter = {"I": "u = 2 (Fw + dom) + 2 (Fl + dom)",
                 "C": "u = (Fw + dom / 2) + (Fl + dom / 2)",
                 "E": "u = 2 (min(Fw, Fl) + dom / 2) + (max(Fw, Fl) + dom)"}[where]
    rows = [
        calcpad.row("Effective depth", "dom = 0.9 h", f"{num(rack['dom'], 1)} mm", "T48 Cl 3.3.8.6"),
        calcpad.row(f"Critical perimeter, {POSITIONS[where].lower()}", perimeter,
                    f"{num(rack['uu'], 0)} mm", "AS 3600 Cl 9.3.1.3"),
        calcpad.row("Loaded area aspect", "betah = max(Fl, Fw) / min(Fl, Fw)", num(rack["bh"], 3),
                    "AS 3600 Cl 9.3.1.4"),
        calcpad.row("Shear strength limit", "fcv.max = 0.34 sqrt(f'c)", f"{num(rack['maxfcv'], 3)} MPa"),
        calcpad.row("Shear strength, aspect", "fcv1 = 0.17 (1 + 2 / betah) sqrt(f'c)",
                    f"{num(rack['fcv1'], 3)} MPa"),
        calcpad.row("Concrete shear strength", "fcv = min(fcv1, fcv.max)",
                    f"{num(rack['fcv'], 3)} MPa", "AS 3600 Cl 9.3.3"),
        calcpad.row("Capacity reduction factor", "phi", num(rack["phiv"], 2), "AS 3600 Table 2.2.2"),
        calcpad.row("Punching capacity", "phiVuo = phi u dom fcv", f"{num(rack['fVu'], 1)} kN",
                    "AS 3600 Eq 9.3.3(1)"),
        calcpad.row("Punching check", "V* / phiVuo", calcpad.badge(result["util"]["rackPunching"])),
    ]
    return calcpad.table("Rack Post Punching Shear - AS 3600 Cl 9.3.3", rows)


def _point_rows(radius: float, b: float, internal: float, edge: float, corner: float,
                load_t: float, stresses: tuple[float, float, float], radius_eq: str) -> list[str]:
    return [
        calcpad.row("Radius of loaded area", radius_eq, f"{num(radius, 2)} mm"),
        calcpad.row("Equivalent radius", "b = sqrt(1.6 r^2 + h^2) - 0.675 h for r < 1.72 h",
                    f"{num(b, 2)} mm", "Westergaard"),
        calcpad.row("Internal stress per tonne",
                    "sigma_i = 2.7 (1 + mu) / h^2 [4 log(l / b) + 1.069] 10^3",
                    f"{num(internal, 4)} MPa/t", "Westergaard"),
        calcpad.row("Edge stress per tonne",
                    "sigma_e = 5.19 (1 + 0.54 mu) / h^2 [4 log(l / b) + log(b / 25.4)] 10^3",
                    f"{num(edge, 4)} MPa/t", "Kelley"),
        calcpad.row("Corner stress per tonne",
                    "sigma_c = 41.2 / h^2 [1 - sqrt(r / l) / (0.925 + 0.22 r / l)] 10^3",
                    f"{num(corner, 4)} MPa/t", "Pickett"),
        calcpad.row(f"Stresses for {num(load_t, 3)} t", "internal / edge / corner",
                    " / ".join(f"{num(value, 3)}" for value in stresses) + " MPa"),
    ]


def _rack_stresses(result: dict[str, Any]) -> str:
    rack = result["racking"]
    rows = _point_rows(rack["RRadius"], rack["Rb"], rack["Internal"], rack["Edge"],
                       rack["Corner"], rack["RPL"] / 10, (rack["Rsi"], rack["Rse"], rack["Rsc"]),
                       "r = sqrt(Fa / pi)")
    if rack["invalid"]:
        rows.append(calcpad.row("Validity", "all stresses per tonne >= 0",
                                calcpad.badge(float("inf")), "Invalid geometry"))
    return calcpad.table("Rack Post Stresses - Chandler (Westergaard, Kelley, Pickett)", rows)


def _increase_grid(title: str, points: list[dict[str, Any]], result: dict[str, Any],
                   loads: bool = False) -> str:
    headers = ["Point", *(["Load (kN)"] if loads else []), "Dist. (mm)", "x / l", "Dir X",
               "Increase X (%)", "Dir Y", "Increase Y (%)"]
    rows = [[escape(item["point"]), *([num(item["load"], 1)] if loads else []),
             num(item["dist"], 0), num(item["x"], 3), item["dirX"], num(item["pctX"], 2),
             item["dirY"], num(item["pctY"], 2)] for item in points]
    curves = "internal" if result["inputs"]["where"] == "I" else "edge"
    note = (f"Chandler stress-increase curves ({curves}) at distance / l; T tangential, R radial, "
            "C the critical of both. Zero beyond 3l (T) or 4l (R).")
    if result["inputs"]["includeNegative"]:
        note += " Negative (relieving) values are included."
    return calcpad.grid(title, headers, rows, note)


def _stress_rows(sx: float, sy: float, totals: tuple[float, float, float], selected: float,
                 factored: float, k_label: str, prefix: str) -> list[str]:
    return [
        calcpad.row("Stress increase from adjacent loads", "sum X / sum Y",
                    f"{num(sx, 2)} / {num(sy, 2)} %"),
        calcpad.row("Total stresses", "sigma (1 + max(sum X, sum Y) / 100), edge Te, corner Tc",
                    " / ".join(num(value, 3) for value in totals) + " MPa"),
        calcpad.row("Stress at the point under consideration",
                    f"sigma_{prefix} = sigma_i, sigma_e or sigma_c by position",
                    f"{num(selected, 3)} MPa"),
        calcpad.row("Factored stress", f"sigma_{prefix}f = sigma_{prefix} / ({k_label})",
                    f"{num(factored, 3)} MPa", "T48 Table 1.16"),
    ]


def _rack_total(result: dict[str, Any]) -> str:
    rack, mat = result["racking"], result["material"]
    moment = rack["moment"]
    rows = [
        calcpad.row("Material and repetition factors", "Rk1 / Rk2",
                    f"{num(rack['Rk1'], 2)} / {num(rack['Rk2'], 2)}", "T48 Cl 3.3.6"),
        *_stress_rows(rack["Rsx"], rack["Rsy"], (rack["Rsit"], rack["Rset"], rack["Rsct"]),
                      rack["Rst"], rack["RackSP"], "Rk1 Rk2", "r"),
        calcpad.row("Ground pallet load", "PGwt g / (PRl PRe)", f"{num(rack['Rudl'], 2)} kPa"),
        calcpad.row("Aisle bending moment", f"M / q at aisle {num(moment['aisle'], 0)}, "
                    f"l = {moment['l']}", f"{num(rack['BM'], 5)} kNm/m per kPa", "Chandler Fig 3"),
        calcpad.row("Uniform load stress", "sigma_u = M q / Z", f"{num(rack['Rsudl'], 3)} MPa"),
        calcpad.row("Factored uniform stress", "sigma_uf = sigma_u / (Uk1 Uk2)",
                    f"{num(rack['RackSU'], 3)} MPa"),
        calcpad.row("Total stress at G", "sigma_rt = sigma_rf + sigma_uf",
                    f"{num(rack['racks'], 3)} MPa"),
        calcpad.row("Limiting stress", "f'ct.f", f"{num(mat['fcf'], 3)} MPa"),
        calcpad.row("Rack flexural check", "sigma_rt / f'ct.f",
                    calcpad.badge(result["util"]["rackFlexure"])),
    ]
    return calcpad.table("Rack Flexural Stress - T48 Cl 3.3.6", rows)


def _wheel_stresses(result: dict[str, Any]) -> str:
    wheels = result["wheels"]
    rows = [
        calcpad.row("Wheel load", "WPL = P / wheels per axle",
                    f"{num(wheels['WPL'], 3)} t", f"{escape(wheels['Fork'])}"),
        *_point_rows(wheels["WRadius"], wheels["Wb"], wheels["WInternal"], wheels["WEdge"],
                     wheels["WCorner"], wheels["WPL"], (wheels["Wsi"], wheels["Wse"], wheels["Wsc"]),
                     "r = 1000 sqrt(WPL 10 / (pi Pr))"),
        calcpad.row("Repetitions in design life", "N = life x daily cycles x 365",
                    num(wheels["Repetitions"], 0)),
        calcpad.row("Load repetition factor", "Wk2 = (11.791 - log N) / 12.136, 0.50 to 0.84",
                    num(wheels["Wk2"], 4), "T48 Table 1.17"),
    ]
    if wheels["invalid"]:
        rows.append(calcpad.row("Validity", "all stresses per tonne >= 0",
                                calcpad.badge(float("inf")), "Invalid geometry"))
    return calcpad.table("Wheel Stresses - Chandler (Westergaard, Kelley, Pickett)", rows)


def _wheel_total(result: dict[str, Any]) -> str:
    wheels = result["wheels"]
    case = wheels[wheels["axleCase"]]
    rows = [
        calcpad.row("Axle arrangement", "Bogie = 0 is a single axle",
                    f"{wheels['axleCase'].title()} axle, {wheels['WheelsPerAxle']} wheels per axle"),
        calcpad.row("Material factor", "Wk1", num(wheels["Wk1"], 2), "T48 Table 1.16"),
        *_stress_rows(case["Wsx"], case["Wsy"], (case["Wsit"], case["Wset"], case["Wsct"]),
                      case["Wst"], case["stress"], "Wk1 Wk2", "w"),
        calcpad.row("Limiting stress", "f'ct.f", f"{num(result['material']['fcf'], 3)} MPa"),
        calcpad.row("Wheel flexural check", "sigma_wf / f'ct.f",
                    calcpad.badge(result["util"]["wheelFlexure"])),
    ]
    return calcpad.table("Wheel Flexural Stress - T48 Table 1.17", rows)


def _uniform_variable(result: dict[str, Any]) -> str:
    uniform = result["uniform"]
    basis = "1 / FOS" if uniform["useFOS"] else "Uk1 Uk2"
    rows = [
        calcpad.row("Uniform floor load", "q = pallets x mass x g / area",
                    f"{num(uniform['UDL'], 2)} kPa"),
        calcpad.row("Reduction", basis, num(uniform["reduction"], 4), "C&amp;CA Cl 5.6.3"),
        calcpad.row("Factored limiting stress", "fca = f'ct.f x reduction",
                    f"{num(uniform['fca'], 3)} MPa"),
        calcpad.row("Allowable uniform load", "W = 0.33 fca sqrt(h K)",
                    f"{num(uniform['UDLall'], 2)} kPa", "C&amp;CA Cl 5.6.3"),
        calcpad.row("Variable layout check", "q / W", calcpad.badge(result["util"]["uniformVariable"])),
    ]
    return calcpad.table("Uniform Load, Variable Storage Layout - C&amp;CA Cl 5.6.3", rows)


def _uniform_patterned(result: dict[str, Any]) -> str:
    uniform, fcf = result["uniform"], result["material"]["fcf"]
    rows = [
        calcpad.row("Characteristic", "lambda = [3 K / (E h^3)]^0.25",
                    f"{num(uniform['lam'] * 1000, 5)} /m"),
        calcpad.row("Critical half aisle", "a = pi / (4 lambda); b = 5 a",
                    f"{num(uniform['udla'], 0)} / {num(uniform['udlb'], 0)} mm"),
        calcpad.row("Critical aisle width", "2 a", f"{num(uniform['criticalAisle'], 0)} mm"),
        calcpad.row("Maximum moment", "Mc = 5.313 q sqrt(E h^3 / 3K)",
                    f"{num(uniform['Mcmax'], 3)} kNm/m"),
        calcpad.row("Stress, critical aisle", "sigma_u = 6 M / h^2 / (Uk1 Uk2)",
                    f"{num(uniform['patc1'], 3)} / {num(uniform['patc'], 3)} MPa"),
        calcpad.row("Critical aisle check", "sigma_uf / f'ct.f",
                    calcpad.badge(result["util"]["uniformCritical"])),
        calcpad.row("Actual half aisle", "a = aisle / 2; b = 5 a",
                    f"{num(uniform['udlai'], 0)} / {num(uniform['udlbi'], 0)} mm"),
        calcpad.row("Moment, actual aisle",
                    "Mc = q / (2 lambda^2) [e^(-lambda a) sin(lambda a) - e^(-lambda b) sin(lambda b)]",
                    f"{num(uniform['Mc'], 3)} kNm/m", "Hetenyi"),
        calcpad.row("Stresses", "sigma_u1 = 6 Mc / h^2; sigma_u2 = 0.031387 q / h^2 sqrt(E h^3 / 3K)",
                    f"{num(uniform['su1'], 3)} / {num(uniform['su2'], 3)} MPa"),
        calcpad.row("Factored stress, actual aisle", "max(sigma_u1, sigma_u2) / (Uk1 Uk2)",
                    f"{num(uniform['pata'], 3)} MPa"),
        calcpad.row("Limiting stress", "f'ct.f", f"{num(fcf, 3)} MPa"),
        calcpad.row("Actual aisle check", "sigma_uf / f'ct.f",
                    calcpad.badge(result["util"]["uniformAisle"])),
    ]
    return calcpad.table("Uniform Load, Patterned Aisle - Hetenyi Beam on Elastic Foundation", rows)


def _custom(result: dict[str, Any]) -> list[str]:
    custom = result["custom"]
    if not custom:
        return []
    rows = [
        calcpad.row("Point G load", "CPL", f"{num(custom['CPL'], 2)} kN"),
        calcpad.row("Loading type", "P post, W wheel",
                    "Wheel" if custom["ltype"] == "W" else "Post"),
        calcpad.row("Foot area", "CFa = CFl CFw", f"{num(custom['CFa'], 0)} mm2"),
        *_point_rows(custom["CRadius"], custom["cb"], custom["CInternal"], custom["Cedge"],
                     custom["Ccorner"], custom["CPL"] / 10,
                     (custom["Csi"], custom["Cse"], custom["Csc"]), "r = sqrt(CFa / pi)"),
        calcpad.row("Factors", "Ck1 / Ck2", f"{num(custom['Ck1'], 2)} / {num(custom['Ck2'], 4)}",
                    "T48 Tables 1.16 and 1.17"),
    ]
    totals = [
        *_stress_rows(custom["Csx"], custom["Csy"], (custom["Csit"], custom["Cset"], custom["Csct"]),
                      custom["Cst"], custom["CStressP"], "Ck1 Ck2", "c"),
        calcpad.row("Aisle bending moment", f"M / q at aisle {num(custom['moment']['aisle'], 0)}",
                    f"{num(custom['CBM'], 5)} kNm/m per kPa", "Chandler Fig 3"),
        calcpad.row("Factored uniform stress", "sigma_uf = M q / Z / (Uk1 Uk2)",
                    f"{num(custom['CstressU'], 3)} MPa"),
        calcpad.row("Total stress at G", "sigma_cf + sigma_uf", f"{num(custom['CStress'], 3)} MPa"),
        calcpad.row("Limiting stress", "f'ct.f", f"{num(result['material']['fcf'], 3)} MPa"),
        calcpad.row("Custom flexural check", "total / f'ct.f",
                    calcpad.badge(result["util"]["customFlexure"])),
    ]
    return [calcpad.table("Custom Point Load Stresses - Chandler", rows),
            _grid_block(_increase_grid("Adjacent Custom Load Stress Increases - Chandler",
                                       custom["points"], result, loads=True)),
            calcpad.table("Custom Load Flexural Stress - T48 Cl 3.3.6", totals)]


def _location(result: dict[str, Any]) -> str:
    data = result["location"]
    if not data:
        return ""
    where = result["inputs"]["where"]
    rows = [
        calcpad.row("Distances to edges or joints", "x / y",
                    f"{num(data['edgeDistX'], 0)} / {num(data['edgeDistY'], 0)} mm"),
        calcpad.row(f"Largest contact radius ({escape(data['load'])})", "a", f"{num(data['a'], 1)} mm"),
        calcpad.row("Clear distance for interior behaviour", "a + l", f"{num(data['required'], 0)} mm",
                    "Westergaard; Tedds"),
        calcpad.row("Classified position", "internal if min(x, y) >= a + l; edge if max(x, y) >= a + l",
                    POSITIONS[data["classified"]]),
        calcpad.row("Selected position", "whereinput", POSITIONS[where]),
        calcpad.row("Position applicability", {"I": "(a + l) / min(x, y)", "E": "(a + l) / max(x, y)",
                                               "C": "corner always applicable"}[where],
                    calcpad.badge(result["util"]["positionApplicability"])),
    ]
    return calcpad.table("Load Position Applicability - Generic, after Tedds", rows)


def _reinforcement(result: dict[str, Any]) -> str:
    reo = result["reinforcement"]
    thickness = "250 mm to each face" if reo["perFace250"] else "h"
    rows = [
        calcpad.row("AS 3600 unrestrained shrinkage", f"1.75 b ({thickness}) 10^-3",
                    f"{num(reo['Ast3600'], 1)} mm2/m - {escape(reo['reo1'])}", "AS 3600 Cl 9.4.3"),
        calcpad.row("T48 minimum", "0.0014 h b", f"{num(reo['AstMin'], 1)} mm2/m - {escape(reo['reo3'])}",
                    "T48 Appendix F"),
        calcpad.row("T48 subgrade drag", "rho g mu h L / 2 / (0.67 fsy)",
                    f"{num(reo['AstT48'], 1)} mm2/m - {escape(reo['reo4'])}", "T48 Appendix F"),
        calcpad.row("Austroads subgrade drag", "mu L / 2 rho g h / (0.6 fsy)",
                    f"{num(reo['AstAustroads'], 1)} mm2/m - {escape(reo['reo5'])}",
                    "Austroads Sec 9.5.3"),
        calcpad.row("Maximum of all methods", "max", f"{num(reo['AstMax'], 1)} mm2/m - {escape(reo['reo2'])}"),
        calcpad.row("Reinforcement for the selected method", reo["methodLabel"],
                    f"<b>{escape(reo['ReoDesc'])}</b>", "Grade 500 mesh areas"),
    ]
    return calcpad.table("Shrinkage Reinforcement - AS 3600, T48 Appendix F and Austroads", rows)


def _basis(result: dict[str, Any]) -> str:
    def items(values: list[str]) -> str:
        return "<ul>" + "".join(f"<li>{escape(value)}</li>" for value in values) + "</ul>"

    body = ("<h3>Assumptions</h3>" + items(result["assumptions"])
            + "<h3>Limitations and exclusions</h3>" + items(result["limitations"]))
    if result["warnings"]:
        body += "<h3>Warnings</h3>" + items(result["warnings"])
    weight = 6 + 2 * (len(result["assumptions"]) + len(result["limitations"])
                      + len(result["warnings"]))
    return calcpad.prose("Design Basis, Assumptions and Limitations", _grid_block(body),
                         weight=weight)
