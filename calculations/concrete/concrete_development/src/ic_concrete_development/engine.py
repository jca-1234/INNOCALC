"""AS 3600:2018 Section 13 reinforcement development and lapped splice engine.

Working units are mm, MPa and mm2.  This module produces **lengths**, not a
member design check, so it returns no utilisation.  It does report the source
workbook's two lap validity errors, which force a FAIL summary.

The design basis is a transcription of the retained Structural Toolkit workbook
``Concrete_Development_506.xls`` (REINFORCEMENT DEVELOPMENT V5.06, sheets
``Development`` and ``Cogs``).
"""

from __future__ import annotations

import math
from typing import Any

from .version import VERSION

MODULE_ID = "concrete-development"

YES_NO = {"Y": "Yes", "N": "No"}
ELEMENTS = {"W": "Wide element", "N": "Narrow element"}
ROUNDINGS = {"-1": "Up to 10 mm", "0": "Up to 1 mm", "1": "Up to 0.1 mm"}

STANDARD_BARS = (10.0, 12.0, 16.0, 20.0, 24.0, 28.0, 32.0, 36.0)
YIELD_STRENGTHS = (280.0, 500.0)
BUNDLE_SIZES = (1.0, 2.0, 3.0, 4.0)

FC_MIN = 20.0  # Cl 1.1.2
FC_MAX = 120.0  # Cl 1.1.2
FC_TENSION_CAP = 65.0  # Cl 13.1.2.2
FC_COMPRESSION_CAP = 65.0  # Cl 13.1.5.2, applied only when the user asks for it
MS = 1.0  # Cl 13.1.2.2(c); the slip formed switch was removed at workbook v5.04
COMPRESSION_FLOOR = 200.0  # Cl 13.1.5.2
COMPRESSION_LAP_FLOOR = 300.0  # Cl 13.2.4
PLAIN_TENSION_FLOOR = 300.0  # Cl 13.1.3
HOOK_EXTENSION_FLOOR = 70.0  # Cl 13.1.2.7

ASSUMPTIONS = [
    "This module produces development and lapped splice lengths. It performs no member "
    "strength, serviceability or detailing check and returns no utilisation.",
    "The single bar results carry full precision through the whole chain and are rounded only "
    "for display. The bar size table rounds at every step, exactly as the source workbook does, "
    "so a table value can exceed the corresponding single bar value.",
    "Lapped splices are valid only at the full yield stress. Entering a reduced tension or "
    "compression stress raises the workbook's own lap error and forces a FAIL summary.",
    "The Cl 13.1.2.2(c) slip formed multiplier ms is fixed at 1.0, as the source workbook has "
    "done since its v5.04.",
    "The hook and cog block uses one bar diameter and one set of galvanising and rebending "
    "flags for both shapes; the source workbook repeats the identical formulas twice.",
]

LIMITATIONS = [
    "Transcribed from Structural Toolkit REINFORCEMENT DEVELOPMENT V5.06. Independent "
    "engineering review of this transcription has not been completed and the module is not "
    "approved for design.",
    "Fitments, tendons, welded splices, mechanical splices, headed bars and anchorage of "
    "shear reinforcement are outside this module.",
    "The module does not check that the calculated length fits the member, nor bar spacing, "
    "cover, congestion or constructability.",
    "The Cl 13.2.2 tension lap uses the workbook's own LapCorrection factor, which removes the "
    "Eq 13.1.2.2 lower limit before applying k7. Its derivation is a workbook note, not a "
    "clause, and must be confirmed by the reviewer.",
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


def roundup(value: float, digits: int) -> float:
    """Excel ROUNDUP, which always rounds away from zero at the given precision."""
    factor = 10.0 ** (-digits)
    scaled = value / factor
    return math.ceil(scaled - 1e-9) * factor


def k2_factor(db: float) -> float:
    """Cl 13.1.2.2 bar size factor."""
    return (132.0 - db) / 100.0


def k3_factor(cd: float, db: float) -> float:
    """Cl 13.1.2.2 cover and spacing factor, bounded to 0.7 and 1.0."""
    return min(max(1.0 - 0.15 * (cd - db) / db, 0.7), 1.0)


def lap_correction(db: float, fc: float, cd: float) -> float:
    """The workbook's ``LapCorrection`` VBA function, used by Cl 13.2.2.

    It removes the Eq 13.1.2.2 lower limit before k7 is applied.  Never less
    than one.
    """
    return max(0.058 / 0.5 * k2_factor(db) * math.sqrt(fc) / k3_factor(cd, db), 1.0)


def bundle_multiplier(bundle: float) -> float:
    """Cl 13.1.7 bundled bar multiplier."""
    if bundle <= 2:
        return 1.0
    if bundle == 3:
        return 1.2
    return 1.33


def internal_diameter_factor(db: float, galvanised: str, rebent: str) -> float:
    """Cl 17.2.3.3 nominal internal diameter of a bend, as a multiple of db."""
    if galvanised == "N" and rebent == "N":
        return 5.0
    if galvanised == "Y":
        return 5.0 if db <= 16 else 8.0
    if rebent == "Y":
        if db <= 16:
            return 4.0
        return 5.0 if db <= 24 else 6.0
    return 4.0


def _tension_basic(db: float, *, k1: float, cd: float, fsy: float, fc_tension: float,
                   me: float, ml: float) -> dict[str, float]:
    """Eq 13.1.2.2 basic development length of a deformed bar in tension."""
    k2 = k2_factor(db)
    k3 = k3_factor(cd, db)
    first = 0.5 * k1 * k3 * fsy * db / (k2 * math.sqrt(fc_tension))
    second = 0.058 * fsy * k1 * db
    return {"k2": k2, "k3": k3, "first": first, "second": second,
            "value": max(first, second) * me * ml * MS}


def _compression_basic(db: float, *, fsy: float, fc_compression: float) -> dict[str, float]:
    """Eq 13.1.5.2 basic development length of a deformed bar in compression."""
    first = 0.22 * fsy / math.sqrt(fc_compression) * db
    second = max(0.0435 * fsy * db, COMPRESSION_FLOOR)
    return {"first": first, "second": second, "value": max(first, second)}


def compute(inputs: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(inputs, dict):
        raise ValueError("An input dictionary is required")

    # -- Materials and geometry, Development sheet rows 8 to 23 --------------
    fc = _number(inputs, "fc", "Concrete strength f'c")
    if not FC_MIN <= fc <= FC_MAX:
        raise ValueError(
            f"Concrete strength f'c must be between {FC_MIN:g} and {FC_MAX:g} MPa (Cl 1.1.2)")
    db = _positive(inputs, "db", "Bar diameter db")
    fsy = _from_set(inputs, "fsy", "Reinforcement yield strength fsy", YIELD_STRENGTHS)
    plain = _option(inputs, "plain", "Plain bar", YES_NO)
    lightweight = _option(inputs, "lightweight", "Lightweight concrete", YES_NO)
    epoxy = _option(inputs, "epoxy", "Epoxy coated bars", YES_NO)
    bundle = _from_set(inputs, "bundle", "Bars in bundle", BUNDLE_SIZES)
    cover = _positive(inputs, "cover", "Minimum cover")
    clear = _positive(inputs, "clear", "Clear distance between bars a")
    below = _non_negative(inputs, "below", "Concrete cast below the bar")
    rounding = int(_option(inputs, "rounding", "Rounding", ROUNDINGS))

    fc_tension = min(fc, FC_TENSION_CAP)  # Cl 13.1.2.2
    k1 = 1.3 if below > 300.0 else 1.0  # Cl 13.1.2.2
    cd = min(clear / 2.0, cover)  # Fig 13.1.2.2
    mb = bundle_multiplier(bundle)  # Cl 13.1.7
    me = 1.5 if epoxy == "Y" else 1.0  # Cl 13.1.2.2(a)
    ml = 1.3 if lightweight == "Y" else 1.0  # Cl 13.1.2.2(b)

    # -- Deformed bar in tension, Cl 13.1.2 ----------------------------------
    stress = _positive(inputs, "stress", "Tension bar stress")
    basic = _tension_basic(db, k1=k1, cd=cd, fsy=fsy, fc_tension=fc_tension, me=me, ml=ml)
    Lsytb_b = mb * basic["value"]
    Lst1 = min(stress, fsy) / fsy * Lsytb_b  # Eq 13.1.2.4
    Lst2 = 12.0 * db  # Cl 13.1.2.4(a)
    Lst = max(Lst1, Lst2)
    Lsyt = Lst if stress < fsy else Lsytb_b

    # -- Plain bar in tension, Cl 13.1.3 -------------------------------------
    Lsytp = max(1.5 * Lsyt, PLAIN_TENSION_FLOOR)

    # -- Tension lapped splice, Cl 13.2.2 ------------------------------------
    element = _option(inputs, "element", "Wide or narrow element", ELEMENTS)
    sbb = _non_negative(inputs, "sbb", "Clear distance between spliced bars")
    twice = _option(inputs, "twiceProvided", "Twice the steel provided", YES_NO)
    sb = sbb if sbb >= 3.0 * db else 0.0
    k7 = 1.0 if twice == "Y" else 1.25  # Cl 13.2.2
    correction = max(basic["second"] / basic["first"], 1.0)
    single = (Lsyt if plain == "N" else Lsytp) / mb
    Lsytlap1 = k7 * single / correction
    Lsytlap2 = 0.058 * fsy * k1 * db
    Lsytlap3 = 1.5 * sb + Lsyt / mb
    if element == "W":
        Lsytlap_1 = max(Lsytlap1, Lsytlap2)
    else:
        Lsytlap_1 = max(Lsytlap1, Lsytlap2, Lsytlap3)
    Lsytlap_b = mb * Lsytlap_1

    # -- Deformed bar in compression, Cl 13.1.5 ------------------------------
    stressc = _positive(inputs, "stressc", "Compression bar stress")
    limit_compression = _option(inputs, "limitCompressionFc",
                                "Limit the compression f'c to 65 MPa", YES_NO)
    fc_compression = (FC_COMPRESSION_CAP
                      if limit_compression == "Y" and fc > FC_COMPRESSION_CAP else fc)
    compression = _compression_basic(db, fsy=fsy, fc_compression=fc_compression)
    Lsycb_b = mb * compression["value"]
    Lsc1 = min(stressc, fsy) / fsy * Lsycb_b  # Eq 13.1.5.4
    Lsc = max(COMPRESSION_FLOOR, Lsc1)
    Lsyc = Lsc if stressc < fsy else Lsycb_b
    Lsycp = 2.0 * Lsyc  # Cl 13.1.6

    # -- Compression lapped splice, Cl 13.2.4 --------------------------------
    fitment = _positive(inputs, "fitment", "Fitment diameter")
    spacing = _positive(inputs, "fitmentSpacing", "Fitment spacing")
    three_fitments = _option(inputs, "threeFitments", "At least three fitments", YES_NO)
    helical = _option(inputs, "helical", "Helical fitments", YES_NO)
    helix_bars = _positive(inputs, "helixBars", "Number of bars in the helix")
    Atr = math.pi * fitment ** 2 / 4.0
    Ab = math.pi * db ** 2 / 4.0
    Atr_s = Atr / spacing
    non_helical_ok = Atr_s >= Ab / 1000.0  # Cl 13.2.4(b)
    helical_ok = Atr_s >= helix_bars * Ab / 6000.0  # Cl 13.2.4(c)
    rn = 0.8 if helical == "N" and three_fitments == "Y" and non_helical_ok else 1.0
    rh = 0.8 if helical == "Y" and three_fitments == "Y" and helical_ok else 1.0
    Lsyclap1 = max((Lsyc if plain == "N" else Lsycp) / mb, COMPRESSION_LAP_FLOOR)
    Lsyclap2 = 40.0 * db  # Cl 13.2.4(a)
    Lsyclap_b = mb * rn * rh * max(Lsyclap1, Lsyclap2)

    # -- Table over the standard bar sizes, rounding at every step -----------
    table: list[dict[str, Any]] = []
    for size in STANDARD_BARS:
        tension = _tension_basic(size, k1=k1, cd=cd, fsy=fsy, fc_tension=fc_tension,
                                 me=me, ml=ml)
        Lsytb = roundup(mb * tension["value"], rounding)
        Lsytp_row = roundup(max(1.5 * Lsytb, PLAIN_TENSION_FLOOR), rounding)
        base = Lsytb if plain == "N" else Lsytp_row
        lap1 = k7 * base / mb / lap_correction(size, fc, cd)
        if element == "W":
            lap = max(lap1, 29.0 * k1 * size)
        else:
            lap = max(lap1, 0.058 * fsy * k1 * size,
                      1.5 * (sbb if sbb >= 3.0 * size else 0.0) + Lsytb / mb)
        Lsytlap = roundup(mb * lap, rounding)
        row_compression = _compression_basic(size, fsy=fsy, fc_compression=fc_compression)
        Lsycb = roundup(mb * row_compression["value"], rounding)
        Lsycp_row = roundup(2.0 * Lsycb, rounding)
        compression_base = Lsycb if plain == "N" else Lsycp_row
        Lsyclap = roundup(
            mb * rn * rh * max(max(compression_base / mb, COMPRESSION_LAP_FLOOR),
                               40.0 * size), rounding)
        table.append({"db": size, "Lsytb": Lsytb, "Lsytp": Lsytp_row, "Lsytlap": Lsytlap,
                      "Lsycb": Lsycb, "Lsycp": Lsycp_row, "Lsyclap": Lsyclap})

    # -- Optional hooks and cogs, Cl 13.1.2.7 --------------------------------
    checks = inputs.get("checks") or {}
    if not isinstance(checks, dict):
        raise ValueError("checks must be a dictionary of check activations")
    bends: dict[str, Any] | None = None
    if bool(checks.get("hooksAndCogs")):
        bend_db = _positive(inputs, "bendDb", "Bend bar diameter")
        galvanised = _option(inputs, "galvanised", "Galvanised", YES_NO)
        rebent = _option(inputs, "rebent", "Bar to be rebent or straightened", YES_NO)
        max_internal = _positive(inputs, "maxInternal", "Maximum internal diameter")
        factor = internal_diameter_factor(bend_db, galvanised, rebent)
        nominal = (factor + 1.0) * bend_db
        nominal_max = (max_internal + 1.0) * bend_db
        extension = max(4.0 * bend_db, HOOK_EXTENSION_FLOOR)
        hook = math.pi * nominal / 2.0 + extension
        cog_max = math.pi * nominal_max / 2.0 + extension
        bends = {
            "db": bend_db, "galvanised": galvanised, "rebent": rebent,
            "internalFactor": factor, "nominal": nominal,
            "maxInternalFactor": max_internal, "nominalMax": nominal_max,
            "extension": extension,
            "hook180": hook, "hook135": hook,
            "hook135Extension": 0.125 * math.pi * nominal + extension,
            "cogLength": hook,
            "cogStraight": hook - math.pi * nominal / 4.0,
            "cogHeight": hook - math.pi * nominal / 4.0 + nominal / 2.0 + bend_db / 2.0,
            "cogLengthMax": cog_max,
            "cogStraightMax": cog_max - math.pi * nominal_max / 4.0,
            "cogHeightMax": (cog_max - math.pi * nominal_max / 4.0
                             + nominal_max / 2.0 + bend_db / 2.0),
        }

    errors: list[str] = []
    if stress < fsy:
        errors.append("Tension lapped splices are valid for the full stress only "
                      "(Cl 13.2.2); the tension lap length below must not be used")
    if stressc < fsy:
        errors.append("Compression lapped splices are valid for the full stress only "
                      "(Cl 13.2.4); the compression lap length below must not be used")

    warnings: list[str] = []
    if db not in STANDARD_BARS:
        sizes = ", ".join(f"{size:g}" for size in STANDARD_BARS)
        warnings.append(f"The bar diameter of {db:g} mm is not a standard size ({sizes} mm)")
    if fc > FC_TENSION_CAP:
        warnings.append(
            f"The tension development uses f'c limited to {FC_TENSION_CAP:g} MPa (Cl 13.1.2.2)")
    if limit_compression == "N" and fc > FC_COMPRESSION_CAP:
        warnings.append(
            "The compression development uses the full f'c; the workbook offers an option to "
            "limit it to 65 MPa and that option is off")
    if plain == "Y":
        warnings.append("Plain bar lengths are reported; deformed bar values are also shown "
                        "for comparison")

    return {
        "module": MODULE_ID,
        "version": VERSION,
        "inputs": {"fc": fc, "db": db, "fsy": fsy, "plain": plain,
                   "lightweight": lightweight, "epoxy": epoxy, "bundle": bundle,
                   "cover": cover, "clear": clear, "below": below, "rounding": rounding,
                   "stress": stress, "stressc": stressc, "element": element, "sbb": sbb,
                   "twiceProvided": twice, "limitCompressionFc": limit_compression,
                   "fitment": fitment, "fitmentSpacing": spacing,
                   "threeFitments": three_fitments, "helical": helical,
                   "helixBars": helix_bars},
        "factors": {"fcTension": fc_tension, "fcCompression": fc_compression,
                    "k1": k1, "k2": basic["k2"], "k3": basic["k3"], "cd": cd,
                    "mb": mb, "me": me, "ml": ml, "ms": MS, "k7": k7,
                    "correction": correction, "sb": sb, "rn": rn, "rh": rh},
        "tension": {"Lsytb1": basic["first"], "Lsytb2": basic["second"],
                    "Lsytb1Bar": basic["value"], "Lsytb": Lsytb_b,
                    "Lst1": Lst1, "Lst2": Lst2, "Lst": Lst, "Lsyt": Lsyt,
                    "hookAllowance": 0.5 * Lsyt,
                    "Lsytp": Lsytp, "hookAllowancePlain": 0.5 * Lsytp},
        "tensionLap": {"Lsytlap1": Lsytlap1, "Lsytlap2": Lsytlap2, "Lsytlap3": Lsytlap3,
                       "Lsytlap": Lsytlap_b, "element": element, "sb": sb,
                       "correction": correction},
        "compression": {"Lsycb1": compression["first"], "Lsycb2": compression["second"],
                        "Lsycb1Bar": compression["value"], "Lsycb": Lsycb_b,
                        "Lsc1": Lsc1, "Lsc": Lsc, "Lsyc": Lsyc, "Lsycp": Lsycp},
        "compressionLap": {"Atr": Atr, "Ab": Ab, "AtrOverS": Atr_s,
                           "nonHelicalThreshold": Ab / 1000.0,
                           "helicalThreshold": helix_bars * Ab / 6000.0,
                           "nonHelicalOk": non_helical_ok, "helicalOk": helical_ok,
                           "rn": rn, "rh": rh, "Lsyclap1": Lsyclap1, "Lsyclap2": Lsyclap2,
                           "Lsyclap": Lsyclap_b},
        "table": table,
        "bends": bends,
        "checks": {"hooksAndCogs": bends is not None},
        "util": {},
        "worstUtil": 0.0,
        "unattainable": [],
        "errors": errors,
        "warnings": warnings,
        "assumptions": list(ASSUMPTIONS),
        "limitations": list(LIMITATIONS),
    }
