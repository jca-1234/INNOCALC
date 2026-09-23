"""Deep beam design engine using the superseded CEB approach.

Working units are N, mm, MPa and N.mm.  Forces arrive from the form in kN,
moments in kNm and distributed load in kN/m; all are converted once, here.

The design basis is a transcription of the retained Structural Toolkit workbook
``Concrete_DeepBeam_502.xls`` (DEEP BEAMS V5.02, sheet ``Design``).  That
workbook labels its own method "Superceded CEB Approach - Informative only"
(``Info!F19`` and ``Design!B15``); the equations come from Warner, Rangan, Hall
and Faulkes, *Reinforced Concrete*, Longman 1998, cited below as WRHF.
"""

from __future__ import annotations

import math
from typing import Any

from .version import VERSION

MODULE_ID = "concrete-deep-beam"

# CEB span-to-depth applicability limits, Design!H24.
SPAN_TYPES = {
    "S": {"label": "Simple span", "ldLimit": 2.0},
    "D": {"label": "Double span", "ldLimit": 2.5},
    "M": {"label": "Multi-span", "ldLimit": 3.0},
    "C": {"label": "Cantilever", "ldLimit": 1.0},
}

# Serviceability stress limits by crack control class, Design!E38, Cl 12.7.
CRACK_CLASSES = {
    "M": {"label": "Minor", "fsi": 350.0},
    "O": {"label": "Moderate", "fsi": 250.0},
    "S": {"label": "Strong", "fsi": 200.0},
    "W": {"label": "WRHF weak", "fsi": 365.0},
    "C": {"label": "Custom", "fsi": None},
}

BAR_SIZES = (12.0, 16.0, 20.0, 24.0, 28.0, 32.0, 40.0)
YIELD_STRENGTHS = (400.0, 500.0)
STANDARD_MESH_WIRES = (6.75, 7.6, 8.55, 9.5, 10.65, 11.9, 12.0)

FC_MIN = 20.0  # Cl 1.1.2
FC_MAX = 120.0  # Cl 1.1.2
SUPPORT_WIDTH_RATIO = 5.0  # c <= L/5, Design!D23
MESH_RATIO = 0.0025  # WRHF Eq 24.25, welded mesh
BAR_RATIO = 0.002  # WRHF Eq 24.25, plain or deformed bar
CUSTOM_FSI_FLOOR = 0.001  # Design!E38 fallback when a custom fsi is not positive

ASSUMPTIONS = [
    "The design actions Mp*, Mn*, V* and R* are entered directly. The point load and uniform "
    "load fields only produce the informative moment, shear and reaction printed beside them; "
    "they do not feed the design.",
    "The tension tie area is Ast = M* / (fsy.d z), with z the CEB effective lever arm for the "
    "selected span type.",
    "fsy.d is the lesser of fsy / gamma_s and the serviceability stress limit fsi, so "
    "serviceability normally governs the tie area.",
    "External support bearing is not checked for a cantilever and internal support bearing is "
    "not checked for a simple span, matching the source workbook.",
    "Web reinforcement spacing is the maximum permitted by the WRHF reinforcement ratio for a "
    "single wire or bar of the nominated diameter, each way, each face.",
]

LIMITATIONS = [
    "SUPERSEDED METHOD. The source workbook itself states 'Superceded CEB Approach - "
    "Informative only'. This module is informative and must not be used as the sole basis of a "
    "deep beam design. AS 3600:2018 Section 12 strut-and-tie is the current method.",
    "Transcribed from Structural Toolkit DEEP BEAMS V5.02. Independent engineering review of "
    "this transcription has not been completed and the module is not approved for design.",
    "gamma_s and gamma_c are CEB material safety factors, not AS 3600 capacity reduction "
    "factors, and they are entered by the user.",
    "Anchorage and development of the tension tie, detailing of the support zone, torsion, "
    "openings in the web, deflection and fire are excluded.",
    "The reinforcement output is a required area and a nominal bar count; it is not a bar "
    "schedule and it does not check bar spacing, cover or fit.",
]


def _number(inputs: dict[str, Any], key: str, label: str) -> float:
    if key not in inputs or isinstance(inputs[key], bool) or inputs[key] in (None, ""):
        raise ValueError(f"{label} ({key}) must be supplied as a finite number")
    try:
        value = float(inputs[key])
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} ({key}) must be supplied as a finite number") from exc
    if not math.isfinite(value):
        raise ValueError(f"{label} ({key}) must be finite")
    return value


def _positive(inputs: dict[str, Any], key: str, label: str) -> float:
    value = _number(inputs, key, label)
    if value <= 0:
        raise ValueError(f"{label} ({key}) must be greater than zero")
    return value


def _non_negative(inputs: dict[str, Any], key: str, label: str) -> float:
    value = _number(inputs, key, label)
    if value < 0:
        raise ValueError(f"{label} ({key}) must be zero or greater")
    return value


def _option(inputs: dict[str, Any], key: str, label: str, permitted: Any) -> str:
    raw = inputs.get(key)
    if raw in (None, "") or isinstance(raw, bool):
        raise ValueError(f"{label} ({key}) must be one of {', '.join(permitted)}")
    value = str(raw).strip()
    folded = {str(item).upper(): item for item in permitted}
    if value.upper() not in folded:
        raise ValueError(f"{label} ({key}) must be one of {', '.join(permitted)}, not '{value}'")
    return folded[value.upper()]


def _from_set(inputs: dict[str, Any], key: str, label: str, permitted: tuple[float, ...]) -> float:
    value = _number(inputs, key, label)
    if value not in permitted:
        allowed = ", ".join(f"{item:g}" for item in permitted)
        raise ValueError(f"{label} ({key}) must be one of {allowed}, not {value:g}")
    return value


def _ratio(action: float, capacity: float) -> float:
    if not math.isfinite(capacity) or capacity <= 0:
        return math.inf if action > 0 else 0.0
    return action / capacity


def lever_arm(span_type: str, L: float, D: float) -> float:
    """WRHF Eq 24.20 to Eq 24.23 effective lever arm z, Design!E41."""
    ratio = L / D
    if span_type == "S":
        return 0.6 * L if ratio <= 1 else 0.15 * D * (3 + ratio)
    if span_type == "D":
        return 0.45 * L if ratio <= 1 else 0.1 * D * (2.5 + 2 * ratio)
    if span_type == "M":
        return 0.45 * L if ratio <= 1 else 0.15 * D * (2 + ratio)
    return 1.2 * L if ratio <= 0.5 else 0.15 * D * (3 + 2 * ratio)


def compute(inputs: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(inputs, dict):
        raise ValueError("An input dictionary is required")

    # -- Geometry, Design sheet rows 17 to 25 --------------------------------
    span_type = _option(inputs, "spanType", "Span type", SPAN_TYPES)
    L = _positive(inputs, "L", "Span or cantilever length L")
    D = _positive(inputs, "D", "Depth D")
    bw = _positive(inputs, "bw", "Thickness bw")
    support = _positive(inputs, "support", "Support width c")
    Df = _non_negative(inputs, "Df", "Depth of slab Df")
    ld_limit = float(SPAN_TYPES[span_type]["ldLimit"])
    ld_actual = L / D
    support_limit = L / SUPPORT_WIDTH_RATIO

    # -- Materials, Design sheet rows 19 to 22 -------------------------------
    fc = _number(inputs, "fc", "Concrete strength f'c")
    if not FC_MIN <= fc <= FC_MAX:
        raise ValueError(
            f"Concrete strength f'c must be between {FC_MIN:g} and {FC_MAX:g} MPa (Cl 1.1.2)")
    fsy = _from_set(inputs, "fsy", "Reinforcement yield strength fsy", YIELD_STRENGTHS)
    bar = _from_set(inputs, "bar", "Additional bar size", BAR_SIZES)
    mesh = _positive(inputs, "mesh", "Panel mesh wire diameter")

    # -- Crack control and design stress, Design sheet rows 36 to 40 ---------
    crack = _option(inputs, "crack", "Crack control", CRACK_CLASSES)
    if crack == "C":
        custom = _number(inputs, "fsic", "Custom serviceability stress fsi")
        fsi = custom if custom > 0 else CUSTOM_FSI_FLOOR
    else:
        fsi = float(CRACK_CLASSES[crack]["fsi"])
    gamma_s = _positive(inputs, "gs", "Material safety factor gamma_s")
    fsyd = min(fsy / gamma_s, fsi)

    # -- Design actions, Design sheet rows 29 to 33 --------------------------
    Mstar = _non_negative(inputs, "Mstar", "Design positive moment Mp*") * 1e6
    Mstarn = _non_negative(inputs, "Mstarn", "Design negative moment Mn*") * 1e6
    Vstar = _non_negative(inputs, "Vstar", "Design shear V*") * 1e3
    Rstar = _non_negative(inputs, "Rstar", "Design reaction R*") * 1e3
    Pstar = _non_negative(inputs, "Pstar", "Point load P*") * 1e3
    wstar = _non_negative(inputs, "wstar", "Uniform load w*")  # kN/m is numerically N/mm
    if span_type == "C":
        indicative_M = wstar * L ** 2 / 2.0 + Pstar * L
        indicative_V = wstar * L + Pstar
    else:
        indicative_M = wstar * L ** 2 / 8.0 + Pstar * L / 4.0
        indicative_V = wstar * L / 2.0 + Pstar / 2.0

    # -- Tension tie, Design sheet rows 41 to 50 -----------------------------
    z = lever_arm(span_type, L, D)
    Abar = math.pi * bar ** 2 / 4.0
    Ast_pos = Mstar / (fsyd * z)
    Ast_neg = Mstarn / (fsyd * z)
    bars_pos = Ast_pos / Abar
    bars_neg = Ast_neg / Abar
    outer_positive = _number(inputs, "reodiste", "Positive steel fraction in the outer zone")
    if not 0.0 <= outer_positive <= 1.0:
        raise ValueError("The positive steel fraction in the outer zone must be between 0 and 1")
    outer_negative = 0.0 if ld_actual <= 1 else min(0.5 * (ld_actual - 1.0), 1.0)
    outer_depth = 0.2 * D
    middle_depth = 0.6 * D

    # -- Diagonal compression, Design sheet rows 54 to 58 --------------------
    gamma_c = _positive(inputs, "gc", "Material safety factor gamma_c")
    fcd = fc / gamma_c
    phiVu_depth = 0.1 * bw * D * fcd
    phiVu_span = 0.1 * bw * L * fcd
    phiVu = min(phiVu_depth, phiVu_span)

    # -- Web reinforcement, Design sheet rows 62 to 65 -----------------------
    Asw = math.pi * mesh ** 2 / 4.0
    mesh_spacing = Asw / MESH_RATIO / bw
    bar_spacing = Asw / BAR_RATIO / bw

    # -- Support zones, Design sheet rows 69 to 70 ---------------------------
    phiRe = 0.8 * bw * (support + Df) * fcd
    phiRi = 1.2 * bw * (support + 2.0 * Df) * fcd
    external_applies = span_type != "C"  # Design!I11
    internal_applies = span_type != "S"  # Design!I12

    util = {
        "diagonalCompression": _ratio(Vstar, phiVu),
        "spanDepthLimit": _ratio(ld_actual, ld_limit),
        "supportWidthLimit": _ratio(support, support_limit),
    }
    if external_applies:
        util["externalSupport"] = _ratio(Rstar, phiRe)
    if internal_applies:
        util["internalSupport"] = _ratio(Rstar, phiRi)
    finite = [value for value in util.values() if math.isfinite(value)]

    warnings = [
        "The CEB approach used by this calculation is superseded. It is informative only and "
        "must be confirmed against AS 3600:2018 Section 12 strut-and-tie.",
    ]
    if mesh not in STANDARD_MESH_WIRES:
        standard = ", ".join(f"{item:g}" for item in STANDARD_MESH_WIRES)
        warnings.append(
            f"The mesh wire diameter of {mesh:g} mm is not a standard size ({standard} mm)")
    if fsy / gamma_s < fsi:
        warnings.append(
            "fsy / gamma_s governs fsy.d, so the serviceability stress limit is not the "
            "controlling criterion for the tie area")

    return {
        "module": MODULE_ID,
        "version": VERSION,
        "inputs": {"spanType": span_type, "L": L, "D": D, "bw": bw, "support": support, "Df": Df,
                   "fc": fc, "fsy": fsy, "bar": bar, "mesh": mesh, "crack": crack, "fsi": fsi,
                   "gs": gamma_s, "gc": gamma_c, "Mstar": Mstar, "Mstarn": Mstarn,
                   "Vstar": Vstar, "Rstar": Rstar, "Pstar": Pstar, "wstar": wstar,
                   "reodiste": outer_positive},
        "geometry": {"spanType": span_type, "label": SPAN_TYPES[span_type]["label"],
                     "L": L, "D": D, "bw": bw, "support": support, "Df": Df,
                     "ldActual": ld_actual, "ldLimit": ld_limit,
                     "supportLimit": support_limit, "z": z},
        "material": {"fc": fc, "fsy": fsy, "fcd": fcd, "gammaS": gamma_s, "gammaC": gamma_c},
        "serviceability": {"crack": crack, "label": CRACK_CLASSES[crack]["label"],
                           "fsi": fsi, "fsyd": fsyd},
        "loads": {"Mstar": Mstar, "Mstarn": Mstarn, "Vstar": Vstar, "Rstar": Rstar,
                  "Pstar": Pstar, "wstar": wstar,
                  "indicativeM": indicative_M, "indicativeV": indicative_V},
        "reinforcement": {"bar": bar, "Abar": Abar, "AstPositive": Ast_pos,
                          "AstNegative": Ast_neg, "barsPositive": bars_pos,
                          "barsNegative": bars_neg, "outerDepth": outer_depth,
                          "middleDepth": middle_depth},
        "positiveRegion": {"fraction": outer_positive, "depth": outer_depth,
                           "bars": bars_pos * outer_positive},
        "distribution": {"fraction": outer_negative, "outerDepth": outer_depth,
                         "middleDepth": middle_depth,
                         "barsOuterPositive": bars_pos * outer_negative,
                         "barsOuterNegative": bars_neg * outer_negative,
                         "barsMiddlePositive": bars_pos * (1.0 - outer_negative),
                         "barsMiddleNegative": bars_neg * (1.0 - outer_negative)},
        "shear": {"phiVuDepth": phiVu_depth, "phiVuSpan": phiVu_span, "phiVu": phiVu},
        "web": {"mesh": mesh, "Asw": Asw, "meshSpacing": mesh_spacing,
                "barSpacing": bar_spacing},
        "support": {"phiRe": phiRe, "phiRi": phiRi, "externalApplies": external_applies,
                    "internalApplies": internal_applies},
        "checks": {"diagonalCompression": True, "spanDepthLimit": True,
                   "supportWidthLimit": True, "externalSupport": external_applies,
                   "internalSupport": internal_applies},
        "util": util,
        "worstUtil": max(finite) if finite else 0.0,
        "unattainable": [],
        "warnings": warnings,
        "assumptions": list(ASSUMPTIONS),
        "limitations": list(LIMITATIONS),
    }
