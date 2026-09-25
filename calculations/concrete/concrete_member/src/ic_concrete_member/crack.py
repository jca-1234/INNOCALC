"""Crack control - AS 3600:2018 Cl 8.6 (beams) and Cl 9.5 (slabs).

Transcribes ``Detailed!C89:M164``: uncracked and cracked transformed sections, the
serviceability steel stresses, the maximum-stress Tables 8.6.2.2 and 9.5.2.1
(``Settings!V205:AD241`` through VBA ``CalcTable``) and the calculated crack width of
Cl 8.6.2.3.
"""

from __future__ import annotations

import math
from typing import Any

from .common import ES
from .section import FLANGED, SLAB, cracked_k, cracked_kappa, uncracked_kappa, uncracked_na

CRACK_WIDTHS = (0.2, 0.3, 0.4)
# Table 8.6.2.2(A), Settings!V205:Y213: bar diameter -> sigma.scr for w'max 0.2 / 0.3 / 0.4 mm.
BEAM_BAR = ((10, 190, 265, 335), (12, 175, 245, 305), (16, 155, 215, 270), (20, 140, 195, 240),
            (24, 125, 175, 215), (28, 115, 160, 200), (32, 105, 150, 185), (36, 100, 140, 175),
            (40, 90, 130, 165))
# Table 8.6.2.2(B) and Table 9.5.2.1(B), Settings!AA205:AD210 and AA221:AD226: bar centres.
SPACING = ((50, 200, 300, 400), (100, 170, 270, 360), (150, 155, 245, 330),
           (200, 145, 225, 300), (250, 135, 210, 280), (300, 125, 200, 260))
# Table 9.5.2.1(A), slabs D <= 300 (Settings!V221:Y227) and D > 300 (Settings!V235:Y241).
SLAB_BAR_THIN = ((6, 210, 290, 365), (8, 195, 260, 340), (10, 180, 240, 315),
                 (12, 165, 225, 290), (16, 150, 205, 260), (20, 140, 190, 235),
                 (24, 125, 175, 215))
SLAB_BAR_THICK = ((6, 230, 315, 390), (8, 210, 290, 360), (10, 190, 265, 335),
                  (12, 175, 245, 305), (16, 155, 215, 270), (20, 140, 195, 240),
                  (24, 125, 175, 215))
BEYOND_TABLE = 0.01  # CalcTable dLargerthanLast


def table_lookup(value: float, column: int, table: tuple[tuple[float, ...], ...]) -> float:
    """VBA ``CalcTable`` with dSmallerthanfirst = -1 (first row) and dLargerthanLast = 0.01."""
    if value < table[0][0]:
        return float(table[0][column])
    if value > table[-1][0]:
        return BEYOND_TABLE
    for low, high in zip(table, table[1:]):
        if value <= high[0]:
            return (value - low[0]) / (high[0] - low[0]) * (high[column] - low[column]) + low[column]
    return float(table[-1][column])


def uncracked(geom: dict[str, Any], reo: dict[str, Any], n: float,
              with_steel: bool) -> dict[str, float]:
    """Detailed!D72:D76 and D91:D93."""
    D, W = geom["D"], geom["W"]
    args = (reo["Ast"], reo["Asc"], reo["ds"], D - reo["dc"])
    if with_steel:
        uk = uncracked_na(geom, n, *args)
        ukappa = uncracked_kappa(geom, n, *args)
        Iuncrk = ukappa * W * D ** 3 / 12.0 / 1e6
    else:
        uk, ukappa, Iuncrk = geom["na"] / D, 1.0, geom["Ig"]
    na = uk * D
    section, bef, Tf = geom["section"], geom["bef"], geom["Tf"]
    if section == FLANGED:
        act_pos = W * (D - Tf) + bef * (Tf - na) if na <= Tf else W * (D - na)
        act_neg = bef * na if na <= Tf else bef * Tf + (na - Tf) * W
        actm_pos = W * D / 2.0 if Tf < D / 2.0 else (Tf - D / 2.0) * (bef - W) + W * D / 2.0
        actm_neg = Tf * (bef - W) + W * D / 2.0 if Tf < D / 2.0 else bef * D / 2.0
    else:
        act_pos, act_neg = W * (D - na), W * na
        actm_pos = actm_neg = W * D / 2.0
    return {"uk": uk, "NA": na, "ukappa": ukappa, "Iuncrk": Iuncrk, "withSteel": with_steel,
            "ActPos": act_pos, "ActNeg": act_neg, "ActmPos": actm_pos, "ActmNeg": actm_neg}


def _face(geom: dict[str, Any], n: float, *, positive: bool, Ast: float, Asc: float, d: float,
          dmax: float, dc: float, ms: float, ms1: float, bar: float, centres: float, fsy: float,
          column: int) -> dict[str, Any]:
    section, W, bef, Tf, D = geom["section"], geom["W"], geom["bef"], geom["Tf"], geom["D"]
    k = cracked_k(geom, n, Ast, Asc, d, dc, positive)
    kd = k * d
    kappa = cracked_kappa(geom, n, Ast, Asc, d, dc, positive)
    width = bef if (positive and section == FLANGED and kd < Tf) else W
    Icr = kappa * width * d ** 3 / 12.0 / 1e6
    fscr = n * abs(ms) * (dmax - kd) / Icr if Icr else 0.0
    fscr1 = ms1 / ms * fscr if ms else 0.0
    if section == SLAB:
        bar_table = SLAB_BAR_THIN if D <= 300 else SLAB_BAR_THICK
    else:
        bar_table = BEAM_BAR
    limit_bar = table_lookup(bar, column, bar_table)
    limit_spacing = table_lookup(centres, column, SPACING)
    limit_yield = 0.8 * fsy
    limit = min(limit_yield, max(limit_bar, limit_spacing))
    return {"Ast": Ast, "Asc": Asc, "d": d, "dmax": dmax, "dc": dc, "k": k, "kd": kd,
            "kappa": kappa, "IcrWidth": width, "Icr": Icr, "fscr": fscr, "fscr1": fscr1,
            "limitBar": limit_bar, "limitSpacing": limit_spacing, "limit": limit,
            "limit1": limit_yield, "bar": bar, "centres": centres,
            "ratio": abs(fscr) / limit if limit else 0.0,
            "ratio1": abs(fscr1) / limit_yield if limit_yield else 0.0}


def stresses(geom: dict[str, Any], reo: dict[str, Any], flex: dict[str, Any], *, n: float,
             fsy: float, ms: float, ms1: float, wmax: float) -> dict[str, Any]:
    column = CRACK_WIDTHS.index(wmax) + 1
    D = geom["D"]
    pos, neg = flex["positive"], flex["negative"]
    positive = _face(geom, n, positive=True, Ast=pos["Ast"], Asc=pos["Asc"], d=pos["d"],
                     dmax=pos["dmax"], dc=pos["dc"], ms=ms, ms1=ms1, bar=reo["bottom"]["bar"],
                     centres=reo["bottom"]["centres"], fsy=fsy, column=column)
    negative = _face(geom, n, positive=False, Ast=neg["Ast"], Asc=neg["Asc"], d=neg["d"],
                     dmax=neg["dmax"], dc=neg["dc"], ms=ms, ms1=ms1, bar=reo["top"]["bar"],
                     centres=reo["top"]["centres"], fsy=fsy, column=column)
    governing = positive if flex["Mstar"] >= 0 else negative
    return {"wmax": wmax, "column": column, "positive": positive, "negative": negative,
            "governing": governing, "Ms": ms, "Ms1": ms1,
            "clause": "Cl 9.5.2.1" if geom["section"] == SLAB else "Cl 8.6.2.2",
            "tableBar": ("Table 9.5.2.1(A)" if geom["section"] == SLAB else "Table 8.6.2.2(A)"),
            "tableSpacing": ("Table 9.5.2.1(B)" if geom["section"] == SLAB
                             else "Table 8.6.2.2(B)"),
            "sideFace": _side_face(geom, D)}


def _side_face(geom: dict[str, Any], D: float) -> str:
    """Detailed!D87 note on side-face reinforcement (Cl 8.6.4 as cited by the workbook)."""
    if geom["section"] == SLAB:
        return "Not applicable to slabs"
    depth = D - (geom["Tf"] if geom["section"] == FLANGED else 0.0)
    need = "N12-200 or N16-300" if depth > 750 else "Not required as face depth <= 750 mm"
    return f"{need} - face depth = {depth:.0f} mm"


def width(geom: dict[str, Any], reo: dict[str, Any], mat: dict[str, float],
          creep: dict[str, Any], crack: dict[str, Any], *, nstar: float, shape_bot: str,
          shape_top: str, mstar: float) -> dict[str, Any]:
    """Cl 8.6.2.3 calculated crack width, Detailed!C121:M164.

    The negative-moment tension depth uses D - kd (deliberate departure D3); the workbook
    limits hc.eff by kd itself.
    """
    D, W, bef, Tf, section = geom["D"], geom["W"], geom["bef"], geom["Tf"], geom["section"]
    Ec, fcc, ecs = mat["Ec"], creep["fcc"], creep["ecs"]
    ne = (1.0 + fcc) * ES / Ec
    fctf = mat["fctf"]
    fct = 0.6 * fctf
    fctm = 1.4 * fct
    axial_stress = -nstar * 1000.0 / geom["Ag"]
    axial_strain = axial_stress / Ec * 1e6
    faces = {}
    for name, face, cover, shape, bar, centres in (
            ("positive", crack["positive"], reo["cover"], shape_bot, reo["bottom"]["bar"],
             reo["bottom"]["centres"]),
            ("negative", crack["negative"], reo["coverTop"], shape_top, reo["top"]["bar"],
             reo["top"]["centres"])):
        d, kd, fscr = face["d"], face["kd"], face["fscr"]
        hc = min(2.5 * (D - d), (D - kd) / 3.0, D / 2.0)
        hca = min(hc, D - kd)
        if name == "positive":
            if section == FLANGED:
                aceff = W * hca if hca < D - Tf else W * (D - Tf) + bef * (hca - (D - Tf))
            else:
                aceff = bef * hca
        else:
            if section == FLANGED:
                aceff = bef * hca if hca <= Tf else bef * Tf + (hca - Tf) * W
            else:
                aceff = W * hca
        peff = face["Ast"] / aceff if aceff else 0.0
        min_diff = 0.6 * fscr / ES * 1e6
        steel_strain = fscr / ES * 1e6
        tension_term = -0.6 * fctm / (ES * peff) * 1e6 if peff else 0.0
        stiffening = 1.0 + ne * peff
        diff1 = steel_strain + tension_term * stiffening + ecs
        diff = max(diff1, min_diff)
        if name == "positive":
            top = -steel_strain * kd / (D - kd) + axial_strain
            bottom = steel_strain * (D - kd) / (face["dmax"] - kd) + axial_strain
        else:
            top = steel_strain * (D - kd) / (face["dmax"] - kd) + axial_strain
            bottom = -steel_strain * kd / (D - kd) + axial_strain
        e1 = max(bottom, top)
        e2 = max(0.0, min(bottom, top))
        k1 = 1.6 if shape == "P" else 0.8
        if mstar != 0:
            k2 = 0.5 if nstar == 0 else max(0.5, min(1.0, (e1 + e2) / (2.0 * e1)))
        else:
            k2 = 1.0 if nstar < 0 else 0.0
        clear_cover = cover + reo["ligs"]
        simple_max = 5.0 * (clear_cover + 0.5 * bar)
        sr1 = 1.3 * (D - kd)
        sr2 = 3.4 * clear_cover + 0.3 * k1 * k2 * bar / peff if peff else math.inf
        sr = min(sr1, sr2)
        w = sr * diff / 1e6
        faces[name] = {"hc": hc, "hca": hca, "Aceff": aceff, "peff": peff, "minDiff": min_diff,
                       "steelStrain": steel_strain, "tensionTerm": tension_term,
                       "stiffening": stiffening, "diff1": diff1, "diff": diff, "top": top,
                       "bottom": bottom, "e1": e1, "e2": e2, "shape": shape, "k1": k1, "k2": k2,
                       "clearCover": clear_cover, "simpleMax": simple_max, "sr1": sr1,
                       "sr2": sr2, "sr": sr, "srDisplay": sr if centres <= simple_max else 0.0,
                       "w": w}
    governing = faces["positive"] if mstar >= 0 else faces["negative"]
    return {"ne": ne, "fctf": fctf, "fct": fct, "fctm": fctm, "ecs": ecs, "fcc": fcc,
            "Nstar": nstar, "axialStress": axial_stress, "axialStrain": axial_strain,
            "positive": faces["positive"], "negative": faces["negative"],
            "governing": governing, "w": governing["w"], "wmax": crack["wmax"],
            "ratio": governing["w"] / crack["wmax"]}
