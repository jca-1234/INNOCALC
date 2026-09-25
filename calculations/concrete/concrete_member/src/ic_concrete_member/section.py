"""Section geometry, bar layout and transformed-section properties.

Transcribes ``Design!C13:N70`` (geometry, effective flange, bar layout) and the VBA
routines ``centroid``, ``CalcIuncrkna``, ``CalcIuncrkk``, ``CalcIcrkna`` and ``CalcIcrkk``
(module ``Cracking``).  Section codes follow ``Settings!Y58``: 0 = slab (1 m strip),
1 = rectangular beam, 2 = flanged T or L beam.
"""

from __future__ import annotations

import math
from typing import Any

from .common import bar_area, rounddown, roundup, vba_mod

SLAB, RECTANGULAR, FLANGED = 0, 1, 2
SECTION_CODES = {"S": SLAB, "R": RECTANGULAR, "F": FLANGED}
SECTION_LABELS = {"S": "Slab (1 m design strip)", "R": "Rectangular beam",
                  "F": "Flanged T or L beam"}
MODES = {"N": "number of bars", "S": "bar centres", "A": "area"}
MAX_BARS = 30  # Design!D40 "Error - Max 30 bottom bars"


def centroid(bar: float, bars: float, layers: int, per_layer: int, vclear: float) -> float:
    """VBA ``centroid``: offset of the bar-group centroid from the outermost layer centre."""
    partial = vba_mod(bars, per_layer)
    full = layers if partial == 0 else layers - 1
    area_partial = partial * math.pi * bar ** 2 / 4.0
    area_full = full * per_layer * math.pi * bar ** 2 / 4.0
    dist_partial = (vclear + bar) * (layers - 1) if partial > 0 else 0.0
    dist_full = (vclear + bar) * (full - 1) / 2.0
    total = area_partial + area_full
    if total == 0:
        return 0.0
    return (area_partial * dist_partial + area_full * dist_full) / total


def _layer(face: str, *, bar: float, mode: str, value: float, section: int, W: float,
           bef: float, cover_side: float, ligs: float, clear: float, vclear: float,
           extend: bool) -> dict[str, Any]:
    """Bar count, area, bars per layer and centres for one face (Design!D47:H56)."""
    spread = bef if (face == "top" and extend) else W
    count_width = bef if face == "top" else W
    if value == 0:
        nbars, area = 0.0, 0.0
    elif mode == "N":
        nbars = value
        area = nbars * bar_area(bar)
    elif mode == "S":
        nbars = count_width / value if section == SLAB else rounddown(count_width / value, 0)
        area = nbars * bar_area(bar)
    else:
        nbars, area = 1.0, value
    if area == 0:
        per_layer = 1
    elif (mode == "N" and value == 1) or mode == "A":
        per_layer = 1
    else:
        side = 2.0 * cover_side if section != SLAB else 0.0
        per_layer = max(1, 1 + int((spread - side - 2.0 * ligs - bar) / (bar + clear)))
    layers = 0 if area == 0 else int(roundup(nbars / per_layer, 0))
    if area == 0:
        centres = 0.0
    elif section == SLAB:
        centres = W / min(nbars, per_layer)
    elif nbars == 1 or per_layer == 1:
        centres = W
    else:
        centres = ((spread - 2.0 * cover_side - 2.0 * ligs - bar)
                   / ((per_layer if layers > 1 else nbars) - 1))
    offset = centroid(bar, nbars, layers, per_layer, vclear) if area > 0 else 0.0
    return {"bar": bar, "mode": mode, "value": value, "nbars": nbars, "As": area,
            "perLayer": per_layer, "layers": layers, "centres": centres, "offset": offset,
            "clear": clear, "vclear": vclear, "clearGap": centres - bar, "db3": 3.0 * bar}


def geometry(*, kind: str, D: float, W: float, Bf: float, Tf: float, btype: str, Lm: float,
             support: str, mke: float, density: float, use_bef: bool) -> dict[str, Any]:
    section = SECTION_CODES[kind]
    ww = 1000.0 if section == SLAB else W
    kee = {"S": 1.0, "C": 0.7}.get(support, mke)
    beft = ww + 0.2 * kee * Lm if section == FLANGED else 0.0
    befl = ww + 0.1 * kee * Lm if section == FLANGED else 0.0
    bef_calc = (beft if btype == "T" else befl) if section == FLANGED else ww
    bef = min(Bf, bef_calc) if section == FLANGED else ww
    tf = Tf if section == FLANGED else 0.0
    Ag = (D - tf) * ww + Bf * tf if section == FLANGED else D * ww
    width_flange = bef if use_bef else Bf
    if section == FLANGED:
        Agbef = (D - tf) * ww + width_flange * tf
        na = (tf * width_flange * tf / 2.0 + ww * (D - tf) * (tf + (D - tf) / 2.0)) / Agbef
        Ig = (width_flange * tf ** 3 / 12.0 + width_flange * tf * (na - tf / 2.0) ** 2
              + ww * (D - tf) ** 3 / 12.0 + (D - tf) * ww * (tf + (D - tf) / 2.0 - na) ** 2) / 1e6
    else:
        Agbef = D * ww
        na = D / 2.0
        Ig = ww * D ** 3 / 12.0 / 1e6
    unit_weight = density / 100.0 + 1.0  # Design!C25 "Concrete weight = rse/100+1"
    return {"section": section, "kind": kind, "label": SECTION_LABELS[kind], "D": D, "W": ww,
            "Bf": Bf if section == FLANGED else 0.0, "Tf": tf, "btype": btype, "Lm": Lm,
            "kee": kee, "beft": beft, "befl": befl, "befCalc": bef_calc, "bef": bef,
            "Ag": Ag, "Agbef": Agbef, "na": na, "Ig": Ig, "unitWeight": unit_weight,
            "swt": Ag * unit_weight / 1e6, "useBef": use_bef}


def reinforcement(geom: dict[str, Any], *, bottom: dict[str, Any], top: dict[str, Any],
                  cover: float, cover_top: float, cover_side: float, ligs: float,
                  extend: bool) -> dict[str, Any]:
    section, W, bef, D = geom["section"], geom["W"], geom["bef"], geom["D"]
    common = {"section": section, "W": W, "bef": bef, "cover_side": cover_side, "ligs": ligs,
              "extend": extend}
    bot = _layer("bottom", **bottom, **common)
    tp = _layer("top", **top, **common)
    fit = ligs if section > SLAB else 0.0
    dsmax = D - cover - fit - bot["bar"] / 2.0
    dcmax = cover_top + fit + tp["bar"] / 2.0
    ds = dsmax - (bot["offset"] if bot["As"] else 0.0)
    dc = dcmax + (tp["offset"] if tp["As"] else 0.0)
    if ds <= 0 or ds >= D:
        raise ValueError("Cover, fitment and bottom bars leave no effective depth ds inside D")
    if dc <= 0 or dc >= D:
        raise ValueError("Cover, fitment and top bars place the top steel outside the section")
    if dc >= ds:
        raise ValueError("The top steel centroid lies at or below the bottom steel centroid")
    return {"bottom": bot, "top": tp, "Ast": bot["As"], "Asc": tp["As"], "ds": ds,
            "dsmax": dsmax, "dc": dc, "dcmax": dcmax, "cover": cover, "coverTop": cover_top,
            "coverSide": cover_side, "ligs": ligs, "extend": extend,
            "maxCentres": min(2.0 * D, 300.0) if section == SLAB else 300.0}


# ---------------------------------------------------------------------------
#  Transformed-section properties (OneSteel RCB-1.1(1) Figs 5.3 to 5.9)
# ---------------------------------------------------------------------------
def uncracked_na(geom: dict[str, Any], n: float, as_bot: float, as_top: float,
                 d_bot: float, d_top: float) -> float:
    """``CalcIuncrkna``: uncracked neutral-axis depth from the top as a fraction of D.

    ``d_top`` is measured from the bottom face (the workbook passes D - dc).
    """
    section, b, D = geom["section"], geom["W"], geom["D"]
    if section in (SLAB, RECTANGULAR):
        return ((b * D ** 2 / 2.0 + as_top * (n - 1.0) * (D - d_top) + as_bot * (n - 1.0) * d_bot)
                / (b * D + as_top * (n - 1.0) + as_bot * (n - 1.0)) / D)
    beff, tf = geom["bef"], geom["Tf"]
    return ((beff * tf ** 2 / 2.0 + b * (D - tf) * (tf + (D - tf) / 2.0)
             + as_top * (n - 1.0) * (D - d_top) + as_bot * (n - 1.0) * d_bot)
            / (beff * tf + b * (D - tf) + as_top * (n - 1.0) + as_bot * (n - 1.0)) / D)


def uncracked_kappa(geom: dict[str, Any], n: float, as_bot: float, as_top: float,
                    d_bot: float, d_top: float) -> float:
    """``CalcIuncrkk``: uncracked second moment of area divided by W D^3 / 12."""
    k = uncracked_na(geom, n, as_bot, as_top, d_bot, d_top)
    section, b, D = geom["section"], geom["W"], geom["D"]
    if section in (SLAB, RECTANGULAR):
        return ((b * D ** 3 / 12.0 + b * D * (D / 2.0 - k * D) ** 2
                 + as_top * (n - 1.0) * (k * D - (D - d_top)) ** 2
                 + as_bot * (n - 1.0) * (d_bot - k * D) ** 2) / (b * D ** 3 / 12.0))
    beff, tf = geom["bef"], geom["Tf"]
    return ((beff * tf ** 3 / 12.0 + beff * tf * (tf / 2.0 - k * D) ** 2
             + b * (D - tf) ** 3 / 12.0 + b * (D - tf) * (k * D - (tf + (D - tf) / 2.0)) ** 2
             + as_top * (n - 1.0) * (k * D - (D - d_top)) ** 2
             + as_bot * (n - 1.0) * (d_bot - k * D) ** 2) / (b * D ** 3 / 12.0))


def _cracked_rect(n: float, ast: float, asc: float, d: float, dsc: float, b: float) -> float:
    p = ast / (b * d)
    x = n * p * (1.0 + (n - 1.0) * asc * dsc / (n * ast * d))
    y = n * p * (1.0 + (n - 1.0) * asc / (n * ast))
    return -y + math.sqrt(y ** 2 + 2.0 * x)


def _cracked_tee(n: float, ast: float, asc: float, d: float, dsc: float, b: float,
                 beff: float, tf: float) -> float:
    p = ast / (b * d)
    x = n * p * (1.0 + (n - 1.0) * asc * dsc / (n * ast * d))
    y = n * p * (1.0 + (n - 1.0) * asc / (n * ast))
    xx = (tf / d) ** 2 * (beff / b - 1.0) + 2.0 * x
    yy = (tf / d) * (beff / b - 1.0) + y
    return -yy + math.sqrt(yy ** 2 + xx)


def cracked_k(geom: dict[str, Any], n: float, ast: float, asc: float, d: float, dsc: float,
              positive: bool) -> float:
    """``CalcIcrkna``: cracked neutral-axis depth as a fraction of d.

    Reproduces the VBA test ``If dsc < k*d Then`` recompute with Asc = 0, which drops the
    compression steel whenever it lies inside the compression zone (concern C6).
    """
    if ast == 0:
        return 0.0
    section, b = geom["section"], geom["W"]
    if section in (SLAB, RECTANGULAR) or not positive:
        k = _cracked_rect(n, ast, asc, d, dsc, b)
        if dsc < k * d:
            k = _cracked_rect(n, ast, 0.0, d, dsc, b)
        return k
    beff, tf = geom["bef"], geom["Tf"]
    k = _cracked_tee(n, ast, asc, d, dsc, b, beff, tf)
    if dsc < k * d:
        k = _cracked_tee(n, ast, 0.0, d, dsc, b, beff, tf)
    if k * d < tf:
        k = _cracked_rect(n, ast, asc, d, dsc, beff)
    return k


def cracked_kappa(geom: dict[str, Any], n: float, ast: float, asc: float, d: float,
                  dsc: float, positive: bool) -> float:
    """``CalcIcrkk``: cracked second moment of area divided by b d^3 / 12."""
    section, b = geom["section"], geom["W"]
    if ast == 0 or d == 0 or b == 0:
        return 0.0
    k = cracked_k(geom, n, ast, asc, d, dsc, positive)
    if k == 0:
        return 0.0
    p = ast / (b * d)
    if section == FLANGED and positive:
        beff, tf = geom["bef"], geom["Tf"]
        if k * d < tf:
            p = ast / (beff * d)
            return (4.0 * k ** 3 + 12.0 * n * p * (1.0 - k) ** 2
                    + 12.0 * (n - 1.0) * p * (asc / ast) * (k - dsc / d) ** 2)
        return (4.0 * (beff / b * k ** 3 - (beff / b - 1.0) * (k - tf / d) ** 3)
                + 12.0 * n * p * (1.0 - k) ** 2
                + 12.0 * (n - 1.0) * p * (asc / ast) * (k - dsc / d) ** 2)
    return (4.0 * k ** 3 + 12.0 * n * p * (1.0 - k) ** 2
            + 12.0 * (n - 1.0) * p * (asc / ast) * (k - dsc / d) ** 2)
