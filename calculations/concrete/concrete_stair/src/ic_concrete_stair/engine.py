"""AS 3600:2018 (Amendments 1 and 2) reinforced concrete stair flight engine.

The stair is designed as a one-way spanning member on a **one metre width**.
Working units are N and mm on that strip, so a load in kPa is numerically a line
load in N/mm and a moment is in N.mm per metre width.  Stresses are in MPa and
the concrete density is in kg/m3 because that is the unit AS 3600 Cl 3.1.2 uses.

The design basis is a transcription of the retained Structural Toolkit workbook
``Concrete_Stair_506.xls`` (CONCRETE STAIRS V5.06, sheet ``Design``).
"""

from __future__ import annotations

import math
from typing import Any

from .version import VERSION

MODULE_ID = "concrete-stair"

# Table 2.3.2 deflection constant k4 by span type, Design!D64.
SPAN_TYPES = {
    "S": {"label": "Simple span", "k4": 1.4},
    "I": {"label": "Interior span", "k4": 2.1},
    "E": {"label": "End or exterior span", "k4": 1.75},
}

# AS/NZS 1170.0 Table 4.1 short and long term imposed action factors, Design!D56 and D57.
LOAD_TYPES = {
    "FLOOR": {"label": "Floor", "psiS": 0.7, "psiL": 0.4},
    "OTHER": {"label": "Other", "psiS": 1.0, "psiL": 0.6},
}

DUCTILITY_CLASSES = {"N": "Class N, normal ductility", "L": "Class L, low ductility"}
REINFORCEMENT_MODES = {
    "count": "Total number of bars across the flight width",
    "centres": "Bar centres",
    "area": "Steel area per metre width",
}
DEFLECTION_BASIS = {
    "L": "Local vertical deflection, modifier (1/cos^2 theta)^(1/4)",
    "G": "Global vertical deflection, modifier (1/cos theta)^(1/4)",
}
YES_NO = {"Y": "Yes", "N": "No"}

BAR_SIZES = (10.0, 12.0, 16.0, 20.0, 24.0)
YIELD_STRENGTHS = (250.0, 400.0, 500.0)
BAR_CLASS_PREFIX = {500.0: "N", 400.0: "Y", 250.0: "R"}

FC_MIN = 20.0  # Cl 1.1.2
FC_MAX = 120.0  # Cl 1.1.2
ES = 200000.0  # Cl 3.2.2 modulus of elasticity of reinforcement
KUO_DUCTILITY_LIMIT = 0.36  # Cl 8.1.5
PHI_MIN = 0.65  # Table 2.2.2(b)(i)
PHI_MAX = 0.85  # Table 2.2.2(b)(i)
PHI_CLASS_L = 0.65  # Table 2.2.2(b)(ii)
KCS_FLOOR = 0.8  # Cl 8.5.3.2
STRIP_WIDTH = 1000.0  # the calculation is per metre width

ASSUMPTIONS = [
    "The flight is designed as a one-way member spanning the horizontal span L, on a one metre "
    "width. Every area, load, moment and capacity below is per metre width.",
    "Self weight uses the average thickness of the stepped profile, ath = th + going/ang x "
    "riser/2, increased by the vertical average thickness factor f = ang/going.",
    "The design moment is the simply supported value w* L^2 / 8 for every span type. The span "
    "type only selects the Table 2.3.2 deflection constant k4.",
    "Deflection is the Cl 9.4.4 deemed-to-comply minimum thickness, not a calculated deflection.",
    "Compression steel that falls inside the cracked tension zone is ignored when forming kcs, "
    "as the source workbook does, and a warning is raised.",
]

LIMITATIONS = [
    "Transcribed from Structural Toolkit CONCRETE STAIRS V5.06. Independent engineering review "
    "of this transcription has not been completed and the module is not approved for design.",
    "Shear, torsion, landings, supports, the connection to the supporting structure, "
    "the stair nosing and any transverse or distribution reinforcement are excluded.",
    "Crack control, vibration, fire, durability and a calculated deflection are excluded. Only "
    "the deemed-to-comply thickness rule is applied.",
    "The workbook's mesh naming lookup, a VBA function that matches a pair of steel areas to a "
    "standard mesh designation, is not transcribed. Reinforcement is described by bar size and "
    "spacing only.",
    "The stair is assumed to span the full horizontal span without a mid landing contributing "
    "support. A landed flight must be modelled as separate spans.",
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


def cracked_neutral_axis(n: float, p: float, pc: float, dc_ds: float) -> float:
    """Cracked section neutral axis parameter ku, Design!I58."""
    base = n * p + (n - 1.0) * pc
    return math.sqrt(base ** 2 + 2.0 * (n * p + (n - 1.0) * pc * dc_ds)) - base


def compute(inputs: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(inputs, dict):
        raise ValueError("An input dictionary is required")

    # -- Geometry, Design sheet rows 14 to 21 --------------------------------
    fc = _number(inputs, "fc", "Concrete strength f'c")
    if not FC_MIN <= fc <= FC_MAX:
        raise ValueError(
            f"Concrete strength f'c must be between {FC_MIN:g} and {FC_MAX:g} MPa (Cl 1.1.2)")
    L = _positive(inputs, "L", "Horizontal span L")
    W = _positive(inputs, "W", "Flight width W")
    th = _positive(inputs, "th", "Throat thickness th")
    cover = _non_negative(inputs, "cover", "Bottom cover")
    span_type = _option(inputs, "spanType", "Span type", SPAN_TYPES)
    riser = _positive(inputs, "riser", "Riser")
    going = _positive(inputs, "going", "Going")
    conc = _positive(inputs, "conc", "Concrete unit weight")
    density = _positive(inputs, "density", "Concrete density")

    ang = math.hypot(riser, going)
    f = ang / going
    incline = math.degrees(math.atan(riser / going))
    ath = th + going / ang * riser / 2.0

    # -- Loading, Design sheet rows 24 to 29 ---------------------------------
    wsdl = _non_negative(inputs, "wsdl", "Superimposed dead load")
    wll = _non_negative(inputs, "wll", "Live load")
    wdl = conc * ath / 1000.0 * f
    dead = wdl + wsdl
    wstar = max(1.35 * dead, 1.2 * dead + 1.5 * wll)
    load_case = "1.35 G" if 1.35 * dead > 1.2 * dead + 1.5 * wll else "1.2 G + 1.5 Q"
    Mstar = wstar * L ** 2 / 8.0

    # -- Reinforcement, Design sheet rows 33 to 41 ---------------------------
    bar = _from_set(inputs, "bar", "Bar size", BAR_SIZES)
    fsy = _from_set(inputs, "fsy", "Yield strength fsy", YIELD_STRENGTHS)
    ductility = _option(inputs, "ductilityClass", "Reinforcement ductility class",
                        DUCTILITY_CLASSES)
    mode = _option(inputs, "reoMode", "Reinforcement entry", REINFORCEMENT_MODES)
    quantity = _positive(inputs, "reoValue", "Reinforcement quantity")
    if mode == "count":
        nbars = quantity / (W / 1000.0)
        Ast = nbars * math.pi * bar ** 2 / 4.0
    elif mode == "centres":
        nbars = 1000.0 / quantity
        Ast = nbars * math.pi * bar ** 2 / 4.0
    else:
        nbars = 1.0
        Ast = quantity
    if Ast <= 0:
        raise ValueError("The reinforcement entry gives no tensile steel")
    cts = STRIP_WIDTH / nbars if nbars else 0.0
    ds = th - cover - bar / 2.0
    if ds <= 0:
        raise ValueError("Cover and bar size leave no positive depth to the steel")
    use_vertical_moment = _option(inputs, "useVertM", "Use the vertical depth for bending",
                                  YES_NO)
    eds = (f if use_vertical_moment == "Y" else 1.0) * ds

    # -- Bending, Design sheet rows 43 to 50 ---------------------------------
    alpha2 = max(0.67, 0.85 - 0.0015 * fc)  # Eq 8.1.3(1)
    gamma = max(0.67, 0.97 - 0.0025 * fc)  # Eq 8.1.3(2)
    kuo = fsy * Ast / (alpha2 * fc * gamma * STRIP_WIDTH * ds)
    if ductility == "N":
        phi = min(PHI_MAX, max(PHI_MIN, 1.24 - 13.0 * kuo / 12.0))  # Table 2.2.2(b)(i)
    else:
        phi = PHI_CLASS_L  # Table 2.2.2(b)(ii)
    lever_factor = 1.0 - fsy * Ast / (2.0 * alpha2 * fc * STRIP_WIDTH * eds)
    phiMuo = phi * fsy * Ast * eds * lever_factor
    D = (f if use_vertical_moment == "Y" else 1.0) * th
    Astmin = 0.2 * (D / eds) ** 2 * 0.6 * math.sqrt(fc) / fsy * STRIP_WIDTH * eds

    # -- Deflection, Design sheet rows 52 to 69 ------------------------------
    Asc = _non_negative(inputs, "Asc", "Compression steel area Asc")
    dc = _non_negative(inputs, "dc", "Depth to the compression steel dc")
    load_type = _option(inputs, "loadtype", "Live load type", LOAD_TYPES)
    psiS = float(LOAD_TYPES[load_type]["psiS"])
    psiL = float(LOAD_TYPES[load_type]["psiL"])
    use_fcmi = _option(inputs, "usefcmi", "Use the mean in-situ strength", YES_NO)
    fcmi = (-0.0015 * fc ** 2 + 1.1429 * fc - 0.0614) if use_fcmi == "Y" else fc
    if fcmi <= 40.0:
        Ec = density ** 1.5 * 0.043 * math.sqrt(fcmi)  # Cl 3.1.2
    else:
        Ec = density ** 1.5 * (0.024 * math.sqrt(fcmi) + 0.12)  # Cl 3.1.2
    n = ES / Ec
    p = Ast / (STRIP_WIDTH * ds)
    pc = Asc / (STRIP_WIDTH * ds)
    dc_ds = dc / ds
    ku = cracked_neutral_axis(n, p, pc, dc_ds)
    NA = ku * ds
    compression_in_tension = NA - bar / 2.0 < dc and Asc > 0
    effective_Asc = 0.0 if NA - bar / 2.0 < dc else Asc
    kcs = max(KCS_FLOOR, 2.0 - 1.2 * (effective_Asc / Ast))  # Cl 8.5.3.2
    fdef = (1.0 + kcs) * dead + (psiS + kcs * psiL) * wll
    fdefi = kcs * dead + (psiS + kcs * psiL) * wll

    basis = _option(inputs, "deflectionBasis", "Vertical deflection basis", DEFLECTION_BASIS)
    radians = math.radians(incline)
    if basis == "G":
        incline_mod = (1.0 / math.cos(radians)) ** 0.25
    else:
        incline_mod = (1.0 / math.cos(radians) ** 2) ** 0.25
    k3 = _positive(inputs, "k3", "Deflection constant k3")
    k4 = float(SPAN_TYPES[span_type]["k4"])
    limit_total = _positive(inputs, "spanOverDeflection", "Span to deflection ratio")
    limit_incremental = _positive(inputs, "spanOverDeflectionIncremental",
                                  "Incremental span to deflection ratio")
    use_vertical_deflection = _option(inputs, "useVertD",
                                      "Use the vertical depth for deflection", YES_NO)
    divisor = 1.0 if use_vertical_deflection == "Y" else f

    def minimum_depth(limit: float, load: float) -> float:
        """Table 2.3.2 rearranged for d, with the v5.06 inclined deflection modifier."""
        if load <= 0:
            return 0.0
        return incline_mod * L / (k3 * k4 * (Ec * (1.0 / limit) / (load / 1000.0)) ** (1.0 / 3.0))

    dmin = minimum_depth(limit_total, fdef)
    dmini = minimum_depth(limit_incremental, fdefi)
    thmin = dmin / divisor + bar / 2.0 + cover
    thmin_incremental = dmini / divisor + bar / 2.0 + cover

    util = {
        "bending": _ratio(Mstar, phiMuo),
        "minimumSteel": _ratio(Astmin, Ast),
        "ductility": _ratio(kuo, KUO_DUCTILITY_LIMIT),
        "deflection": _ratio(thmin, ath),
        "deflectionIncremental": _ratio(thmin_incremental, ath),
    }
    finite = [value for value in util.values() if math.isfinite(value)]

    warnings: list[str] = []
    if compression_in_tension:
        warnings.append(
            "Compression steel is inside the cracked tension zone, so Asc is ignored when "
            "forming kcs (Cl 8.5.3.2)")
    if kuo > KUO_DUCTILITY_LIMIT:
        warnings.append(f"kuo is {kuo:.3f}, above the Cl 8.1.5 limit of "
                        f"{KUO_DUCTILITY_LIMIT:g}; the section is non-ductile")
    if lever_factor <= 0:
        warnings.append("The lever arm term is not positive; the section is grossly "
                        "over-reinforced and the capacity is not meaningful")

    return {
        "module": MODULE_ID,
        "version": VERSION,
        "inputs": {"fc": fc, "L": L, "W": W, "th": th, "cover": cover, "spanType": span_type,
                   "riser": riser, "going": going, "conc": conc, "density": density,
                   "wsdl": wsdl, "wll": wll, "loadtype": load_type,
                   "bar": bar, "fsy": fsy, "ductilityClass": ductility,
                   "reoMode": mode, "reoValue": quantity,
                   "Asc": Asc, "dc": dc, "usefcmi": use_fcmi,
                   "useVertM": use_vertical_moment, "useVertD": use_vertical_deflection,
                   "deflectionBasis": basis, "k3": k3,
                   "spanOverDeflection": limit_total,
                   "spanOverDeflectionIncremental": limit_incremental},
        "geometry": {"L": L, "W": W, "th": th, "cover": cover, "riser": riser, "going": going,
                     "ang": ang, "f": f, "incline": incline, "ath": ath, "ds": ds, "eds": eds,
                     "D": D, "spanType": span_type,
                     "label": SPAN_TYPES[span_type]["label"]},
        "material": {"fc": fc, "fsy": fsy, "fcmi": fcmi, "Ec": Ec, "n": n,
                     "density": density, "alpha2": alpha2, "gamma": gamma},
        "loads": {"wdl": wdl, "wsdl": wsdl, "wll": wll, "dead": dead, "wstar": wstar,
                  "case": load_case, "Mstar": Mstar, "psiS": psiS, "psiL": psiL},
        "reinforcement": {"bar": bar, "fsy": fsy, "class": BAR_CLASS_PREFIX[fsy],
                          "mode": mode, "nbars": nbars, "cts": cts, "Ast": Ast,
                          "Astmin": Astmin, "ductility": ductility},
        "bending": {"alpha2": alpha2, "gamma": gamma, "kuo": kuo, "phi": phi,
                    "leverFactor": lever_factor, "phiMuo": phiMuo, "Mstar": Mstar},
        "deflection": {"Asc": Asc, "effectiveAsc": effective_Asc, "dc": dc, "dcOverDs": dc_ds,
                       "p": p, "pc": pc, "ku": ku, "NA": NA, "kcs": kcs,
                       "fdef": fdef, "fdefIncremental": fdefi,
                       "inclineModifier": incline_mod, "basis": basis, "k3": k3, "k4": k4,
                       "dmin": dmin, "dminIncremental": dmini,
                       "thmin": thmin, "thminIncremental": thmin_incremental,
                       "ath": ath, "compressionInTension": compression_in_tension},
        "factors": {"phi": phi, "kcs": kcs, "k3": k3, "k4": k4},
        "checks": {key: True for key in util},
        "util": util,
        "worstUtil": max(finite) if finite else 0.0,
        "unattainable": [],
        "warnings": warnings,
        "assumptions": list(ASSUMPTIONS),
        "limitations": list(LIMITATIONS),
    }
