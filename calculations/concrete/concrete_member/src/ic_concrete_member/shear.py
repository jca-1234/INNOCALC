"""Shear and torsion - AS 3600:2018 Cl 8.2 and Cl 8.3.

Transcribes ``Shear!A18:I249`` and the supporting ``Settings!J303:AF495`` logic:
the general (Cl 8.2.4.2) and simplified (Cl 8.2.4.3) methods for kv and theta_v, the
fitment contribution (Cl 8.2.5), minimum fitments (Cl 8.2.1.7), web crushing
(Cl 8.2.3.3), torsion (Cl 8.2.1.2, Cl 8.2.5.5, Cl 8.2.5.6), combined crushing, detailing
(Cl 8.3.2.2, Cl 8.3.3) and the additional longitudinal force (Cl 8.2.8, cited by the
workbook as Cl 8.2.7).  Prestress terms (``Pv``, ``Apt``) are zero: prestressed members are
outside the module scope.
"""

from __future__ import annotations

import math
from typing import Any

from .common import ES, calc_ast, cot, ratio, roundup, excel_round, rounddown
from .section import SLAB, uncracked_na

PHI_CONCRETE = 0.7   # Table 2.2.2(e)(ii) as used for ks.phi.Vuc and Vu.max
KC = 0.55            # Cl 8.2.3.3
EPS_X_MAX = 3000.0   # x1e-6
EPS_X_MIN = -200.0   # x1e-6
KV_SIMPLE_CAP = 0.10  # Cl 8.2.4.3 without minimum fitments (deliberate departure D1)
PHI_COMPRESSION = 0.65  # Table 2.2.2 (2018); the workbook holds 0.6 (deliberate departure D6)


def _strain(numerator: float, ast: float, ec: float, act: float) -> tuple[float, float]:
    first = min(numerator / (2.0 * ES * ast / 1000.0), 0.003) * 1e6 if ast else EPS_X_MAX
    denominator = 2.0 * (ES * ast + ec * act) / 1000.0
    second = min(0.0, max(numerator / denominator, -0.0002) * 1e6) if denominator else 0.0
    return first, second


def _act(section_act: dict[str, float], positive: bool, definition: str) -> float:
    if definition == "AS5100":
        return section_act["ActPos"] if positive else section_act["ActNeg"]
    return section_act["ActmPos"] if positive else section_act["ActmNeg"]


def _no_fitment(geom, reo, mat, *, positive, mstar_strain, V, N, ast_prov, kdg, simple,
                comp_cracked, ks, act_definition, with_steel, crack_uncracked, root_fc,
                torsion: tuple[float, float] | None):
    """Settings!X459:X481: Vuc recomputed without fitments, used for the fitment requirement."""
    D, W = geom["D"], geom["W"]
    bot, top, ligs = reo["bottom"], reo["top"], reo["ligs"]
    dsmax = D - reo["cover"] - bot["bar"] / 2.0 - ligs
    ds = D - reo["cover"] - bot["bar"] / 2.0 - (bot["offset"] if bot["As"] else 0.0)
    dcmax = reo["coverTop"] + top["bar"] / 2.0 + ligs
    dc = reo["coverTop"] + top["bar"] / 2.0 + (top["offset"] if top["As"] else 0.0)
    do = dsmax if positive else D - dcmax
    dv = max(0.72 * D, 0.9 * do)
    if with_steel:
        na = uncracked_na(geom, mat["n"], reo["Ast"], reo["Asc"], ds, D - dc) * D
    else:
        na = geom["na"]
    if act_definition == "AS5100":
        section, bef, Tf = geom["section"], geom["bef"], geom["Tf"]
        if section == 2:
            act = ((W * (D - Tf) + bef * (Tf - na) if na <= Tf else W * (D - na)) if positive
                   else (bef * na if na <= Tf else bef * Tf + (na - Tf) * W))
        else:
            act = W * (D - na) if positive else W * na
    else:
        act = _act(crack_uncracked, positive, "AS3600")
    if torsion is None:
        numerator = abs(mstar_strain / (dv / 1000.0)) + abs(V) - 0.5 * N
    else:
        mstar_tors, resultant = torsion
        numerator = abs(mstar_tors / (dv / 1000.0)) + resultant - 0.5 * N
    first, second = _strain(numerator, ast_prov, mat["Ec"], act)
    eps = first if first >= 0 else second
    kv_general = 0.4 / (1.0 + 1500.0 * eps / 1e6) * 1300.0 / (1000.0 + kdg * dv)
    kv_simple = min(200.0 / (1000.0 + 1.3 * dv), KV_SIMPLE_CAP)
    kv = kv_simple if simple else kv_general
    vuc = 0.0 if comp_cracked else kv * W * dv * root_fc / 1000.0
    return {"dsmax": dsmax, "ds": ds, "dcmax": dcmax, "dc": dc, "do": do, "dv": dv, "NA": na,
            "Act": act, "eps1": first, "eps2": second, "eps": eps, "kvGeneral": kv_general,
            "kvSimple": kv_simple, "kv": kv, "Vuc": vuc, "ksPhiVuc": ks * PHI_CONCRETE * vuc}


def _evaluate(geom, reo, mat, flex, uncr, opts, *, wide: bool) -> dict[str, Any]:
    section, D, W, bef = geom["section"], geom["D"], geom["W"], geom["bef"]
    fc, fsy = opts["fc"], opts["fsy"]
    V, M, N, T = abs(opts["V"]), opts["M"], opts["N"], abs(opts["T"])
    positive = M >= 0
    do = reo["dsmax"] if positive else D - reo["dcmax"]
    ds_v = reo["ds"] if positive else D - reo["dc"]
    dv = max(0.72 * D, 0.9 * ds_v)
    bv = W
    ligs, s, fsyf = reo["ligs"], opts["s"], opts["fsyf"]
    legs = opts["legs"]
    legs_v = 2 if legs <= 0 else legs
    leg_area = 0.0 if opts["ignoreLigs"] else math.pi * ligs ** 2 / 4.0
    asv_actual = legs * leg_area
    sigma_min = 0.08 * math.sqrt(fc)
    asv_min = sigma_min * bv * s / fsyf
    s_max_strength = fsyf * asv_actual / (sigma_min * bv)
    s_limit = min(500.0, 0.75 * D) if wide else min(300.0, 0.5 * D)
    if section == SLAB:
        transverse = 0.0 if legs <= 0 else 1000.0 / legs
    else:
        transverse = 0.0 if legs <= 1 else (W - 2.0 * reo["coverSide"] - ligs) / (legs - 1)
    transverse_limit = min(600.0, D)
    spacing_fail = (not opts["waiveSpacing"]) and s > roundup(s_limit, 0)
    transverse_fail = (not opts["waiveTransverse"]) and transverse > transverse_limit
    asv = 0.0 if (spacing_fail or transverse_fail or asv_actual < asv_min) else asv_actual
    has_min = asv >= asv_min and asv > 0
    phi_v = 0.75 if (opts["classFit"] == "N" and asv >= asv_min) else 0.7

    # Torsion geometry and cracking torque, Cl 8.2.1.2.
    uc = 2.0 * D + 2.0 * W
    acp = D * W
    root_plain = math.sqrt(fc)
    Tcr = 0.33 * root_plain * ((acp / 1e6) ** 2 / (uc / 1000.0)) * 1000.0
    phi_t = phi_v
    phi_tcr = phi_t * Tcr
    trigger = 0.25 * phi_tcr
    ratio_trigger = T / trigger if trigger else 0.0
    consider = T > trigger
    x = min(W, D)
    y = max(W, D)
    d_xyo = D - reo["cover"] - reo["coverTop"] - ligs
    w_xyo = W - 2.0 * reo["coverSide"] - ligs
    xo, yo = (w_xyo, d_xyo) if W < D else (d_xyo, w_xyo)
    uh = 2.0 * (xo + yo)
    Aoh = xo * yo
    Ao = 0.85 * Aoh

    ast_design = flex["positive"]["Ast"] if positive else flex["negative"]["Ast"]
    asc_design = flex["negative"]["Ast"] if positive else flex["positive"]["Ast"]
    ast_prov = opts["AstManual"] or ast_design
    asc_prov = opts["AscManual"] or asc_design

    torsion_shear = T * uh / 1000.0 / 2.0 / (Ao / 1e6) if Ao else 0.0
    mstar_strain = max(abs(M), V * dv / 1000.0)
    mstar_tors = max(abs(M), math.sqrt(V ** 2 + (0.9 * torsion_shear) ** 2) * dv / 1000.0)
    act = _act(uncr, positive, opts["actDefinition"])
    num_shear = abs(mstar_strain / (dv / 1000.0)) + V - 0.5 * N
    ex1, ex2 = _strain(num_shear, ast_prov, mat["Ec"], act)
    num_tors = (abs(mstar_tors / (dv / 1000.0)) + math.sqrt(V ** 2 + (0.9 * torsion_shear) ** 2)
                - 0.5 * N)
    ext1, ext2 = _strain(num_tors, ast_prov, mat["Ec"], act)
    if consider:
        eps = ext1 if ext1 >= 0 else ext2
    else:
        eps = ex1 if ex1 >= 0 else ex2
    kdg = 2.0 if (fc > 65 or opts["lightweight"]) else max(32.0 / (16.0 + opts["dg"]), 0.8)
    kv_general = 0.4 / (1.0 + 1500.0 * eps / 1e6)
    if asv < asv_min:
        kv_general *= 1300.0 / (1000.0 + kdg * dv)
    kvo = 200.0 / (1000.0 + 1.3 * dv)
    kv_simple = min(kvo, KV_SIMPLE_CAP) if asv < asv_min else 0.15
    theta_general = 29.0 + 7000.0 * eps / 1e6
    simple = opts["method"] == "S"
    kv = kv_simple if simple else kv_general
    theta = 36.0 if simple else theta_general
    root_fc = min(root_plain, 8.0)
    vuc = 0.0 if opts["compCracked"] else kv * bv * dv * root_fc / 1000.0
    ks = 0.5 if D >= 650 else (1.0 if D <= 300 else (1000.0 - D) / 700.0)
    ks_phi_vuc = ks * PHI_CONCRETE * vuc
    phi_vuc = phi_v * vuc
    alpha = math.radians(opts["alphaV"])
    theta_r = math.radians(theta)
    angle_term = math.sin(alpha) / math.tan(theta_r) + math.cos(alpha)
    vus = (asv * fsyf * dv / s) * angle_term / 1000.0
    phi_vus = phi_v * vus
    cot_alpha = 1.0 / math.tan(alpha)
    vu_max = KC * (0.9 * fc * bv * dv / 1000.0 * ((cot(theta_r) + cot_alpha)
                                                   / (1.0 + cot(theta_r) ** 2)))
    phi_vu_max = PHI_CONCRETE * vu_max
    phi_vu = phi_vuc if asv < asv_min else min(phi_vuc + phi_vus, phi_vu_max)
    vus_min = (asv_min * fsyf * dv / s) * angle_term / 1000.0
    phi_vu_min = phi_v * (vuc + vus_min)
    phi_vus_max = phi_vu_max - phi_vuc
    asv_max = phi_vus_max / phi_v * 1000.0 / (fsyf * dv / s) / angle_term
    phi_vus_req = max(0.0, V - phi_vuc)
    vus_req = phi_vus_req / phi_v
    asv_req = vus_req / ((fsyf * dv / s) * angle_term / 1000.0)
    s_req = rounddown((asv * fsyf * dv / vus_req) * angle_term / 1000.0, 0) if vus_req else 0.0

    # Torsion with fitments, Cl 8.2.5.5 and Cl 8.2.5.6.
    asw_actual = leg_area if legs > 0 else 0.0
    s_max_torsion = excel_round(min(0.12 * uh, 300.0), 0)
    asw_min1 = asv_min / legs_v
    torsion_factor = 2.0 * Ao * fsyf / s / math.tan(theta_r) / 1e6
    asw_min2 = 0.25 * Tcr / torsion_factor
    asw_min = max(asw_min1, asw_min2)
    torsion_spacing_fail = (not opts["waiveSpacing"]) and s > s_max_torsion
    asw = 0.0 if (torsion_spacing_fail or asw_actual < asw_min) else asw_actual
    Tus = torsion_factor * asw
    phi_tus = 0.0 if s > s_max_torsion else phi_t * Tus
    s_max2 = (2.0 * Ao * asw * fsyf / math.tan(theta_r) / (0.25 * Tcr)) / 1e6
    Tus_min = torsion_factor * asw_min

    # Combined shear and torsion crushing.
    v_stress = V / (bv * dv) * 1000.0
    t_stress = T * uh / (1.7 * Aoh ** 2) * 1e6 if Aoh else 0.0
    combined = math.hypot(v_stress, t_stress)
    combined_limit = phi_vu_max * 1000.0 / bv / dv

    # Additional longitudinal force, Cl 8.2.8.
    pos, neg, alpha2 = flex["positive"], flex["negative"], flex["alpha2"]
    ast_req = (0.0 if M == 0 else calc_ast(fsy, fc, bef, reo["ds"], abs(M), 0.85 if opts[
        "classBot"] == "N" else 0.65, alpha2) if M > 0 else calc_ast(
        fsy, fc, W, D - reo["dc"], abs(M), 0.85 if opts["classTop"] == "N" else 0.65, alpha2))
    mmax = opts["Mmax"] if opts["Mmax"] else M
    ast_req_max = (0.0 if mmax == 0 else calc_ast(fsy, fc, bef, reo["ds"], abs(mmax), 0.85 if opts[
        "classBot"] == "N" else 0.65, alpha2) if mmax > 0 else calc_ast(
        fsy, fc, W, D - reo["dc"], abs(mmax), 0.85 if opts["classTop"] == "N" else 0.65, alpha2))
    if positive:
        lever = pos["d"] * (1.0 - fsy * ast_prov / (2.0 * alpha2 * fc * pos["b"] * pos["d"]))
    else:
        lever = neg["d"] * (1.0 - fsy * ast_prov / (2.0 * alpha2 * fc * neg["b"] * neg["d"]))
    uo = 0.92 * uh
    ftd_limit = max(0.0, 0.5 * (V + phi_vuc))
    ftd_shear = max(min(ftd_limit, V) / math.tan(theta_r), 0.0)
    ftd_torsion = (max(0.0, 0.5 * T * (uo / 1000.0) / (2.0 * (Ao / 1e6)) / math.tan(theta_r))
                   if consider else 0.0)
    ftd = ftd_shear + ftd_torsion
    class_t = opts["classBot"] if positive else opts["classTop"]
    class_c = opts["classTop"] if positive else opts["classBot"]
    phi_bt = ((0.65 if class_t == "L" else 0.85) if opts["AstManual"]
              else (pos["phi"] if positive else neg["phi"]))
    phi_bc = ((0.65 if class_c == "L" else 0.85) if opts["AscManual"]
              else (neg["phi"] if positive else pos["phi"]))
    nuot = ((0.65 if opts["classBot"] == "L" else 0.85) * reo["Ast"] * fsy
            + (0.65 if opts["classTop"] == "L" else 0.85) * reo["Asc"] * fsy) / 1000.0
    nub = 0.36 * nuot

    def phi_axial(phi_b: float, klass: str) -> float:
        if N == 0:
            return phi_b
        if N < 0:
            if klass == "L":
                return 0.65
            return max(0.65, min(0.85, phi_b + (0.85 - phi_b) * (abs(N) / nuot))) if nuot else 0.65
        base = PHI_COMPRESSION
        return max(base, base + (0.85 - base) * (1.0 - abs(N) / nub)) if nub else base

    phi_tt, phi_tc = phi_axial(phi_bt, class_t), phi_axial(phi_bc, class_c)
    from_shear = asv != 0
    ttd = max(0.0, abs(M) * 1000.0 / lever - N / 2.0 + ftd)
    ast_long_total = ttd * 1000.0 / (phi_tt * fsy)
    ast_long_basis = min(ast_req_max, ast_long_total) if opts["limitTtd"] else ast_long_total
    ast_long_add = max(0.0, ast_long_basis - ast_prov) if from_shear else 0.0
    fcd = max(0.0, -abs(M) * 1000.0 / lever - N / 2.0 + ftd)
    asc_long_total = fcd * 1000.0 / (phi_tc * fsy)
    asc_long_add = max(0.0, asc_long_total - asc_prov) if from_shear else 0.0
    return {
        "positive": positive, "do": do, "ds": ds_v, "dv": dv, "bv": bv,
        "dvPos": max(0.72 * D, 0.9 * reo["dsmax"]), "dvNeg": max(0.72 * D, 0.9 * (D - reo["dcmax"])),
        "legs": legs, "legArea": leg_area, "AsvActual": asv_actual, "sigmaMin": sigma_min,
        "AsvMin": asv_min, "sMaxStrength": s_max_strength, "sLimit": s_limit, "wide": wide,
        "transverse": transverse, "transverseLimit": transverse_limit,
        "spacingFail": spacing_fail, "transverseFail": transverse_fail, "Asv": asv,
        "hasMinimum": has_min, "phiV": phi_v, "uc": uc, "Acp": acp, "Tcr": Tcr, "phiTcr": phi_tcr,
        "trigger": trigger, "ratioTrigger": ratio_trigger, "considerTorsion": consider,
        "x": x, "y": y, "Dxyo": d_xyo, "Wxyo": w_xyo, "xo": xo, "yo": yo, "uh": uh, "Aoh": Aoh,
        "Ao": Ao, "AstDesign": ast_design, "AscDesign": asc_design, "AstProv": ast_prov,
        "AscProv": asc_prov, "MstarStrain": mstar_strain, "MstarStrainTorsion": mstar_tors,
        "Act": act, "eps1": ex1, "eps2": ex2, "epsT1": ext1, "epsT2": ext2, "eps": eps,
        "epsSimple": 0.85 * fsy / (2.0 * ES) * 1e6, "kdg": kdg, "kvGeneral": kv_general,
        "kvo": kvo, "kvSimple": kv_simple, "thetaGeneral": theta_general, "kv": kv,
        "theta": theta, "method": "Simplified Cl 8.2.4.3" if simple else "General Cl 8.2.4.2",
        "rootFc": root_fc, "Vuc": vuc, "ks": ks, "ksPhiVuc": ks_phi_vuc, "phiVuc": phi_vuc,
        "Vus": vus, "phiVus": phi_vus, "VuMax": vu_max, "phiVuMax": phi_vu_max, "phiVu": phi_vu,
        "VusMin": vus_min, "phiVuMin": phi_vu_min, "phiVusMax": phi_vus_max, "AsvMax": asv_max,
        "phiVusReq": phi_vus_req, "VusReq": vus_req, "AsvReq": asv_req, "sReq": s_req,
        "AswActual": asw_actual, "sMaxTorsion": s_max_torsion, "AswMin1": asw_min1,
        "AswMin2": asw_min2, "AswMin": asw_min, "Asw": asw, "Tus": Tus, "phiTus": phi_tus,
        "sMaxTorsion1": s_max_strength, "sMaxTorsion2": s_max2,
        "sMaxTorsionMin": min(s_max_strength, s_max2), "TusMin": Tus_min,
        "phiTusMin": phi_t * Tus_min, "vStress": v_stress, "tStress": t_stress,
        "combined": combined, "combinedLimit": combined_limit,
        "Vcomb": combined * bv * dv / 1000.0, "AstReq": ast_req, "AstReqMax": ast_req_max,
        "Mmax": mmax, "lever": lever, "uo": uo, "ftdLimit": ftd_limit, "ftdLimited": ftd_limit > V,
        "FtdShear": ftd_shear, "FtdTorsion": ftd_torsion, "Ftd": ftd, "phiBt": phi_bt,
        "phiBc": phi_bc, "Nuot": nuot, "Nub": nub, "phiTt": phi_tt, "phiTc": phi_tc,
        "fromShear": from_shear, "Ttd": ttd, "AstLongTotal": ast_long_total,
        "AstLongBasis": ast_long_basis, "AstLongAdd": ast_long_add, "Fcd": fcd,
        "AscLongTotal": asc_long_total, "AscLongAdd": asc_long_add,
        "rootFcPlain": root_plain, "phiT": phi_t,
        "torsionResultant": math.sqrt(V ** 2 + (0.9 * torsion_shear) ** 2),
    }


def check(geom: dict[str, Any], reo: dict[str, Any], mat: dict[str, float],
          flex: dict[str, Any], uncr: dict[str, Any], opts: dict[str, Any]) -> dict[str, Any]:
    V, T, D = abs(opts["V"]), abs(opts["T"]), geom["D"]
    result = _evaluate(geom, reo, mat, flex, uncr, opts, wide=opts["increaseSpacing"])
    wide_rejected = False
    if opts["increaseSpacing"] and V > result["phiVuMin"]:
        result = _evaluate(geom, reo, mat, flex, uncr, opts, wide=False)
        wide_rejected = True
    positive = result["positive"]
    simple = opts["method"] == "S"
    nolig = _no_fitment(geom, reo, mat, positive=positive,
                        mstar_strain=result["MstarStrain"], V=V, N=opts["N"],
                        ast_prov=result["AstProv"], kdg=result["kdg"], simple=simple,
                        comp_cracked=opts["compCracked"], ks=result["ks"],
                        act_definition=opts["actDefinition"], with_steel=opts["withSteel"],
                        crack_uncracked=uncr, root_fc=result["rootFc"],
                        torsion=((result["MstarStrainTorsion"], result["torsionResultant"])
                                 if result["considerTorsion"] else None))
    two_way = geom["section"] == SLAB and opts["slabType"] in ("T", "C", "F")
    deep = D >= 750 and not two_way and not opts["waiveDeep"]
    torsion_needed = result["ratioTrigger"] > 1
    torsion_none = result["ratioTrigger"] <= 0
    threshold = result["ksPhiVuc"] if torsion_needed else nolig["ksPhiVuc"]
    shear_none = V <= threshold and not deep
    shear_min = (V > threshold and V < result["phiVuMin"]) or deep
    no_ligs = shear_none and torsion_none
    if shear_none:
        requirement = "No shear fitments required - Cl 8.2.1.6(a)"
    elif shear_min:
        requirement = ("Minimum fitments required, D >= 750 mm - Cl 8.2.1.6(c)" if deep and V <= threshold
                       else "Minimum shear fitments required - Cl 8.2.1.6")
    else:
        requirement = "Shear fitments required, V* > phi.Vu.min - Cl 8.2.5"

    fvu = result["phiVu"]
    long_add = result["AstLongAdd"] != 0 or result["AscLongAdd"] != 0
    shear_check = result["AsvActual"] < result["AsvMin"] and V > result["ksPhiVuc"]
    if fvu == 0:
        ratio_shear = math.inf if V > 0 else 0.0
        shear_basis = "V* / phi.Vu"
    elif long_add:
        ratio_shear, shear_basis = V / fvu, "V* / phi.Vu"
    elif V < result["ksPhiVuc"]:
        ratio_shear, shear_basis = V / result["ksPhiVuc"], "V* / (ks phi Vuc)"
    elif shear_check:
        ratio_shear, shear_basis = V / result["ksPhiVuc"], "V* / (ks phi Vuc), fitments < Asv.min"
    else:
        ratio_shear, shear_basis = V / fvu, "V* / phi.Vu"

    detailing_terms: dict[str, float] = {}
    if result["AsvActual"] > 0 and not no_ligs:
        if not opts["waiveSpacing"]:
            detailing_terms["spacing"] = opts["s"] / roundup(result["sLimit"], 0)
        if not opts["waiveTransverse"]:
            detailing_terms["transverse"] = result["transverse"] / result["transverseLimit"]
        detailing_terms["area"] = result["AsvMin"] / result["AsvActual"]
    if deep and result["AsvActual"] < result["AsvMin"]:
        detailing_terms["deep"] = ratio(result["AsvMin"], result["AsvActual"])
    ratio_detailing = max(detailing_terms.values()) if detailing_terms else 0.0

    if T == 0:
        ratio_torsion = ratio_torsion_min = 0.0
    else:
        ratio_torsion = ratio(T, result["phiTus"])
        ratio_torsion_min = max(ratio(result["AswMin"], result["AswActual"]),
                                opts["s"] / result["sMaxTorsion"])
    ratio_crush = ratio(result["combined"], result["combinedLimit"])
    if result["fromShear"]:
        ratio_long_t = ratio(result["AstLongBasis"], result["AstProv"])
        ratio_long_c = ratio(result["AscLongTotal"], result["AscProv"])
    else:
        ratio_long_t = ratio_long_c = 0.0
    applicability = None
    if simple:
        applicability = max(opts["fc"] / 65.0, opts["fsy"] / 500.0, opts["fsyf"] / 500.0,
                            10.0 / opts["dg"])
    return {**result, "noFitment": nolig, "twoWay": two_way, "deep": deep,
            "torsionNeeded": torsion_needed, "torsionNone": torsion_none,
            "threshold": threshold, "shearNone": shear_none, "shearMin": shear_min,
            "noLigsRequired": no_ligs, "requirement": requirement, "wideRejected": wide_rejected,
            "shearCheck": shear_check, "longitudinalRequired": long_add,
            "ratioShear": ratio_shear, "shearBasis": shear_basis,
            "detailingTerms": detailing_terms, "ratioDetailing": ratio_detailing,
            "ratioTorsion": ratio_torsion, "ratioTorsionMin": ratio_torsion_min,
            "ratioCrush": ratio_crush, "ratioLongTension": ratio_long_t,
            "ratioLongCompression": ratio_long_c, "ratioMethod": applicability,
            "V": V, "M": opts["M"], "N": opts["N"], "T": T, "s": opts["s"],
            "fsyf": opts["fsyf"], "alphaV": opts["alphaV"], "compCracked": opts["compCracked"],
            "flexureShortfall": result["AstReq"] > result["AstProv"]}
