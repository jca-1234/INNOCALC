"""Strength in bending - AS 3600:2018 Cl 8.1 (beams) and Cl 9.1 (slabs).

Transcribes ``Detailed!C7:L67`` (rectangular stress block with tension and compression
steel, WRH Eqs 4.49 to 4.58 and RCB Eq 3.78 for a T or L beam with the stress block in
the web) and ``Detailed!C69:R87`` (minimum strength, Cl 8.1.6.1 / Cl 9.1.1).
"""

from __future__ import annotations

import math
from typing import Any

from .common import EPS_CU, ES, calc_ast, ratio
from .section import FLANGED, RECTANGULAR, SLAB

KU_DUCTILITY = 0.36  # Cl 8.1.5
SLAB_ALPHA_B = {"O": 0.20, "C": 0.24, "T": 0.19, "F": 0.19}  # Settings!AA43
SLAB_TYPES = {"O": "One-way slab", "C": "Two-way slab supported by columns",
              "T": "Two-way slab supported by walls or beams", "F": "Two-way footing"}


def stress_block(fc: float) -> dict[str, float]:
    """Eqs 8.1.3(1) and (2)."""
    alpha2 = max(0.67, 0.85 - 0.0015 * fc)
    gamma = max(0.67, 0.97 - 0.0025 * fc)
    return {"alpha2": alpha2, "gamma": gamma}


def phi_bending(klass: str, kuo: float) -> float:
    """Table 2.2.2(b): Class N 1.24 - 13 kuo/12 within 0.65 to 0.85; Class L 0.65."""
    return min(0.85, max(0.65, 1.24 - 13.0 * kuo / 12.0)) if klass == "N" else 0.65


def _face(*, positive: bool, Ast: float, Asc: float, d: float, dmax: float, dc: float,
          b: float, W: float, bef: float, Tf: float, section: int, fc: float, fsy: float,
          alpha2: float, gamma: float, klass: str, asc_global: float, dc_global: float,
          mstar: float) -> dict[str, Any]:
    """One bending direction (``Detailed`` columns D (+ve) or J (-ve))."""
    esy = fsy / ES
    kub = EPS_CU / (EPS_CU + esy)
    asc = min(Asc, Ast)
    ku_y = (1.0 / (alpha2 * gamma) * (Ast - asc) * (fsy / fc) / (b * d)) if b * d else 0.0
    if Ast == asc or ku_y == 0:
        eps_st = eps_sc = 0.0
    else:
        eps_st = EPS_CU * (d - ku_y * d) / (ku_y * d)
        eps_sc = EPS_CU * (ku_y * d - dc) / (ku_y * d)
    yield_valid = eps_st >= esy and eps_sc >= esy
    mu_yield = 0.0
    if yield_valid and ku_y > 0:
        mu_yield = (fsy * asc * (d - dc) + alpha2 * fc * b * gamma * ku_y * d
                    * (d - 0.5 * gamma * ku_y * d)) / 1e6
    u1 = (EPS_CU * ES * asc - fsy * Ast) / (alpha2 * fc * gamma * b * d)
    u2 = -EPS_CU * dc * ES * asc / (alpha2 * fc * gamma * b * d ** 2)
    ku_elastic = (-u1 + math.sqrt(u1 ** 2 - 4.0 * u2)) / 2.0
    kud_trial = (ku_y if yield_valid else ku_elastic) * d
    ts = Ast * fsy / 1000.0
    if positive:
        asc_test, dc_test = asc_global, dc_global
    else:
        asc_test, dc_test = Ast, dc
    if asc_test > 0 and kud_trial > dc_test:
        g_kud = gamma * kud_trial
    else:
        g_kud = Ast * fsy / (alpha2 * fc * b)
    kud_flange = g_kud / gamma
    in_flange = not (positive and section == FLANGED and g_kud > Tf)
    cf = 0.0 if in_flange else alpha2 * fc * Tf * (bef - W) / 1000.0
    if in_flange:
        kud = kud_flange
    else:
        kud = (ts - cf) * 1000.0 / (alpha2 * fc * gamma * W)
    gkud = gamma * kud
    if positive:
        asc_in_comp = asc > 0 and kud_trial > dc
    else:
        asc_in_comp = asc > 0 and kud > dc
    cs = (ES * min(esy, EPS_CU * (kud - dc) / kud) * asc / 1000.0) if asc_in_comp and kud else 0.0
    cc = alpha2 * fc * gkud * b / 1000.0 if in_flange else ts - cf
    mu_flange = (cs * (d - dc) + cc * (d - 0.5 * g_kud)) / 1000.0
    mu_web = (cf * (d - 0.5 * Tf) + cc * (d - 0.5 * gamma * kud)) / 1000.0
    eps_s = EPS_CU * (d - kud) / kud if kud else 0.0
    ku = max(0.0, kud / d)
    if ku > kub:
        mu = 0.0
    elif yield_valid:
        mu = mu_yield
    else:
        mu = mu_flange if in_flange else mu_web
    kuo = ku * d / dmax
    phi = phi_bending(klass, kuo)
    phi_mu = max(0.0, phi * mu)
    loaded = mstar > 0 if positive else mstar < 0
    ast_req = calc_ast(fsy, fc, b, d, abs(mstar), phi, alpha2) if loaded else 0.0
    return {
        "Ast": Ast, "Asc": asc, "d": d, "dmax": dmax, "dc": dc, "b": b, "esy": esy, "kub": kub,
        "kuYield": ku_y, "epsSt": eps_st, "epsSc": eps_sc, "yieldValid": yield_valid,
        "MuYield": mu_yield, "u1": u1, "u2": u2, "kuElastic": ku_elastic, "kudTrial": kud_trial,
        "gammaKudTrial": g_kud, "kudFlange": kud_flange, "inFlange": in_flange,
        "ascInCompression": asc_in_comp, "Ts": ts, "Cs": cs, "Cc": cc, "Cf": cf,
        "balance": ts - cc - cs if in_flange else ts - cc - cf,
        "MuFlange": mu_flange, "MuWeb": mu_web, "kud": kud, "gammaKud": gkud, "epsS": eps_s,
        "steelYields": eps_s >= esy, "ku": ku, "Mu": mu, "kuo": kuo, "phi": phi, "phiMu": phi_mu,
        "AstReq": ast_req, "leverFactor": (phi_mu * 1e6 / (phi * fsy * d * Ast)) if Ast else 0.0,
        "klass": klass,
    }


def strength(geom: dict[str, Any], reo: dict[str, Any], *, fc: float, fsy: float,
             class_bot: str, class_top: str, mstar: float) -> dict[str, Any]:
    block = stress_block(fc)
    section, D, W, bef, Tf = geom["section"], geom["D"], geom["W"], geom["bef"], geom["Tf"]
    Ast, Asc, ds, dc = reo["Ast"], reo["Asc"], reo["ds"], reo["dc"]
    positive = _face(
        positive=True, Ast=Ast, Asc=Asc, d=ds, dmax=reo["dsmax"], dc=dc,
        b=W if section in (SLAB, RECTANGULAR) else bef, W=W, bef=bef, Tf=Tf, section=section,
        fc=fc, fsy=fsy, **block, klass=class_bot, asc_global=Asc, dc_global=dc, mstar=mstar)
    negative = _face(
        positive=False, Ast=Asc, Asc=Ast, d=D - dc, dmax=D - reo["dcmax"], dc=D - ds, b=W, W=W,
        bef=bef, Tf=Tf, section=section, fc=fc, fsy=fsy, **block, klass=class_top,
        asc_global=Ast, dc_global=D - ds, mstar=mstar)
    governing = positive if mstar >= 0 else negative
    return {**block, "eu": EPS_CU, "Es": ES, "esy": fsy / ES, "kub": positive["kub"],
            "positive": positive, "negative": negative, "sign": "+" if mstar >= 0 else "-",
            "governing": governing, "As": governing["Ast"], "Mstar": mstar,
            "phiMu": governing["phiMu"], "ku": governing["ku"], "kuo": governing["kuo"],
            "tfMin": (Ast * fsy / (block["alpha2"] * fc * bef)) if section == FLANGED else 0.0,
            "compressionInFlange": (section != FLANGED
                                    or block["alpha2"] * fc * bef * Tf >= Ast * fsy)}


def minimum_strength(geom: dict[str, Any], reo: dict[str, Any], flex: dict[str, Any], *,
                     fc: float, fsy: float, uncracked: dict[str, Any], slab_type: str,
                     basis: str) -> dict[str, Any]:
    """Cl 8.1.6.1 (beams) and Cl 9.1.1 (slabs): (Muo)min = 1.2 Z f'ct.f, or deemed Ast.min."""
    section, D, W, bef, Tf = geom["section"], geom["D"], geom["W"], geom["bef"], geom["Tf"]
    ds, dc = reo["ds"], reo["dc"]
    fctf = 0.6 * math.sqrt(fc)
    Iuncrk = uncracked["Iuncrk"]
    na = uncracked["NA"]
    Zb = Iuncrk * 1000.0 / (D - na)
    Zt = Iuncrk * 1000.0 / na
    mu_min_pos = 1.2 * Zb * fctf / 1000.0
    mu_min_neg = 1.2 * Zt * fctf / 1000.0
    pos, neg, alpha2 = flex["positive"], flex["negative"], flex["alpha2"]
    ast_min_calc_pos = calc_ast(fsy, fc, bef, ds, pos["phi"] * mu_min_pos, pos["phi"], alpha2)
    ast_min_calc_neg = calc_ast(fsy, fc, W, D - dc, neg["phi"] * mu_min_neg, neg["phi"], alpha2)
    ratio_f = bef / W
    web_tension = max(0.2 * ratio_f ** 0.25, 0.2 + (ratio_f - 1.0) * (0.4 * Tf / D - 0.18))
    flange_tension = max(0.2 * ratio_f ** (2.0 / 3.0),
                         0.2 + (ratio_f - 1.0) * (0.25 * Tf / D - 0.08))
    if section == SLAB:
        ab_pos = ab_neg = SLAB_ALPHA_B[slab_type]
    elif section == RECTANGULAR:
        ab_pos = ab_neg = 0.2
    else:
        ab_pos, ab_neg = web_tension, flange_tension
    deemed_pos = ab_pos * fctf / fsy * (D / ds) ** 2 * W * ds
    deemed_neg = ab_neg * fctf / fsy * (D / (D - dc)) ** 2 * W * (D - dc)
    positive = flex["Mstar"] >= 0
    deemed = deemed_pos if positive else deemed_neg
    actual = ast_min_calc_pos if positive else ast_min_calc_neg
    required = {"D": deemed, "A": actual}.get(basis, min(deemed, actual))
    provided = flex["As"]
    if section == SLAB:
        clause = {"O": "Cl 8.1.6.1", "C": "Cl 9.1.1(a)", "T": "Cl 9.1.1(b)",
                  "F": "Cl 21.3.1(b)(i)"}[slab_type]
    else:
        clause = "Cl 8.1.6.1"
    return {"fctf": fctf, "Zb": Zb, "Zt": Zt, "MuoMinPos": mu_min_pos, "MuoMinNeg": mu_min_neg,
            "AstMinCalcPos": ast_min_calc_pos, "AstMinCalcNeg": ast_min_calc_neg,
            "alphaBPos": ab_pos, "alphaBNeg": ab_neg, "AstMinDeemedPos": deemed_pos,
            "AstMinDeemedNeg": deemed_neg, "deemed": deemed, "actual": actual,
            "basis": basis, "AsMin": required, "As": provided, "clause": clause,
            "ratio": ratio(required, provided)}


def ductility(flex: dict[str, Any], reo: dict[str, Any]) -> dict[str, Any]:
    """Cl 8.1.5 kuo <= 0.36, or Asc >= 0.01 b kuo do when kuo exceeds 0.36 (Tedds AS3600-2018)."""
    face = flex["governing"]
    kuo = face["kuo"]
    asc_required = 0.01 * face["b"] * kuo * face["dmax"]
    asc_available = face["Asc"] if face["ascInCompression"] else 0.0
    if kuo <= KU_DUCTILITY or asc_available <= 0:
        value, basis = kuo / KU_DUCTILITY, "kuo / 0.36"
    else:
        value, basis = ratio(asc_required, asc_available), "Asc.req / Asc"
    return {"kuo": kuo, "ku": face["ku"], "limit": KU_DUCTILITY, "AscRequired": asc_required,
            "AscAvailable": asc_available, "basis": basis, "ratio": value,
            "exceedsBalanced": face["ku"] > face["kub"]}


def bar_spacing(geom: dict[str, Any], reo: dict[str, Any], mstar: float) -> dict[str, Any]:
    """Cl 8.6.1(b) / Cl 9.5.1(b): tension face bar centres (not checked for area input)."""
    face = reo["bottom"] if mstar >= 0 else reo["top"]
    applicable = face["mode"] != "A" and face["As"] > 0
    limit = reo["maxCentres"]
    return {"face": "bottom" if mstar >= 0 else "top", "centres": face["centres"],
            "limit": limit, "applicable": applicable,
            "clause": "Cl 9.5.1(b)" if geom["section"] == SLAB else "Cl 8.6.1(b)",
            "ratio": face["centres"] / limit if applicable else 0.0,
            "bottomRatio": reo["bottom"]["centres"] / limit, "topRatio": reo["top"]["centres"] / limit}
