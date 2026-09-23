"""AS 3600:2018 (Amendments 1 and 2) Section 20 plain concrete design engine.

Working units are N, mm, MPa and N.mm.  Forces arrive from the form in kN and
moments in kNm; both are converted once, here, at the input boundary.

The design basis is a transcription of the retained Structural Toolkit workbook
``Concrete_Plain_502.xls`` (PLAIN CONCRETE V5.02, sheet ``Design``).  Every
capacity equation carries the clause the workbook cites.
"""

from __future__ import annotations

import math
from typing import Any

from .version import VERSION

MODULE_ID = "concrete-plain"

DIRECTIONS = {"L": "Parallel to the column length L", "W": "Parallel to the column width W"}
PERIMETER_MODES = {"calculated": "From aL and aW", "manual": "Manually entered perimeter"}
YES_NO = {"Y": "Yes", "N": "No"}

PHI = 0.6  # Table 2.2.2(g), plain concrete
FC_MIN = 20.0  # Cl 1.1.2
FC_MAX = 120.0  # Cl 1.1.2
DEPTH_ALLOWANCE = 50.0  # Cl 20.4.1, D = Dt - 50
MINIMUM_NOMINAL_DEPTH = 200.0  # Cl 20.4.1
PEDESTAL_HEIGHT_FACTOR = 3.0  # Cl 20.1(a)
MINIMUM_ECCENTRICITY_RATIO = 0.1  # Cl 20.3

ASSUMPTIONS = [
    "Plain concrete: no reinforcement is relied on for strength anywhere in this calculation.",
    "The footing design depth is D = Dt - 50 mm, the Cl 20.4.1 allowance for unevenness.",
    "P* is positive in compression. Mx*, My*, Mstar and Vstar are used as magnitudes; the "
    "pedestal stress equations take the absolute value of each applied moment.",
    "The pedestal bending stresses combine the applied moment with the eccentric moment "
    "|P*| x design eccentricity about the same axis.",
    "The punching perimeter is the mid-slab case of Fig 9.3(A). Edge and corner columns, and "
    "perimeters interrupted by penetrations, need the manual perimeter entry.",
    "The source workbook prints the Cl 20.4.2 bending capacity and the Eq 20.4.3(1) one-way "
    "shear capacity without an on-sheet comparison. This module compares them against the same "
    "M* and V* that the workbook uses for the Eq 20.4.3(2) punching interaction. Confirm that "
    "those actions are the correct demands for all three checks before relying on the result.",
]

LIMITATIONS = [
    "Transcribed from Structural Toolkit PLAIN CONCRETE V5.02. Independent engineering review "
    "of this transcription has not been completed and the module is not approved for design.",
    "Bearing, sliding, overturning, soil pressure, settlement and any geotechnical check are "
    "outside this module. It sizes the concrete only.",
    "Serviceability, shrinkage, temperature, durability, fire and fatigue are excluded.",
    "The pedestal height is not an input; only the Cl 20.1(a) maximum permitted height is "
    "reported for the engineer to check against the actual pedestal.",
    "The workbook's retired 'cast against soil' switch is not offered; AS 3600:2018 makes the "
    "50 mm depth allowance mandatory.",
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
    # Excel compares text case-insensitively, so the workbook accepts "w" for "W".
    value = str(raw).strip()
    folded = {str(item).upper(): item for item in permitted}
    if value.upper() not in folded:
        raise ValueError(f"{label} ({key}) must be one of {', '.join(permitted)}, not '{value}'")
    return folded[value.upper()]


def _ratio(action: float, capacity: float) -> float:
    if not math.isfinite(capacity) or capacity <= 0:
        return math.inf if action > 0 else 0.0
    return action / capacity


def compute(inputs: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(inputs, dict):
        raise ValueError("An input dictionary is required")

    # -- Footing geometry, Design sheet rows 9 to 18 -------------------------
    fc = _number(inputs, "fc", "Concrete strength f'c")
    if not FC_MIN <= fc <= FC_MAX:
        raise ValueError(
            f"Concrete strength f'c must be between {FC_MIN:g} and {FC_MAX:g} MPa (Cl 1.1.2)")
    Dt = _positive(inputs, "Dt", "Nominal depth Dt")
    B = _positive(inputs, "B", "Breadth b")
    D = max(0.0, Dt - DEPTH_ALLOWANCE)
    if D <= 0:
        raise ValueError("The nominal depth Dt must exceed the 50 mm Cl 20.4.1 allowance")

    # -- Bending, Cl 20.4.2 --------------------------------------------------
    fcf = 0.6 * math.sqrt(fc)  # Cl 3.1.1.3
    phiMuo = PHI * fcf * B * D ** 2 / 6.0

    # -- One-way shear, Eq 20.4.3(1) -----------------------------------------
    critical = 0.5 * D
    phiVu1 = PHI * 0.15 * B * D * fc ** (1.0 / 3.0)

    # -- Two-way shear, Cl 20.4.3(b) -----------------------------------------
    L = _positive(inputs, "L", "Column length L")
    W = _positive(inputs, "W", "Column width W")
    aL = L + D
    aW = W + D
    uc = 2.0 * aL + 2.0 * aW
    perimeter_mode = _option(inputs, "uMode", "Shear perimeter", PERIMETER_MODES)
    u = _positive(inputs, "um", "Manual shear perimeter") if perimeter_mode == "manual" else uc
    bh = max(L, W) / min(L, W)  # Cl 9.3.1.4 aspect ratio
    phiVumax = PHI * 0.2 * u * D * math.sqrt(fc)
    phiVuu = PHI * 0.1 * u * D * (1.0 + 2.0 / bh) * math.sqrt(fc)
    phiVu = min(phiVuu, phiVumax)

    # -- Effect of moment on punching, Eq 20.4.3(2) --------------------------
    Mstar = _non_negative(inputs, "Mstar", "Design moment M*") * 1e6
    Vstar = _non_negative(inputs, "Vstar", "Design shear V*") * 1e3
    direction = _option(inputs, "Dir", "Direction", DIRECTIONS)
    a = aL if direction == "L" else aW
    if Mstar == 0.0:
        phiVum = phiVu
    elif Vstar == 0.0:
        raise ValueError(
            "A design shear V* is required to apply the Eq 20.4.3(2) moment reduction; "
            "enter V*, or set M* to zero")
    else:
        phiVum = phiVu / (1.0 + u * Mstar / (8.0 * Vstar * a * D))

    # -- Unreinforced pedestal, Cl 20.3 --------------------------------------
    Pstar = _number(inputs, "Pstar", "Ultimate reaction P*") * 1e3
    eccx = _non_negative(inputs, "eccx", "Eccentricity eccx")
    eccy = _non_negative(inputs, "eccy", "Eccentricity eccy")
    Mxstar = _number(inputs, "Mxstar", "Applied moment Mx*") * 1e6
    Mystar = _number(inputs, "Mystar", "Applied moment My*") * 1e6
    Lpx = _positive(inputs, "Lpx", "Pedestal plan length Lpx")
    Wpy = _positive(inputs, "Wpy", "Pedestal plan width Wpy")
    ignore_ecc = _option(inputs, "ignoreEcc", "Ignore minimum eccentricity", YES_NO)
    Ag = Lpx * Wpy
    max_height = PEDESTAL_HEIGHT_FACTOR * min(Wpy, Lpx)
    ax = 0.0 if ignore_ecc == "Y" else MINIMUM_ECCENTRICITY_RATIO * Lpx
    ay = 0.0 if ignore_ecc == "Y" else MINIMUM_ECCENTRICITY_RATIO * Wpy
    dax = max(eccx, ax)
    day = max(eccy, ay)

    sigma_a = Pstar / Ag
    Mxecc = abs(Pstar) * dax
    Myecc = abs(Pstar) * day
    sigma_bx = 6.0 * (abs(Mxstar) + Mxecc) / (Wpy * Lpx ** 2)
    sigma_by = 6.0 * (abs(Mystar) + Myecc) / (Lpx * Wpy ** 2)
    sigma_tc = max(0.0, sigma_a + sigma_bx + sigma_by)
    sigma_tt = min(0.0, sigma_a - sigma_bx - sigma_by)
    sigma_cmax = PHI * 0.4 * fc
    sigma_tmax = PHI * 0.45 * math.sqrt(fc)
    phiNuo_c = sigma_cmax * Ag
    phiNuo_t = sigma_tmax * Ag

    util = {
        "bending": _ratio(Mstar, phiMuo),
        "oneWayShear": _ratio(Vstar, phiVu1),
        "punchingShear": _ratio(Vstar, phiVum),
        "pedestalCompression": _ratio(sigma_tc, sigma_cmax),
        "pedestalTension": _ratio(abs(sigma_tt), sigma_tmax),
        "minimumDepth": _ratio(MINIMUM_NOMINAL_DEPTH, Dt),
    }
    finite = [value for value in util.values() if math.isfinite(value)]

    warnings: list[str] = []
    if ignore_ecc == "Y":
        warnings.append(
            "The Cl 20.3 minimum eccentricity of 0.1 times each plan dimension has been "
            "overridden and is not applied")
    if perimeter_mode == "manual":
        warnings.append(
            f"The punching perimeter was entered manually as {u:.0f} mm; the calculated "
            f"mid-slab perimeter is {uc:.0f} mm")
    if bh > 2.0:
        warnings.append(
            f"The column aspect ratio beta_h is {bh:.2f}; confirm the Cl 20.4.3(b) punching "
            "model suits such an elongated loaded area")

    return {
        "module": MODULE_ID,
        "version": VERSION,
        "inputs": {
            "fc": fc, "Dt": Dt, "B": B, "L": L, "W": W,
            "uMode": perimeter_mode, "um": u if perimeter_mode == "manual" else 0.0,
            "Mstar": Mstar, "Vstar": Vstar, "Dir": direction,
            "Pstar": Pstar, "eccx": eccx, "eccy": eccy,
            "Mxstar": Mxstar, "Mystar": Mystar, "Lpx": Lpx, "Wpy": Wpy,
            "ignoreEcc": ignore_ecc,
        },
        "geometry": {"Dt": Dt, "D": D, "B": B, "minimumDepth": MINIMUM_NOMINAL_DEPTH},
        "material": {"fc": fc, "fcf": fcf},
        "footing": {"fcf": fcf, "phiMuo": phiMuo, "critical": critical, "phiVu1": phiVu1},
        "punching": {"aL": aL, "aW": aW, "uc": uc, "u": u, "bh": bh, "a": a,
                     "phiVumax": phiVumax, "phiVuu": phiVuu, "phiVu": phiVu,
                     "phiVum": phiVum, "mode": perimeter_mode, "direction": direction},
        "pedestal": {"Lpx": Lpx, "Wpy": Wpy, "Ag": Ag, "maxHeight": max_height,
                     "ax": ax, "ay": ay, "dax": dax, "day": day,
                     "sigmaA": sigma_a, "Mxecc": Mxecc, "Myecc": Myecc,
                     "sigmaBx": sigma_bx, "sigmaBy": sigma_by,
                     "sigmaTc": sigma_tc, "sigmaTt": sigma_tt,
                     "sigmaCmax": sigma_cmax, "sigmaTmax": sigma_tmax,
                     "phiNuoC": phiNuo_c, "phiNuoT": phiNuo_t,
                     "ignoreEcc": ignore_ecc},
        "loads": {"Mstar": Mstar, "Vstar": Vstar, "Pstar": Pstar,
                  "Mxstar": Mxstar, "Mystar": Mystar},
        "factors": {"phi": PHI},
        "checks": {"bending": True, "oneWayShear": True, "punchingShear": True,
                   "pedestalCompression": True, "pedestalTension": True,
                   "minimumDepth": True},
        "util": util,
        "worstUtil": max(finite) if finite else 0.0,
        "unattainable": [],
        "warnings": warnings,
        "assumptions": list(ASSUMPTIONS),
        "limitations": list(LIMITATIONS),
    }
