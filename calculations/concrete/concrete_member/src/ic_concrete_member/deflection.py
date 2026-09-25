"""Deflection - AS 3600:2018 Cl 8.5 (beams) and Cl 9.4 (slabs).

* ``deemed`` transcribes ``BeamDefl!D14:E55`` (Cl 8.5.4) and ``SlabDefl!D14:E53``
  (Cl 9.4.4.1) deemed-to-comply span-to-depth checks.
* ``calculated`` transcribes ``Defl!C13:U81``: Cl 8.5.3 effective second moment of area at
  the left, midspan and right positions, the Iav combination and long-term deflection from
  gross elastic deflections supplied by the analysis.
* ``wrh`` transcribes ``Creep&Shrink!D63:H86``: the Warner, Rangan and Hall alternative
  shrinkage and creep deflections (information only).
"""

from __future__ import annotations

import math
from typing import Any

from .common import ES, calc_ast, ratio
from .section import FLANGED, RECTANGULAR, SLAB, cracked_k, cracked_kappa, uncracked_kappa, uncracked_na

PSI = {"N": (0.7, 0.4), "S": (1.0, 0.6)}  # AS/NZS 1170.0 Table 4.1, normal and storage use
BEAM_K2 = {"I": 1.5 / 384.0, "E": 2.4 / 384.0, "S": 5.0 / 384.0}  # Cl 8.5.4
SLAB_K4 = {"I": 2.1, "E": 1.75, "S": 1.4}  # Cl 9.4.4.1
SPAN_TYPES = {"S": "Simply supported", "E": "End span", "I": "Interior span"}
CREEP_SPAN_TYPES = {"S": "Simple", "E": "Exterior", "I": "Interior", "C": "Cantilever",
                    "P": "Propped", "F": "Fixed", "O": "Other"}
POSITIONS = ("L", "X", "R")


def _cracked_axis(n: float, p: float, pc: float, dc_ds: float) -> float:
    term = n * p + (n - 1.0) * pc
    return math.sqrt(term ** 2 + 2.0 * (n * p + (n - 1.0) * pc * dc_ds)) - term


def deemed(geom: dict[str, Any], reo: dict[str, Any], mat: dict[str, float], *, fc: float,
           span_type: str, spans: str, wsdl: float, wll: float, load_type: str,
           lef_total: float, lef_inc: float, k3: float, class_bot: str,
           class_top: str) -> dict[str, Any]:
    section = geom["section"]
    L = geom["Lm"]
    wdl = geom["swt"]
    g = wdl + wsdl
    psi_s, psi_l = PSI[load_type]
    fd = max(1.35 * g, 1.2 * g + 1.5 * wll)
    divisor_pos = (16.0 if class_bot == "N" else 14.0) if span_type == "I" else (
        11.0 if span_type == "E" else 8.0)
    if span_type == "S":
        divisor_neg = 0.0
    elif span_type == "I":
        divisor_neg = 11.0
    else:
        divisor_neg = (9.0 if class_top == "N" else 8.0) if spans == "2" else 10.0
    m_pos = fd * (L / 1000.0) ** 2 / divisor_pos
    m_neg = -fd * (L / 1000.0) ** 2 / divisor_neg if divisor_neg else 0.0
    Ast, Asc, ds, dc = reo["Ast"], reo["Asc"], reo["ds"], reo["dc"]
    Ec, n = mat["Ec"], mat["n"]
    slab = section == SLAB
    width = 1000.0 if slab else geom["bef"]
    p, pc = Ast / (width * ds), Asc / (width * ds)
    ku = _cracked_axis(n, p, pc, dc / ds)
    na = ku * ds
    test_bar = reo["top"]["bar"] if slab else reo["bottom"]["bar"]
    asc_ignored = na - test_bar / 2.0 < dc
    kcs = max(0.8, 2.0 - 1.2 * ((0.0 if asc_ignored else Asc) / Ast)) if Ast else 2.0
    fdef = (1.0 + kcs) * g + (psi_s + psi_l * kcs) * wll
    fdefi = kcs * g + (psi_s + psi_l * kcs) * wll
    out = {"L": L, "wdl": wdl, "wsdl": wsdl, "g": g, "wll": wll, "loadType": load_type,
           "psiS": psi_s, "psiL": psi_l, "Fd": fd, "Mpos": m_pos, "Mneg": m_neg,
           "divisorPos": divisor_pos, "divisorNeg": divisor_neg, "spanType": span_type,
           "spans": spans, "p": p, "pc": pc, "dcds": dc / ds, "n": n, "ku": ku, "NA": na,
           "ascIgnored": asc_ignored and Asc > 0, "kcs": kcs, "Fdef": fdef, "Fdefi": fdefi,
           "Ec": Ec, "lefDelta": lef_total, "lefDeltaInc": lef_inc, "ds": ds, "Ast": Ast,
           "Asc": Asc, "dc": dc, "slab": slab,
           "clause": "Cl 9.4.4.1" if slab else "Cl 8.5.4"}
    if slab:
        k4 = SLAB_K4[span_type]

        def required(limit: float, load: float) -> float:
            return 0.0 if load == 0 else L / (k3 * k4 * (Ec / limit / (load / 1000.0)) ** (1.0 / 3.0))

        out.update({"k3": k3, "k4": k4})
    else:
        beta = max(1.0, geom["bef"] / geom["W"])
        threshold = 0.001 * fc ** (1.0 / 3.0) / beta ** (2.0 / 3.0)
        if p >= threshold:
            k1 = min(0.1 / beta ** (2.0 / 3.0), (5.0 - 0.04 * fc) * p + 0.002)
        else:
            k1 = min(0.06 / beta ** (2.0 / 3.0), 0.055 * fc ** (1.0 / 3.0) / beta ** (2.0 / 3.0)
                     - 50.0 * p)
        k2 = BEAM_K2[span_type]
        bef = geom["bef"]

        def required(limit: float, load: float) -> float:
            if load == 0:
                return 0.0
            if k1 * k2 <= 0:
                return math.inf
            return L / ((k1 / limit * bef * Ec / (k2 * load)) ** (1.0 / 3.0))

        out.update({"beta": beta, "k1Threshold": threshold, "k1": k1, "k2": k2})
    dmin, dmini = required(lef_total, fdef), required(lef_inc, fdefi)
    base = reo["bottom"]["bar"] / 2.0 + reo["cover"]
    out.update({"dmin": dmin, "dmini": dmini, "Dmin": base + dmin, "Dmini": base + dmini,
                "ratioTotal": ratio(dmin, ds), "ratioIncremental": ratio(dmini, ds),
                "ratioLive": ratio(wll, g)})
    return out


def _position(geom: dict[str, Any], reo: dict[str, Any], mat: dict[str, float], flex: dict[str, Any], *,
              fc: float, fsy: float, mstar: float, ms: float, top_override: float,
              bottom_override: float, ecs: float, use_fcs: bool, with_steel: bool) -> dict[str, Any]:
    section, D, W, bef, Tf = geom["section"], geom["D"], geom["W"], geom["bef"], geom["Tf"]
    ds, dc, n = reo["ds"], reo["dc"], mat["n"]
    alpha2 = flex["alpha2"]
    width = bef if mstar >= 0 else W
    depth = ds if mstar > 0 else D - dc
    top_req = (calc_ast(fsy, fc, width, depth, abs(mstar), flex["negative"]["phi"], alpha2)
               if mstar < 0 else 0.0)
    bot_req = (calc_ast(fsy, fc, width, depth, mstar, flex["positive"]["phi"], alpha2)
               if mstar > 0 else 0.0)

    def adopt(override: float, required_area: float) -> float:
        if mstar == 0:
            return 0.0
        if override > 0:
            return override
        return 0.0 if override < 0 else required_area

    top_as, bot_as = adopt(top_override, top_req), adopt(bottom_override, bot_req)
    if math.isinf(top_as) or math.isinf(bot_as):
        raise ValueError(f"Calculated deflection: M* = {mstar:g} kNm exceeds the section capacity; "
                         "enter the steel area at this position")
    if with_steel:
        na = uncracked_na(geom, n, bot_as, top_as, ds, D - dc) * D
        ukappa = uncracked_kappa(geom, n, bot_as, top_as, ds, D - dc)
        Iuncrk = ukappa * W * D ** 3 / 12.0 / 1e6
    else:
        na, ukappa, Iuncrk = geom["na"], 1.0, geom["Ig"]
    ast = 0.0 if mstar == 0 else (bot_as if mstar > 0 else top_as)
    asc = 0.0 if mstar == 0 else (top_as if mstar > 0 else bot_as)
    dcomp = dc if mstar > 0 else D - ds
    k = cracked_k(geom, n, ast, asc, depth, dcomp, mstar >= 0)
    kd = k * depth
    comp_bar = reo["top"]["bar"] if mstar > 0 else reo["bottom"]["bar"]
    if asc > 0:
        use_comp = "No" if dcomp + max(5.0, 0.45 * comp_bar) > kd else "Yes"
    else:
        use_comp = "-"
    yt = D - na if mstar > 0 else na
    pw = ast / (width * depth)
    pcw = asc / (width * (D - dcomp))
    sigma_cs = max(0.0, (2.5 * pw - 0.8 * pcw) / (1.0 + 50.0 * pw) * ES * ecs * 1e-6
                   if use_fcs else 0.0)
    fctf = mat["fctf"]
    Mcr = max((fctf - sigma_cs) * Iuncrk / yt, 0.0)
    kappa = cracked_kappa(geom, n, ast, asc, depth, dcomp, mstar >= 0)
    if section in (SLAB, RECTANGULAR):
        icr_width = W
    else:
        icr_width = W if mstar < 0 else (bef if kd < Tf else W)
    Icr = icr_width * kappa * depth ** 3 / 12.0 / 1e6
    Ief_max = 0.6 * geom["Ig"] if pw < 0.005 else geom["Ig"]
    if ms == 0 or Icr == 0:
        Ief = Icr
    else:
        cracking = min(1.0, abs(Mcr / ms))
        Ief = min(Icr / (1.0 - (1.0 - Icr / Iuncrk) * cracking ** 2), Ief_max)
    return {"Mstar": mstar, "Ms": ms, "width": width, "d": depth, "topReq": top_req,
            "bottomReq": bot_req, "topAs": top_as, "bottomAs": bot_as, "NA": na,
            "ukappa": ukappa, "Iuncrk": Iuncrk, "Ast": ast, "Asc": asc, "dc": dcomp, "k": k,
            "kd": kd, "useComp": use_comp, "yt": yt, "ecs": ecs, "pw": pw, "pcw": pcw,
            "sigmaCs": sigma_cs, "Mcr": Mcr, "kappa": kappa, "IcrWidth": icr_width, "Icr": Icr,
            "IefMax": Ief_max, "Ief": Ief}


def calculated(geom: dict[str, Any], reo: dict[str, Any], mat: dict[str, float],
               flex: dict[str, Any], *, fc: float, fsy: float, positions: dict[str, dict[str, float]],
               ecs: float, use_fcs: bool, with_steel: bool, delta_dl: float, delta_ll: float,
               psi_s: float, psi_l: float, cutoff_percent: float,
               limits: dict[str, tuple[float, float]]) -> dict[str, Any]:
    rows = {key: _position(geom, reo, mat, flex, fc=fc, fsy=fsy, ecs=ecs, use_fcs=use_fcs,
                           with_steel=with_steel, **positions[key]) for key in POSITIONS}
    peak = max(abs(rows[key]["Mstar"]) for key in POSITIONS)
    cutoff = cutoff_percent / 100.0 * peak
    m1 = 0.0 if abs(rows["L"]["Mstar"]) < cutoff else rows["L"]["Mstar"]
    mx = rows["X"]["Mstar"]
    m2 = 0.0 if abs(rows["R"]["Mstar"]) < cutoff else rows["R"]["Mstar"]
    ief = {key: rows[key]["Ief"] for key in POSITIONS}
    cases = [
        ("interior", "Interior/Fixed", "(M + (L + R) / 2) / 2", m1 != 0 and m2 != 0,
         (ief["X"] + (ief["L"] + ief["R"]) / 2.0) / 2.0),
        ("exteriorR", "Exterior/Propped (R. Cont.)", "(M + R) / 2",
         m1 == 0 and mx != 0 and m2 != 0, (ief["X"] + ief["R"]) / 2.0),
        ("exteriorL", "Exterior/Propped (L. Cont.)", "(M + L) / 2",
         m1 != 0 and mx != 0 and m2 == 0, (ief["X"] + ief["L"]) / 2.0),
        ("simple", "Simple", "M", m1 == 0 and mx != 0 and m2 == 0, ief["X"]),
        ("cantileverR", "Cantilever (R. Cont.)", "R", m1 == 0 and mx == 0 and m2 != 0, ief["R"]),
        ("cantileverL", "Cantilever (L. Cont.)", "L", m1 != 0 and mx == 0 and m2 == 0, ief["L"]),
    ]
    active = [case for case in cases if case[3]]
    valid = len(active) == 1
    key, label, code, _, Iav = active[0] if valid else cases[0]
    cant_r, cant_l = valid and key == "cantileverR", valid and key == "cantileverL"
    at = "R" if cant_r else ("L" if cant_l else "X")
    ratio_i = rows[at]["Iuncrk"] / Iav if Iav else 0.0
    ast_at, asc_at = rows[at]["Ast"], rows[at]["Asc"]
    if not Iav:
        kcs = 0.8
    else:
        share = 1.0 if ast_at == 0 else min(asc_at / ast_at, 1.0)
        kcs = max(0.8, 2.0 - 1.2 * share)
    short = (delta_dl + psi_s * delta_ll) * ratio_i
    sustained = (delta_dl + psi_l * delta_ll) * ratio_i
    long_term = kcs * sustained
    dl_short = delta_dl * ratio_i
    ll_short = psi_s * delta_ll * ratio_i
    dl_long = kcs * delta_dl * ratio_i
    ll_long = kcs * psi_l * delta_ll * ratio_i
    incremental = long_term + ll_short
    total = short + long_term
    L = geom["Lm"]

    def limit(name: str) -> float:
        span_ratio, absolute = limits[name]
        values = [L / span_ratio]
        if absolute > 0:
            values.append(absolute)
        return min(values)

    lim = {name: limit(name) for name in ("dead", "live", "incremental", "total")}
    return {"positions": rows, "cutoff": cutoff, "cutoffPercent": cutoff_percent,
            "M1": m1, "Mx": mx, "M2": m2, "IavCase": key, "IavLabel": label, "IavCode": code,
            "IavValid": valid, "Iav": Iav, "at": at, "ratioI": ratio_i, "kcs": kcs,
            "deltaDL": delta_dl, "deltaLL": delta_ll, "psiS": psi_s, "psiL": psi_l,
            "short": short, "sustained": sustained, "long": long_term, "dlShort": dl_short,
            "llShort": ll_short, "dlLong": dl_long, "llLong": ll_long, "dlTotal": dl_short + long_term,
            "incremental": incremental, "total": total, "limits": lim,
            "spanOver": math.floor(L / total) if total >= 0.1 else None,
            "ratioDead": ratio(dl_long, lim["dead"]), "ratioLive": ratio(ll_short, lim["live"]),
            "ratioIncremental": ratio(incremental, lim["incremental"]),
            "ratioTotal": ratio(total, lim["total"]),
            "compressionInTension": any(rows[k]["useComp"] == "No" for k in POSITIONS)}


def wrh(geom: dict[str, Any], mat: dict[str, float], creep: dict[str, Any],
        calc: dict[str, Any], span_type: str) -> dict[str, Any]:
    """WRH Ch 9.3 shrinkage and creep deflections, Creep&Shrink!D63:H86."""
    cant = span_type == "C"
    row = calc["positions"]["R" if cant else "X"]
    ast, asc, d = row["Ast"], row["Asc"], row["d"]
    ecs, fcc, L = creep["ecs"], creep["fcc"], geom["Lm"]
    kappa_sh = (1.15 * ecs / d * (1.0 - asc / ast)) * 1000.0 if ast else 0.0
    beta_sh = {"C": 0.5, "S": 0.125, "P": 0.086, "E": 0.086, "I": 0.063, "F": 0.063}.get(
        span_type, 0.125)
    delta_sh = beta_sh * kappa_sh * L ** 2 / 1e9
    pn = row["pw"] * mat["n"]
    delta_cr = (fcc * (1.0 - 6.0 * pn * (1.0 - 6.0 * pn)) / (3.0 * (1.0 + asc / ast))
                * calc["short"]) if ast else 0.0
    total = calc["short"] + delta_sh + delta_cr
    return {"spanType": span_type, "Ast": ast, "Asc": asc, "d": d, "kappaSh": kappa_sh,
            "betaSh": beta_sh, "deltaSh": delta_sh, "pn": pn, "deltaCr": delta_cr,
            "permanent": delta_sh + delta_cr, "total": total,
            "spanOver": math.floor(L / total) if total >= 0.1 else None}
