"""Concrete properties, shrinkage and creep - AS 3600:2018 Section 3.

Transcribes ``Defl!C13:I19`` (density, fcmi and Ec) and ``Creep&Shrink!D11:G61``
(Cl 3.1.7 design shrinkage strain and Cl 3.1.8 creep coefficient).
"""

from __future__ import annotations

import math
from typing import Any

from .common import ES, excel_round

ENVIRONMENTS = {"A": "Arid", "I": "Interior", "T": "Temperate", "R": "Tropical"}
K4_ENVIRONMENT = {"A": 0.7, "I": 0.65, "T": 0.6, "R": 0.5}  # Cl 3.1.7.2 and Cl 3.1.8.3
BASIC_DRYING_STANDARD = 800.0  # x1e-6, Creep&Shrink!E34
# Table 3.1.8.2 basic creep coefficient; the workbook steps to the next listed grade.
CREEP_BASIC = ((20.0, 5.2), (25.0, 4.2), (32.0, 3.4), (40.0, 2.8), (50.0, 2.4), (65.0, 2.0),
               (80.0, 1.7))
CREEP_BASIC_OVER = 1.5


def elastic(fc: float, density: float, use_fcmi: bool) -> dict[str, float]:
    """Cl 3.1.2 Ec from the workbook fcmi curve fit (Defl!D15, Defl!H18)."""
    fcmi = -0.0015 * fc ** 2 + 1.1429 * fc - 0.0614 if use_fcmi else fc
    if fcmi <= 40.0:
        Ec = density ** 1.5 * 0.043 * math.sqrt(fcmi)
    else:
        Ec = density ** 1.5 * (0.024 * math.sqrt(fcmi) + 0.12)
    return {"fcmi": fcmi, "Ec": Ec, "n": ES / Ec, "density": density, "useFcmi": use_fcmi,
            "fctf": 0.6 * math.sqrt(fc), "Es": ES}


def exposed_perimeter(geom: dict[str, Any]) -> float:
    """Creep&Shrink!E25."""
    section, W, D, bef, Tf = geom["section"], geom["W"], geom["D"], geom["bef"], geom["Tf"]
    if section == 0:
        return 2.0 * W
    if section == 1:
        return 2.0 * W + 2.0 * D
    if geom["btype"] == "T":
        return 2.0 * bef + 2.0 * (D - Tf)
    return 2.0 * bef + (D - Tf) + D


def creep_shrinkage(geom: dict[str, Any], mat: dict[str, float], *, fc: float, env: str,
                    shrinkage_mode: str, basic_tested: float, t: float, tau: float,
                    th_manual: float | None, ecs_manual: float | None,
                    fcc_manual: float | None, sigma_o: float) -> dict[str, Any]:
    ue = exposed_perimeter(geom)
    th = th_manual if th_manual is not None else 2.0 * geom["Agbef"] / ue
    k4 = K4_ENVIRONMENT[env]
    alpha1 = 0.8 + 1.2 * math.exp(-0.005 * th)
    k1 = alpha1 * t ** 0.8 / (t ** 0.8 + 0.15 * th)
    basic_star = basic_tested if shrinkage_mode == "T" else BASIC_DRYING_STANDARD
    auto_star = (0.08 * fc - 1.0) * 50.0 if fc > 50 else (0.07 * fc - 0.5) * 50.0
    auto = auto_star * (1.0 - math.exp(-0.07 * t))
    basic = (0.9 - 0.005 * fc) * basic_star
    drying = k1 * k4 * basic
    total = auto + drying
    rounded = excel_round(total, -1)
    ecs = ecs_manual if ecs_manual is not None else rounded

    fccb = next((value for grade, value in CREEP_BASIC if fc <= grade), CREEP_BASIC_OVER)
    alpha2 = 1.0 + 1.12 * math.exp(-0.008 * th)
    k2 = alpha2 * t ** 0.8 / (t ** 0.8 + 0.15 * th)
    k3 = 2.7 / (1.0 + math.log10(tau))
    alpha3 = 0.7 / (k4 * alpha2)
    if fc <= 50:
        k5 = 1.0
    elif fc <= 100:
        k5 = (2.0 - alpha3) - 0.02 * (1.0 - alpha3) * fc
    else:
        k5 = None
    limit = 0.45 * mat["fcmi"]
    k6 = math.exp(1.5 * (sigma_o / mat["fcmi"] - 0.45)) if sigma_o > limit else 1.0
    fcc_calc = k2 * k3 * k4 * k5 * k6 * fccb if k5 is not None else None
    if fcc_manual is not None:
        fcc = fcc_manual
    elif fc > 100:
        raise ValueError("Cl 3.1.8.3 defines k5 only for f'c <= 100 MPa; enter a manual creep "
                         "coefficient (fccManual) for higher strengths")
    else:
        fcc = fcc_calc
    return {"environment": env, "environmentLabel": ENVIRONMENTS[env], "ue": ue, "th": th,
            "thManual": th_manual is not None, "alpha1": alpha1, "k1": k1, "k4": k4,
            "shrinkageMode": shrinkage_mode, "basicStar": basic_star, "autoStar": auto_star,
            "auto": auto, "basic": basic, "drying": drying, "total": total, "rounded": rounded,
            "ecs": ecs, "ecsManual": ecs_manual is not None, "t": t, "tau": tau,
            "fccb": fccb, "alpha2": alpha2, "k2": k2, "k3": k3, "alpha3": alpha3, "k5": k5,
            "sigmaO": sigma_o, "limit045": limit, "k6": k6, "fccCalc": fcc_calc, "fcc": fcc,
            "fccManual": fcc_manual is not None}
