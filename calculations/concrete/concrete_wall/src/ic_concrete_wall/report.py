"""Calculation-pad presentation for the concrete wall module, in the column-module layout.

Only formatting happens here; every engineering value comes from
:func:`ic_concrete_wall.engine.compute`.
"""

from __future__ import annotations

import math
from html import escape
from typing import Any

import calcpad

from .engine import LOAD_TYPES
from .version import VERSION

DATA_ID = "concrete-wall-inputs"
DEFAULT_SUBJECT = "Concrete wall design"
num = calcpad.number

CHECK_ROWS = [
    ("designMethod", "Wall design method applicable", "Cl 11.1, Cl 11.2.1 conditions",
     "Cl 11.1, 11.2.1"),
    ("axial", "Design axial strength", "N* / phiNu", "Cl 11.5.3"),
    ("slenderness", "Slenderness", "(Hwe / tw) / limit", "Cl 11.5.2(c), 11.1(b)"),
    ("singleLayer", "Single layer of reinforcement", "governing single-layer limit",
     "Cl 11.5.2(a), 11.7.3"),
    ("verticalSteel", "Minimum vertical reinforcement", "pwv.min / pwv", "Cl 11.7.1(a)"),
    ("horizontalSteel", "Minimum horizontal reinforcement", "pwh.min / pwh", "Cl 11.7.1(b)"),
    ("verticalSpacing", "Vertical bar spacing", "sv / min(350, 2.5 tw)", "Cl 11.7.3"),
    ("horizontalSpacing", "Horizontal bar spacing", "sh / min(350, 2.5 tw)", "Cl 11.7.3"),
    ("barGap", "Minimum clear gap", "3 db / clear gap", "Cl 11.7.3"),
    ("inPlaneShear", "In-plane shear", "V* / phiVu", "Cl 11.6"),
    ("ductileWall", "Limited ductile wall", "pwv / (16 / fsy), Class N", "Cl 14.6.7"),
    ("fireResistance", "Fire resistance level", "FRL.req / FRL", "Cl 5.7"),
    ("crackControl", "Horizontal crack control", "p.req / pwh", "Cl 11.7.2"),
    ("cover", "Cover for exposure", "c.min / c", "Table 4.10.3.2"),
]


def render(inputs: dict[str, Any], result: dict[str, Any], *, standalone: bool = False,
           appendix: list[str] | None = None, anchor_prefix: str = "",
           contents_href: str = "") -> str:
    blocks = [
        _summary(result),
        *_inputs(inputs),
        _elevation_figure(result),
        _section_figure(result),
        _effective_height(result),
        _actions(result),
        _method(result),
        _axial(result),
        _reinforcement(result),
        _crack_table(result),
        _shear(result),
        _ductile(result),
        _fire(result),
        _durability(result),
        _basis(result),
    ]
    title = (f"{inputs.get('memberType', 'Wall')}-{inputs.get('memberNumber', '')} "
             f"- Concrete Wall Design {VERSION}")
    return calcpad.render(inputs, blocks, standalone=standalone, appendix=appendix,
                          anchor_prefix=anchor_prefix, contents_href=contents_href,
                          default_subject=DEFAULT_SUBJECT, data_id=DATA_ID, title=title)


def _bars(diameter: float, spacing: float, fsy: float) -> str:
    return f"{'N' if fsy == 500 else 'Y'}{num(diameter, 0)}-{num(spacing, 0)}"


def _summary(result: dict[str, Any]) -> str:
    values, heights, loads = result["inputs"], result["effectiveHeight"], result["loads"]
    axial, reo = result["axial"], result["reinforcement"]
    layout = "each face" if reo["layers"] == 2 else "central"
    rows = [
        calcpad.row("Wall", "tw x Hw x Lw, f'c",
                    f"{num(values['tw'], 0)} x {num(values['Hw'], 0)} x {num(values['Lw'], 0)} mm, "
                    f"f'c = {num(values['fc'], 0)} MPa"),
        calcpad.row("Reinforcement", f"{reo['layers']} layer(s), {layout}",
                    f"{_bars(reo['dbv'], reo['sv'], reo['fsy'])} vert., "
                    f"{_bars(reo['dbh'], reo['sh'], reo['fsy'])} horz.", "Cl 11.7"),
        calcpad.row("Effective height", "Hwe = k Hw",
                    f"{num(heights['hwe'], 0)} mm, k = {num(heights['k'], 3)}, "
                    f"Hwe/tw = {num(heights['hweTw'], 2)}", "Cl 11.4"),
        calcpad.row("Design method", result["method"]["text"],
                    escape(result["method"]["reason"]), "Cl 11.1"),
        calcpad.row("Design axial action", "N* incl. in-plane stress",
                    f"{num(axial['demand'], 1)} kN/m", "AS/NZS 1170.0 Cl 4.2.2"),
        calcpad.row("Design axial strength", "phi Nu", f"{num(axial['fNu'], 1)} kN/m",
                    "Cl 11.5.3"),
        calcpad.row("In-plane shear capacity", "phi Vu",
                    f"{num(result['shear']['fVu'], 0)} kN", "Cl 11.6"),
    ]
    if result["fire"]:
        rows.append(calcpad.row("Fire resistance level", "FRL = min(adequacy, insulation)",
                                f"{num(result['fire']['frl'], 0)} min", "Cl 5.7"))
    for key, label, expression, reference in CHECK_ROWS:
        if key in result["util"]:
            rows.append(calcpad.row(label, expression, calcpad.badge(result["util"][key]),
                                    reference))
    rows.append(calcpad.row("Governing", "Maximum utilisation", calcpad.badge(result["worstUtil"])))
    return calcpad.table("Design Summary", rows)


def _inputs(inputs: dict[str, Any]) -> list[str]:
    groups = [
        ("Geometry and Material", [
            ("Concrete strength f'c", "fc", "MPa"), ("Wall thickness", "tw", "mm"),
            ("Wall height", "Hw", "mm"), ("Wall length", "Lw", "mm"),
            ("Cover to outer bars", "cover", "mm"), ("Formwork", "formwork", ""),
            ("Wall braced", "braced", ""), ("Design as wall when slab permitted", "designAsWall", ""),
            ("Limited ductile shear wall", "dwall", "")]),
        ("Effective Height", [
            ("Rotational restraint top and bottom", "rotRestraint", ""),
            ("Sides with intersecting walls", "wallIntersect", ""),
            ("Effective height factor source", "kMode", ""), ("User factor k", "k", ""),
            ("Openings", "openings", ""), ("Area of openings", "Aopen", "m2"),
            ("Total height of openings", "Sopen", "mm")]),
        ("Design Actions", [
            ("Dead load", "Ndl", "kN/m"), ("Live load", "Nll", "kN/m"),
            ("Ultimate earthquake axial load", "Neu", "kN/m"),
            ("Include mid-height self weight", "includeSW", ""), ("Load type", "loadType", ""),
            ("Load eccentricity", "wallecc", "mm"), ("Out-of-plane moment", "Mstar", "kNm/m"),
            ("In-plane moment", "Mstari", "kNm"), ("In-plane shear", "Vstar", "kN"),
            ("Overall height for shear", "H", "mm")]),
        ("Reinforcement", [
            ("Layers", "layers", ""), ("Ductility class", "reoClass", ""),
            ("Yield strength", "fsy", "MPa"), ("Vertical bar size", "dbv", "mm"),
            ("Vertical bar spacing", "sv", "mm"), ("Horizontal bar size", "dbh", "mm"),
            ("Horizontal bar spacing", "sh", "mm"),
            ("Unrestrained against shrinkage", "unrest", "")]),
    ]
    if str(inputs.get("kMode", "")).upper() != "USER":
        groups[1][1].remove(("User factor k", "k", ""))
    if str(inputs.get("openings", "")).upper() != "Y":
        groups[1][1][:] = [item for item in groups[1][1] if item[1] not in ("Aopen", "Sopen")]
    if str(inputs.get("loadType", "")).upper() == "O":
        groups[2][1] += [("Long-term factor (other)", "psiLOther", ""),
                         ("Earthquake factor (other)", "psiEOther", "")]
    checks = inputs.get("checks") or {}
    if checks.get("fire"):
        groups.append(("Fire Resistance", [
            ("Required FRL", "frlRequired", "min"), ("Exposed on one side only", "exposed1side", ""),
            ("Lateral support on one side only", "lat1side", ""),
            ("Top support requires FRL", "frlTop", ""), ("Adopt load level 0.7", "ll07", "")]))
    if checks.get("crackControl"):
        groups.append(("Crack Control", [("Degree of crack control", "crackDegree", "")]))
    if checks.get("durability"):
        groups.append(("Durability", [("Exposure classification", "exposureClass", "")]))
    return [calcpad.matrix(f"Design Inputs - {title}",
                           [(label, key, inputs.get(key, ""), unit) for label, key, unit in fields
                            if str(inputs.get(key, "")).strip() != ""])
            for title, fields in groups]


def _text(x: float, y: float, value: str, *, anchor: str = "middle", size: float = 2.6,
          colour: str = "#111", rotate: bool = False) -> str:
    spin = f' transform="rotate(-90 {x:.2f} {y:.2f})"' if rotate else ""
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" text-anchor="{anchor}" '
            f'fill="{colour}"{spin}>{escape(value)}</text>')


def _hatch_band(x: float, y: float, width: float, height: float) -> str:
    """Hatched support band (floor slab or intersecting wall)."""
    parts = [f'<rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="{height:.2f}" '
             'fill="#dcdfdd" stroke="#555" stroke-width="0.2"/>']
    step = 2.0
    offset = 0.0
    while offset < width + height:
        x1, y1 = x + max(0.0, offset - height), y + min(offset, height)
        x2, y2 = x + min(offset, width), y + max(0.0, offset - width)
        parts.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                     'stroke="#777" stroke-width="0.15"/>')
        offset += step
    return "".join(parts)


def _dimension(x1: float, y1: float, x2: float, y2: float, label: str, *,
               vertical: bool = False) -> str:
    line = (f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="#111" '
            'stroke-width="0.2" marker-start="url(#cwArrow)" marker-end="url(#cwArrow)"/>')
    if vertical:
        return line + _text(x1 - 1.4, (y1 + y2) / 2, label, rotate=True)
    return line + _text((x1 + x2) / 2, y1 - 1.2, label)


ARROW = ('<defs><marker id="cwArrow" markerWidth="4" markerHeight="4" refX="2" refY="2" '
         'orient="auto"><path d="M0,2 L4,0.8 L4,3.2 Z" fill="#111"/></marker>'
         '<marker id="cwLoad" markerWidth="5" markerHeight="5" refX="4" refY="2.5" '
         'orient="auto"><path d="M0,0.5 L5,2.5 L0,4.5 Z" fill="#b1257a"/></marker></defs>')


def elevation_drawing(result: dict[str, Any], target: float = 62.0) -> str:
    """Front elevation with lateral supports and side section with the eccentric load."""
    values, heights, loads = result["inputs"], result["effectiveHeight"], result["loads"]
    Hw, Lw, tw = values["Hw"], values["Lw"], values["tw"]
    scale = min(target / Hw, 58.0 / Lw)
    body_w, body_h = Lw * scale, Hw * scale
    left, top = 14.0, 20.0
    band = 3.2
    parts = [ARROW]
    # Front elevation.
    parts.append(_hatch_band(left - band, top - band, body_w + 2 * band, band))
    parts.append(_hatch_band(left - band, top + body_h, body_w + 2 * band, band))
    if heights["sides"] >= 1:
        parts.append(_hatch_band(left - band, top, band, body_h))
    if heights["sides"] >= 2:
        parts.append(_hatch_band(left + body_w, top, band, body_h))
    parts.append(f'<rect x="{left:.2f}" y="{top:.2f}" width="{body_w:.2f}" height="{body_h:.2f}" '
                 'fill="#f1f2f0" stroke="#111" stroke-width="0.55"/>')
    parts.append(_text(left + body_w / 2, top + body_h / 2, "Elevation", colour="#555"))
    parts.append(_dimension(left, top + body_h + band + 5.0, left + body_w,
                            top + body_h + band + 5.0, f"Lw = {num(Lw, 0)}"))
    parts.append(_dimension(left - band - 5.0, top, left - band - 5.0, top + body_h,
                            f"Hw = {num(Hw, 0)}", vertical=True))
    # Side section, drawn with an exaggerated thickness.
    sec_w = 12.0
    sx = left + body_w + band + 16.0
    parts.append(_hatch_band(sx - 6.0, top - band, sec_w + 12.0, band))
    parts.append(_hatch_band(sx - 6.0, top + body_h, sec_w + 12.0, band))
    parts.append(f'<rect x="{sx:.2f}" y="{top:.2f}" width="{sec_w:.2f}" height="{body_h:.2f}" '
                 'fill="#f1f2f0" stroke="#111" stroke-width="0.55"/>')
    centre = sx + sec_w / 2
    parts.append(f'<line x1="{centre:.2f}" y1="{top - band - 2:.2f}" x2="{centre:.2f}" '
                 f'y2="{top + body_h + band + 2:.2f}" stroke="#444" stroke-width="0.2" '
                 'stroke-dasharray="3,1,0.6,1"/>')
    # Eccentricity drawn to the exaggerated thickness scale, capped inside the section.
    e_draw = min(sec_w / 2 - 0.8, loads["walle"] / tw * sec_w)
    lx = centre + e_draw
    parts.append(f'<line x1="{lx:.2f}" y1="{top - band - 9:.2f}" x2="{lx:.2f}" '
                 f'y2="{top - band - 0.4:.2f}" stroke="#b1257a" stroke-width="0.5" '
                 'marker-end="url(#cwLoad)"/>')
    parts.append(_text(lx - 1.2, top - band - 9.8, f"N* = {num(loads['Nstard'], 0)} kN/m",
                       anchor="end", colour="#b1257a"))
    parts.append(_text(lx - 1.2, top - band - 6.6, f"e = {num(loads['walle'], 1)} mm",
                       anchor="end", colour="#b1257a"))
    # Restraint markers at the supports.
    restrained = heights["rotation"]
    for y in (top, top + body_h):
        if restrained:
            parts.append(f'<rect x="{sx - 1.2:.2f}" y="{y - 1.2:.2f}" width="{sec_w + 2.4:.2f}" '
                         'height="2.4" fill="none" stroke="#1c4fa1" stroke-width="0.4"/>')
        else:
            parts.append(f'<circle cx="{centre:.2f}" cy="{y:.2f}" r="1.1" fill="#fff" '
                         'stroke="#1c4fa1" stroke-width="0.4"/>')
    # Buckled shape over the effective height.
    bulge = sec_w * 0.9
    parts.append(f'<path d="M{centre:.2f},{top:.2f} Q{centre + bulge:.2f},{top + body_h / 2:.2f} '
                 f'{centre:.2f},{top + body_h:.2f}" fill="none" stroke="#1c4fa1" '
                 'stroke-width="0.3" stroke-dasharray="1.2,0.8"/>')
    parts.append(_text(sx + sec_w + 6.5, top + body_h / 2,
                       f"Hwe = {num(heights['hwe'], 0)} mm (k = {num(heights['k'], 3)})",
                       rotate=True, colour="#1c4fa1"))
    parts.append(_text(centre, top + body_h + band + 5.0, f"tw = {num(tw, 0)}"))
    parts.append(_text(centre, top + body_h + band + 8.2, "Section (not to scale)", size=2.2,
                       colour="#555"))
    width = sx + sec_w + 9.0
    height = top + body_h + band + 11.0
    return (f'<svg viewBox="0 0 {width:.2f} {height:.2f}" width="{width:.2f}mm" '
            f'height="{height:.2f}mm" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="Wall elevation and section">{"".join(parts)}</svg>')


def _elevation_figure(result: dict[str, Any]) -> str:
    heights = result["effectiveHeight"]
    restraint = ("Restrained against rotation top and bottom (blue boxes)" if heights["rotation"]
                 else "Not restrained against rotation (blue circles)")
    sides = {0: "Laterally supported by floors top and bottom only.",
             1: "Laterally supported top, bottom and by an intersecting wall on one side.",
             2: "Laterally supported top, bottom and by intersecting walls on both sides."}
    caption = (f"{sides[heights['sides']]} {restraint}. Hatched bands are the supports. The "
               "axial load is applied at the design eccentricity e; the dashed curve indicates "
               "buckling over the effective height.")
    return calcpad.figure("Wall Elevation, Restraint and Load Eccentricity",
                          elevation_drawing(result), caption, weight=17)


def section_drawing(result: dict[str, Any], target: float = 94.0) -> str:
    """Plan section of the wall with the vertical and horizontal bars to scale."""
    reo, tw = result["reinforcement"], result["inputs"]["tw"]
    sv, dbv, dbh, cover = reo["sv"], reo["dbv"], reo["dbh"], reo["cover"]
    count = 4
    length = count * sv
    scale = target / length
    if tw * scale > 40.0:
        scale = 40.0 / tw
        length = target / scale
        count = max(1, int(length // sv))
    left, top = 14.0, 12.0
    body_w, body_h = length * scale, tw * scale
    parts = [ARROW]
    parts.append(f'<rect x="{left:.2f}" y="{top:.2f}" width="{body_w:.2f}" height="{body_h:.2f}" '
                 'fill="#f1f2f0" stroke="#111" stroke-width="0.55"/>')
    for x in (left, left + body_w):
        parts.append(f'<path d="M{x:.2f},{top - 1.5:.2f} l1.2,{body_h / 2 + 1.5:.2f} '
                     f'l-2.4,0.6 l1.2,{body_h / 2 + 0.9:.2f}" fill="none" stroke="#111" '
                     'stroke-width="0.25"/>')
    if reo["layers"] == 2:
        v_layers = [cover + dbv / 2.0, tw - cover - dbv / 2.0]
        h_layers = [cover + dbv + dbh / 2.0, tw - cover - dbv - dbh / 2.0]
    else:
        v_layers = [tw / 2.0]
        h_layers = [tw / 2.0 - dbv / 2.0 - dbh / 2.0]
    for y in h_layers:
        parts.append(f'<line x1="{left + 1.0:.2f}" y1="{top + y * scale:.2f}" '
                     f'x2="{left + body_w - 1.0:.2f}" y2="{top + y * scale:.2f}" stroke="#8d959a" '
                     f'stroke-width="{max(0.3, dbh * scale):.2f}"/>')
    radius = max(0.45, dbv / 2.0 * scale)
    for y in v_layers:
        for index in range(count):
            x = left + (sv / 2.0 + index * sv) * scale
            parts.append(f'<circle cx="{x:.2f}" cy="{top + y * scale:.2f}" r="{radius:.2f}" '
                         'fill="#111"/>')
    parts.append(_dimension(left - 5.0, top, left - 5.0, top + body_h, f"tw = {num(tw, 0)}",
                            vertical=True))
    x1 = left + sv / 2.0 * scale
    parts.append(_dimension(x1, top - 3.0, x1 + sv * scale, top - 3.0, f"sv = {num(sv, 0)}"))
    fsy = reo["fsy"]
    layout = "each face" if reo["layers"] == 2 else "central"
    parts.append(_text(left + body_w / 2, top + body_h + 5.0,
                       f"Vertical {_bars(dbv, sv, fsy)} {layout}, horizontal "
                       f"{_bars(dbh, reo['sh'], fsy)}, cover {num(cover, 0)} mm"))
    width, height = left + body_w + 8.0, top + body_h + 8.0
    return (f'<svg viewBox="0 0 {width:.2f} {height:.2f}" width="{width:.2f}mm" '
            f'height="{height:.2f}mm" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="Wall section and reinforcement">{"".join(parts)}</svg>')


def _section_figure(result: dict[str, Any]) -> str:
    reo = result["reinforcement"]
    caption = (f"Plan section to scale. Vertical bars are black; horizontal bars are grey and lie "
               f"inside the vertical bars. Axis distance to the vertical bars "
               f"a.s = {num(reo['axis'], 1)} mm. Exposure achieved by the cover: {reo['exposure']}.")
    return calcpad.figure("Wall Section and Reinforcement", section_drawing(result), caption,
                          weight=10)


def _effective_height(result: dict[str, Any]) -> str:
    h = result["effectiveHeight"]
    four = ("k = 1 / (1 + (Hw / L1)^2)" if h["fourSidedFormula"] == "Hw <= L1"
            else "k = L1 / (2 Hw)")
    rows = [
        calcpad.row("One-way buckling, restrained against rotation", "k = 0.75",
                    f"Hwe = {num(h['hwe1'], 0)} mm", "Cl 11.4(a)"),
        calcpad.row("One-way buckling, not restrained", "k = 1.0",
                    f"Hwe = {num(h['hwe2'], 0)} mm", "Cl 11.4(a)"),
        calcpad.row("Three sides supported", "k = 1 / (1 + (Hw / (3 L1))^2) >= 0.3",
                    f"k = {num(h['k3'], 4)}, Hwe = {num(h['hwe3'], 0)} mm", "Cl 11.4(b)"),
        calcpad.row("Four sides supported", f"{four}, {h['fourSidedFormula']}",
                    f"k = {num(h['k4'], 4)}, Hwe = {num(h['hwe4'], 0)} mm", "Cl 11.4(c)"),
        calcpad.row("Calculated factor", h["description"], num(h["kCalc"], 4), "Cl 11.4"),
        calcpad.row("Adopted factor", "calculated" if h["kMode"] == "CALC" else "user value",
                    num(h["k"], 4) + (" (differs from calculated)" if h["kDiffers"] else "")),
        calcpad.row("Effective height", "Hwe = k Hw", f"{num(h['hwe'], 0)} mm", "Cl 11.4"),
        calcpad.row("Slenderness", "Hwe / tw", num(h["hweTw"], 2)),
        calcpad.row("Return wall for lateral support", "0.2 Hw", f"{num(h['returnWall'], 0)} mm",
                    "Cl 11.4"),
    ]
    if h["openings"]:
        rows.append(calcpad.row("Openings", "Ho <= Hw / 3 and Ao <= Aw / 10",
                                f"Ho = {num(h['Sopen'], 0)} mm, Ao = {num(h['Aopen'], 2)} of "
                                f"{num(h['wallArea'], 2)} m2: "
                                + ("may be ignored" if h["openingsOk"] else "exceed limits"),
                                "Cl 11.4"))
    return calcpad.table("Effective Height - Cl 11.4", rows)


def _actions(result: dict[str, Any]) -> str:
    loads = result["loads"]
    sw = (f"{num(loads['swtmid'], 2)} kN/m" if loads["includeSW"]
          else f"{num(loads['swtmid'], 2)} kN/m, excluded")
    rows = [
        calcpad.row("Mid-height self weight", "25 tw Hw / 2", sw),
        calcpad.row("Dead load at mid-height", "G = Ndl + S.wt", f"{num(loads['Ndls'], 2)} kN/m"),
        calcpad.row("Live load", "Q = Nll", f"{num(loads['Nll'], 2)} kN/m"),
        calcpad.row("Load factors", LOAD_TYPES[loads["loadType"]],
                    f"\u03c8l = {num(loads['psiL'], 2)}, \u03c8E = {num(loads['psiE'], 2)}",
                    "AS/NZS 1170.0 Table 4.1"),
        calcpad.row("Strength combination", "N* = max(1.35 G, 1.2 G + 1.5 Q)",
                    f"{num(loads['Nstard1'], 1)} kN/m", f"Cl 4.2.2, {escape(loads['strengthCase'])}"),
        calcpad.row("Earthquake combination", "Ne* = G + Eu + psi_E Q",
                    f"{num(loads['Nstard2'], 1)} kN/m", "Cl 4.2.2(e)"),
        calcpad.row("Design axial load", "N* = max(N*, Ne*)", f"{num(loads['Nstard'], 1)} kN/m",
                    f"governing: {escape(loads['governing'])}"),
        calcpad.row("Fire combination", "Nf* = G + psi_l Q", f"{num(loads['Nstarfd'], 1)} kN/m",
                    "Cl 4.2.4"),
        calcpad.row("Design eccentricity", "e = max(e.input, 0.05 tw)",
                    f"{num(loads['walle'], 1)} mm", "Cl 11.5.4"),
        calcpad.row("Eccentricity moment", "Moe* = N* e", f"{num(loads['Moestar'], 2)} kNm/m"),
        calcpad.row("Stress from N*", "sigma.n = N* / tw", f"{num(loads['smidN'], 3)} MPa"),
        calcpad.row("In-plane stress", "sigma.in = 6 Mi* / (tw Lw^2)",
                    f"+/- {num(loads['smidIn'], 3)} MPa"),
        calcpad.row("Mid-height stress", "sigma.max / sigma.min",
                    f"{num(loads['smidMax'], 3)} / {num(loads['smidMin'], 3)} MPa"),
    ]
    return calcpad.table("Design Actions - AS/NZS 1170.0", rows)


def _method(result: dict[str, Any]) -> str:
    method, loads, heights = result["method"], result["loads"], result["effectiveHeight"]
    slab_met = method["desmode"] == 2
    rows = [
        calcpad.row("Slab limits", "sigma.min > 0, sigma.max <= 0.03 f'c, Hwe/tw <= 50",
                    f"\u03c3.max = {num(loads['smidMax'], 3)} MPa, 0.03 f'c = "
                    f"{num(loads['slabLimit'], 2)} MPa, Hwe/tw = {num(heights['hweTw'], 2)}: "
                    + ("met" if slab_met else "not met"), "Cl 11.1(b)(i)"),
        calcpad.row("Out-of-plane moment", "Mo*", f"{num(loads['Mstar'], 2)} kNm/m", "Cl 11.1(b)"),
        calcpad.row("Wall braced", "Cl 11.3", "Yes" if method["braced"] else "No", "Cl 11.3"),
        calcpad.row("Design mode", method["text"], escape(method["reason"]),
                    "Cl 11.1, 11.2.1"),
        calcpad.row("Method applicability", "applicable = OK",
                    calcpad.badge(result["util"]["designMethod"])),
    ]
    return calcpad.table("Design Method Selection - Cl 11.1 and Cl 11.2.1", rows)


def _axial(result: dict[str, Any]) -> str:
    axial, heights, method = result["axial"], result["effectiveHeight"], result["method"]
    loads, util = result["loads"], result["util"]
    rows = [
        calcpad.row("Capacity reduction factor", "phi", num(axial["phi"], 2), "Cl 11.5.3"),
        calcpad.row("Additional eccentricity", "ea = Hwe^2 / (2500 tw)", f"{num(axial['ae'], 3)} mm",
                    "Cl 11.5.3"),
        calcpad.row("Axial strength", "Nus = (tw - 1.2 e - 2 ea) 0.6 f'c",
                    f"{num(axial['Nus'], 1)} kN/m", "Eq 11.5.3"),
        calcpad.row("Simplified slenderness limit", "Hwe / tw <= 20 (1 layer), 30 (2 layers)",
                    escape(f"{num(heights['hweTw'], 2)} <= {num(method['simpleLimit'], 0)}"),
                    "Cl 11.5.2(c)"),
    ]
    if result["reinforcement"]["layers"] == 1:
        rows.append(calcpad.row("Single layer limit", "3.0 tw", f"{num(axial['fNuMax1'], 0)} kN/m",
                                "Cl 11.5.2(a)"))
    rows.append(calcpad.row("Simplified design strength",
                            "phiNus = min(3 tw, phi Nus)" if result["reinforcement"]["layers"] == 1
                            else "phiNus = phi Nus", f"{num(axial['fNus'], 1)} kN/m", "Cl 11.5.3"))
    if method["desmode"] == 2:
        rows.append(calcpad.row("Slab axial limit", "phiNuo = (0.03 f'c - sigma.in) tw",
                                f"{num(axial['fNuo'], 1)} kN/m", "Cl 11.1(b)(i)"))
    rows += [
        calcpad.row("Design axial strength", "phi Nu", f"{num(axial['fNu'], 1)} kN/m",
                    "slab" if method["approach"] == "slab" else "Cl 11.5.3"),
        calcpad.row("Design axial action", "N* + sigma.in tw" if method["approach"] != "slab"
                    else "N*", f"{num(axial['demand'], 1)} kN/m"),
        calcpad.row("Axial strength check", "N* / phiNu", calcpad.badge(util["axial"]), "Cl 11.5.3"),
        calcpad.row("Slenderness check", f"(Hwe / tw) / {num(axial['slenderLimit'], 0)}",
                    calcpad.badge(util["slenderness"]), "Cl 11.5.2(c)"),
    ]
    for item in result["reinforcement"]["singleRules"]:
        rows.append(calcpad.row(f"Single layer: {escape(item['rule'])}", "ratio",
                                num(item["ratio"], 3), item["clause"]))
    if "singleLayer" in util:
        rows.append(calcpad.row("Single layer check", "governing ratio",
                                calcpad.badge(util["singleLayer"]), "Cl 11.5.2(a), 11.7.3"))
    rows += [
        calcpad.row(f"Height for zero capacity at e = {num(loads['walle'], 0)} mm",
                    "Hwe = sqrt((tw - 1.2 e) 2500 tw / 2)", f"{num(axial['maxHeight'], 0)} mm"),
        calcpad.row(f"Eccentricity for zero capacity at Hwe = {num(heights['hwe'], 0)} mm",
                    "e = (tw - 2 ea) / 1.2", f"{num(axial['maxEcc'], 1)} mm"),
        calcpad.row("Tensile capacity, anchored, no bending", "phiNuot = phi.t fsy Ast",
                    f"{num(axial['fNuot'], 1)} kN/m", f"phi.t = {num(axial['phiT'], 2)}, Table 2.2.2"),
        calcpad.row("Column route bar restraint", "N* / (0.5 phiNu)", num(axial["halfCapacity"], 3),
                    "Cl 11.7.4"),
    ]
    return calcpad.table("Design Axial Strength - Cl 11.5", rows)


def _reinforcement(result: dict[str, Any]) -> str:
    reo, util = result["reinforcement"], result["util"]
    each = " each face" if reo["layers"] == 2 else ""
    rows = [
        calcpad.row("Vertical steel", "Astv = 1000 / sv x pi db^2 / 4",
                    f"{num(reo['Ast'], 1)} mm2/m{each}"),
        calcpad.row("Vertical steel ratio", "pwv = layers Astv / (1000 tw)", num(reo["pwv"], 5)),
        calcpad.row("Minimum vertical ratio",
                    "0.0015 if sigma.max <= min(2, 0.03 f'c), else 0.0025",
                    f"{num(reo['pwmin'], 4)} ({num(reo['AstvMin'], 0)} mm2/m)",
                    "Cl 14.6.7" if result["inputs"]["dwall"] else "Cl 11.7.1(a)"),
        calcpad.row("Vertical steel check", "pwv.min / pwv", calcpad.badge(util["verticalSteel"]),
                    "Cl 11.7.1(a)"),
        calcpad.row("Horizontal steel", "Asth = 1000 / sh x pi db^2 / 4",
                    f"{num(reo['Astc'], 1)} mm2/m{each}"),
        calcpad.row("Horizontal steel ratio", "pwh = layers Asth / (1000 tw)", num(reo["pwh"], 5)),
        calcpad.row("Minimum horizontal ratio",
                    "0.0025; unrestrained one-way: 0 (Lw <= 2500) or 0.0015",
                    f"{num(reo['pwminh'], 4)} ({num(reo['AsthMin'], 0)} mm2/m)", "Cl 11.7.1(b)"),
        calcpad.row("Horizontal steel check", "pwh.min / pwh",
                    calcpad.badge(util["horizontalSteel"]), "Cl 11.7.1(b)"),
        calcpad.row("Crack control achieved", "by pwh", escape(reo["crackText"]), "Cl 11.7.2"),
        calcpad.row("Maximum spacing", "min(350, 2.5 tw)", f"{num(reo['maxSpacing'], 0)} mm",
                    "Cl 11.7.3"),
        calcpad.row("Vertical spacing check", "sv / s.max", calcpad.badge(util["verticalSpacing"]),
                    "Cl 11.7.3"),
        calcpad.row("Horizontal spacing check", "sh / s.max",
                    calcpad.badge(util["horizontalSpacing"]), "Cl 11.7.3"),
        calcpad.row("Clear gaps", "s - db, vertical / horizontal",
                    f"{num(reo['gapV'], 0)} / {num(reo['gapH'], 0)} mm"),
        calcpad.row("Clear gap check", "3 db / gap", calcpad.badge(util["barGap"]), "Cl 11.7.3"),
    ]
    if reo["layers"] == 1:
        rows.append(calcpad.row("Geometric cover, central layer", "vertical / horizontal bars",
                                f"{num(reo['coverV'], 1)} / {num(reo['coverH'], 1)} mm"))
    return calcpad.table("Wall Reinforcement - Cl 11.7", rows)


def _crack_table(result: dict[str, Any]) -> str:
    reo, crack = result["reinforcement"], result["crackControl"]
    rows = [calcpad.row(escape(item["label"]), f"As = {item['p']:g} x 1000 tw",
                        f"{num(item['As'], 0)} mm2/m", "Cl 11.7.2")
            for item in reo["crackTable"]]
    rows.append(calcpad.row("Horizontal steel provided", "pwh / As.h",
                            f"{num(reo['pwh'], 5)} / {num(reo['pwh'] * 1000.0 * result['inputs']['tw'], 0)} "
                            "mm2/m"))
    if crack and "crackControl" in result["util"]:
        rows.append(calcpad.row(f"Selected: {escape(crack['label'])}", "p.req / pwh",
                                calcpad.badge(result["util"]["crackControl"]), "Cl 11.7.2"))
    elif crack:
        rows.append(calcpad.row(f"Selected: {escape(crack['label'])}", "restrained walls only",
                                "not applied, wall unrestrained", "Cl 11.7.2"))
    return calcpad.table("Horizontal Crack Control - Cl 11.7.2", rows)


def _shear(result: dict[str, Any]) -> str:
    s = result["shear"]
    vucb = num(s["Vucb"], 1) + " kN" if s["Vucb"] is not None else "not applicable, H/Lw <= 1"
    rows = [
        calcpad.row("Aspect ratio", "H / Lw", num(s["ratio"], 3)),
        calcpad.row("Capacity reduction factor", "phi", num(s["phi"], 2), "Table 2.2.2"),
        calcpad.row("Maximum strength", "Vu.max = 0.2 f'c (0.8 Lw tw)", f"{num(s['Vumax'], 1)} kN",
                    "Cl 11.6.2"),
        calcpad.row("Minimum concrete strength", "Vuc.min = 0.17 sqrt(f'c) (0.8 Lw tw)",
                    f"{num(s['Vucmin'], 1)} kN", "Cl 11.6.3"),
        calcpad.row("Concrete strength, Eq 1", "(0.66 sqrt(f'c) - 0.21 (H/Lw) sqrt(f'c)) 0.8 Lw tw",
                    f"{num(s['Vuca'], 1)} kN", "Eq 11.6.3(1)"),
        calcpad.row("Concrete strength, Eq 2", "(0.05 sqrt(f'c) + 0.1 sqrt(f'c) / (H/Lw - 1)) 0.8 Lw tw",
                    vucb, "Eq 11.6.3(2)"),
        calcpad.row("Concrete contribution", "Vuc", f"{num(s['Vuc'], 1)} kN", "Cl 11.6.3"),
        calcpad.row("Steel ratio", "pw = min(pwv, pwh) if H/Lw <= 1, else pwh", num(s["pw"], 5),
                    "Cl 11.6.4"),
        calcpad.row("Steel contribution", "Vus = pw fsy (0.8 Lw tw)", f"{num(s['Vus'], 1)} kN",
                    "Cl 11.6.4"),
        calcpad.row("Shear strength", "Vu = min(Vuc + Vus, Vu.max)", f"{num(s['Vu'], 1)} kN",
                    escape(s["governs"])),
        calcpad.row("Design shear strength", "phi Vu", f"{num(s['fVu'], 1)} kN"),
        calcpad.row("Design shear", "V*", f"{num(s['Vstar'], 1)} kN"),
        calcpad.row("In-plane shear check", "V* / phiVu", calcpad.badge(result["util"]["inPlaneShear"]),
                    "Cl 11.6"),
    ]
    return calcpad.table("In-Plane Shear - Cl 11.6", rows)


def _ductile(result: dict[str, Any]) -> str:
    if not result["ductile"]:
        return ""
    reo = result["reinforcement"]
    rows = [
        calcpad.row("Maximum vertical ratio", "pwv.max = 16 / fsy",
                    f"{num(reo['pwmax'], 4)} ({num(reo['AstvMax'], 0)} mm2/m)", "Cl 14.6.7"),
        calcpad.row("Ductility class", "Class N required", "Class " + reo["class"], "Cl 14.6.7"),
        calcpad.row("Limited ductile wall check", "pwv / pwv.max, Class N",
                    calcpad.badge(result["util"]["ductileWall"]), "Cl 14.6.7"),
    ]
    return calcpad.table("Limited Ductile Wall - Cl 14.6", rows)


def _fire(result: dict[str, Any]) -> str:
    f = result["fire"]
    if not f:
        return ""
    side = 1 if f["exposed1side"] else 2
    blended = f["blended1"] if side == 1 else f["blended2"]
    rows = [
        calcpad.row("Load level", "mu.fi = Nf* / phiNu" if not f["ll07"] else "adopted 0.7",
                    f"{num(f['ufi'], 3)} (actual {num(f['ufiActual'], 3)})", "Cl 5.7.2"),
        calcpad.row("Insulation", "Table 5.7.1, interpolated on tw", f"{num(f['insulation'], 1)} min",
                    "Cl 5.7.1"),
        calcpad.row(f"Adequacy, mu.fi 0.35, {side} side(s)", "axis distance / thickness",
                    f"{num(f['tables'][f'35_{side}']['as'], 1)} / "
                    f"{num(f['tables'][f'35_{side}']['t'], 1)} min", "Table 5.7.2"),
        calcpad.row(f"Adequacy, mu.fi 0.70, {side} side(s)", "axis distance / thickness",
                    f"{num(f['tables'][f'70_{side}']['as'], 1)} / "
                    f"{num(f['tables'][f'70_{side}']['t'], 1)} min", "Table 5.7.2"),
        calcpad.row("Interpolated adequacy", "min(a.s, tw) at mu.fi", f"{num(blended['frl'], 1)} min",
                    "Cl 5.3.2"),
        calcpad.row("Effective height limit", f"Hwe <= {num(f['maxHeightFactor'], 0)} tw",
                    f"{num(f['maxHeight'], 0)} mm" + (", exceeded" if f["tooSlender"] else ""),
                    "Cl 5.7.3"),
        calcpad.row("Structural adequacy", "deemed = insulation" if f["deemed"] else "Table 5.7.2",
                    f"{num(f['adequacyAdopted'], 1)} min", "Cl 5.7.2"),
        calcpad.row("Fire resistance level", "FRL = min(adequacy, insulation)",
                    f"{num(f['frl'], 1)} min"),
        calcpad.row("Required", "FRL.req", f"{num(f['required'], 0)} min"),
        calcpad.row("Fire resistance check", "FRL.req / FRL",
                    calcpad.badge(result["util"]["fireResistance"]), "Cl 5.7"),
    ]
    return calcpad.table("Fire Resistance - Cl 5.7", rows)


def _durability(result: dict[str, Any]) -> str:
    d = result["durability"]
    if not d:
        return ""
    reo = result["reinforcement"]
    table = "Table 4.10.3.2" if reo["formwork"] == "S" else "Table 4.10.3.3"
    cmin = f"{num(d['cmin'], 0)} mm" if math.isfinite(d["cmin"]) else "not permitted at this f'c"
    rows = [
        calcpad.row("Required exposure classification", "input", d["exposure"], "Table 4.3"),
        calcpad.row("Minimum cover", "c.min" + (" (bracketed, Cl 4.3.2)" if d["concession"] else ""),
                    cmin, table),
        calcpad.row("Cover provided", "c", f"{num(d['cover'], 0)} mm"),
        calcpad.row("Cover check", "c.min / c", calcpad.badge(result["util"]["cover"]), table),
    ]
    return calcpad.table("Cover for Durability - Section 4", rows)


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
