"""Calculation-pad presentation for the concrete beam and slab module, in the column-module layout.

Only formatting happens here; every engineering value comes from
:func:`ic_concrete_member.engine.compute`.
"""

from __future__ import annotations

import math
from html import escape
from typing import Any

import calcpad

from .common import bar_area
from .engine import CHECK_LABELS
from .section import FLANGED, SLAB
from .version import VERSION

DATA_ID = "concrete-member-inputs"
DEFAULT_SUBJECT = "Concrete beam and slab design"
num = calcpad.number

CHECK_ROWS = [
    ("flexure", "M* / phiMuo", "Cl 8.1"),
    ("ductility", "kuo / 0.36", "Cl 8.1.5"),
    ("minimumSteel", "Ast.min / Ast", "Cl 8.1.6.1"),
    ("barSpacing", "s / s.max", "Cl 8.6.1"),
    ("crackStress", "sigma.scr / sigma.scr.max", "Cl 8.6.2.2"),
    ("crackStressYield", "sigma.scr1 / 0.8 fsy", "Cl 8.6.2.2"),
    ("crackWidth", "w / w'max", "Cl 8.6.2.3"),
    ("shear", "V* / phiVu", "Cl 8.2"),
    ("shearDetailing", "max(s, s.t, Asv.min / Asv)", "Cl 8.3.2.2"),
    ("shearMethod", "max(f'c / 65, fsy / 500, 10 / dg)", "Cl 8.2.4.3"),
    ("torsion", "T* / phiTus", "Cl 8.2.5.6"),
    ("torsionReinforcement", "max(Asw.min / Asw, s / s.max)", "Cl 8.2.5.5"),
    ("webCrushing", "v.comb / (phiVu.max / bv dv)", "Cl 8.2.3.3"),
    ("longitudinalTension", "Ast.req / Ast", "Cl 8.2.8"),
    ("longitudinalCompression", "Asc.req / Asc", "Cl 8.2.8"),
    ("deflectionTotal", "d.min / ds", "Cl 8.5.4"),
    ("deflectionIncremental", "d.min.inc / ds", "Cl 8.5.4"),
    ("liveLoadLimit", "q / g", "Cl 8.5.4"),
    ("deflectionDead", "delta.dl.long / limit", "Cl 8.5.3"),
    ("deflectionLive", "delta.ll.short / limit", "Cl 8.5.3"),
    ("deflectionIncrementalCalc", "delta.inc / limit", "Cl 8.5.3"),
    ("deflectionTotalCalc", "delta.total / limit", "Cl 8.5.3"),
    ("slenderness", "L.restraint / L1", "Cl 8.9"),
    ("secondarySteel", "Ast.min / Ast", "Cl 9.5.3"),
]
SLAB_CLAUSES = {"minimumSteel": "Cl 9.1.1", "barSpacing": "Cl 9.5.1", "crackStress": "Cl 9.5.2.1",
                "crackStressYield": "Cl 9.5.2.1", "crackWidth": "Cl 9.5.2.1",
                "deflectionTotal": "Cl 9.4.4.1", "deflectionIncremental": "Cl 9.4.4.1",
                "liveLoadLimit": "Cl 9.4.4.1"}


def _units(result: dict[str, Any]) -> dict[str, str]:
    slab = result["section"]["section"] == SLAB
    return {"m": "kNm/m" if slab else "kNm", "v": "kN/m" if slab else "kN",
            "a": "mm2/m" if slab else "mm2", "w": "kPa" if slab else "kN/m"}


def _face_text(face: dict[str, Any], slab: bool) -> str:
    if not face["As"]:
        return "none"
    bar = f"N{num(face['bar'], 0)}"
    if face["mode"] == "A":
        return f"{num(face['As'], 0)} mm2 ({bar})"
    if face["mode"] == "S" or slab:
        return f"{bar} at {num(face['centres'], 0)} centres"
    layers = f", {face['layers']} layers" if face["layers"] > 1 else ""
    return f"{num(face['nbars'], 0)} - {bar}{layers}"


def render(inputs: dict[str, Any], result: dict[str, Any], *, standalone: bool = False,
           appendix: list[str] | None = None, anchor_prefix: str = "",
           contents_href: str = "") -> str:
    blocks = [
        _summary(result),
        *_inputs(inputs),
        _section_figure(result),
        _properties(result),
        _material(result),
        *_bending(result),
        _ductility(result),
        _minimum(result),
        _crack(result),
        _creep(result),
        _crack_width(result),
        _shear(result),
        _detailing(result),
        _torsion(result),
        _longitudinal(result),
        _deemed(result),
        *_calculated(result),
        _slenderness(result),
        _secondary(result),
        _basis(result),
        _warnings(result),
    ]
    title = (f"{inputs.get('memberType', 'Beam')}-{inputs.get('memberNumber', '')} "
             f"- Concrete Beam and Slab Design {VERSION}")
    return calcpad.render(inputs, blocks, standalone=standalone, appendix=appendix,
                          anchor_prefix=anchor_prefix, contents_href=contents_href,
                          default_subject=DEFAULT_SUBJECT, data_id=DATA_ID, title=title)


def _summary(result: dict[str, Any]) -> str:
    geom, reo, flex, shr, u = (result["section"], result["reinforcement"], result["flexure"],
                               result["shear"], _units(result))
    slab = geom["section"] == SLAB
    size = (f"{num(geom['D'], 0)} mm thick, 1000 mm strip" if slab
            else f"{num(geom['D'], 0)} x {num(geom['W'], 0)} mm")
    if geom["section"] == FLANGED:
        size += f", bef = {num(geom['bef'], 0)} mm, Tf = {num(geom['Tf'], 0)} mm"
    rows = [
        calcpad.row("Section", escape(geom["label"]),
                    f"{size}, f'c = {num(result['inputs']['fc'], 0)} MPa"),
        calcpad.row("Reinforcement", "bottom / top",
                    f"{escape(_face_text(reo['bottom'], slab))} / {escape(_face_text(reo['top'], slab))}"),
        calcpad.row("Bending", f"M* {'+ve' if flex['Mstar'] >= 0 else '-ve'} / phiMuo",
                    f"{num(abs(flex['Mstar']), 1)} / {num(flex['phiMu'], 1)} {u['m']}", "Cl 8.1"),
        calcpad.row("Shear", "V* / phiVu",
                    f"{num(shr['V'], 1)} / {num(shr['phiVu'], 1)} {u['v']}", "Cl 8.2"),
        calcpad.row("Fitment requirement", "Cl 8.2.1.6", escape(shr["requirement"])),
        calcpad.row("Deemed-to-comply depth", "d.min / d.min.inc against ds",
                    f"{num(result['deemed']['dmin'], 0)} / {num(result['deemed']['dmini'], 0)} "
                    f"against {num(reo['ds'], 0)} mm", result["deemed"]["clause"]),
    ]
    for key, expression, reference in CHECK_ROWS:
        if key in result["util"]:
            if slab:
                reference = SLAB_CLAUSES.get(key, reference)
            rows.append(calcpad.row(CHECK_LABELS[key], expression,
                                    calcpad.badge(result["util"][key]), reference))
    rows.append(calcpad.row("Governing", "Maximum utilisation", calcpad.badge(result["worstUtil"])))
    if result["unattainable"]:
        rows.append(calcpad.row("Unattainable", "Capacity zero or undefined",
                                escape(", ".join(result["unattainable"]))))
    return calcpad.table("Design Summary", rows)


def _inputs(inputs: dict[str, Any]) -> list[str]:
    kind = str(inputs.get("sectionType", "R")).upper()
    geometry = [("Section type", "sectionType", ""), ("Concrete strength f'c", "fc", "MPa"),
                ("Overall depth", "D", "mm")]
    if kind != "S":
        geometry.append(("Web width", "W", "mm"))
    if kind == "F":
        geometry += [("Flange width", "Bf", "mm"), ("Flange thickness", "Tf", "mm"),
                     ("Flanged beam type", "btype", ""), ("Support for a", "supportType", "")]
    geometry.append(("Span", "Lm", "mm"))
    if kind == "S":
        geometry.append(("Slab type", "slabType", ""))
    geometry += [("Concrete density", "density", "kg/m3"), ("Use fcmi", "useFcmi", "")]
    groups = [
        ("Section and Material", geometry),
        ("Reinforcement", [
            ("Bottom bar size", "barBot", "mm"), ("Bottom bars given as", "botMode", ""),
            ("Bottom number, centres or area", "botValue", ""), ("Top bar size", "barTop", "mm"),
            ("Top bars given as", "topMode", ""), ("Top number, centres or area", "topValue", ""),
            ("Yield strength", "fsy", "MPa"), ("Bottom ductility class", "classBot", ""),
            ("Top ductility class", "classTop", ""), ("Bottom cover", "cover", "mm"),
            ("Top cover", "coverTop", "mm"), ("Side cover", "coverSide", "mm"),
            ("Fitment bar size", "ligs", "mm"), ("Bottom clear gaps h / v", "clearBot", "mm"),
            ("", "vclearBot", "mm"), ("Top clear gaps h / v", "clearTop", "mm"),
            ("", "vclearTop", "mm"), ("Top bars extend into bef", "extend", "")]),
        ("Bending Actions", [
            ("Design moment M*", "Mstar", "kNm"), ("Ms1* source", "ms1Mode", ""),
            ("Ms1*", "Ms1", "kNm"), ("Ms* source", "msMode", ""), ("Ms*", "Ms", "kNm"),
            ("Minimum steel basis", "astMinBasis", "")]),
        ("Serviceability", [
            ("Fully enclosed", "enclosed", ""), ("Maximum crack width", "wmax", "mm"),
            ("Steel in Iuncr", "withSteel", ""), ("Use bef", "useBef", ""),
            ("Environment", "environment", ""), ("Drying shrinkage source", "shrinkageMode", ""),
            ("Tested eps.csd.b*", "ecsdbTested", "x1e-6"), ("Time t", "tDays", "days"),
            ("Loading age tau", "tauDays", "days"), ("th source", "thMode", ""),
            ("Manual th", "thManual", "mm"), ("eps.cs source", "ecsMode", ""),
            ("Manual eps.cs", "ecsManual", "x1e-6"), ("phi.cc source", "fccMode", ""),
            ("Manual phi.cc", "fccManual", ""), ("Sustained stress", "sigmaO", "MPa")]),
        ("Shear and Torsion", [
            ("Design shear V*", "Vstar", "kN"), ("Coexisting M*", "MstarV", "kNm"),
            ("Section Mmax*", "MmaxV", "kNm"), ("Axial N*", "NstarV", "kN"),
            ("Torsion T*", "Tstar", "kNm"), ("Method", "shearMethod", ""),
            ("Aggregate size", "dg", "mm"), ("Lightweight", "lightweight", ""),
            ("Compression zone cracked", "compCracked", ""), ("Ignore fitments", "ignoreLigs", ""),
            ("Fitment spacing", "s", "mm"), ("Fitment legs", "legs", ""),
            ("Fitment fsy.f", "fsyf", "MPa"), ("Fitment class", "classFit", ""),
            ("Fitment angle", "alphaV", "deg"), ("Allow wider spacing", "increaseSpacing", ""),
            ("Waive spacing", "waiveSpacing", ""), ("Waive transverse", "waiveTransverse", ""),
            ("Waive D >= 750", "waiveDeep", ""), ("Act definition", "actDefinition", ""),
            ("Limit Ttd", "limitTtd", ""), ("Manual Ast", "AstManual", "mm2"),
            ("Manual Asc", "AscManual", "mm2")]),
        ("Deemed-to-Comply Deflection", [
            ("Span type", "spanType", ""), ("Spans", "spans", ""),
            ("Superimposed dead load", "wsdl", "kN/m"), ("Live load", "wll", "kN/m"),
            ("Live load type", "loadTypeDefl", ""), ("Lef/Delta total", "lefDelta", ""),
            ("Lef/Delta incremental", "lefDeltaInc", "")] + (
            [("Slab factor k3", "k3", "")] if kind == "S" else [])),
    ]
    checks = inputs.get("checks") or {}
    if checks.get("crackWidth"):
        groups.append(("Crack Width", [("Bottom bar shape", "barShapeBot", ""),
                                       ("Top bar shape", "barShapeTop", ""),
                                       ("Axial N*", "NstarCrack", "kN")]))
    if checks.get("calcDeflection"):
        fields = []
        for key in ("L", "X", "R"):
            fields += [(f"M* at {key}", f"m{key}", "kNm"), (f"Ms* at {key}", f"ms{key}", "kNm"),
                       (f"Top steel at {key}", f"topAs{key}", "mm2"),
                       (f"Bottom steel at {key}", f"botAs{key}", "mm2")]
        fields += [("Gross dead load deflection", "deltaDL", "mm"),
                   ("Gross live load deflection", "deltaLL", "mm"), ("psi.s", "psiSDefl", ""),
                   ("psi.l", "psiLDefl", ""), ("Include sigma.cs", "useFcs", ""),
                   ("Dead load limit span /", "limDL", ""), ("Live load limit span /", "limLL", ""),
                   ("Incremental limit span /", "limInc", ""), ("Total limit span /", "limTotal", ""),
                   ("Absolute limits DL / LL", "absDL", "mm"), ("", "absLL", "mm"),
                   ("Absolute limits Inc / Total", "absInc", "mm"), ("", "absTotal", "mm"),
                   ("End moment cut-off", "cutoff", "%"),
                   ("Span type for WRH", "creepSpanType", "")]
        groups.append(("Calculated Deflection", fields))
    if checks.get("slenderness"):
        groups.append(("Lateral Restraint", [("Restraint spacing", "restraintSpacing", "mm"),
                                             ("Cantilever", "cantilever", "")]))
    if checks.get("secondary"):
        groups.append(("Shrinkage and Temperature Steel", [
            ("Restraint", "restraint", ""), ("sigma.cp", "sigmaCp", "MPa"),
            ("Provided", "AsSecondary", "mm2/m")]))
    return [calcpad.matrix(f"Design Inputs - {title}",
                           [(label, key, inputs.get(key, ""), unit) for label, key, unit in fields
                            if str(inputs.get(key, "")).strip() != ""])
            for title, fields in groups]


# ---------------------------------------------------------------------------
#  Drawings
# ---------------------------------------------------------------------------
def _bar_positions(face: dict[str, Any], *, width: float, x0: float, side: float,
                   y_outer: float, inward: float, slab: bool) -> list[tuple[float, float]]:
    if not face["As"]:
        return []
    bar = face["bar"]
    if face["mode"] == "A":
        count = max(1, math.ceil(face["As"] / bar_area(bar)))
        per_layer, layers = count, 1
    else:
        count = max(1, int(face["nbars"])) if not slab else max(1, int(round(face["nbars"])))
        per_layer, layers = max(1, face["perLayer"]), max(1, face["layers"])
    positions = []
    remaining = count
    for layer in range(layers):
        n = min(per_layer, remaining)
        remaining -= n
        y = y_outer + inward * layer * (face["vclear"] + bar)
        if slab:
            pitch = width / max(1, n)
            xs = [x0 + pitch * (i + 0.5) for i in range(n)]
        elif n == 1:
            xs = [x0 + width / 2.0]
        else:
            first, last = x0 + side + bar / 2.0, x0 + width - side - bar / 2.0
            xs = [first + (last - first) * i / (n - 1) for i in range(n)]
        positions += [(x, y) for x in xs]
        if remaining <= 0:
            break
    return positions


def drawing_scale(result: dict[str, Any]) -> float:
    geom = result["section"]
    total_w = geom["bef"] if geom["section"] == FLANGED else geom["W"]
    return min(50.0 / geom["D"], 84.0 / total_w)


def section_drawing(result: dict[str, Any], scale: float | None = None) -> str:
    """Scaled cross-section with outline, flange, fitment, bars and dimensions."""
    geom, reo = result["section"], result["reinforcement"]
    section, D, W = geom["section"], geom["D"], geom["W"]
    flanged = section == FLANGED
    slab = section == SLAB
    total_w = geom["bef"] if flanged else W
    web_x0 = 0.0
    if flanged:
        web_x0 = (total_w - W) / 2.0 if geom["btype"] == "T" else 0.0
    scale = scale or drawing_scale(result)
    left, top = 16.0, 10.0
    body_w, body_h = total_w * scale, D * scale
    width, height = body_w + left + 12.0, body_h + top + 16.0

    def sx(value: float) -> float:
        return left + value * scale

    def sy(value: float) -> float:
        return top + value * scale

    if flanged:
        tf = geom["Tf"]
        points = [(0, 0), (total_w, 0), (total_w, tf), (web_x0 + W, tf), (web_x0 + W, D),
                  (web_x0, D), (web_x0, tf), (0, tf)]
        path = " ".join(f"{sx(x):.2f},{sy(y):.2f}" for x, y in points)
        outline = (f'<polygon points="{path}" fill="#f1f2f0" stroke="#111" stroke-width="0.55"/>')
    else:
        outline = (f'<rect x="{sx(0):.2f}" y="{sy(0):.2f}" width="{body_w:.2f}" '
                   f'height="{body_h:.2f}" fill="#f1f2f0" stroke="#111" stroke-width="0.55"/>')
    fit = reo["ligs"]
    fitment = ""
    if fit and not slab:
        inset_side = reo["coverSide"] + fit / 2.0
        y_top, y_bot = reo["coverTop"] + fit / 2.0, D - reo["cover"] - fit / 2.0
        fitment = (f'<rect x="{sx(web_x0 + inset_side):.2f}" y="{sy(y_top):.2f}" '
                   f'width="{(W - 2 * inset_side) * scale:.2f}" height="{(y_bot - y_top) * scale:.2f}" '
                   f'rx="{max(0.8, 2.0 * fit * scale):.2f}" fill="none" stroke="#8d959a" '
                   f'stroke-width="{max(0.25, fit * scale):.2f}"/>')
    side = 0.0 if slab else reo["coverSide"] + fit
    fit_depth = 0.0 if slab else fit
    bottom = _bar_positions(reo["bottom"], width=W, x0=web_x0, side=side,
                            y_outer=D - reo["cover"] - fit_depth - reo["bottom"]["bar"] / 2.0,
                            inward=-1.0, slab=slab)
    top_width = total_w if (flanged and reo["extend"]) else W
    top_x0 = 0.0 if (flanged and reo["extend"]) else web_x0
    top_bars = _bar_positions(reo["top"], width=top_width, x0=top_x0, side=side,
                              y_outer=reo["coverTop"] + fit_depth + reo["top"]["bar"] / 2.0,
                              inward=1.0, slab=slab)
    bars = "".join(
        f'<circle cx="{sx(x):.2f}" cy="{sy(y):.2f}" r="{max(0.45, bar / 2.0 * scale):.2f}" fill="#111"/>'
        for positions, bar in ((bottom, reo["bottom"]["bar"]), (top_bars, reo["top"]["bar"]))
        for x, y in positions)
    ds_line = (f'<line x1="{sx(0) - 2:.2f}" y1="{sy(reo["ds"]):.2f}" x2="{sx(total_w) + 2:.2f}" '
               f'y2="{sy(reo["ds"]):.2f}" stroke="#b1257a" stroke-width="0.2" '
               'stroke-dasharray="1.2,0.8"/>')
    dim_y = top + body_h + 8.0
    dim_x = left - 8.0

    def text(x: float, y: float, value: str, rotate: bool = False) -> str:
        spin = f' transform="rotate(-90 {x:.2f} {y:.2f})"' if rotate else ""
        return (f'<text x="{x:.2f}" y="{y:.2f}" font-size="2.6" text-anchor="middle" '
                f'fill="#111"{spin}>{escape(value)}</text>')

    arrows = 'marker-start="url(#cmArrow)" marker-end="url(#cmArrow)"'
    dims = (f'<line x1="{sx(web_x0):.2f}" y1="{dim_y:.2f}" x2="{sx(web_x0 + W):.2f}" y2="{dim_y:.2f}" '
            f'stroke="#111" stroke-width="0.2" {arrows}/>'
            + text(sx(web_x0 + W / 2), dim_y - 1.2, f"{'b' if slab else 'W'} = {num(W, 0)}")
            + f'<line x1="{dim_x:.2f}" y1="{sy(0):.2f}" x2="{dim_x:.2f}" y2="{sy(D):.2f}" '
            f'stroke="#111" stroke-width="0.2" {arrows}/>'
            + text(dim_x - 1.4, sy(D / 2), f"D = {num(D, 0)}", rotate=True)
            + text(sx(total_w) + 5.5, sy(reo["ds"]) + 1.0, "ds"))
    if flanged:
        dims += (f'<line x1="{sx(0):.2f}" y1="{top - 4:.2f}" x2="{sx(total_w):.2f}" y2="{top - 4:.2f}" '
                 f'stroke="#111" stroke-width="0.2" {arrows}/>'
                 + text(sx(total_w / 2), top - 5.2, f"bef = {num(total_w, 0)}"))
    return (f'<svg viewBox="0 0 {width:.2f} {height:.2f}" width="{width:.2f}mm" height="{height:.2f}mm" '
            'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Member cross-section">'
            '<defs><marker id="cmArrow" markerWidth="4" markerHeight="4" refX="2" refY="2" orient="auto">'
            '<path d="M0,2 L4,0.8 L4,3.2 Z" fill="#111"/></marker></defs>'
            f"{outline}{fitment}{bars}{ds_line}{dims}</svg>")


def strain_diagram(result: dict[str, Any], height: float = 58.0) -> str:
    """Ultimate strain and stress-block diagram for the governing bending direction."""
    flex = result["flexure"]
    face = flex["governing"]
    D = result["section"]["D"]
    if not face["Ast"] or not face["kud"]:
        return ""
    scale = height / D
    top, left = 10.0, 6.0
    strain_w, gap, stress_w = 16.0, 8.0, 14.0
    width = left + strain_w * 2 + gap + stress_w + 16.0
    total = height + top + 16.0
    negative = flex["Mstar"] < 0

    def y(depth: float) -> float:
        value = depth if not negative else D - depth
        return top + value * scale

    x_axis = left + strain_w
    eps_s = min(face["epsS"], 0.02)
    ratio = strain_w / max(0.003, eps_s)
    comp_x = x_axis - 0.003 * ratio
    steel_x = x_axis + eps_s * ratio
    strain = (f'<line x1="{x_axis:.2f}" y1="{y(0):.2f}" x2="{x_axis:.2f}" y2="{y(D):.2f}" '
              'stroke="#111" stroke-width="0.3"/>'
              f'<polygon points="{comp_x:.2f},{y(0):.2f} {x_axis:.2f},{y(0):.2f} {x_axis:.2f},{y(face["kud"]):.2f}" '
              'fill="#d9e4f2" stroke="#1c4fa1" stroke-width="0.3"/>'
              f'<polygon points="{x_axis:.2f},{y(face["kud"]):.2f} {x_axis:.2f},{y(face["d"]):.2f} '
              f'{steel_x:.2f},{y(face["d"]):.2f}" fill="#f6dce9" stroke="#b1257a" stroke-width="0.3"/>'
              f'<line x1="{x_axis - 4:.2f}" y1="{y(face["kud"]):.2f}" x2="{x_axis + 4:.2f}" '
              f'y2="{y(face["kud"]):.2f}" stroke="#111" stroke-width="0.25" stroke-dasharray="1,0.6"/>')
    s0 = left + strain_w * 2 + gap
    block = (f'<line x1="{s0:.2f}" y1="{y(0):.2f}" x2="{s0:.2f}" y2="{y(D):.2f}" stroke="#111" '
             'stroke-width="0.3"/>'
             f'<rect x="{s0 - stress_w * 0.7:.2f}" y="{min(y(0), y(face["gammaKud"])):.2f}" '
             f'width="{stress_w * 0.7:.2f}" height="{abs(y(face["gammaKud"]) - y(0)):.2f}" '
             'fill="#d9e4f2" stroke="#1c4fa1" stroke-width="0.3"/>'
             f'<line x1="{s0:.2f}" y1="{y(face["d"]):.2f}" x2="{s0 + stress_w * 0.5:.2f}" '
             f'y2="{y(face["d"]):.2f}" stroke="#b1257a" stroke-width="0.6" marker-end="url(#cmArrow2)"/>')

    def label(x: float, yy: float, value: str, anchor: str = "middle") -> str:
        return (f'<text x="{x:.2f}" y="{yy:.2f}" font-size="2.4" text-anchor="{anchor}" '
                f'fill="#111">{escape(value)}</text>')

    labels = (label(comp_x, y(0) + (-1.5 if not negative else 3.5), "0.003")
              + label(steel_x, y(face["d"]) + (3.5 if not negative else -1.5),
                      f"{face['epsS']:.4f}", "end")
              + label(x_axis + 5, y(face["kud"]) + 1, f"kud = {num(face['kud'], 1)}", "start")
              + label(s0 - stress_w * 0.35, y(0) + (-1.5 if not negative else 3.5),
                      f"\u03b12 f'c = {num(flex['alpha2'] * result['inputs']['fc'], 1)}")
              + label(s0 + stress_w * 0.5 + 1.0, y(face["d"]) + 0.8,
                      f"T = {num(face['Ts'], 0)} kN", "start")
              + label(x_axis, total - 3.0, "Strain") + label(s0, total - 3.0, "Stress block"))
    return (f'<svg viewBox="0 0 {width:.2f} {total:.2f}" width="{width:.2f}mm" height="{total:.2f}mm" '
            'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Strain and stress diagram">'
            '<defs><marker id="cmArrow2" markerWidth="4" markerHeight="4" refX="2" refY="2" orient="auto">'
            '<path d="M0,0.8 L4,2 L0,3.2 Z" fill="#b1257a"/></marker></defs>'
            f"{strain}{block}{labels}</svg>")


def _section_figure(result: dict[str, Any]) -> str:
    reo, geom, flex = result["reinforcement"], result["section"], result["flexure"]
    slab = geom["section"] == SLAB
    caption = (f"{geom['label']}. Bottom {_face_text(reo['bottom'], slab)}, top "
               f"{_face_text(reo['top'], slab)}"
               + ("" if slab or not reo["ligs"] else f", N{num(reo['ligs'], 0)} fitments")
               + f". Dashed line at ds = {num(reo['ds'], 1)} mm. Right: ultimate strain and "
               f"stress block for {'negative' if flex['Mstar'] < 0 else 'positive'} bending.")
    scale = drawing_scale(result)
    svg = (section_drawing(result, scale)
           + strain_diagram(result, max(30.0, geom["D"] * scale)))
    svg = f'<div style="margin-right:37mm;display:flex;gap:6mm;align-items:flex-start">{svg}</div>'
    return calcpad.figure("Section, Reinforcement and Ultimate Strain", svg, caption, weight=22)


# ---------------------------------------------------------------------------
#  Check tables
# ---------------------------------------------------------------------------
def _properties(result: dict[str, Any]) -> str:
    geom, reo, u = result["section"], result["reinforcement"], _units(result)
    rows = []
    if geom["section"] == FLANGED:
        rule = "bw + 0.2 a" if geom["btype"] == "T" else "bw + 0.1 a"
        rows += [
            calcpad.row("Zero-moment length factor", "a = k L", num(geom["kee"], 2), "Cl 8.8.2"),
            calcpad.row("Effective flange width", f"bef = min(Bf, {rule})",
                        f"{num(geom['bef'], 0)} mm", "Cl 8.8.2"),
        ]
    rows += [
        calcpad.row("Gross area", "Ag", f"{num(geom['Ag'], 0)} mm2"),
        calcpad.row("Self weight", "S.Wt = Ag (rho/100 + 1)", f"{num(geom['swt'], 2)} {u['w']}"),
        calcpad.row("Gross second moment", "Ig (bef or Bf)", f"{num(geom['Ig'], 1)} x1e6 mm4"),
        calcpad.row("Bottom steel", f"Ast, {reo['bottom']['layers']} layer(s)",
                    f"{num(reo['Ast'], 1)} {u['a']}"),
        calcpad.row("Top steel", f"Asc, {reo['top']['layers']} layer(s)",
                    f"{num(reo['Asc'], 1)} {u['a']}"),
        calcpad.row("Depth to bottom steel", "ds.max / ds (centroid)",
                    f"{num(reo['dsmax'], 1)} / {num(reo['ds'], 1)} mm"),
        calcpad.row("Depth to top steel", "dc.max / dc (centroid)",
                    f"{num(reo['dcmax'], 1)} / {num(reo['dc'], 1)} mm"),
        calcpad.row("Bars per layer", "bottom / top",
                    f"{reo['bottom']['perLayer']} / {reo['top']['perLayer']}"),
        calcpad.row("Bar centres", "bottom / top",
                    f"{num(reo['bottom']['centres'], 1)} / {num(reo['top']['centres'], 1)} mm"),
    ]
    return calcpad.table("Section Properties and Reinforcement", rows)


def _material(result: dict[str, Any]) -> str:
    mat, flex = result["materials"], result["flexure"]
    fcmi = ("fcmi = -0.0015 f'c^2 + 1.1429 f'c - 0.0614" if mat["useFcmi"] else "fcmi taken as f'c")
    ec = "Ec = rho^1.5 (0.043 sqrt(fcmi))" if mat["fcmi"] <= 40 else "Ec = rho^1.5 (0.024 sqrt(fcmi) + 0.12)"
    rows = [
        calcpad.row("Concrete strength", "f'c", f"{num(result['inputs']['fc'], 0)} MPa",
                    "Cl 1.1.2"),
        calcpad.row("Stress block", "alpha2 = 0.85 - 0.0015 f'c; gamma = 0.97 - 0.0025 f'c",
                    f"{num(flex['alpha2'], 3)} / {num(flex['gamma'], 3)}", "Eq 8.1.3(1), (2)"),
        calcpad.row("Mean in-situ strength", fcmi, f"{num(mat['fcmi'], 2)} MPa", "Table 3.1.2"),
        calcpad.row("Modulus of elasticity", ec, f"{num(mat['Ec'], 0)} MPa", "Cl 3.1.2"),
        calcpad.row("Modular ratio", "n = Es / Ec", num(mat["n"], 3), "Cl 3.2.2"),
        calcpad.row("Flexural tensile strength", "f'ct.f = 0.6 sqrt(f'c)",
                    f"{num(mat['fctf'], 3)} MPa", "Cl 3.1.1.3"),
        calcpad.row("Steel yield strain", "eps.sy = fsy / Es",
                    num(flex["esy"], 5), f"fsy = {num(result['inputs']['fsy'], 0)} MPa"),
        calcpad.row("Balanced neutral axis", "ku.b = 0.003 / (0.003 + fsy / Es)",
                    num(flex["kub"], 4)),
    ]
    return calcpad.table("Material Properties - Section 3", rows)


def _bending(result: dict[str, Any]) -> list[str]:
    flex, u = result["flexure"], _units(result)
    face = flex["governing"]
    sign = "negative" if flex["Mstar"] < 0 else "positive"
    if face["yieldValid"]:
        method = "Compression steel yields, WRH Eq 4.49"
    elif face["ascInCompression"]:
        method = "Compression steel elastic, WRH Eq 4.55"
    else:
        method = "Compression steel ignored (tension zone)"
    rows = [
        calcpad.row("Tension steel", "Ast (Asc limited to Ast)",
                    f"{num(face['Ast'], 1)} / {num(face['Asc'], 1)} {u['a']}"),
        calcpad.row("Depths", "d / do / dc", f"{num(face['d'], 1)} / {num(face['dmax'], 1)} / "
                    f"{num(face['dc'], 1)} mm"),
        calcpad.row("Width of compression zone", "b", f"{num(face['b'], 0)} mm"),
        calcpad.row("Neutral axis method", escape(method),
                    f"ku = {num(face['kuYield'], 4)} / {num(face['kuElastic'], 4)}", "WRH"),
        calcpad.row("Stress block depth", "gamma kud",
                    f"{num(face['gammaKud'], 1)} mm" + ("" if face["inFlange"] else " (web)")),
        calcpad.row("Forces", "T = Ast fsy; Cc; Cs",
                    f"{num(face['Ts'], 1)} / {num(face['Cc'], 1)} / {num(face['Cs'], 1)} kN"),
        calcpad.row("Neutral axis parameter", "ku = kud / d", num(face["ku"], 4), "Cl 8.1.5"),
        calcpad.row("Ultimate moment", "Muo", f"{num(face['Mu'], 1)} {u['m']}", "Cl 8.1.3"),
        calcpad.row("Capacity factor", "phi = 1.24 - 13 kuo / 12 (Class N)",
                    f"kuo = {num(face['kuo'], 4)}, phi = {num(face['phi'], 3)}", "Table 2.2.2"),
        calcpad.row("Design capacity", "phiMuo", f"{num(face['phiMu'], 1)} {u['m']}"),
        calcpad.row("Steel required", "Ast.req for |M*|", f"{num(face['AstReq'], 1)} {u['a']}"),
        calcpad.row("Bending check", "|M*| / phiMuo", calcpad.badge(result["util"]["flexure"]),
                    "Cl 8.1"),
    ]
    table = calcpad.table(f"Strength in Bending, {sign.capitalize()} Moment - "
                          f"{'Cl 9.1' if result['section']['section'] == SLAB else 'Cl 8.1'}", rows)
    grid = calcpad.grid(
        "Bending Capacity in Both Directions",
        ["Direction", "Ast", "Asc", "d", "ku", "kuo", "phi", "Muo", "phiMuo"],
        [[label, num(item["Ast"], 0), num(item["Asc"], 0), num(item["d"], 0), num(item["ku"], 4),
          num(item["kuo"], 4), num(item["phi"], 3), num(item["Mu"], 1), num(item["phiMu"], 1)]
         for label, item in (("Positive, bottom tension", flex["positive"]),
                             ("Negative, top tension", flex["negative"]))],
        f"Areas in {u['a']}, depths in mm and moments in {u['m']}.")
    return [table, f'<div style="margin-right:37mm">{grid}</div>']


def _ductility(result: dict[str, Any]) -> str:
    duct = result["ductility"]
    rows = [
        calcpad.row("Neutral axis at do", "kuo", num(duct["kuo"], 4), "Cl 8.1.5"),
        calcpad.row("Limit", "kuo <= 0.36", "0.36"),
        calcpad.row("Compression steel alternative", "Asc >= 0.01 b kuo do",
                    f"{num(duct['AscRequired'], 0)} required, {num(duct['AscAvailable'], 0)} "
                    "in compression", "Tedds AS3600-2018"),
        calcpad.row("Ductility check", escape(duct["basis"]),
                    calcpad.badge(result["util"]["ductility"]), "Cl 8.1.5"),
    ]
    return calcpad.table("Ductility - Cl 8.1.5", rows)


def _minimum(result: dict[str, Any]) -> str:
    m, u = result["minimum"], _units(result)
    positive = result["flexure"]["Mstar"] >= 0
    basis = {"D": "Deemed-to-comply", "A": "Actual (Muo)min", "M": "Lesser of the two"}[m["basis"]]
    rows = [
        calcpad.row("Uncracked neutral axis", "NA from top", f"{num(result['uncracked']['NA'], 1)} mm",
                    "RCB-1.1(1) Fig 5.3"),
        calcpad.row("Uncracked second moment", "Iuncr = u.kappa W D^3 / 12",
                    f"{num(result['uncracked']['Iuncrk'], 1)} x1e6 mm4"),
        calcpad.row("Section modulus", "Zb / Zt",
                    f"{num(m['Zb'], 0)} / {num(m['Zt'], 0)} x1e3 mm3"),
        calcpad.row("Minimum moment", "(Muo)min = 1.2 Z f'ct.f",
                    f"{num(m['MuoMinPos' if positive else 'MuoMinNeg'], 1)} {u['m']}",
                    "Eq 8.1.6.1(1)"),
        calcpad.row("Steel for (Muo)min", "Ast giving phiMuo = phi (Muo)min",
                    f"{num(m['actual'], 1)} {u['a']}"),
        calcpad.row("Deemed-to-comply", "alpha.b (D/d)^2 f'ct.f / fsy bw d",
                    f"alpha.b = {num(m['alphaBPos' if positive else 'alphaBNeg'], 3)}, "
                    f"{num(m['deemed'], 1)} {u['a']}", "Eq 8.1.6.1(2)"),
        calcpad.row("Adopted minimum", escape(basis), f"{num(m['AsMin'], 1)} {u['a']}"),
        calcpad.row("Minimum strength check", "Ast.min / Ast",
                    calcpad.badge(result["util"]["minimumSteel"]), escape(m["clause"])),
    ]
    return calcpad.table(f"Minimum Strength Requirements - {escape(m['clause'])}", rows)


def _crack(result: dict[str, Any]) -> str:
    crack, spacing, u = result["crack"], result["spacing"], _units(result)
    face = crack["governing"]
    rows = [
        calcpad.row("Service moments", "Ms1* (psi.s = 1) / Ms*",
                    f"{num(crack['Ms1'], 1)} / {num(crack['Ms'], 1)} {u['m']}"),
        calcpad.row("Cracked neutral axis", "kd = k d", f"k = {num(face['k'], 4)}, "
                    f"kd = {num(face['kd'], 1)} mm", "RCB-1.1(1) Fig 5.7"),
        calcpad.row("Cracked second moment", "Icr = kappa b d^3 / 12",
                    f"{num(face['Icr'], 1)} x1e6 mm4"),
        calcpad.row("Steel stress under Ms*", "sigma.scr = n Ms* (do - kd) / Icr",
                    f"{num(face['fscr'], 1)} MPa"),
        calcpad.row("Steel stress under Ms1*", "sigma.scr1 = (Ms1* / Ms*) sigma.scr",
                    f"{num(face['fscr1'], 1)} MPa"),
        calcpad.row("Limit from bar size", f"db = {num(face['bar'], 0)} mm",
                    f"{num(face['limitBar'], 1)} MPa", escape(crack["tableBar"])),
        calcpad.row("Limit from bar centres", f"s = {num(face['centres'], 0)} mm",
                    f"{num(face['limitSpacing'], 1)} MPa", escape(crack["tableSpacing"])),
        calcpad.row("Maximum stress", "sigma.scr.max = min(0.8 fsy, max(A, B))",
                    f"{num(face['limit'], 1)} MPa"),
    ]
    if "crackStress" in result["util"]:
        rows += [
            calcpad.row("Stress check, Ms*", "sigma.scr / sigma.scr.max",
                        calcpad.badge(result["util"]["crackStress"]), escape(crack["clause"])),
            calcpad.row("Stress check, Ms1*", "sigma.scr1 / 0.8 fsy",
                        calcpad.badge(result["util"]["crackStressYield"]), escape(crack["clause"])),
        ]
    else:
        rows.append(calcpad.row("Crack control", "Fully enclosed", "Not checked"))
    rows += [
        calcpad.row("Tension bar centres", f"s <= {num(spacing['limit'], 0)} mm",
                    calcpad.badge(result["util"]["barSpacing"]) if spacing["applicable"]
                    else "Area input, not checked", escape(spacing["clause"])),
        calcpad.row("Side face reinforcement", "D - Tf > 750 mm", escape(crack["sideFace"])),
    ]
    clause = "Cl 9.5" if result["section"]["section"] == SLAB else "Cl 8.6"
    return calcpad.table(f"Crack Control - {clause}", rows)


def _creep(result: dict[str, Any]) -> str:
    c = result["creep"]
    rows = [
        calcpad.row("Hypothetical thickness", "th = 2 Ag / ue" if not c["thManual"] else "th (manual)",
                    f"{num(c['th'], 1)} mm", "Cl 1.7"),
        calcpad.row("Environment", escape(c["environmentLabel"]), f"k4 = {num(c['k4'], 2)}",
                    "Cl 3.1.7.2"),
        calcpad.row("Autogenous shrinkage", "eps.cse = eps.cse* (1 - e^(-0.07 t))",
                    f"{num(c['auto'], 1)} x1e-6", "Eq 3.1.7.2(2)"),
        calcpad.row("Basic drying shrinkage", "eps.csd.b = (0.9 - 0.005 f'c) eps.csd.b*",
                    f"eps.csd.b* = {num(c['basicStar'], 0)}, {num(c['basic'], 1)} x1e-6",
                    "Eq 3.1.7.2(5)"),
        calcpad.row("Drying shrinkage", "eps.csd = k1 k4 eps.csd.b",
                    f"k1 = {num(c['k1'], 3)}, {num(c['drying'], 1)} x1e-6", "Eq 3.1.7.2(4)"),
        calcpad.row("Design shrinkage strain", "eps.cs = eps.cse + eps.csd, rounded",
                    f"{num(c['ecs'], 0)} x1e-6" + (" (manual)" if c["ecsManual"] else ""),
                    "Eq 3.1.7.2(1)"),
        calcpad.row("Basic creep coefficient", "phi.cc.b", num(c["fccb"], 2), "Table 3.1.8.2"),
        calcpad.row("Creep factors", "k2 / k3 / k5 / k6",
                    f"{num(c['k2'], 3)} / {num(c['k3'], 3)} / "
                    f"{'-' if c['k5'] is None else num(c['k5'], 3)} / {num(c['k6'], 3)}",
                    "Cl 3.1.8.3"),
        calcpad.row("Creep coefficient", "phi.cc = k2 k3 k4 k5 k6 phi.cc.b",
                    num(c["fcc"], 3) + (" (manual)" if c["fccManual"] else ""), "Eq 3.1.8.3"),
    ]
    return calcpad.table("Shrinkage and Creep - Cl 3.1.7 and Cl 3.1.8", rows)


def _crack_width(result: dict[str, Any]) -> str:
    width = result["crackWidth"]
    if not width:
        return ""
    face = width["governing"]
    rows = [
        calcpad.row("Effective modular ratio", "ne = (1 + phi.cc) Es / Ec", num(width["ne"], 3),
                    "Cl 8.6.2.3"),
        calcpad.row("Effective tension depth", "hc.ef = min(2.5 (D - d), (D - kd)/3, D/2)",
                    f"{num(face['hca'], 1)} mm"),
        calcpad.row("Effective reinforcement ratio", "rho.eff = Ast / Ac.eff",
                    f"Ac.eff = {num(face['Aceff'], 0)} mm2, {num(face['peff'], 5)}"),
        calcpad.row("Strain difference", "eps.sm - eps.cm >= 0.6 sigma.scr / Es",
                    f"{num(face['diff'], 1)} x1e-6", "Eq 8.6.2.3(2)"),
        calcpad.row("Strain factors", "k1 / k2", f"{num(face['k1'], 2)} / {num(face['k2'], 2)}"),
        calcpad.row("Crack spacing", "sr.max = min(1.3 (D - kd), 3.4 c + 0.3 k1 k2 db / rho.eff)",
                    f"{num(face['sr'], 1)} mm", "Eq 8.6.2.3(3)"),
        calcpad.row("Crack width", "w = sr.max (eps.sm - eps.cm)", f"{num(face['w'], 3)} mm"),
        calcpad.row("Crack width check", "w / w'max", calcpad.badge(result["util"]["crackWidth"]),
                    "Cl 8.6.2.3"),
    ]
    return calcpad.table("Calculated Crack Width - Cl 8.6.2.3", rows)


def _shear(result: dict[str, Any]) -> str:
    s, u = result["shear"], _units(result)
    rows = [
        calcpad.row("Actions", "V* / M* / N* (compression +ve)",
                    f"{num(s['V'], 1)} {u['v']} / {num(s['M'], 1)} {u['m']} / {num(s['N'], 1)} kN"),
        calcpad.row("Effective shear depth", "dv = max(0.72 D, 0.9 d)",
                    f"{num(s['dv'], 1)} mm, bv = {num(s['bv'], 0)} mm", "Cl 8.2.1.9"),
        calcpad.row("Fitments", f"{s['legs']} legs N{num(result['reinforcement']['ligs'], 0)} at "
                    f"{num(s['s'], 0)}", f"Asv = {num(s['AsvActual'], 1)}, Asv.min = "
                    f"{num(s['AsvMin'], 1)} mm2", "Eq 8.2.1.7"),
        calcpad.row("Longitudinal strain", "eps.x = (|M*|/dv + |V*| - 0.5 N*) / (2 Es Ast)",
                    f"{num(s['eps'], 1)} x1e-6", "Cl 8.2.4.2.2"),
        calcpad.row("Concrete factors", escape(s["method"]),
                    f"kv = {num(s['kv'], 4)}, theta.v = {num(s['theta'], 2)} deg",
                    "Cl 8.2.4.2" if s["method"].startswith("General") else "Cl 8.2.4.3"),
        calcpad.row("Concrete contribution", "Vuc = kv bv dv min(sqrt(f'c), 8)",
                    f"{num(s['Vuc'], 1)} {u['v']}", "Eq 8.2.4.1"),
        calcpad.row("No-fitment threshold", "ks (phi = 0.7) Vuc",
                    f"ks = {num(s['ks'], 3)}, {num(s['ksPhiVuc'], 1)} {u['v']}", "Eq 8.2.1.6"),
        calcpad.row("Fitment contribution", "Vus = (Asv fsy.f dv / s) cot(theta.v)",
                    f"{num(s['Vus'], 1)} {u['v']}", "Eq 8.2.5.2"),
        calcpad.row("Web crushing", "Vu.max = 0.55 (0.9 f'c bv dv cot / (1 + cot^2))",
                    f"phi = 0.7, {num(s['phiVuMax'], 1)} {u['v']}", "Eq 8.2.3.3(1)"),
        calcpad.row("Minimum fitment capacity", "phiVu.min = phi (Vuc + Vus.min)",
                    f"{num(s['phiVuMin'], 1)} {u['v']}", "Cl 8.2.1.7"),
        calcpad.row("Design strength", "phiVu = phiVuc + phiVus <= phiVu.max",
                    f"phi = {num(s['phiV'], 2)}, {num(s['phiVu'], 1)} {u['v']}", "Cl 8.2.3.1"),
        calcpad.row("Fitment requirement", "Cl 8.2.1.6", escape(s["requirement"])),
        calcpad.row("Shear check", escape(s["shearBasis"]), calcpad.badge(result["util"]["shear"]),
                    "Cl 8.2"),
    ]
    if "shearMethod" in result["util"]:
        rows.append(calcpad.row("Simplified method limits", "f'c <= 65, fsy <= 500, dg >= 10",
                                calcpad.badge(result["util"]["shearMethod"]), "Cl 8.2.4.3"))
    return calcpad.table("Shear Strength - Cl 8.2", rows)


def _detailing(result: dict[str, Any]) -> str:
    s = result["shear"]
    rows = [
        calcpad.row("Longitudinal spacing limit",
                    "min(0.75 D, 500)" if s["wide"] else "min(0.5 D, 300)",
                    f"{num(s['sLimit'], 0)} mm", "Cl 8.3.2.2"),
        calcpad.row("Spacing for minimum area", "s.max = Asv fsy.f / (0.08 sqrt(f'c) bv)",
                    f"{num(s['sMaxStrength'], 0)} mm", "Eq 8.2.1.7"),
        calcpad.row("Transverse leg spacing", "<= min(600, D)",
                    f"{num(s['transverse'], 0)} / {num(s['transverseLimit'], 0)} mm", "Cl 8.3.2.2"),
        calcpad.row("Fitments required for strength", "Asv.req / s.req",
                    f"{num(s['AsvReq'], 1)} mm2 / {num(s['sReq'], 0)} mm", "Eq 8.2.5.2"),
        calcpad.row("Detailing check", "max(s / s.max, s.t / s.t.max, Asv.min / Asv)",
                    calcpad.badge(result["util"]["shearDetailing"]), "Cl 8.3.2"),
    ]
    return calcpad.table("Shear Fitment Detailing - Cl 8.3.2", rows)


def _torsion(result: dict[str, Any]) -> str:
    s = result["shear"]
    rows = [
        calcpad.row("Cracking torque", "Tcr = 0.33 sqrt(f'c) Acp^2 / uc",
                    f"{num(s['Tcr'], 1)} kNm, phiTcr = {num(s['phiTcr'], 1)} kNm", "Eq 8.2.1.2(2)"),
        calcpad.row("Torsion trigger", "T* / 0.25 phiTcr",
                    f"{num(s['ratioTrigger'], 3)}" + (" - considered" if s["considerTorsion"]
                                                       else " - may be neglected"), "Cl 8.2.1.2"),
        calcpad.row("Fitment perimeter", "uh = 2 (xo + yo); Ao = 0.85 xo yo",
                    f"{num(s['uh'], 0)} mm, {num(s['Ao'], 0)} mm2", "Cl 8.2.5.6"),
        calcpad.row("Torsional strength", "Tus = 2 Ao Asw fsy.f cot(theta) / s",
                    f"{num(s['Tus'], 1)} kNm, phiTus = {num(s['phiTus'], 1)} kNm", "Eq 8.2.5.6"),
        calcpad.row("Minimum torsion fitments", "Asw.min = max(Asv.min / legs, 0.25 Tcr / ...)",
                    f"{num(s['AswMin'], 1)} mm2, s <= {num(s['sMaxTorsion'], 0)} mm", "Cl 8.2.5.5"),
        calcpad.row("Torsion check", "T* / phiTus", calcpad.badge(result["util"]["torsion"]),
                    "Cl 8.2.5.6"),
        calcpad.row("Torsion fitment check", "max(Asw.min / Asw, s / s.max)",
                    calcpad.badge(result["util"]["torsionReinforcement"]), "Cl 8.2.5.5, 8.3.3"),
        calcpad.row("Combined stress", "sqrt[(V*/bv dv)^2 + (T* uh / 1.7 Aoh^2)^2]",
                    f"{num(s['combined'], 3)} / {num(s['combinedLimit'], 3)} MPa", "Eq 8.2.3.3(5)"),
        calcpad.row("Web crushing check", "v.comb / v.limit",
                    calcpad.badge(result["util"]["webCrushing"]), "Cl 8.2.3.3"),
    ]
    return calcpad.table("Torsion and Web Crushing - Cl 8.2.1.2 and Cl 8.2.5", rows)


def _longitudinal(result: dict[str, Any]) -> str:
    s, u = result["shear"], _units(result)
    applies = "fitments effective" if s["fromShear"] else "not applicable (no effective fitments)"
    rows = [
        calcpad.row("Applicability", "Workbook: fitments present", escape(applies)),
        calcpad.row("Lever arm", "z = d (1 - fsy Ast / (2 alpha2 f'c b d))",
                    f"{num(s['lever'], 1)} mm"),
        calcpad.row("Shear contribution", "dFtd = min(V*, 0.5 (V* + phiVuc)) cot(theta)",
                    f"{num(s['FtdShear'], 1)} kN", "Eq 8.2.8.2"),
        calcpad.row("Torsion contribution", "0.5 T* uo / (2 Ao) cot(theta)",
                    f"{num(s['FtdTorsion'], 1)} kN"),
        calcpad.row("Tension face force", "Ttd = |M*| / z - N*/2 + dFtd",
                    f"{num(s['Ttd'], 1)} kN, phi = {num(s['phiTt'], 3)}"),
        calcpad.row("Tension steel required", "Ttd / (phi fsy)",
                    f"{num(s['AstLongTotal'], 1)} / {num(s['AstProv'], 1)} {u['a']}"),
        calcpad.row("Compression face force", "Fcd = -|M*| / z - N*/2 + dFtd",
                    f"{num(s['Fcd'], 1)} kN"),
        calcpad.row("Longitudinal tension check", "Ast.req / Ast",
                    calcpad.badge(result["util"]["longitudinalTension"]), "Cl 8.2.8"),
        calcpad.row("Compression face check", "Asc.req / Asc",
                    calcpad.badge(result["util"]["longitudinalCompression"]), "Cl 8.2.8"),
    ]
    return calcpad.table("Longitudinal Reinforcement for Shear - Cl 8.2.8", rows)


def _deemed(result: dict[str, Any]) -> str:
    d, u = result["deemed"], _units(result)
    rows = [
        calcpad.row("Loads", "g = S.Wt + wsdl; q", f"{num(d['g'], 2)} / {num(d['wll'], 2)} {u['w']}"),
        calcpad.row("Live load factors", "psi.s / psi.l", f"{num(d['psiS'], 2)} / {num(d['psiL'], 2)}",
                    "AS/NZS 1170.0 Table 4.1"),
        calcpad.row("Cracked neutral axis", "WRH Eq 5.22", f"{num(d['NA'], 1)} mm"),
        calcpad.row("Long-term factor", "kcs = 2 - 1.2 Asc / Ast >= 0.8", num(d["kcs"], 3),
                    "Cl 8.5.3.2"),
        calcpad.row("Effective load, total", "Fd.ef = (1 + kcs) g + (psi.s + kcs psi.l) q",
                    f"{num(d['Fdef'], 2)} {u['w']}"),
        calcpad.row("Effective load, incremental", "Fd.ef.inc = kcs g + (psi.s + kcs psi.l) q",
                    f"{num(d['Fdefi'], 2)} {u['w']}"),
    ]
    if d["slab"]:
        rows += [
            calcpad.row("Slab factors", "k3 / k4", f"{num(d['k3'], 2)} / {num(d['k4'], 2)}",
                        "Cl 9.4.4.1"),
            calcpad.row("Minimum depth, total", "d.min = Lef / (k3 k4 [(Delta/Lef) Ec / Fd.ef]^(1/3))",
                        f"{num(d['dmin'], 1)} mm", "Eq 9.4.4.1"),
        ]
    else:
        rows += [
            calcpad.row("Beam factors", "k1 / k2", f"{num(d['k1'], 5)} / {num(d['k2'], 5)}",
                        "Cl 8.5.4"),
            calcpad.row("Minimum depth, total",
                        "d.min = Lef / [k1 (Delta/Lef) bef Ec / (k2 Fd.ef)]^(1/3)",
                        f"{num(d['dmin'], 1)} mm", "Eq 8.5.4"),
        ]
    rows += [
        calcpad.row("Minimum depth, incremental", "same with Fd.ef.inc", f"{num(d['dmini'], 1)} mm"),
        calcpad.row("Equivalent overall depth", "D.min = db/2 + cover + d.min",
                    f"{num(d['Dmin'], 0)} / {num(d['Dmini'], 0)} mm"),
        calcpad.row("Total deflection check", "d.min / ds",
                    calcpad.badge(result["util"]["deflectionTotal"]), escape(d["clause"])),
        calcpad.row("Incremental deflection check", "d.min.inc / ds",
                    calcpad.badge(result["util"]["deflectionIncremental"]), escape(d["clause"])),
        calcpad.row("Applicability", "q <= g", calcpad.badge(result["util"]["liveLoadLimit"]),
                    escape(d["clause"])),
    ]
    return calcpad.table(f"Deemed-to-Comply Deflection - {escape(d['clause'])}", rows)


def _calculated(result: dict[str, Any]) -> list[str]:
    calc, u = result["deflection"], _units(result)
    if not calc:
        return []
    grid = calcpad.grid(
        "Effective Second Moment of Area by Position - Cl 8.5.3.1",
        ["Position", "M*", "Ms*", "Ast", "Asc", "Iuncr", "Mcr", "Icr", "Ief"],
        [[label, num(row["Mstar"], 1), num(row["Ms"], 1), num(row["Ast"], 0), num(row["Asc"], 0),
          num(row["Iuncrk"], 0), num(row["Mcr"], 1), num(row["Icr"], 0), num(row["Ief"], 0)]
         for label, row in (("Left", calc["positions"]["L"]), ("Position x", calc["positions"]["X"]),
                            ("Right", calc["positions"]["R"]))],
        f"Moments in {u['m']}, areas in {u['a']}, second moments in x1e6 mm4. Mcr includes sigma.cs.")
    lim = calc["limits"]
    rows = [
        calcpad.row("Average stiffness", escape(f"{calc['IavLabel']}: {calc['IavCode']}"),
                    f"{num(calc['Iav'], 0)} x1e6 mm4", "Cl 8.5.3.1"),
        calcpad.row("Stiffness ratio", "Iuncr / Iav", num(calc["ratioI"], 4)),
        calcpad.row("Long-term factor", "kcs = 2 - 1.2 Asc / Ast >= 0.8", num(calc["kcs"], 3),
                    "Cl 8.5.3.2"),
        calcpad.row("Short-term", "(delta.dl.g + psi.s delta.ll.g) Iuncr / Iav",
                    f"{num(calc['short'], 2)} mm"),
        calcpad.row("Long-term", "kcs (delta.dl.g + psi.l delta.ll.g) Iuncr / Iav",
                    f"{num(calc['long'], 2)} mm"),
        calcpad.row("Dead load, long-term", "kcs delta.dl.g Iuncr / Iav",
                    f"{num(calc['dlLong'], 2)} / {num(lim['dead'], 1)} mm"),
        calcpad.row("Live load, short-term", "psi.s delta.ll.g Iuncr / Iav",
                    f"{num(calc['llShort'], 2)} / {num(lim['live'], 1)} mm"),
        calcpad.row("Incremental", "delta.long + delta.ll.short",
                    f"{num(calc['incremental'], 2)} / {num(lim['incremental'], 1)} mm"),
        calcpad.row("Total", "delta.short + delta.long",
                    f"{num(calc['total'], 2)} / {num(lim['total'], 1)} mm", "Table 2.3.2"),
        calcpad.row("Dead load check", "delta / limit", calcpad.badge(result["util"]["deflectionDead"])),
        calcpad.row("Live load check", "delta / limit", calcpad.badge(result["util"]["deflectionLive"])),
        calcpad.row("Incremental check", "delta / limit",
                    calcpad.badge(result["util"]["deflectionIncrementalCalc"])),
        calcpad.row("Total check", "delta / limit", calcpad.badge(result["util"]["deflectionTotalCalc"])),
    ]
    wrh = result["wrh"]
    if wrh:
        rows += [
            calcpad.row("WRH shrinkage curvature", "kappa.sh = 1.15 eps.cs / d (1 - Asc/Ast)",
                        f"{num(wrh['kappaSh'], 2)} x1e-9 /mm", "WRH Eq 9.14"),
            calcpad.row("WRH creep and shrinkage", "delta.sh + delta.cr (information)",
                        f"{num(wrh['deltaSh'], 2)} + {num(wrh['deltaCr'], 2)} = "
                        f"{num(wrh['permanent'], 2)} mm", "WRH Eqs 9.15, 9.21"),
        ]
    return [f'<div style="margin-right:37mm">{grid}</div>',
            calcpad.table("Calculated Deflection - Cl 8.5.3", rows)]


def _slenderness(result: dict[str, Any]) -> str:
    s = result["slenderness"]
    if not s:
        return ""
    rows = [calcpad.row("Limit", s["basis"], f"{num(s['limit'], 0)} mm", escape(s["clause"])),
            calcpad.row("Restraint spacing", "L.restraint", f"{num(s['spacing'], 0)} mm")]
    if s["applicable"]:
        rows.append(calcpad.row("Lateral restraint check", "L.restraint / L1",
                                calcpad.badge(result["util"]["slenderness"]), escape(s["clause"])))
    else:
        rows.append(calcpad.row("Applicability", "Slab", "Not applicable"))
    return calcpad.table("Lateral Restraint - Cl 8.9", rows)


def _secondary(result: dict[str, Any]) -> str:
    s = result["secondary"]
    if not s:
        return ""
    rows = [calcpad.row("Restraint condition", "Cl 9.5.3", escape(s["label"])),
            calcpad.row("Design thickness", "D, or 250 mm per face when D > 500",
                        f"{num(s['designThickness'], 0)} mm", "Cl 9.5.3.1")]
    if s["applicable"]:
        rows += [calcpad.row("Minimum area", "(k - 2.5 sigma.cp) b D x 1e-3",
                             f"{num(s['required'], 0)} mm2/m" + (" each face" if s["eachFace"] else "")),
                 calcpad.row("Shrinkage steel check", "Ast.min / Ast",
                             calcpad.badge(result["util"]["secondarySteel"]), "Cl 9.5.3")]
    else:
        rows.append(calcpad.row("Applicability", "Beam", "Not applicable"))
    return calcpad.table("Shrinkage and Temperature Steel - Cl 9.5.3", rows)


def _basis(result: dict[str, Any]) -> str:
    def items(values: list[str]) -> str:
        return "<ul>" + "".join(f"<li>{escape(value)}</li>" for value in values) + "</ul>"

    body = ("<h3>Assumptions</h3>" + items(result["assumptions"])
            + "<h3>Limitations and exclusions</h3>" + items(result["limitations"]))
    weight = 6 + 2 * (len(result["assumptions"]) + len(result["limitations"]))
    return calcpad.prose("Design Basis, Assumptions and Limitations", body, weight=weight)


def _warnings(result: dict[str, Any]) -> str:
    if not result["warnings"]:
        return ""
    body = "<ul>" + "".join(f"<li>{escape(value)}</li>" for value in result["warnings"]) + "</ul>"
    return calcpad.prose("Warnings", body, weight=4 + 2 * len(result["warnings"]))
