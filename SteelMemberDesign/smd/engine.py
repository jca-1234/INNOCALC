"""AS 4100:2020 steel member calculation engine.

All working units are N and mm.  The browser sends the selected section record
from the static DCT catalogue; every design calculation is performed here.
"""

from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

PHI = 0.9
E_STEEL = 200_000.0
G_STEEL = 80_000.0

DEFAULT_CHECKS = {
    "compression": False,
    "tension": False,
    "torsion": False,
    "bearing": False,
    "momentAmplification": False,
    "fire": False,
}


def _number(values: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        value = float(values.get(key, default))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be a finite number") from exc
    if not math.isfinite(value):
        raise ValueError(f"{key} must be a finite number")
    return value


def _ratio(action: float, capacity: float) -> float:
    if not math.isfinite(action) or not math.isfinite(capacity) or capacity < 0:
        return math.inf
    if capacity == 0:
        return math.inf if action else 0.0
    return action / capacity


def apply_grade(section: dict[str, Any], grade: str) -> dict[str, Any]:
    sec = deepcopy(section)
    grades = {
        "350": {"fyf": 340.0, "fyw": 340.0, "fu": 480.0},
        "400": {"fyf": 360.0, "fyw": 360.0, "fu": 480.0},
    }
    sec.update(grades.get(str(grade), {}))
    return sec


def section_alpha_b(sec: dict[str, Any]) -> float:
    section_type = sec.get("type")
    kf = _number(sec, "kf", 1.0)
    if section_type in {"UB", "UC", "TFB"}:
        return 0.0
    if section_type in {"WB", "WC"}:
        return 0.5 if kf < 1.0 else 0.0
    if section_type in {"PFC", "EA", "UA"}:
        return 1.0 if kf < 1.0 else 0.5
    if section_type == "CUSTOM":
        if sec.get("family") == "channel":
            return 1.0 if kf < 1.0 else 0.5
        return 0.5 if kf < 1.0 else 0.0
    return 0.0


def alpha_a(lambda_n: float) -> float:
    denominator = lambda_n * lambda_n - 15.3 * lambda_n + 2050.0
    return 2100.0 * (lambda_n - 13.5) / denominator


def member_slender_reduction(lambda_n: float, alpha_b: float) -> dict[str, float]:
    if lambda_n < 1e-6:
        return {"aa": 0.0, "lambda": 0.0, "eta": 0.0, "xi": 1.0, "ac": 1.0}
    aa = alpha_a(lambda_n)
    slenderness = lambda_n + aa * alpha_b
    eta = max(0.0, 0.00326 * (slenderness - 13.5))
    ratio = slenderness / 90.0
    xi = (ratio * ratio + 1.0 + eta) / (2.0 * ratio * ratio)
    inside = 1.0 - (90.0 / (xi * slenderness)) ** 2
    ac = xi * (1.0 - math.sqrt(max(0.0, inside)))
    return {"aa": aa, "lambda": slenderness, "eta": eta, "xi": xi,
            "ac": max(0.0, min(ac, 1.0))}


def reference_buckling(sec: dict[str, Any], effective_length: float) -> dict[str, float]:
    length = max(effective_length, 1e-6)
    constant_1 = math.pi**2 * E_STEEL * sec["Iy"] / length**2
    constant_2 = math.pi**2 * E_STEEL * sec.get("Iw", 0.0) / length**2
    moment = math.sqrt(max(0.0, constant_1 * (G_STEEL * sec.get("J", 0.0) + constant_2)))
    return {"c1": constant_1, "c2": constant_2, "Mo": moment}


def _effective_length(sec: dict[str, Any], inp: dict[str, Any]) -> dict[str, Any]:
    code = str(inp.get("end1", "F")) + str(inp.get("end2", "F"))
    length = max(_number(inp, "L", 4000.0), 1e-6)
    base = (_number(sec, "d1") / length) * (_number(sec, "tf") / (2.0 * max(_number(sec, "tw"), 1e-6))) ** 3
    if "U" in code:
        kt, kt_note = 1.0, "End unrestrained - cantilever (kl governs)"
    else:
        partial = code.count("P")
        kt = 1.0 + (0.5 * base if partial == 1 else base if partial == 2 else 0.0)
        kt_note = "Table 5.6.3(1)"
    if inp.get("loadpos", "E") == "E":
        kl, kl_note = 1.0, "Load at segment end"
    elif inp.get("loadht", "S") == "T":
        kl = 1.4 if all(letter in "FL" for letter in code) else 2.0
        kl_note = "Top-flange load within segment"
    else:
        kl, kl_note = 1.0, "Load at/below shear centre"
    restraints = int(_number(inp, "latrot"))
    if all(letter in "FPL" for letter in code):
        kr = 0.70 if restraints == 2 else 0.85 if restraints == 1 else 1.0
    else:
        kr = 1.0
    factor = kt * kl * kr
    return {"code": code, "kt": kt, "kl": kl, "kr": kr, "k": factor,
            "Le": factor * length, "ktNote": kt_note, "klNote": kl_note}


def _alpha_m(inp: dict[str, Any]) -> float:
    if inp.get("amMode") != "quarter":
        return _number(inp, "am", 1.0)
    moments = [_number(inp, key) for key in ("M14", "M12", "M34")]
    denominator = math.sqrt(sum(value * value for value in moments))
    return min(2.5, 1.7 * abs(_number(inp, "Mmax")) / denominator) if denominator else 2.5


def _primitives(sec: dict[str, Any], inp: dict[str, Any]) -> dict[str, Any]:
    """Family-specific section quantities; every check downstream is common.

    Angles are designed about their geometric axes for bending and about their
    principal axes for buckling, so the second moments that drive the reference
    buckling moment and the compression curves are the principal ones.
    """
    fyf, fyw, fu = sec["fyf"], sec["fyw"], sec["fu"]
    fy, area, kf = min(fyf, fyw), sec["Ag"], sec["kf"]
    common = {"fy": fy, "fyf": fyf, "fyw": fyw, "fu": fu, "area": area, "kf": kf,
              "netArea": _number(inp, "An") or area}
    if sec.get("family") == "angle":
        leg_down = inp.get("legOrient", "down") != "up"
        rx, ry = sec["rxP"], sec["ryP"]
        thickness, leg, other = sec["t"], sec["b1"], sec["b2"]
        return {**common,
                "zex": sec["Zex_A"] if leg_down else sec["Zex_C"], "zey": sec["Zey_B"],
                "rx": rx, "ry": ry, "Ix": area * rx * rx, "Iy": area * ry * ry,
                # Cl 5.6.1.1 with the open-section torsion constant of the two legs.
                "J": (leg + other - thickness) * thickness**3 / 3.0, "Iw": 0.0,
                "Aw": leg * thickness, "Awy": other * thickness,
                "dp": leg - thickness, "tw": thickness,
                "tf": thickness, "bf": other,
                "df": leg - thickness, "legDown": leg_down}
    welded = sec.get("type") in {"WB", "WC", "CUSTOM"}
    return {**common,
            "zex": sec["Zex"], "zey": sec["Zey"],
            "rx": math.sqrt(sec["Ix"] / area), "ry": math.sqrt(sec["Iy"] / area),
            "Ix": sec["Ix"], "Iy": sec["Iy"], "J": sec.get("J", 0.0), "Iw": sec.get("Iw", 0.0),
            "Aw": (sec["d1"] if welded else sec["d"]) * sec["tw"],
            "Awy": 2.0 * sec["bf"] * sec["tf"],
            "dp": sec["d"] - 2.0 * sec["tf"], "tw": sec["tw"],
            "tf": sec["tf"], "bf": sec["bf"],
            "df": sec["d"] - sec["tf"], "legDown": True}


def compute_design(section: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    """Return all capacities and enabled utilisation checks for one section."""
    inp = deepcopy(inputs)
    checks = DEFAULT_CHECKS | (inp.get("checks") or {})
    sec = apply_grade(section, str(inp.get("grade", "300")))
    prim = _primitives(sec, inp)

    fyf, fyw, fu = prim["fyf"], prim["fyw"], prim["fu"]
    fy, area = prim["fy"], prim["area"]
    net_area = prim["netArea"]
    rx, ry = prim["rx"], prim["ry"]
    result: dict[str, Any] = {"family": sec.get("family", "doubly"), "checks": checks}
    result["props"] = {
        "fy": fy, "fyf": fyf, "fyw": fyw, "fu": fu,
        "df": prim["df"], "kf": sec["kf"],
        "doublySym": bool(sec.get("doublySym")),
        "compact": sec.get("compactX") == "C" and sec.get("compactY") == "C",
        "weight": area * 78.5e-6 * 9.81 / 1000.0,
    }

    effective = _effective_length(sec, inp)
    result["effLength"] = effective
    alpha_m = _alpha_m(inp)
    result["alpha_m"] = alpha_m
    constants = {"K1": 60.0, "K2": 40.0} if sec.get("family") == "channel" else {"K1": 80.0, "K2": 50.0}
    beta_m_flr = -1.0
    lmax = ry * (constants["K1"] + constants["K2"] * beta_m_flr) * math.sqrt(250.0 / fy)
    result["flr"] = {"Lmax": lmax, "betaM": beta_m_flr, "isFLR": bool(inp.get("flr", False))}

    msx, msy = fy * prim["zex"], fy * prim["zey"]
    phi_msx, phi_msy = PHI * msx, PHI * msy
    buckling = reference_buckling({"Iy": prim["Iy"], "J": prim["J"], "Iw": prim["Iw"]},
                                  effective["Le"])
    ms_ratio = msx / max(buckling["Mo"], 1e-9)
    alpha_s = 0.6 * (math.sqrt(ms_ratio * ms_ratio + 3.0) - ms_ratio)
    phi_mbx_am1 = PHI * min(alpha_s, 1.0) * msx
    phi_mbx_calc = PHI * min(alpha_m * alpha_s * msx, msx)
    phi_mbx = phi_msx if inp.get("flr", False) else phi_mbx_calc
    result["bending"] = {
        "Msx": msx, "Zex": prim["zex"], "Zey": prim["zey"],
        "phiMsx": phi_msx, "Msy": msy, "phiMsy": phi_msy,
        **buckling, "alpha_s": alpha_s, "phiMbx_am1": phi_mbx_am1,
        "phiMbx_calc": phi_mbx_calc, "phiMbx": phi_mbx, "legDown": prim["legDown"],
    }

    web_area = prim["Aw"]
    vw = 0.6 * fyw * web_area
    clear_depth, web_thickness = prim["dp"], prim["tw"]
    alpha_v = (82.0 / ((clear_depth / web_thickness) * math.sqrt(fyw / 250.0))) ** 2
    vu = vw if clear_depth / web_thickness <= 82.0 * math.sqrt(250.0 / fyw) else min(vw, alpha_v * vw)
    phi_vu = PHI * vu
    weak_area = prim["Awy"]
    weak_v = 0.6 * fyw * weak_area
    result["shear"] = {
        "Aw": web_area, "Vw": vw, "dp": clear_depth, "alpha_v": alpha_v,
        "Vb": alpha_v * vw, "Vu": vu, "phiVu": phi_vu, "phiVvm": phi_vu,
        "Awy": weak_area, "Vwy": weak_v, "phiVuy": PHI * weak_v,
        "phiVvmy": PHI * weak_v,
    }

    alpha_b = section_alpha_b(sec)
    lex = _number(inp, "kex", 1.0) * _number(inp, "Lx", 4000.0)
    ley = _number(inp, "key", 1.0) * _number(inp, "Ly", 4000.0)
    phi_ns = PHI * sec["kf"] * net_area * fy
    lambda_x = lex / rx * math.sqrt(sec["kf"]) * math.sqrt(fy / 250.0)
    lambda_y = ley / ry * math.sqrt(sec["kf"]) * math.sqrt(fy / 250.0)
    curve_x, curve_y = member_slender_reduction(lambda_x, alpha_b), member_slender_reduction(lambda_y, alpha_b)
    phi_ncx, phi_ncy = phi_ns * curve_x["ac"], phi_ns * curve_y["ac"]
    lambda_x_1 = _number(inp, "Lx", 4000.0) / rx * math.sqrt(sec["kf"]) * math.sqrt(fy / 250.0)
    lambda_y_1 = _number(inp, "Ly", 4000.0) / ry * math.sqrt(sec["kf"]) * math.sqrt(fy / 250.0)
    phi_ncx_1 = phi_ns * member_slender_reduction(lambda_x_1, alpha_b)["ac"]
    phi_ncy_1 = phi_ns * member_slender_reduction(lambda_y_1, alpha_b)["ac"]
    result["compression"] = {
        "enabled": checks["compression"], "phiNs": phi_ns, "Lex": lex, "Ley": ley,
        "lam_nx": lambda_x, "lam_ny": lambda_y, "cx": curve_x, "cy": curve_y,
        "rx": rx, "ry": ry, "phiNcx": phi_ncx, "phiNcy": phi_ncy,
        "phiNc": min(phi_ncx, phi_ncy), "phiNcx1": phi_ncx_1,
        "phiNcy1": phi_ncy_1,
        "minAxis": ("minor principal" if sec.get("family") == "angle"
                    else "x" if phi_ncx < phi_ncy else "y"),
    }

    phi_nty, phi_ntf = PHI * area * fy, PHI * 0.85 * _number(inp, "kt", 1.0) * net_area * fu
    result["tension"] = {
        "enabled": checks["tension"], "phiNty": phi_nty, "phiNtf": phi_ntf,
        "phiNt": min(phi_nty, phi_ntf), "kt": _number(inp, "kt", 1.0),
        "An": net_area, "govern": "yield" if phi_nty < phi_ntf else "fracture",
    }

    nc = _number(inp, "Nc") * 1000.0 if checks["compression"] else 0.0
    nt = _number(inp, "Nt") * 1000.0 if checks["tension"] else 0.0
    mx, my = _number(inp, "Mx") * 1e6, _number(inp, "My") * 1e6
    phi_nt = result["tension"]["phiNt"]
    use_compression = nc >= nt
    axial = nc if use_compression else nt
    axial_capacity = phi_ns if use_compression else phi_nt
    # Cl 8.3.2 / 8.3.3 - reduced section moment capacities in the presence of axial force.
    phi_mrxc = max(0.0, phi_msx * (1.0 - nc / phi_ns))
    phi_mrxt = max(0.0, phi_msx * (1.0 - nt / phi_nt))
    phi_mryc = max(0.0, phi_msy * (1.0 - nc / phi_ns))
    phi_mryt = max(0.0, phi_msy * (1.0 - nt / phi_nt))
    phi_mrx = phi_mrxc if use_compression else phi_mrxt
    phi_mry = phi_mryc if use_compression else phi_mryt
    # Cl 8.4.2 / 8.4.4 - in-plane and out-of-plane member moment capacities.
    phi_mixc = max(0.0, phi_msx * (1.0 - nc / phi_ncx_1))
    phi_miyc = max(0.0, phi_msy * (1.0 - nc / phi_ncy_1))
    phi_moxc = max(0.0, phi_mbx * (1.0 - nc / phi_ncy))
    phi_moxt = min(phi_mbx * (1.0 + nt / phi_nt), phi_mrxt)
    phi_mcx = min(phi_moxc, phi_mixc)
    phi_miy = phi_miyc if use_compression else phi_mryt
    in_plane = mx / phi_msx + (nc / phi_ncx_1 if use_compression else nt / phi_nt)
    # Cl 8.4.2.2 about the minor principal axis: My* <= phiMsy(1 - N*/phiNcy).
    in_plane_y = my / phi_msy + (nc / phi_ncy_1 if use_compression else nt / phi_nt)
    out_plane = mx / phi_mbx + (nc / phi_ncy if use_compression else nt / phi_nt)
    # Cl 8.3.4 - linear form is the requirement; the exponent form is the
    # alternative permitted for compact doubly symmetric sections.
    exponent = min(2.0, 1.4 + nc / max(phi_ns, 1e-9))
    biaxial_section = _ratio(mx, phi_mrx) ** exponent + _ratio(my, phi_mry) ** exponent
    biaxial_section_linear = _ratio(axial, axial_capacity) + mx / phi_msx + my / phi_msy
    biaxial_member = _ratio(mx, phi_mcx) ** 1.4 + _ratio(my, phi_miy) ** 1.4
    result["combined"] = {
        "phiMrxc": phi_mrxc, "phiMrxt": phi_mrxt, "phiMryc": phi_mryc,
        "phiMryt": phi_mryt, "phiMrx": phi_mrx, "phiMry": phi_mry,
        "phiMixc": phi_mixc, "phiMiyc": phi_miyc, "phiMoxc": phi_moxc,
        "phiMoxt": phi_moxt, "phiMcx": phi_mcx, "phiMiy": phi_miy,
        "gamma": exponent, "axial": axial, "axialCapacity": axial_capacity,
        "compressionGoverns": use_compression,
        "inPlane": in_plane, "inPlaneY": in_plane_y, "outPlane": out_plane,
        "biaxSection": biaxial_section,
        "biaxSectionLinear": biaxial_section_linear,
        "biaxMember": biaxial_member,
        "biaxialRequired": bool(my),
        "memberChecks": bool(checks["compression"] or checks["tension"]),
    }


    nomx = math.pi**2 * E_STEEL * prim["Ix"] / max(lex * lex, 1e-9)
    nomy = math.pi**2 * E_STEEL * prim["Iy"] / max(ley * ley, 1e-9)
    result["buckling"] = {"Nomx": nomx, "Nomy": nomy, "Nom": min(nomx, nomy),
                          "critical": "x" if nomx < nomy else "y"}
    if checks["momentAmplification"]:
        end_1, end_2 = abs(_number(inp, "Mend1")), abs(_number(inp, "Mend2"))
        larger, smaller = max(end_1, end_2), min(end_1, end_2)
        reverse = _number(inp, "Mend1") * _number(inp, "Mend2") < 0
        beta_m = (smaller / larger if reverse else -smaller / larger) if larger else -1.0
        cm = min(1.0, 0.6 - 0.4 * beta_m)
        result["momentAmp"] = {
            "enabled": True, "betaM": beta_m, "cm": cm,
            "delta_bx": max(1.0, cm / max(1e-9, 1.0 - nc / nomx)),
            "delta_by": max(1.0, cm / max(1e-9, 1.0 - nc / nomy)),
            "type": inp.get("frame", "B"), "Mend1": _number(inp, "Mend1"),
            "Mend2": _number(inp, "Mend2"),
        }

    if checks["torsion"]:
        mz = _number(inp, "Mz") * 1e6
        df = result["props"]["df"]
        fv = PHI * 0.6 * fy
        phi_mz = fv * prim["J"] / max(prim["tf"], 1e-9)
        flange_force = mz / max(df, 1e-9)
        span_m = _number(inp, "L") / 1000.0
        myf = ((flange_force / 1000.0) * span_m**2 / 8.0 if inp.get("tload") == "U"
               else (flange_force / 1000.0) * span_m / 4.0) * 1e6
        zef = prim["tf"] * prim["bf"]**2 / 4.0
        fw = myf / max(zef, 1e-9)
        m1t = mx + fw * msx / (1.12 * fyf)
        tau = mz * prim["tf"] / max(prim["J"], 1e-9)
        v1t = _number(inp, "Vx") * 1000.0 + tau * vw / (0.6 * fyw)
        result["torsion"] = {"enabled": True, "fv": fv, "phiMz": phi_mz,
                             "fh": flange_force, "Myf": myf, "Zef": zef,
                             "fw": fw, "M1t": m1t, "tau_u": tau, "V1t": v1t}

    if checks["bearing"]:
        bearing_length = _number(inp, "bs", 150.0) + 2.5 * prim["tf"]
        web_dispersion = clear_depth / 2.0
        edge = max(0.0, _number(inp, "boc", 75.0) - bearing_length / 2.0)
        rby = 1.25 * bearing_length * prim["tw"] * fyw
        total_length = edge + bearing_length + web_dispersion
        bearing_area = prim["tw"] * total_length
        bearing_slenderness = 2.5 * clear_depth / prim["tw"]
        bearing_curve = member_slender_reduction(bearing_slenderness, 0.5)
        rbb = fyw * bearing_area * bearing_curve["ac"]
        result["bearing"] = {"enabled": True, "bbf": bearing_length,
                             "bbw": web_dispersion, "bb": total_length,
                             "Rby": rby, "phiRby": PHI * rby,
                             "lam_n_b": bearing_slenderness,
                             "alpha_c_b": bearing_curve["ac"], "Rbb": rbb,
                             "phiRbb": PHI * rbb, "phiRb": min(PHI * rby, PHI * rbb)}

    if checks["fire"]:
        psi = {"F": 0.4, "S": 0.6, "R": 0.0}.get(inp.get("fireload"), 0.4)
        ultimate = 1.2 * _number(inp, "G") + 1.5 * _number(inp, "Q")
        fire_load = _number(inp, "G") + psi * _number(inp, "Q")
        load_ratio = fire_load / ultimate if ultimate else 0.0
        temperature = 905.0 - 690.0 * load_ratio
        ksm = max(_number(inp, "ksm", 25.0), 1e-9)
        result["fire"] = {"enabled": True, "psi_l": psi, "Rstar": ultimate,
                          "Rfire": fire_load, "rf": load_ratio, "Tlim": temperature,
                          "ksm": ksm, "t3": -5.2 + 0.0221 * temperature + 0.433 * temperature / ksm,
                          "t4": -4.7 + 0.0263 * temperature + 0.213 * temperature / ksm}

    utilisation = {
        "bendingX": _ratio(mx, phi_mbx), "bendingY": _ratio(my, phi_msy),
        "shearX": _ratio(_number(inp, "Vx") * 1000.0, phi_vu),
        "shearY": _ratio(_number(inp, "Vy") * 1000.0, PHI * weak_v),
    }
    combined = result["combined"]
    # Cl 8.3.4 applies whenever bending acts about both axes or with axial force,
    # independently of whether the optional axial member checks are enabled.
    if combined["biaxialRequired"] or axial:
        utilisation["combinedSection"] = combined["biaxSectionLinear"]
    if combined["memberChecks"]:
        utilisation["combinedInPlane"] = combined["inPlane"]
        utilisation["combinedInPlaneY"] = combined["inPlaneY"]
        utilisation["combinedOutPlane"] = combined["outPlane"]
    # Cl 8.4.5.1 governs biaxial bending with or without axial force.
    if combined["biaxialRequired"]:
        utilisation["combinedBiaxialMember"] = combined["biaxMember"]
    if checks["compression"]:
        utilisation["compression"] = _ratio(nc, min(phi_ncx, phi_ncy))
    if checks["tension"]:
        utilisation["tension"] = _ratio(nt, result["tension"]["phiNt"])

    if checks["torsion"]:
        torsion = result["torsion"]
        utilisation.update({"torsion": _ratio(_number(inp, "Mz") * 1e6, torsion["phiMz"]),
                            "torsionBendX": _ratio(torsion["M1t"], phi_mbx),
                            "torsionShear": _ratio(torsion["V1t"], phi_vu)})
    if checks["bearing"] and _number(inp, "R"):
        utilisation["bearing"] = _ratio(_number(inp, "R") * 1000.0, result["bearing"]["phiRb"])
    result["util"] = utilisation
    result["worstUtil"] = max((value for value in utilisation.values() if math.isfinite(value)), default=0.0)
    if not checks["compression"]:
        result.pop("compression", None)
    if not checks["tension"]:
        result.pop("tension", None)
    if not checks["compression"] and not checks["momentAmplification"]:
        result.pop("buckling", None)
    return result
