"""AS 3600:2018 (Amendments 1 and 2) reinforced concrete wall engine.

Working units follow the workbook: axial actions and capacities per metre run in
kN/m, out-of-plane moments in kNm/m, the in-plane moment in kNm, in-plane shear in
kN, lengths in mm and stresses in MPa.

The design basis is a transcription of the retained Structural Toolkit workbook
``Concrete_Wall_511.xls`` (CONCRETE WALLS V5.11, sheets ``Design``, ``Shear`` and
``Settings``).  The ``ACI`` and ``Thermal`` sheets are hidden (``Settings!B151:C152``)
and the ``ACI`` sheet states "Not updated to AS 3600-2018 yet, also not checked";
neither is transcribed.  ``As Column`` holds application notes only.
"""

from __future__ import annotations

import math
from typing import Any

from .version import VERSION

MODULE_ID = "concrete-wall"

FC_MIN, FC_MAX = 20.0, 120.0  # Cl 1.1.2
CONCRETE_WEIGHT = 25.0  # kN/m3, Design!D30
BAR_SIZES = (10.0, 12.0, 16.0, 20.0, 24.0, 28.0, 32.0)  # Settings!I11:I17
YIELD_STRENGTHS = (400.0, 500.0)  # Settings!I20:I21
PHI_WALL = 0.65  # Cl 11.5.3, Design!E61
PHI_SHEAR = 0.7  # Table 2.2.2, Shear!E26
SINGLE_LAYER_STRESS = 3.0  # MPa, Cl 11.5.2(a)
SLAB_STRESS_FACTOR = 0.03  # x f'c, Cl 11.1(b)(i)
SLAB_SLENDERNESS = 50.0  # Hwe/tw, Cl 11.1(b)(i)
MAX_SPACING = 350.0  # mm, Cl 11.7.3

LOAD_TYPES = {"F": "Floor", "S": "Storage", "R": "Roof", "O": "Other"}
# Design!H28 and Design!H30; "O" takes the user factors Design!H29 and Design!H31.
PSI_LONG = {"F": 0.6, "S": 1.0, "R": 0.0}
PSI_EARTHQUAKE = {"F": 0.3, "S": 0.6, "R": 0.0}

METHOD_TEXT = {0: "Design for tension", 1: "Design as wall or column", 2: "Design as slab",
               3: "Design as column and slab"}  # Settings!X133

# Cl 11.7.2 horizontal crack control ratios, Design!D115:E118.
CRACK_CONTROL = {
    "MINOR": (0.0025, "Minor (A1 and A2)"),
    "MODERATE": (0.0035, "Moderate and hidden (A1 and A2)"),
    "STRONG": (0.006, "Strong for appearance (A1 and A2)"),
    "EXPOSURE_BC": (0.006, "Exposure classifications B1, B2, C1 and C2"),
}

EXPOSURE_CLASSES = ("A1", "A2", "B1", "B2", "C1", "C2")
# Minimum cover by f'c band from the workbook CalcExposure routine: Table 4.10.3.2
# (standard formwork, "S") and Table 4.10.3.3 (rigid formwork, "R").  A value in a
# 2-tuple is a bracketed cover that relies on the Cl 4.3.2 strength concession.
FC_BANDS = (20.0, 25.0, 32.0, 40.0, 50.0)
EXPOSURE_COVER = {
    "S": (
        {"A1": 20.0, "A2": (50.0,)},
        {"A1": 20.0, "A2": 30.0, "B1": (60.0,)},
        {"A1": 20.0, "A2": 25.0, "B1": 40.0, "B2": (65.0,)},
        {"A1": 20.0, "A2": 20.0, "B1": 30.0, "B2": 45.0, "C1": (70.0,)},
        {"A1": 20.0, "A2": 20.0, "B1": 25.0, "B2": 35.0, "C1": 50.0, "C2": 65.0},
    ),
    "R": (
        {"A1": 20.0, "A2": (45.0,)},
        {"A1": 20.0, "A2": 30.0, "B1": (45.0,)},
        {"A1": 20.0, "A2": 20.0, "B1": 30.0, "B2": (50.0,)},
        {"A1": 20.0, "A2": 20.0, "B1": 25.0, "B2": 35.0, "C1": (60.0,)},
        {"A1": 20.0, "A2": 20.0, "B1": 20.0, "B2": 25.0, "C1": 45.0, "C2": 60.0},
    ),
}

# Fire tables as (x, FRL) break points, interpolated as Settings!T30:AA67 does.
# Table 5.7.1 insulation against wall thickness.
FIRE_INSULATION = ((0, 0), (60, 30), (80, 60), (100, 90), (120, 120), (150, 180), (175, 240))
# Table 5.7.2 structural adequacy: (axis distance points, thickness points).
FIRE_ADEQUACY = {
    (0.35, 1): (((0, 0), (10, 60), (20, 90), (25, 120), (40, 180), (55, 240)),
                ((0, 0), (100, 30), (110, 60), (120, 90), (150, 120), (180, 180), (230, 240))),
    (0.35, 2): (((0, 0), (10, 90), (25, 120), (45, 180), (55, 240)),
                ((0, 0), (120, 60), (140, 90), (160, 120), (200, 180), (250, 240))),
    (0.70, 1): (((0, 0), (10, 60), (25, 90), (35, 120), (50, 180), (60, 240)),
                ((0, 0), (120, 30), (130, 60), (140, 90), (160, 120), (210, 180), (270, 240))),
    (0.70, 2): (((0, 0), (10, 60), (25, 90), (35, 120), (55, 180), (60, 240)),
                ((0, 0), (120, 30), (140, 60), (170, 90), (220, 120), (270, 180), (350, 240))),
}

ASSUMPTIONS = [
    "The wall is planar and solid, designed per metre run for axial actions entered per "
    "metre; the in-plane moment and in-plane shear act on the whole wall length Lw.",
    "Actions are unfactored except the earthquake axial action Eu, which is an ultimate "
    "value. The module forms the AS/NZS 1170.0 strength, earthquake and fire combinations.",
    "Self weight, when included, is the mid-height weight 25 kN/m3 x tw x Hw / 2.",
    "The distance between lateral supports L1 in Cl 11.4 is taken as the wall length Lw.",
    "The cover is to the outer bars and the vertical bars are taken as the outer layer, so "
    "the fire axis distance is cover + db.v / 2.",
    "The wall is laterally braced as required by Cl 11.3 when the simplified method is used.",
]

LIMITATIONS = [
    "Transcribed from Structural Toolkit CONCRETE WALLS V5.11. Independent engineering review "
    "has not been completed and the module is not approved for design.",
    "Walls in part tension, walls with out-of-plane moments that must be designed as columns, "
    "and unbraced walls outside the slab provisions are identified but not designed; use "
    "Section 7 (strut and tie) or the concrete column module (Section 10).",
    "When the wall is designed as a slab under Cl 11.1(b)(i), only the axial stress limit is "
    "checked here. Out-of-plane bending, including the eccentricity moment and second-order "
    "effects, must be designed to Section 9 separately.",
    "Openings are compared with the Cl 11.4 limits only; walls with larger openings, and the "
    "portions between openings, must be assessed separately.",
    "Restraint of vertical bars (Cl 11.7.4 and Cl 10.7.4), anchorage, lapping and the "
    "detailing of limited ductile walls beyond the Cl 14.6 ratios are not designed.",
]


# ---------------------------------------------------------------------------
#  Input reading
# ---------------------------------------------------------------------------
def _number(inputs: dict[str, Any], key: str, label: str) -> float:
    raw = inputs.get(key)
    if raw in (None, "") or isinstance(raw, bool):
        raise ValueError(f"{label} ({key}) must be supplied as a finite number")
    try:
        value = float(raw)
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


def _option(inputs: dict[str, Any], key: str, label: str, permitted: tuple[str, ...]) -> str:
    raw = inputs.get(key)
    # Excel compares text case-insensitively; the saved workbook stores 'y' and 'n'.
    value = str(raw).strip().upper() if isinstance(raw, str) else None
    if value not in permitted:
        raise ValueError(f"{label} ({key}) must be one of {', '.join(permitted)}")
    return value


def _yes(inputs: dict[str, Any], key: str, label: str) -> bool:
    return _option(inputs, key, label, ("Y", "N")) == "Y"


def _from_set(inputs: dict[str, Any], key: str, label: str,
              permitted: tuple[float, ...]) -> float:
    value = _number(inputs, key, label)
    if value not in permitted:
        allowed = ", ".join(f"{item:g}" for item in permitted)
        raise ValueError(f"{label} ({key}) must be one of {allowed}, not {value:g}")
    return value


def _count(inputs: dict[str, Any], key: str, label: str, permitted: tuple[int, ...]) -> int:
    value = _number(inputs, key, label)
    if value not in permitted:
        raise ValueError(f"{label} ({key}) must be one of {', '.join(map(str, permitted))}")
    return int(value)


def _ratio(action: float, capacity: float) -> float:
    if capacity <= 0:
        return math.inf if action > 0 else 0.0
    return action / capacity


def excel_round(value: float, digits: int) -> float:
    """Excel ROUND: halves away from zero."""
    factor = 10.0 ** digits
    return math.copysign(math.floor(abs(value) * factor + 0.5) / factor, value)


# ---------------------------------------------------------------------------
#  Tables
# ---------------------------------------------------------------------------
def table_interp(points: tuple[tuple[float, float], ...], value: float) -> float:
    """Bracket and interpolate as the workbook's nested IF pairs (lower x <= value < upper x)."""
    lower = points[0]
    upper = points[0]
    for index, point in enumerate(points):
        if value >= point[0]:
            lower = point
            upper = points[index + 1] if index + 1 < len(points) else point
    if upper[0] == lower[0]:
        return float(lower[1])
    return (value - lower[0]) / (upper[0] - lower[0]) * (upper[1] - lower[1]) + lower[1]


def calc_exposure(formwork: str, fc: float, cover: float) -> str:
    """Transcription of the workbook VBA ``CalcExposure``: the class a cover achieves."""
    if formwork == "S":
        bands = ((25, ((50, "(A2)*"), (20, "A1"))),
                 (32, ((60, "(B1)*"), (30, "A2"), (20, "A1"))),
                 (40, ((65, "(B2)*"), (40, "B1"), (25, "A2"), (20, "A1"))),
                 (50, ((70, "(C1)*"), (45, "B2"), (30, "B1"), (20, "A2/A1"))),
                 (math.inf, ((65, "C2"), (50, "C1"), (35, "B2"), (25, "B1"), (20, "A2/A1"))))
    elif formwork == "R":
        bands = ((25, ((45, "(A2)*"), (20, "A1"))),
                 (32, ((45, "(B1)*"), (30, "A2"), (20, "A1"))),
                 (40, ((50, "(B2)*"), (30, "B1"), (20, "A2/A1"))),
                 (50, ((60, "(C1)*"), (35, "B2"), (25, "B1"), (20, "A2/A1"))),
                 (math.inf, ((60, "C2"), (45, "C1"), (25, "B2"), (20, "B1/A2/A1"))))
    else:
        return "-"
    if fc < 20:
        return "-"
    for limit, steps in bands:
        if fc < limit:
            for minimum, label in steps:
                if cover >= minimum:
                    return label
            return "-"
    return "-"


def required_cover(formwork: str, fc: float, exposure: str) -> tuple[float, bool]:
    """Minimum cover for an exposure class and whether it relies on the Cl 4.3.2 concession."""
    band = sum(1 for limit in FC_BANDS[1:] if fc >= limit)
    entry = EXPOSURE_COVER[formwork][band].get(exposure)
    if entry is None:
        return math.inf, False
    if isinstance(entry, tuple):
        return entry[0], True
    return entry, False


# ---------------------------------------------------------------------------
#  Calculation
# ---------------------------------------------------------------------------
def effective_height(Hw: float, Lw: float, rotation: bool, sides: int) -> dict[str, Any]:
    """Cl 11.4 effective height factors, Design!G98:G108."""
    k1, k2 = 0.75, 1.0
    k3 = max(0.3, 1.0 / (1.0 + (Hw / (3.0 * Lw)) ** 2))
    k4 = 1.0 / (1.0 + (Hw / Lw) ** 2) if Hw <= Lw else Lw / 2.0 / Hw
    one_way = k1 if rotation else k2
    k_calc = one_way if sides == 0 else (min(one_way, k3) if sides == 1 else k4)
    support = ("laterally supported top and bottom" if sides == 0
               else "laterally supported 3 sides" if sides == 1 else "laterally supported 4 sides")
    description = ("Rotationally restrained, " if rotation else "Rotationally unrestrained, ") + support
    return {"k1": k1, "k2": k2, "k3": k3, "k4": k4, "hwe1": k1 * Hw, "hwe2": k2 * Hw,
            "hwe3": k3 * Hw, "hwe4": k4 * Hw, "kCalc": k_calc, "hweCalc": k_calc * Hw,
            "description": description, "fourSidedFormula": "Hw <= L1" if Hw <= Lw else "Hw > L1"}


def _fire(inputs: dict[str, Any], *, tw: float, axis: float, hwe_tw: float,
          Nf: float, fNu: float) -> dict[str, Any]:
    exposed_one = _yes(inputs, "exposed1side", "Fire exposed on one side only")
    lat_one = _yes(inputs, "lat1side", "Lateral support on one side only")
    frl_top = _yes(inputs, "frlTop", "Top lateral support requires an FRL")
    limit_07 = _yes(inputs, "ll07", "Adopt load level 0.7")
    required = _positive(inputs, "frlRequired", "Required fire resistance level")
    ufi_actual = Nf / fNu if fNu else 0.0
    ufi = 0.7 if limit_07 else ufi_actual
    ufir = max(0.0, (ufi - 0.35) / (0.7 - 0.35))
    tables = {}
    for (level, sides), (axis_points, thick_points) in FIRE_ADEQUACY.items():
        tables[f"{int(level * 100)}_{sides}"] = {
            "as": table_interp(axis_points, axis), "t": table_interp(thick_points, tw)}
    blended = {}
    for sides in (1, 2):
        low, high = tables[f"35_{sides}"], tables[f"70_{sides}"]
        by_axis = ufir * (high["as"] - low["as"]) + low["as"]
        by_thickness = ufir * (high["t"] - low["t"]) + low["t"]
        blended[sides] = {"as": by_axis, "t": by_thickness, "frl": min(by_axis, by_thickness)}
    insulation = table_interp(FIRE_INSULATION, tw)
    adequacy_raw = blended[1 if exposed_one else 2]["frl"]
    max_height = 40.0 * tw if frl_top else 50.0 * tw
    too_slender = hwe_tw > max_height / tw
    adequacy = 0.0 if (too_slender or ufi == 0 or ufi > 0.7) else adequacy_raw
    deemed = lat_one and not frl_top
    adequacy_adopted = insulation if deemed else adequacy
    frl = min(adequacy_adopted, insulation)
    if ufi < 0.35:
        note = "Warning - load level below 0.35, 0.35 used"
    elif ufi > 0.7:
        note = "Error - load level above 0.7, no FRL for structural adequacy"
    else:
        note = ""
    return {"exposed1side": exposed_one, "lat1side": lat_one, "frlTop": frl_top,
            "ll07": limit_07, "required": required, "axis": axis, "ufiActual": ufi_actual,
            "ufi": ufi, "ufir": ufir, "tables": tables,
            "blended1": blended[1], "blended2": blended[2], "insulation": insulation,
            "adequacyRaw": adequacy_raw, "adequacy": adequacy, "deemed": deemed,
            "adequacyAdopted": adequacy_adopted, "maxHeight": max_height,
            "maxHeightFactor": 40.0 if frl_top else 50.0, "tooSlender": too_slender,
            "frl": frl, "note": note}


def compute(inputs: dict[str, Any]) -> dict[str, Any]:
    fc = _number(inputs, "fc", "Concrete strength f'c")
    if not FC_MIN <= fc <= FC_MAX:
        raise ValueError(f"Concrete strength f'c (fc) must be between {FC_MIN:g} and "
                         f"{FC_MAX:g} MPa (Cl 1.1.2)")
    tw = _positive(inputs, "tw", "Wall thickness tw")
    Hw = _positive(inputs, "Hw", "Wall height Hw")
    Lw = _positive(inputs, "Lw", "Wall length Lw")
    cover = _non_negative(inputs, "cover", "Cover to outer bars")
    formwork = _option(inputs, "formwork", "Formwork", ("S", "R"))
    design_as_wall = _yes(inputs, "designAsWall", "Design as wall")
    dwall = _yes(inputs, "dwall", "Limited ductile shear wall")
    braced = _yes(inputs, "braced", "Wall braced")
    rotation = _yes(inputs, "rotRestraint", "Rotational restraint top and bottom")
    sides = _count(inputs, "wallIntersect", "Sides with intersecting walls", (0, 1, 2))
    k_mode = _option(inputs, "kMode", "Effective height factor source", ("CALC", "USER"))
    openings = _yes(inputs, "openings", "Openings")
    Aopen = _non_negative(inputs, "Aopen", "Area of openings")
    Sopen = _non_negative(inputs, "Sopen", "Total height of openings")
    Ndl = _non_negative(inputs, "Ndl", "Dead load Ndl")
    Nll = _non_negative(inputs, "Nll", "Live load Nll")
    Neu = _number(inputs, "Neu", "Ultimate earthquake axial load Neu")
    include_sw = _yes(inputs, "includeSW", "Include mid-height self weight")
    load_type = _option(inputs, "loadType", "Load type", tuple(LOAD_TYPES))
    wallecc = _non_negative(inputs, "wallecc", "Load eccentricity")
    Mstar = _non_negative(inputs, "Mstar", "Out-of-plane moment Mo*")
    Mstari = _non_negative(inputs, "Mstari", "In-plane moment Mi*")
    Vstar = _non_negative(inputs, "Vstar", "In-plane shear V*")
    H = _positive(inputs, "H", "Overall wall height H")
    layers = _count(inputs, "layers", "Reinforcement layers", (1, 2))
    klass = _option(inputs, "reoClass", "Reinforcement ductility class", ("N", "L"))
    fsy = _from_set(inputs, "fsy", "Yield strength fsy", YIELD_STRENGTHS)
    dbv = _from_set(inputs, "dbv", "Vertical bar size", BAR_SIZES)
    sv = _positive(inputs, "sv", "Vertical bar spacing")
    dbh = _from_set(inputs, "dbh", "Horizontal bar size", BAR_SIZES)
    sh = _positive(inputs, "sh", "Horizontal bar spacing")
    unrest = _yes(inputs, "unrest", "Unrestrained against horizontal shrinkage")

    if layers == 1 and (tw - dbv) / 2.0 - dbh < 0:
        raise ValueError("A single central layer of bars does not fit within the wall thickness tw")
    if layers == 2 and cover + dbv + dbh >= tw / 2.0:
        raise ValueError("Cover and bar sizes of the two layers exceed half the wall thickness tw")
    if cover >= tw / 2.0:
        raise ValueError("Cover to outer bars (cover) must be less than half the wall thickness")

    warnings: list[str] = []
    if Lw / tw < 4:
        warnings.append("The wall length is less than 4 times its thickness (Design!B12, cited "
                        "by the workbook as Cl 5.6.2); consider design as a column.")

    # Effective height, Cl 11.4.
    heights = effective_height(Hw, Lw, rotation, sides)
    if k_mode == "USER":
        k = _positive(inputs, "k", "Effective height factor k")
    else:
        k = heights["kCalc"]
    k_differs = excel_round(k, 2) != excel_round(heights["kCalc"], 2)
    if k_differs:
        warnings.append(f"The adopted k = {k:.2f} differs from the Cl 11.4 value "
                        f"k = {heights['kCalc']:.2f}.")
        if k < heights["kCalc"]:
            warnings.append("The adopted k is smaller than the Cl 11.4 value and is unconservative.")
    hwe = k * Hw
    hwe_tw = hwe / tw
    wall_area = Hw * Lw / 1e6
    openings_ok = Aopen <= wall_area / 10.0 and Sopen <= Hw / 3.0
    if openings and not openings_ok:
        warnings.append("Openings exceed the Cl 11.4 limits (height > Hw/3 or area > Aw/10); the "
                        "effective height of the portions between openings must be assessed.")
    heights.update({"k": k, "kMode": k_mode, "kDiffers": k_differs, "hwe": hwe, "hweTw": hwe_tw,
                    "rotation": rotation, "sides": sides, "L1": Lw, "returnWall": 0.2 * Hw,
                    "openings": openings, "Aopen": Aopen, "Sopen": Sopen, "wallArea": wall_area,
                    "openingsOk": openings_ok})

    # Actions, AS/NZS 1170.0.
    swtmid = CONCRETE_WEIGHT * tw * Hw / 2e6
    Ndls = Ndl + (swtmid if include_sw else 0.0)
    strength_a, strength_b = 1.35 * Ndls, 1.2 * Ndls + 1.5 * Nll
    Nstard1 = max(strength_a, strength_b)
    if load_type == "O":
        psi_l = _non_negative(inputs, "psiLOther", "Long-term factor for other loads")
        psi_e = _non_negative(inputs, "psiEOther", "Earthquake factor for other loads")
    else:
        psi_l, psi_e = PSI_LONG[load_type], PSI_EARTHQUAKE[load_type]
    Nstard2 = Ndls + Neu + psi_e * Nll
    Nstard = max(Nstard1, Nstard2)
    Nstarfd = Ndls + psi_l * Nll
    minecc = 0.05 * tw
    walle = max(wallecc, minecc)
    Moestar = Nstard * walle / 1000.0
    smid_n = Nstard / (tw / 1000.0) / 1000.0
    smid_in = (6.0 * Mstari / (tw / 1000.0) / (Lw / 1000.0) ** 2) / 1000.0
    smid_max, smid_min = smid_n + smid_in, smid_n - smid_in
    loads = {
        "Ndl": Ndl, "Nll": Nll, "Neu": Neu, "includeSW": include_sw, "swtmid": swtmid,
        "Ndls": Ndls, "strengthCase": "1.35G" if strength_a > strength_b else "1.2G + 1.5Q",
        "Nstard1": Nstard1, "Nstard2": Nstard2, "Nstard": Nstard,
        "governing": "earthquake" if Nstard2 >= Nstard1 else "strength",
        "Nstarfd": Nstarfd, "loadType": load_type, "psiL": psi_l, "psiE": psi_e,
        "wallecc": wallecc, "minecc": minecc, "walle": walle, "slabOver": 0.05 * tw,
        "discontinuousSlab": tw / 6.0, "Moestar": Moestar, "Mstar": Mstar, "Mstari": Mstari,
        "effectiveEcc": Mstar / Nstard * 1000.0 if Nstard else 0.0, "slabLimit": 0.03 * fc,
        "smidN": smid_n, "smidIn": smid_in, "smidMax": smid_max, "smidMin": smid_min,
        "uniform": smid_max == smid_min, "Vstar": Vstar,
    }

    # Design method, Cl 11.1 and Cl 11.2.1 (Settings!X130:X143).
    simple_limit = 20.0 if layers == 1 else 30.0
    if smid_min > 0 and smid_max <= SLAB_STRESS_FACTOR * fc and hwe_tw <= SLAB_SLENDERNESS:
        desmode = 2
    elif smid_min < 0:
        desmode = 0
    elif Mstar > 0:
        desmode = 3
    else:
        desmode = 1
    slabmode = (0 if hwe_tw > simple_limit else 1 if not design_as_wall else 2) if desmode == 2 else None
    desmode2error = desmode == 2 and Mstar != 0 and design_as_wall
    if desmode == 1 or slabmode == 2:
        approach = "wall"
    elif desmode == 2:
        approach = "slab"
    else:
        approach = "tension" if desmode == 0 else "column"
    if approach == "slab":
        applicable, reason = True, "Designed as a slab for axial stress - Cl 11.1(b)(i)"
    elif approach == "wall" and desmode2error:
        applicable, reason = False, ("Out-of-plane moment Mo* > 0 with the slab option: set "
                                     "Design as wall = N to design as a slab - Cl 11.1(b)(i)")
    elif approach == "wall" and not braced:
        applicable, reason = False, "Unbraced wall: design to Cl 11.1(b) as a slab or column"
    elif approach == "wall":
        applicable, reason = True, "Simplified method for braced walls - Cl 11.5"
    elif approach == "tension":
        applicable, reason = False, ("Wall in part tension: " + (
            "H/L <= 2, design as strut and tie - Cl 11.2.1(b)(i)" if Hw / Lw <= 2
            else "H/L > 2, design as column - Cl 11.2.1(b)(ii)"))
    else:
        applicable, reason = False, ("Out-of-plane moment with stress above 0.03 f'c: "
                                     + ("Hwe/tw > 50, cannot be designed as column/slab - Cl 11.1(b)(ii)"
                                        if hwe_tw > SLAB_SLENDERNESS else
                                        "design as column and slab - Cl 11.1(b)(ii)"))
    if approach == "slab":
        warnings.append("Designed as a slab (Cl 11.1(b)(i)): design the out-of-plane moment "
                        f"Moe* + Mo* = {Moestar + Mstar:.1f} kNm/m, plus second-order effects, "
                        "to Section 9. That design is not part of this module.")
    method = {"desmode": desmode, "text": METHOD_TEXT[desmode], "approach": approach,
              "slabmode": slabmode, "desmode2error": desmode2error, "applicable": applicable,
              "reason": reason, "braced": braced, "designAsWall": design_as_wall,
              "simpleLimit": simple_limit}

    # Design axial strength, Cl 11.5.
    ae = hwe ** 2 / (2500.0 * tw)
    Nus = max(0.0, (tw - 1.2 * walle - 2.0 * ae) * 0.6 * fc)
    fNuMax1 = SINGLE_LAYER_STRESS * tw
    within_slenderness = hwe_tw <= simple_limit
    if within_slenderness:
        fNus = min(fNuMax1, PHI_WALL * Nus) if layers == 1 else PHI_WALL * Nus
    else:
        fNus = 0.0
    fNuo = (SLAB_STRESS_FACTOR * fc - smid_in) * tw if desmode == 2 else 0.0
    fNu = fNuo if approach == "slab" else fNus
    # The slab capacity already deducts the in-plane stress; the wall check adds it to N*.
    demand = Nstard if approach == "slab" else Nstard + smid_in * tw
    axial = {
        "phi": PHI_WALL, "ae": ae, "Nus": Nus, "fNuMax1": fNuMax1, "fNus": fNus, "fNuo": fNuo,
        "fNu": fNu, "demand": demand, "withinSlenderness": within_slenderness,
        "withinSimplifiedLimits": (smid_max <= SINGLE_LAYER_STRESS and hwe_tw <= 20.0)
        if layers == 1 else hwe_tw <= 30.0,
        "exceedsSingleStress": layers == 1 and smid_max > SINGLE_LAYER_STRESS,
        "slenderLimit": SLAB_SLENDERNESS if approach == "slab" else simple_limit,
        "maxHeight": math.sqrt((tw - 1.2 * walle) * 2500.0 * tw / 2.0) if tw - 1.2 * walle >= 0 else 0.0,
        "maxEcc": max((2.0 * ae - tw) / -1.2, 0.0),
        "phiT": 0.65 if klass == "L" else 0.85,
    }
    Ast = 1000.0 / sv * math.pi * dbv ** 2 / 4.0
    Astc = 1000.0 / sh * math.pi * dbh ** 2 / 4.0
    axial["fNuot"] = layers * axial["phiT"] * Ast * fsy / 1000.0
    axial["halfCapacity"] = _ratio(demand, 0.5 * fNu)

    # Reinforcement, Cl 11.7.
    pwv = Ast / 1000.0 / tw * layers
    stress_limit = min(2.0, SLAB_STRESS_FACTOR * fc)
    pwmin = 0.0025 if dwall else (0.0015 if smid_max <= stress_limit else 0.0025)
    pwh = Astc / 1000.0 / tw * layers
    pwminh = (0.0025 if dwall else
              (0.0 if Lw <= 2500 else 0.0015) if (0.75 <= k <= 1.0 and unrest) else 0.0025)
    if pwminh == 0:
        crack_text = "Not required"
    elif pwh < pwminh:
        crack_text = "Horizontal reinforcement less than minimum"
    else:
        crack_text = ("Minor A1 and A2" if pwh < 0.0035 else
                      "Moderate/hidden A1 and A2" if pwh < 0.006 else "Strong B1 to C2")
    max_spacing = min(MAX_SPACING, 2.5 * tw)
    reinforcement = {
        "layers": layers, "class": klass, "fsy": fsy, "fsyh": min(fsy, 500.0),
        "dbv": dbv, "sv": sv, "dbh": dbh, "sh": sh, "cover": cover, "unrest": unrest,
        "Ast": Ast, "Astc": Astc, "pwv": pwv, "pwh": pwh, "stressLimit": stress_limit,
        "pwmin": pwmin, "AstvMin": pwmin * 1000.0 * tw, "pwminh": pwminh,
        "AsthMin": pwminh * 1000.0 * tw, "pwmax": 16.0 / fsy if dwall else 0.0,
        "AstvMax": (16.0 / fsy if dwall else 0.0) * 1000.0 * tw,
        "gapV": max(0.0, sv - dbv), "gapH": max(0.0, sh - dbh), "maxSpacing": max_spacing,
        "crackText": crack_text, "axis": cover + dbv / 2.0,
        "coverV": (tw - dbv) / 2.0 if layers == 1 else None,
        "coverH": (tw - dbv) / 2.0 - dbh if layers == 1 else None,
        "exposure": calc_exposure(formwork, fc, cover), "formwork": formwork,
        "crackTable": [{"key": key, "label": label, "p": ratio, "As": ratio * 1000.0 * tw}
                       for key, (ratio, label) in CRACK_CONTROL.items()],
    }
    if layers == 1 and reinforcement["coverH"] is not None and cover > reinforcement["coverH"] + 1e-9:
        warnings.append(f"The entered cover ({cover:g} mm) exceeds the geometric cover to a single "
                        f"central layer ({reinforcement['coverH']:g} mm).")
    if layers == 2 and not dwall and hwe_tw <= 20 and tw <= 200 and smid_max <= SINGLE_LAYER_STRESS:
        warnings.append("Reinforcement may be provided as a single central layer "
                        "(tw <= 200 mm and Hwe/tw <= 20) - Cl 11.7.3(a) and (d).")

    single_rules: list[tuple[str, float, str]] = []
    if layers == 1:
        if desmode != 2:
            single_rules += [("tw <= 200 mm", tw / 200.0, "Cl 11.7.3(a)"),
                             ("Hwe/tw <= 20", hwe_tw / 20.0, "Cl 11.7.3(d)")]
        single_rules += [("Hw <= 20 m", Hw / 20000.0, "Cl 11.7.3(d)"),
                         ("stress \u03c3.max <= 3 MPa", smid_max / SINGLE_LAYER_STRESS, "Cl 11.5.2(a)")]
        if dwall:
            single_rules.append(("Not a limited ductile wall", math.inf, "Cl 14.6.7"))
    reinforcement["singleRules"] = [{"rule": rule, "ratio": ratio, "clause": clause}
                                    for rule, ratio, clause in single_rules]

    # In-plane shear, Cl 11.6.
    root = math.sqrt(fc)
    area = 0.8 * Lw * tw / 1000.0
    ratio_h = H / Lw
    Vumax = 0.2 * fc * area
    Vucmin = 0.17 * root * area
    Vuca = (0.66 * root - 0.21 * ratio_h * root) * area
    Vucb = (0.05 * root + 0.1 * root / (ratio_h - 1.0)) * area if ratio_h > 1.0 else None
    Vuc = max(Vucmin, Vuca) if ratio_h <= 1.0 else max(Vucmin, min(Vuca, Vucb))
    pw = min(pwv, pwh) if ratio_h <= 1.0 else pwh
    Vus = pw * min(fsy, 500.0) * area
    Vu = min(Vuc + Vus, Vumax)
    shear = {"H": H, "ratio": ratio_h, "phi": PHI_SHEAR, "Vumax": Vumax, "fVumax": PHI_SHEAR * Vumax,
             "Vucmin": Vucmin, "fVucmin": PHI_SHEAR * Vucmin, "Vuca": Vuca, "Vucb": Vucb,
             "Vuc": Vuc, "fVuc": PHI_SHEAR * Vuc, "pw": pw, "Vus": Vus, "fVus": PHI_SHEAR * Vus,
             "Vu": Vu, "fVu": PHI_SHEAR * Vu, "Vstar": Vstar,
             "governs": "Vu.max" if Vu == Vumax else "Vuc + Vus"}

    util = {
        "designMethod": 0.0 if applicable else math.inf,
        "axial": _ratio(demand, fNu),
        "slenderness": hwe_tw / axial["slenderLimit"],
        "verticalSteel": _ratio(pwmin, pwv),
        "horizontalSteel": _ratio(pwminh, pwh),
        "verticalSpacing": sv / max_spacing,
        "horizontalSpacing": sh / max_spacing if pwminh > 0 else 0.0,
        "barGap": max(_ratio(3.0 * dbv, reinforcement["gapV"]), _ratio(3.0 * dbh, reinforcement["gapH"])),
        "inPlaneShear": _ratio(Vstar, shear["fVu"]),
    }
    if single_rules:
        util["singleLayer"] = max(ratio for _, ratio, _ in single_rules)
    ductile = None
    if dwall:
        ductile = {"pwmax": reinforcement["pwmax"], "classOk": klass == "N"}
        util["ductileWall"] = max(_ratio(pwv, reinforcement["pwmax"]),
                                  0.0 if klass == "N" else math.inf)

    enabled = inputs.get("checks") if isinstance(inputs.get("checks"), dict) else {}
    fire = None
    if enabled.get("fire"):
        fire = _fire(inputs, tw=tw, axis=reinforcement["axis"], hwe_tw=hwe_tw, Nf=Nstarfd, fNu=fNu)
        util["fireResistance"] = _ratio(fire["required"], fire["frl"])
        if fire["note"]:
            warnings.append(f"Fire: {fire['note']}.")
    crack = None
    if enabled.get("crackControl"):
        degree = _option(inputs, "crackDegree", "Degree of crack control", tuple(CRACK_CONTROL))
        ratio, label = CRACK_CONTROL[degree]
        crack = {"degree": degree, "label": label, "p": ratio, "As": ratio * 1000.0 * tw,
                 "applies": not unrest}
        if unrest:
            warnings.append("Crack control: the wall is unrestrained against horizontal shrinkage, "
                            "so the Cl 11.7.2 ratios are not applied.")
        else:
            util["crackControl"] = _ratio(ratio, pwh)
    durability = None
    if enabled.get("durability"):
        exposure = _option(inputs, "exposureClass", "Exposure classification", EXPOSURE_CLASSES)
        cmin, concession = required_cover(formwork, fc, exposure)
        durability = {"exposure": exposure, "cmin": cmin, "concession": concession,
                      "cover": cover}
        if concession:
            warnings.append(f"Cover for {exposure} at f'c = {fc:g} MPa relies on the bracketed "
                            "value and the Cl 4.3.2 strength concession.")
        if not math.isfinite(cmin):
            warnings.append(f"f'c = {fc:g} MPa is below the minimum strength for exposure "
                            f"{exposure} (Table 4.10.3.2/3).")
        util["cover"] = _ratio(cmin, cover)

    if approach == "wall" and applicable and axial["halfCapacity"] > 1.0:
        warnings.append("N* > 0.5 phiNu: if the wall is designed as a column, restrain the "
                        "vertical bars to Cl 10.7.4 (Cl 11.7.4).")
    if not math.isfinite(util["axial"]):
        warnings.append("The design axial strength is zero: the wall is too slender or the "
                        "eccentricity too large for the method adopted.")
    finite = [value for value in util.values() if math.isfinite(value)]
    worst = max(finite) if finite else 0.0
    return {
        "module": MODULE_ID, "version": VERSION,
        "inputs": {"fc": fc, "tw": tw, "Hw": Hw, "Lw": Lw, "cover": cover, "formwork": formwork,
                   "layers": layers, "class": klass, "fsy": fsy, "dwall": dwall},
        "effectiveHeight": heights, "loads": loads, "method": method, "axial": axial,
        "reinforcement": reinforcement, "shear": shear, "ductile": ductile,
        "fire": fire, "crackControl": crack, "durability": durability,
        "util": util, "worstUtil": worst, "checks": {key: True for key in util},
        "warnings": warnings, "assumptions": list(ASSUMPTIONS),
        "limitations": list(LIMITATIONS),
    }
