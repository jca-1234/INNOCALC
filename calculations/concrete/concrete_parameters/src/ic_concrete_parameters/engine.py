"""AS 3600:2018 concrete material and stress block parameter engine.

Working units are N, mm and MPa, with concrete density in kg/m3 because that is
the unit AS 3600 Cl 3.1.2 uses in the modulus of elasticity expression.

The design basis is a transcription of the retained Structural Toolkit workbook
``Concrete_Formula_502.xls`` (FORMULA V5.02, sheets ``Formula`` and
``Strength``).  That workbook is a printed reference sheet: it computes material
parameters and carries no member design check, so this module produces no
utilisation.
"""

from __future__ import annotations

import math
from typing import Any

from .version import VERSION

MODULE_ID = "concrete-parameters"

FC_MIN = 20.0  # Cl 1.1.2
FC_MAX = 120.0  # Cl 1.1.2
EPSILON_C = 0.003  # Cl 10.6.1(d), maximum concrete compressive strain
FACTOR_FLOOR = 0.67  # Eq 8.1.3(1), Eq 8.1.3(2), Eq 10.6.2.5(1), Eq 10.6.2.5(2)
ALPHA1_MIN = 0.72  # Eq 10.6.2.2
ALPHA1_MAX = 0.85  # Eq 10.6.2.2
DEFAULT_DENSITY = 2400.0  # Cl 3.1.3, typical normal weight concrete

# AS 3600 Table 3.1.2 mean in-situ compressive strength at 28 days.
TABLE_3_1_2 = {20.0: 22.0, 25.0: 28.0, 32.0: 35.0, 40.0: 43.0, 50.0: 53.0,
               65.0: 68.0, 80.0: 82.0, 100.0: 99.0, 120.0: 115.0}

FCMI_SOURCES = {
    "table": "AS 3600 Table 3.1.2",
    "curve": "Workbook curve fit to Table 3.1.2",
    "as2327": "AS 2327:2017 Table 3.6.2.3",
}

# Workbook Strength sheet: ratio of f'c at age T to f'c at 28 days.
STRENGTH_GAIN = [
    {"day": 1, "normal": 0.16, "highEarly": 0.34},
    {"day": 3, "normal": 0.45, "highEarly": 0.60},
    {"day": 7, "normal": 0.66, "highEarly": 0.78},
    {"day": 28, "normal": 1.00, "highEarly": 1.00},
    {"day": 90, "normal": 1.24, "highEarly": 1.14},
    {"day": 365, "normal": 1.34, "highEarly": 1.20},
]
CEMENTS = {"N": "Normal class cement", "H": "High early strength cement"}

SECTION_TYPES = {
    "rect": "Rectangular section",
    "TLweb": "T or L section, web in tension",
    "TLflange": "T or L section, flange in tension",
    "slabCorner": "Slab supported by columns at its corners",
    "slab4side": "Slab supported by walls or beams on four sides",
}
SLAB_TYPES = ("slabCorner", "slab4side")

ASSUMPTIONS = [
    "This module reports material and section parameters. It performs no strength, "
    "serviceability or detailing check and returns no utilisation.",
    "Eq 8.1.3(1) and Eq 8.1.3(2) are applied with their 0.67 lower bounds, as the workbook "
    "states for the identical column equations Eq 10.6.2.5(1) and Eq 10.6.2.5(2).",
    "The Cl 3.1.2 modulus of elasticity is a mean value with a range of plus or minus 20 per "
    "cent, and it is calculated from the selected mean in-situ strength fcmi.",
    "Minimum reinforcement is the deemed-to-comply area of Cl 8.1.6.1 or Cl 9.1.1; it does not "
    "on its own satisfy the strength or crack control requirements.",
]

LIMITATIONS = [
    "Transcribed from Structural Toolkit FORMULA V5.02. Independent engineering review of this "
    "transcription has not been completed and the module is not approved for design.",
    "The strength gain with age table is the workbook's own; it carries no AS 3600 clause "
    "reference and its provenance has not been established. Do not use it for a specification "
    "or an acceptance decision without an authoritative source.",
    "The fcmi curve fit is the workbook's own approximation to Table 3.1.2 and is not a code "
    "equation. The Table 3.1.2 source is exact but only defined at the standard grades.",
    "The AS 2327:2017 fcmi expression is provided for composite work and is not interchangeable "
    "with the AS 3600 value.",
    "Creep, shrinkage, thermal properties, durability exposure classification and fire "
    "properties are outside this module.",
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


def _option(inputs: dict[str, Any], key: str, label: str, permitted: Any) -> str:
    raw = inputs.get(key)
    if raw in (None, "") or isinstance(raw, bool):
        raise ValueError(f"{label} ({key}) must be one of {', '.join(permitted)}")
    value = str(raw).strip()
    folded = {str(item).upper(): item for item in permitted}
    if value.upper() not in folded:
        raise ValueError(f"{label} ({key}) must be one of {', '.join(permitted)}, not '{value}'")
    return folded[value.upper()]


def fcmi_curve(fc: float) -> float:
    """Workbook curve fit to AS 3600 Table 3.1.2.  Not a code equation."""
    return -0.0015 * fc ** 2 + 1.1429 * fc - 0.0614


def fcmi_as2327(fc: float) -> float:
    """AS 2327:2017 Table 3.6.2.3 mean in-situ compressive strength."""
    return 0.9 * (1.2875 - 0.001875 * fc) * fc


def modulus_of_elasticity(density: float, fcmi: float) -> float:
    """Cl 3.1.2 mean modulus of elasticity, in MPa, plus or minus 20 per cent."""
    if fcmi <= 40.0:
        return density ** 1.5 * 0.043 * math.sqrt(fcmi)
    return density ** 1.5 * (0.024 * math.sqrt(fcmi) + 0.12)


def alpha_b(section: str, *, bef: float, bw: float, Ds: float, D: float) -> float:
    """Cl 8.1.6.1 and Cl 9.1.1 deemed-to-comply minimum reinforcement factor."""
    if section == "rect":
        return 0.20
    if section == "slabCorner":
        return 0.24
    if section == "slab4side":
        return 0.19
    flange = bef / bw
    if section == "TLweb":
        return max(0.20 + (flange - 1.0) * (0.4 * Ds / D - 0.18), 0.20 * flange ** 0.25)
    return max(0.20 + (flange - 1.0) * (0.25 * Ds / D - 0.08), 0.20 * flange ** (2.0 / 3.0))


def compute(inputs: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(inputs, dict):
        raise ValueError("An input dictionary is required")

    fc = _number(inputs, "fc", "Concrete strength f'c")
    if not FC_MIN <= fc <= FC_MAX:
        raise ValueError(
            f"Concrete strength f'c must be between {FC_MIN:g} and {FC_MAX:g} MPa (Cl 1.1.2)")
    density = _positive(inputs, "density", "Concrete density")

    # -- Rectangular stress block ------------------------------------------
    alpha1_raw = 1.0 - 0.003 * fc  # Eq 10.6.2.2, also the AS 3600:2009 alpha2
    alpha1 = min(ALPHA1_MAX, max(ALPHA1_MIN, alpha1_raw))
    alpha2 = max(FACTOR_FLOOR, 0.85 - 0.0015 * fc)  # Eq 8.1.3(1), Eq 10.6.2.5(1)
    gamma = max(FACTOR_FLOOR, 0.97 - 0.0025 * fc)  # Eq 8.1.3(2), Eq 10.6.2.5(2)

    # -- Strength and stiffness --------------------------------------------
    fctf = 0.6 * math.sqrt(fc)  # Cl 3.1.1.3
    fct = 0.36 * math.sqrt(fc)  # Cl 3.1.1.3
    curve = fcmi_curve(fc)
    as2327 = fcmi_as2327(fc)
    table = TABLE_3_1_2.get(fc)
    source = _option(inputs, "fcmiSource", "Mean in-situ strength source", FCMI_SOURCES)
    if source == "table":
        if table is None:
            grades = ", ".join(f"{grade:g}" for grade in sorted(TABLE_3_1_2))
            raise ValueError(
                f"AS 3600 Table 3.1.2 only defines fcmi at f'c = {grades} MPa; choose another "
                "source for an intermediate grade")
        fcmi = table
    else:
        fcmi = curve if source == "curve" else as2327
    Ec = modulus_of_elasticity(density, fcmi)

    # -- Strength gain with age --------------------------------------------
    cement = _option(inputs, "cement", "Cement type", CEMENTS)
    age = _number(inputs, "age", "Age")
    ages = [{"day": entry["day"], "normal": fc * entry["normal"],
             "highEarly": fc * entry["highEarly"],
             "ratioNormal": entry["normal"], "ratioHighEarly": entry["highEarly"]}
            for entry in STRENGTH_GAIN]
    selected = next((entry for entry in ages if float(entry["day"]) == age), None)
    if selected is None:
        days = ", ".join(str(entry["day"]) for entry in STRENGTH_GAIN)
        raise ValueError(f"Age must be one of the tabulated ages {days} days, not {age:g}")
    design_strength = selected["normal"] if cement == "N" else selected["highEarly"]

    checks = inputs.get("checks") or {}
    if not isinstance(checks, dict):
        raise ValueError("checks must be a dictionary of check activations")
    want_minimum = bool(checks.get("minimumSteel"))
    want_cracking = bool(checks.get("cracking"))

    minimum: dict[str, Any] | None = None
    if want_minimum:
        section = _option(inputs, "sectionType", "Section type", SECTION_TYPES)
        bw = _positive(inputs, "bw", "Web width bw")
        D = _positive(inputs, "D", "Overall depth D")
        ds = _positive(inputs, "ds", "Depth to the tensile steel ds")
        fsy = _positive(inputs, "fsy", "Yield strength fsy")
        if ds > D:
            raise ValueError("The depth to the tensile steel ds cannot exceed the overall depth D")
        if section in ("TLweb", "TLflange"):
            bef = _positive(inputs, "bef", "Effective flange width bef")
            Ds = _positive(inputs, "Ds", "Flange thickness Ds")
            if bef < bw:
                raise ValueError("The effective flange width bef cannot be less than the web bw")
            if Ds > D:
                raise ValueError("The flange thickness Ds cannot exceed the overall depth D")
        else:
            bef, Ds = bw, D
        factor = alpha_b(section, bef=bef, bw=bw, Ds=Ds, D=D)
        minimum = {
            "section": section, "alphaB": factor, "bw": bw, "D": D, "ds": ds, "fsy": fsy,
            "bef": bef, "Ds": Ds,
            "Astmin": factor * (D / ds) ** 2 * fctf / fsy * bw * ds,
            "reference": "Cl 9.1.1" if section in SLAB_TYPES else "Cl 8.1.6.1",
        }

    cracking: dict[str, Any] | None = None
    if want_cracking:
        Zt = _positive(inputs, "Zt", "Section modulus Zt")
        Zb = _positive(inputs, "Zb", "Section modulus Zb")
        cracking = {"Zt": Zt, "Zb": Zb, "MuoTop": 1.2 * Zt * fctf, "MuoBottom": 1.2 * Zb * fctf}

    return {
        "module": MODULE_ID,
        "version": VERSION,
        "inputs": {"fc": fc, "density": density, "fcmiSource": source, "cement": cement,
                   "age": selected["day"]},
        "stressBlock": {"alpha1": alpha1, "alpha1Unbounded": alpha1_raw, "alpha2": alpha2,
                        "gamma": gamma, "epsilonC": EPSILON_C,
                        "alpha2_2009": alpha1_raw},
        "material": {"fc": fc, "density": density, "fctf": fctf, "fct": fct,
                     "fcmiTable": table, "fcmiCurve": curve, "fcmiAs2327": as2327,
                     "fcmi": fcmi, "fcmiSource": source, "Ec": Ec,
                     "EcLower": 0.8 * Ec, "EcUpper": 1.2 * Ec},
        "strength": {"cement": cement, "age": selected["day"], "design": design_strength,
                     "ages": ages},
        "minimumSteel": minimum,
        "cracking": cracking,
        "checks": {"minimumSteel": want_minimum, "cracking": want_cracking},
        "util": {},
        "worstUtil": 0.0,
        "unattainable": [],
        "warnings": [],
        "assumptions": list(ASSUMPTIONS),
        "limitations": list(LIMITATIONS),
    }
