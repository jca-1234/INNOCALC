"""Concrete industrial pavement engine - Chandler (C&CA TR550) and CCAA T48 methods.

Working units follow the workbook: lengths in mm, stresses in MPa, subgrade modulus
in kPa/mm, area loads in kPa, post loads in kN and wheel loads in tonnes.

The design basis is a transcription of the retained Structural Toolkit workbook
``Pavements_Industrial_507.xls`` (INDUSTRIAL FLOOR SLABS V5.07, sheets ``Design``,
``Racking``, ``Wheels``, ``Custom``, ``Uniform`` and ``Reinft`` with the VBA module
``Module1``).  The ARC Slabex fibre option and the ARC adjacent-load tables are
hidden ``Settings`` switches in the workbook and are not transcribed.
"""

from __future__ import annotations

import math
from typing import Any

from .version import VERSION

MODULE_ID = "concrete-industrial-pavement"

FC_MIN, FC_MAX = 20.0, 120.0  # AS 3600 Cl 1.1.2, Design!E16
CCA_FC_MIN, CCA_FC_MAX = 25.0, 50.0  # Design!G25
PHI_BEARING = 0.6  # AS 3600 Table 2.2.2, Racking!F18
PHI_SHEAR = 0.7  # AS 3600 Table 2.2.2, Racking!F27
LIVE_LOAD_FACTOR = 1.5  # Racking!F15
TRANSFER_CORNER, TRANSFER_EDGE = 0.7, 0.85  # Chandler, Design!E33:E34
ABRASION_MIN_FC = 25.0  # Settings!N64:N65, "Unsuitable" / "Error" below this grade

POSITIONS = {"I": "Internal", "E": "Edge", "C": "Corner"}
DIRECTIONS = ("T", "R", "C")
OPPOSITE = {"C": "C", "R": "T", "T": "R"}
FLEXURAL_METHODS = {"C": "C&CA 0.438 f'c^(2/3)", "T": "T48 0.7 sqrt(f'c)",
                    "A": "AS 3600 0.6 sqrt(f'c)", "O": "Other, manual value"}
REINFORCEMENT_METHODS = {"A": "AS 3600 - Unrestrained shrinkage",
                         "N": "T48 minimum of 0.14%", "T": "T48 Appendix F subgrade drag",
                         "R": "Austroads subgrade drag", "M": "Maximum of all methods"}
OVERLAP_LEVELS = {"T": "at top of slab", "M": "at mid-depth of slab", "B": "at bottom of slab"}
BOUND_THICKNESSES = (0.0, 100.0, 125.0, 150.0)
YIELD_STRENGTHS = (500.0, 400.0)
WHEEL_COUNTS = (2.0, 4.0)

# Racking!B38:H49: point, dirX, dirY; distances follow the standard Dexian layout.
RACK_POINTS = (("A", "C", "C"), ("B", "C", "C"), ("C", "T", "R"), ("D", "C", "C"),
               ("E", "R", "T"), ("F", "R", "T"), ("G", "C", "C"), ("H", "R", "T"),
               ("I", "C", "C"), ("J", "C", "C"), ("K", "T", "R"), ("L", "C", "C"))
CUSTOM_POINTS = ("A", "B", "C", "D", "E", "F", "H", "I", "J", "K", "L")
CUSTOM_DEFAULTS = {"A": (2863.0, "C"), "B": (2619.0, "C"), "C": (2591.0, "T"),
                   "D": (2723.0, "C"), "E": (1219.0, "R"), "F": (381.0, "R"),
                   "H": (838.0, "R"), "I": (2863.0, "C"), "J": (2619.0, "C"),
                   "K": (2591.0, "T"), "L": (2723.0, "C")}
# Wheels!B40:H47 dual axle directions.
DUAL_DIRECTIONS = {"A": ("R", "T"), "B": ("R", "T"), "C": ("R", "T"), "D": ("R", "T"),
                   "E": ("C", "C"), "F": ("T", "R"), "G": ("C", "C"), "H": ("C", "C")}

# Chandler Fig 3 bending moment coefficient curves (kNm/m per kPa) against aisle width
# in metres, one per radius of relative stiffness (VBA ``Moment``).
MOMENT_CURVES = {
    450: (0.0002, -0.0059, 0.0483, -0.1528, 0.196),
    570: (-0.0014, 0.0171, -0.0688, 0.0815, 0.0799),
    675: (-0.0025, 0.0349, -0.1695, 0.3031, -0.0308),
    800: (-0.00009, 0.0062, -0.0571, 0.1386, 0.1043),
    950: (0.0037, -0.0381, 0.114, -0.0962, 0.2747),
    1200: (0.0009, -0.0101, 0.0002, 0.1571, 0.194),
    1425: (0.0151, -0.2003, 0.8622, -1.3319, 1.1606),
    1580: (0.016, -0.1868, 0.7256, -0.9785, 0.9735),
    1800: (0.0084, -0.1048, 0.3962, -0.3478, 0.6653),
}
AISLE_MIN, AISLE_MAX = 1500.0, 4500.0  # Racking!E61 clamp, "Valid between 1500 and 4500mm"

# VBA ShrinkageSteel: Grade 500 mesh or bar selection by area (mm2/m).
SHRINKAGE_STEEL = ((63, "SL42"), (89, "SL52"), (141, "SL62"), (179, "SL72"), (227, "SL82"),
                   (290, "SL92"), (354, "SL102"), (454, "SL81"), (565, "2/SL92 or N12-200"),
                   (670, "N16-300 cts"), (804, "N16-250 cts"))

ASSUMPTIONS = [
    "The slab is unreinforced for flexure and rests on a subgrade idealised as a dense liquid "
    "(Winkler) foundation of modulus K; the radius of relative stiffness follows Westergaard.",
    "Point loads act on circular contact areas of equal area; the Westergaard equivalent "
    "radius b replaces the contact radius when it is less than 1.72 h.",
    "Rack post, wheel and uniform loads are considered in isolation and are not combined, "
    "as in the workbook.",
    "Rack post loads are rack levels x pallet mass x 10 N/kg; the post bearing and punching "
    "actions are 1.5 times the working post load.",
    "Flexural stresses are working stresses compared with the 90-day characteristic flexural "
    "tensile strength after division by the T48 material (k1) and repetition (k2) factors.",
    "Adjacent-load stress increases are read from curve fits of the digitised Chandler "
    "stress-increase charts as a proportion of the radius of relative stiffness.",
    "Shrinkage reinforcement is reported as a requirement only; no provided reinforcement is "
    "checked.",
]

LIMITATIONS = [
    "Transcribed from Structural Toolkit INDUSTRIAL FLOOR SLABS V5.07. Independent engineering "
    "review has not been completed and the module is not approved for design.",
    "The Chandler stress-increase and aisle-moment charts are digitised curve fits with no "
    "retained source scans; their accuracy has not been verified against TR550.",
    "Joint design (dowels, load transfer detailing), curling and warping stresses, "
    "settlement, fatigue by Miner's rule, fibre reinforced concrete and the ARC adjacent-load "
    "tables are not covered.",
    "The subgrade CBR, K and bound subbase conversions are approximate curve fits; "
    "geotechnical advice is required. K is taken as entered.",
    "Edge and corner positions use the standard internal rack layout unless the custom "
    "layout is used; discontinuity of the slab at the load is not modelled beyond the "
    "Chandler edge and corner formulae.",
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


def _factor(inputs: dict[str, Any], key: str, label: str) -> float:
    value = _positive(inputs, key, label)
    if value > 1.0:
        raise ValueError(f"{label} ({key}) must not exceed 1.0")
    return value


def _option(inputs: dict[str, Any], key: str, label: str, permitted: tuple[str, ...]) -> str:
    raw = inputs.get(key)
    # Excel compares text case-insensitively; the saved workbook stores 'y' for T48 2009.
    value = str(raw).strip().upper() if isinstance(raw, str) else None
    if value not in permitted:
        raise ValueError(f"{label} ({key}) must be one of {', '.join(permitted)}")
    return value


def _from_set(inputs: dict[str, Any], key: str, label: str,
              permitted: tuple[float, ...]) -> float:
    value = _number(inputs, key, label)
    if value not in permitted:
        allowed = ", ".join(f"{item:g}" for item in permitted)
        raise ValueError(f"{label} ({key}) must be one of {allowed}, not {value:g}")
    return value


def _ratio(action: float, capacity: float) -> float:
    if capacity <= 0:
        return math.inf if action > 0 else 0.0
    return action / capacity


# ---------------------------------------------------------------------------
#  VBA Module1 transcriptions
# ---------------------------------------------------------------------------
def stress_ratio(repetitions: float) -> float:
    """T48 Table 1.17 load repetition factor k2 (VBA ``StressRatio``)."""
    if repetitions < 50:
        return 0.84
    if repetitions > 400000:
        return 0.5
    return (11.791 - math.log10(repetitions)) / 12.136


def msr(cbr_value: float) -> float:
    """Chandler Fig 1 curve fit, CBR (%) to modulus of subgrade reaction (kPa/mm)."""
    return 23.3722211 * math.log(cbr_value) + 0.7046933


def cbr(msr_value: float) -> float:
    """Inverse of :func:`msr`."""
    return math.exp((msr_value - 0.7046933) / 23.3722211)


def trans(x: float) -> float:
    """Chandler internal stress increase (%), tangential direction (VBA ``Trans``)."""
    if x == 0.0 or x > 3.0:
        return 0.0
    value = (-0.2646 * x ** 6 + 1.4297 * x ** 5 + 2.0547 * x ** 4 - 30.671 * x ** 3
             + 87.821 * x ** 2 - 117.94 * x + 70.664)
    return max(0.0, value)


def radial(x: float, include_negative: bool = False) -> float:
    """Chandler internal stress increase (%), radial direction (VBA ``Radial``)."""
    if x == 0.0 or x > 4.0:
        return 0.0
    value = (0.1842 * x ** 6 - 2.9734 * x ** 5 + 19.322 * x ** 4 - 65.597 * x ** 3
             + 127.17 * x ** 2 - 138.57 * x + 60.424)
    return value if include_negative else max(0.0, value)


def edge_increase(x: float, include_negative: bool = False) -> float:
    """Chandler edge stress increase (%), VBA ``TransEdge`` and ``RadialEdge`` (identical)."""
    if x == 0.0 or x > 4.0:
        return 0.0
    value = (0.0966 * x ** 6 - 1.6395 * x ** 5 + 11.454 * x ** 4 - 43.104 * x ** 3
             + 94.771 * x ** 2 - 113.38 * x + 44.861)
    return value if include_negative else max(0.0, value)


def stress_increase(x: float, direction: str, internal: bool, include_negative: bool) -> float:
    """One Racking!F38-style cell: T, R or the critical (C) of both."""
    if internal:
        tangential, radial_value = trans(x), radial(x, include_negative)
    else:
        tangential = radial_value = edge_increase(x, include_negative)
    if direction == "T":
        return tangential
    if direction == "R":
        return radial_value
    return max(tangential, radial_value)


def _vba_integer(value: float) -> int:
    # VBA coerces a Double to an Integer argument with banker's rounding, as round() does.
    return int(round(value))


def moment_curve(stiffness: int, x: float) -> float:
    a4, a3, a2, a1, a0 = MOMENT_CURVES[stiffness]
    return a4 * x ** 4 + a3 * x ** 3 + a2 * x ** 2 + a1 * x + a0


def chandler_moment(aisle: float, stiffness: float) -> dict[str, Any]:
    """Chandler Fig 3 aisle bending moment per kPa (VBA ``Moment``), with two corrections.

    The aisle width is clamped to 1500 to 4500 mm and both arguments are rounded to
    integers as the VBA Integer parameters do.  Between the 570 and 675 mm curves the
    VBA extrapolates from the 450 and 570 curves; this interpolates 570 to 675.  Below
    450 mm the VBA returns zero; this uses the 450 curve, which is conservative because
    the moment increases with the stiffness radius.  Above 1800 mm the VBA scales the
    1800 curve by l / 1800 and that is reproduced.
    """
    clamped = max(AISLE_MIN, min(aisle, AISLE_MAX))
    isle, l_int = _vba_integer(clamped), _vba_integer(stiffness)
    x = isle / 1000.0
    radii = sorted(MOMENT_CURVES)
    note = ""
    if l_int < radii[0]:
        value = moment_curve(radii[0], x)
        note = "below450"
    elif l_int >= radii[-1]:
        value = l_int / radii[-1] * moment_curve(radii[-1], x)
        note = "above1800" if l_int > radii[-1] else ""
    else:
        for low, high in zip(radii, radii[1:]):
            if low <= l_int <= high:
                y_low, y_high = moment_curve(low, x), moment_curve(high, x)
                value = y_low + (l_int - low) / (high - low) * (y_high - y_low)
                break
        if 570 < l_int < 675:
            note = "corrected570"
    return {"value": value, "aisle": isle, "aisleInput": aisle, "l": l_int, "x": x,
            "note": note, "clamped": clamped != aisle}


def shrinkage_steel(area: float) -> str:
    for limit, name in SHRINKAGE_STEEL:
        if area <= limit:
            return name
    return f"{area:.0f} mm2"


# ---------------------------------------------------------------------------
#  Chandler stress formulae (MPa per tonne of load)
# ---------------------------------------------------------------------------
def equivalent_radius(radius: float, h: float) -> float:
    """Westergaard equivalent radius b of the loaded area."""
    if radius >= 1.72 * h:
        return radius
    return math.sqrt(1.6 * radius ** 2 + h ** 2) - 0.675 * h


def internal_stress(h: float, u: float, l: float, b: float) -> float:
    """Westergaard interior stress, Racking!D32."""
    return 2.7 * (1 + u) * 1 / h ** 2 * (4 * math.log10(l / b) + 1.069) * 1000


def edge_stress(h: float, u: float, l: float, b: float) -> float:
    """Kelley edge stress, Racking!D33."""
    return 5.19 * (1 + 0.54 * u) * 1 / h ** 2 * (4 * math.log10(l / b) + math.log10(b / 25.4)) * 1000


def corner_stress(h: float, l: float, radius: float) -> float:
    """Pickett corner stress, Racking!D34 (uses the contact radius, not b)."""
    return 41.2 * 1 / h ** 2 * (1 - ((radius / l) ** 0.5) / (0.925 + 0.22 * (radius / l))) * 1000


def _point_stresses(h: float, u: float, l: float, b: float, radius: float) -> tuple[float, float, float]:
    return internal_stress(h, u, l, b), edge_stress(h, u, l, b), corner_stress(h, l, radius)


def _increase_rows(points: list[tuple[str, float, float, str, str, float]], l: float,
                   internal: bool, include_negative: bool) -> list[dict[str, Any]]:
    """Adjacent-load rows (point, raw distance, reduced distance, dirX, dirY, load share)."""
    rows = []
    for point, raw, reduced, dir_x, dir_y, share in points:
        if raw > 0 and reduced < 0:
            raise ValueError(f"Point {point}: the distance reduced by the radius of the loaded "
                             "area is negative")
        x = 0.0 if raw == 0 else reduced / l
        rows.append({"point": point, "dist": reduced, "x": x, "dirX": dir_x, "dirY": dir_y,
                     "share": share,
                     "pctX": stress_increase(x, dir_x, internal, include_negative) * share,
                     "pctY": stress_increase(x, dir_y, internal, include_negative) * share})
    return rows


def _totals(si: float, se: float, sc: float, rows: list[dict[str, Any]], transfer: bool,
            where: str) -> dict[str, float]:
    sx = sum(item["pctX"] for item in rows)
    sy = sum(item["pctY"] for item in rows)
    factor = 1 + max(sx, sy) / 100
    sit = si * factor
    set_ = (TRANSFER_EDGE if transfer else 1) * se * factor
    sct = (TRANSFER_CORNER if transfer else 1) * sc * factor
    st = sct if where == "C" else set_ if where == "E" else sit
    return {"sx": sx, "sy": sy, "sit": sit, "set": set_, "sct": sct, "st": st}


# ---------------------------------------------------------------------------
#  Calculation
# ---------------------------------------------------------------------------
def _material(inputs: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    fc = _number(inputs, "fc", "Concrete strength f'c")
    if not FC_MIN <= fc <= FC_MAX:
        raise ValueError(f"Concrete strength f'c (fc) must be between {FC_MIN:g} and "
                         f"{FC_MAX:g} MPa (AS 3600 Cl 1.1.2)")
    h = _positive(inputs, "h", "Slab thickness h")
    density = _positive(inputs, "density", "Concrete density")
    use_fcmi = _option(inputs, "useFcmi", "Use fcmi for Ec", ("Y", "N"))
    fmethod = _option(inputs, "fmethod", "Method for flexural strength", tuple(FLEXURAL_METHODS))
    fcfo = _positive(inputs, "fcfo", "Other manual flexural strength")
    u = _number(inputs, "u", "Poisson's ratio")
    if not 0.0 <= u < 0.5:
        raise ValueError("Poisson's ratio (u) must be at least 0 and less than 0.5")
    K = _positive(inputs, "K", "Modulus of subgrade reaction K")

    fcmi = -0.0015 * fc ** 2 + 1.1392 * fc + 0.3481 if use_fcmi == "Y" else fc
    E = (density ** 1.5 * 0.043 * math.sqrt(fcmi) if fcmi <= 40
         else density ** 1.5 * (0.024 * math.sqrt(fcmi) + 0.12))
    fcf_cca, fcf_t48 = 0.438 * fc ** (2 / 3), 0.7 * math.sqrt(1.1 * fc)
    fcf_as = 0.6 * math.sqrt(fc)
    if fmethod == "C" and not CCA_FC_MIN <= fc <= CCA_FC_MAX:
        raise ValueError("The C&CA flexural strength (fmethod = C) is valid only for "
                         "25 <= f'c <= 50 MPa")
    if fmethod == "O" and (fcfo < 0.8 * fcf_cca or fcfo > 1.1 * fcf_cca):
        warnings.append("The manual flexural strength varies from the C&CA method by more than "
                        "-20 % / +10 %.")
    fcf = {"C": fcf_cca, "T": 0.7 * math.sqrt(fc), "A": fcf_as, "O": fcfo}[fmethod]
    Z = h * h * 1000 / 6
    l = (E * h ** 3 * 1000 / (12 * (1 - u ** 2) * K)) ** 0.25
    if fc >= 32:
        exposure = "Exposure B1, 7 days curing under ambient conditions, 40mm cover"
    elif fc >= 25:
        exposure = "Exposure A2, 3 days curing under ambient conditions, 30mm cover"
    else:
        exposure = "Error"
    if fc > 40:
        abrasion, abrasion2 = "Steel-wheeled traffic (To be assessed)", ""
    elif fc == 40:
        abrasion, abrasion2 = "Non-pneunmatic-tyred traffic", "Steel-wheeled traffic (To be assessed)"
    elif fc >= 32:
        abrasion, abrasion2 = "Medium or heavy pneumatic-tyred traffic (>3 t gross mass)", ""
    elif fc >= 25:
        abrasion = "Light pneumatic-tyred traffic (≤3 t gross mass)"
        abrasion2 = ("Commerical and industrial floors subject only to pedestrian and/or light "
                     "trolley traffic")
    else:
        abrasion, abrasion2 = "Unsuitable", ""
    return {"fc": fc, "h": h, "density": density, "useFcmi": use_fcmi == "Y", "fcmi": fcmi,
            "E": E, "fcfCCA": fcf_cca, "fcfT48": fcf_t48, "fcfAS": fcf_as, "fcfo": fcfo,
            "fmethod": fmethod, "fmethodLabel": FLEXURAL_METHODS[fmethod], "fcf": fcf,
            "Z": Z, "u": u, "K": K, "l": l, "exposure": exposure + " - Table 1.7",
            "abrasion": abrasion + " - Table 1.6", "abrasion2": abrasion2}


def _subgrade(inputs: dict[str, Any], K: float) -> dict[str, Any]:
    cbr_value = _positive(inputs, "CBRValue", "California bearing ratio")
    msr_value = _positive(inputs, "MSRValue", "Modulus of subgrade reaction for conversion")
    bt = _from_set(inputs, "bt", "Bound sub-base thickness", BOUND_THICKNESSES)
    t48_2009 = _option(inputs, "T48_2009", "Use T48 2009", ("Y", "N"))
    cbr_k = cbr(K)
    x = min(12.0, cbr_value)
    bound2009 = {150.0: -0.0958 * x ** 2 + 5.0867 * x + 6.5887,
                 125.0: -0.0374 * x ** 2 + 3.5531 * x + 6.1496,
                 100.0: -0.1042 * x ** 2 + 3.6643 * x + 3.3307}.get(bt, 0.0)
    bound1999 = {150.0: -2.3366 * x ** 2 + 21.469 * x - 17.971,
                 125.0: -0.7046 * x ** 2 + 10.831 * x - 8.5115,
                 100.0: -0.2081 * x ** 2 + 5.6496 * x - 4.1838}.get(bt, 0.0)
    cbr_b = None if bt == 0 else min(35.0, bound2009 if t48_2009 == "Y" else bound1999)
    return {
        "K": K, "CBRofK": cbr_k,
        "nominalSubbase": 100.0 if cbr_k >= 10 else 200.0 if cbr_k <= 2 else 150.0,
        "subbaseRef": "T48-2009 Table 1.5" if t48_2009 == "Y" else "T48-1999 Table 1.13",
        "CBRValue": cbr_value, "MSRofCBR": msr(cbr_value), "MSRValue": msr_value,
        "CBRofMSR": cbr(msr_value), "bt": bt, "CBRb": x, "bound2009": min(35.0, bound2009),
        "bound1999": min(35.0, bound1999), "CBRbValue": cbr_b,
        "Kbound": None if cbr_b is None else msr(cbr_b),
        "boundRef": "T48-2009 Figure 1.26" if t48_2009 == "Y" else "T48-1999 Figure 1.17",
        "t48_2009": t48_2009 == "Y",
    }


def _uniform(inputs: dict[str, Any], mat: dict[str, Any]) -> dict[str, Any]:
    pf_no = _non_negative(inputs, "PFno", "Number of pallets on the floor")
    pf_wt = _non_negative(inputs, "PFwt", "Floor pallet weight")
    pf_l = _positive(inputs, "PFl", "Floor pallet side length")
    pf_e = _positive(inputs, "PFe", "Floor pallet end length")
    aisle = _positive(inputs, "IsleUDL", "Aisle width for uniform loads")
    uk1 = _factor(inputs, "Uk1", "Material factor for UDL Uk1")
    uk2 = _factor(inputs, "Uk2", "Repetition factor for UDL Uk2")
    use_fos = _option(inputs, "useFOS", "Use factor of safety", ("Y", "N"))
    fos = _positive(inputs, "fos", "Factor of safety")
    h, K, E, fcf = mat["h"], mat["K"], mat["E"], mat["fcf"]
    udl = pf_wt / pf_l / pf_e * 10 * 1000 * pf_no
    reduction = 1 / fos if use_fos == "Y" else uk1 * uk2
    fca = fcf * reduction
    udl_all = 0.33 * fca * math.sqrt(h * K)
    lam = (3 * K / (E * 1000 * h ** 3)) ** 0.25
    udla = math.pi / 4 / lam
    root = math.sqrt(E * h ** 3 / 3 / K)
    mc_max = 5.313 * udl * root / 1000000
    patc1 = 6 * mc_max * 1000 / h ** 2
    a_act, b_act = aisle / 2, 5 * (aisle / 2)
    mc = (udl / (2 * lam ** 2) * (math.exp(-lam * a_act) * math.sin(lam * a_act)
                                  - math.exp(-lam * b_act) * math.sin(lam * b_act)) / 1000000)
    su1, su2 = 6 * mc * 1000 / h ** 2, 0.031387 * udl / h ** 2 * root
    pata1 = max(su1, su2)
    return {"PFno": pf_no, "PFwt": pf_wt, "UDL": udl, "aisle": aisle, "Uk1": uk1, "Uk2": uk2,
            "useFOS": use_fos == "Y", "fos": fos, "reduction": reduction, "fca": fca,
            "UDLall": udl_all, "lam": lam, "udla": udla, "udlb": 5 * udla,
            "criticalAisle": 2 * udla, "Mcmax": mc_max, "patc1": patc1,
            "patc": patc1 / uk1 / uk2, "udlai": a_act, "udlbi": b_act, "Mc": mc,
            "su1": su1, "su2": su2, "pata1": pata1, "pata": pata1 / uk1 / uk2}


def _racking(inputs: dict[str, Any], mat: dict[str, Any], where: str, transfer: bool,
             consider: bool, include_negative: bool, uniform: dict[str, Any],
             warnings: list[str]) -> dict[str, Any]:
    pr_no = _non_negative(inputs, "PRNo", "Number of above ground rack levels")
    pr_wt = _non_negative(inputs, "PRwt", "Rack pallet weight")
    pg_wt = _non_negative(inputs, "PGwt", "Ground pallet weight")
    pr_l = _positive(inputs, "PRl", "Pallet side length")
    pr_e = _positive(inputs, "PRe", "Pallet side width")
    aisle = _positive(inputs, "Isle", "Rack aisle width")
    fl = _positive(inputs, "Fl", "Foot length Fl")
    fw = _positive(inputs, "Fw", "Foot width Fw")
    rk1 = _factor(inputs, "Rk1", "Material factor for racking Rk1")
    rk2 = _factor(inputs, "Rk2", "Repetition factor for racking Rk2")
    dexian = _option(inputs, "Dexian", "Standard Dexian racking", ("Y", "N"))
    d_ab = _positive(inputs, "dAB", "Distance A - B")
    d_ae = _positive(inputs, "dAE", "Distance A - E")
    d_bc = _positive(inputs, "dBC", "Distance B - C")
    h, fc, u, l = mat["h"], mat["fc"], mat["u"], mat["l"]
    if dexian == "Y" and (d_bc != 381 or d_ae != 2591 or d_ab != 838):
        warnings.append("Standard Dexian racking is selected but the layout distances differ "
                        "from 838 / 2591 / 381 mm (reset the Dexian layout).")

    fa = fw * fl
    radius = math.sqrt(fa / math.pi)
    b = equivalent_radius(radius, h)
    rudl = pg_wt * 10 * 1000 / pr_l / pr_e if pg_wt > 0 else 0.0
    rpl = pr_no * pr_wt * 10 / 1000
    v_star = LIVE_LOAD_FACTOR * rpl
    bearing = LIVE_LOAD_FACTOR * rpl / fa * 1000
    allow = PHI_BEARING * 0.9 * fc
    dom = 0.9 * h
    if where == "I":
        perimeter = 2 * (fw + dom) + 2 * (fl + dom)
    elif where == "C":
        perimeter = (fw + dom / 2) + (fl + dom / 2)
    else:
        perimeter = 2 * (min(fw, fl) + dom / 2) + (max(fw, fl) + dom)
    beta_h = max(fl, fw) / min(fl, fw)
    fcv_max, fcv1 = 0.34 * math.sqrt(fc), 0.17 * (1 + 2 / beta_h) * math.sqrt(fc)
    fcv = min(fcv1, fcv_max)
    phi_vuo = PHI_SHEAR * perimeter * dom * fcv / 1000

    si_t, se_t, sc_t = _point_stresses(h, u, l, b, radius)
    invalid = si_t < 0 or se_t < 0 or sc_t < 0
    reduce = radius if consider else 0.0
    diag_a = math.sqrt(d_ae ** 2 + (d_ab + d_bc) ** 2)
    diag_b = math.sqrt(d_ae ** 2 + d_bc ** 2)
    diag_d = math.sqrt(d_ae ** 2 + d_ab ** 2)
    raw = {"A": diag_a, "B": diag_b, "C": d_ae, "D": diag_d, "E": d_ab + d_bc, "F": d_bc,
           "G": 0.0, "H": d_ab, "I": diag_a, "J": diag_b, "K": d_ae, "L": diag_d}
    points = [(p, raw[p], raw[p] - reduce if raw[p] else 0.0, dx, dy, 1.0)
              for p, dx, dy in RACK_POINTS]
    rows = _increase_rows(points, l, where == "I", include_negative)
    rsi, rse, rsc = si_t * rpl / 10, se_t * rpl / 10, sc_t * rpl / 10
    totals = _totals(rsi, rse, rsc, rows, transfer, where)
    rack_sp = totals["st"] / (rk1 * rk2)
    bm = chandler_moment(aisle, l)
    rsudl = bm["value"] * rudl / mat["Z"] * 1000000
    rack_su = rsudl / (uniform["Uk1"] * uniform["Uk2"])
    racks = rack_su + rack_sp
    r_min = {"T": 2 * radius, "M": 2 * radius + h, "B": 2 * radius + 2 * h}
    positions = {"A": (-(d_ab + d_bc), d_ae), "B": (-d_bc, d_ae), "C": (0.0, d_ae),
                 "D": (d_ab, d_ae), "E": (-(d_ab + d_bc), 0.0), "F": (-d_bc, 0.0),
                 "G": (0.0, 0.0), "H": (d_ab, 0.0), "I": (-(d_ab + d_bc), -d_ae),
                 "J": (-d_bc, -d_ae), "K": (0.0, -d_ae), "L": (d_ab, -d_ae)}
    return {
        "PRNo": pr_no, "PRwt": pr_wt, "PGwt": pg_wt, "Rudl": rudl, "RPL": rpl, "aisle": aisle,
        "Fl": fl, "Fw": fw, "Fa": fa, "RRadius": radius, "Rb": b, "Rk1": rk1, "Rk2": rk2,
        "dexian": dexian == "Y", "dAB": d_ab, "dAE": d_ae, "dBC": d_bc,
        "VPstar": v_star, "bearings": bearing, "phib": PHI_BEARING, "allowbs": allow,
        "dom": dom, "uu": perimeter, "bh": beta_h, "maxfcv": fcv_max, "fcv1": fcv1, "fcv": fcv,
        "phiv": PHI_SHEAR, "fVu": phi_vuo,
        "Internal": si_t, "Edge": se_t, "Corner": sc_t, "Rsi": rsi, "Rse": rse, "Rsc": rsc,
        "points": rows, "positions": positions, "Rsx": totals["sx"], "Rsy": totals["sy"],
        "Rsit": totals["sit"], "Rset": totals["set"], "Rsct": totals["sct"],
        "Rst": totals["st"], "RackSP": rack_sp, "BM": bm["value"], "moment": bm,
        "Rsudl": rsudl, "RackSU": rack_su, "racks": racks, "invalid": invalid,
        "Rmin": r_min, "redr": reduce,
    }


def _wheels(inputs: dict[str, Any], mat: dict[str, Any], where: str, transfer: bool,
            consider: bool, include_negative: bool, overlap_where: str,
            warnings: list[str]) -> dict[str, Any]:
    fork = str(inputs.get("Fork") or "").strip()
    axle = _non_negative(inputs, "AxleP", "Maximum single axle load")
    wheels = int(_from_set(inputs, "WheelsPerAxle", "Number of wheels per axle", WHEEL_COUNTS))
    pair = _non_negative(inputs, "WheelPairCentres", "Distance between wheel pair")
    wcts = _positive(inputs, "Wcts", "Distance between wheels across the axle")
    bogie = _non_negative(inputs, "Bogie", "Distance between axles")
    pr = _positive(inputs, "Pr", "Tyre pressure")
    wk1 = _factor(inputs, "Wk1", "Material factor for wheel loads Wk1")
    life = _non_negative(inputs, "Life", "Design life")
    reps = _non_negative(inputs, "Reps", "Daily cycles")
    show = _option(inputs, "showDistWarning", "Show overlap warning", ("Y", "N"))
    if wheels > 2 and pair == 0:
        raise ValueError("Error in number of wheels: four wheels per axle need a wheel pair "
                         "spacing (WheelPairCentres) greater than zero")
    h, u, l = mat["h"], mat["u"], mat["l"]
    wpl = axle / wheels
    radius = 1000 * math.sqrt(wpl * 10 / (math.pi * pr))
    b = equivalent_radius(radius, h)
    repetitions = life * reps * 365
    wk2 = stress_ratio(repetitions)
    si_t, se_t, sc_t = _point_stresses(h, u, l, b, radius)
    invalid = si_t < 0 or se_t < 0 or sc_t < 0
    reduce = radius if consider else 0.0
    four = wheels > 2

    def point(name: str, distance: float, dir_x: str, dir_y: str):
        return (name, distance, distance - reduce if distance else 0.0, dir_x, dir_y, 1.0)

    single = [point("A", pair if four else 0.0, "R", "T"), point("B", 0.0, "R", "T"),
              point("C", wcts - pair if four else 0.0, "R", "T"), point("D", wcts, "R", "T")]
    workbook_g = math.sqrt(bogie ** 2 + (wcts - pair / 2) ** 2) if bogie else 0.0
    dual_raw = {
        "A": pair if four else 0.0, "B": 0.0, "C": wcts - (pair if four else 0.0),
        "D": wcts if four else 0.0,
        "E": math.sqrt(bogie ** 2 + pair ** 2) if bogie and four else 0.0,
        "F": bogie,
        "G": math.sqrt(bogie ** 2 + (wcts - (pair if four else 0.0)) ** 2) if bogie else 0.0,
        "H": math.sqrt(bogie ** 2 + wcts ** 2) if bogie and four else 0.0,
    }
    dual = [point(name, dual_raw[name], *DUAL_DIRECTIONS[name]) for name in DUAL_DIRECTIONS]
    wsi, wse, wsc = si_t * wpl, se_t * wpl, sc_t * wpl
    internal = where == "I"
    single_rows = _increase_rows(single, l, internal, include_negative)
    dual_rows = _increase_rows(dual, l, internal, include_negative)
    single_totals = _totals(wsi, wse, wsc, single_rows, transfer, where)
    dual_totals = _totals(wsi, wse, wsc, dual_rows, transfer, where)
    stress1 = single_totals["st"] / (wk1 * wk2)
    stress2 = dual_totals["st"] / (wk1 * wk2)
    w_min = {"T": 2 * radius, "M": 2 * radius + h, "B": 2 * radius + 2 * h}[overlap_where]
    overlapping = (four and pair > 0 and w_min > pair) or (not four and w_min > wcts)
    if overlapping:
        where_text = OVERLAP_LEVELS[overlap_where]
        warnings.append(f"Warning - Loaded areas overlap {where_text}, treat as single tyre"
                        if show == "Y" else f"Note - Loaded areas overlap {where_text}")
    positions = {"B": (0.0, 0.0), "D": (wcts, 0.0)}
    if four:
        positions.update({"A": (-pair, 0.0), "C": (wcts - pair, 0.0)})
    if bogie:
        positions.update({"F": (0.0, bogie), "G": (wcts, bogie)} if not four else
                         {"F": (0.0, bogie), "E": (-pair, bogie), "G": (wcts - pair, bogie),
                          "H": (wcts, bogie)})
    return {
        "Fork": fork, "AxleP": axle, "WheelsPerAxle": wheels, "WheelPairCentres": pair,
        "Wcts": wcts, "Bogie": bogie, "Pr": pr, "WPL": wpl, "WRadius": radius, "Wb": b,
        "Wk1": wk1, "Life": life, "Reps": reps, "Repetitions": repetitions, "Wk2": wk2,
        "WInternal": si_t, "WEdge": se_t, "WCorner": sc_t, "Wsi": wsi, "Wse": wse, "Wsc": wsc,
        "single": {"points": single_rows, "Wsx": single_totals["sx"], "Wsy": single_totals["sy"],
                   "Wsit": single_totals["sit"], "Wset": single_totals["set"],
                   "Wsct": single_totals["sct"], "Wst": single_totals["st"], "stress": stress1},
        "dual": {"points": dual_rows, "Wsx": dual_totals["sx"], "Wsy": dual_totals["sy"],
                 "Wsit": dual_totals["sit"], "Wset": dual_totals["set"],
                 "Wsct": dual_totals["sct"], "Wst": dual_totals["st"], "stress": stress2,
                 "workbookG": workbook_g},
        "stress": stress2 if bogie else stress1, "axleCase": "dual" if bogie else "single",
        "invalid": invalid, "overlapping": overlapping, "Wmin": w_min, "redw": reduce,
        "positions": positions,
    }


def _custom(inputs: dict[str, Any], mat: dict[str, Any], where: str, transfer: bool,
            consider: bool, include_negative: bool, uniform: dict[str, Any]) -> dict[str, Any]:
    cpl = _positive(inputs, "CPL", "Point G load")
    cfl = _positive(inputs, "CFl", "Custom foot length")
    cfw = _positive(inputs, "CFw", "Custom foot width")
    ltype = _option(inputs, "ltype", "Loading type", ("P", "W"))
    life = _non_negative(inputs, "CLife", "Custom design life")
    reps = _non_negative(inputs, "CReps", "Custom daily cycles")
    mode = _option(inputs, "customLoads", "Adjacent load mode", ("SAME", "LIST"))
    if ltype == "W" and reps == 0:
        raise ValueError("Custom daily cycles (CReps) cannot be 0 for wheel loading")
    h, u, l = mat["h"], mat["u"], mat["l"]
    fa = cfw * cfl
    radius = math.sqrt(fa / math.pi)
    b = equivalent_radius(radius, h)
    ck1 = 0.95 if ltype == "W" else 0.85
    repetitions = life * reps * 365
    ck2 = 1.0 if ltype == "P" else stress_ratio(repetitions)
    si_t, se_t, sc_t = _point_stresses(h, u, l, b, radius)
    invalid = si_t < 0 or se_t < 0 or sc_t < 0
    reduce = radius if consider else 0.0
    points = []
    for name in CUSTOM_POINTS:
        load = cpl if mode == "SAME" else _non_negative(inputs, f"load{name}",
                                                          f"Point {name} load")
        distance = _non_negative(inputs, f"dist{name}", f"Point {name} distance from G")
        dir_x = _option(inputs, f"dir{name}", f"Point {name} direction", DIRECTIONS)
        points.append((name, distance, distance - reduce if distance else 0.0, dir_x,
                       OPPOSITE[dir_x], load / cpl))
    rows = _increase_rows(points, l, where == "I", include_negative)
    for row in rows:
        row["load"] = row["share"] * cpl
    csi, cse, csc = si_t * cpl / 10, se_t * cpl / 10, sc_t * cpl / 10
    totals = _totals(csi, cse, csc, rows, transfer, where)
    stress_p = totals["st"] / (ck1 * ck2)
    bm = chandler_moment(uniform["aisle"], l)
    csudl = bm["value"] * uniform["UDL"] / mat["Z"] * 1000000
    stress_u = csudl / (uniform["Uk1"] * uniform["Uk2"])
    return {"CPL": cpl, "CFl": cfl, "CFw": cfw, "CFa": fa, "CRadius": radius, "cb": b,
            "ltype": ltype, "Ck1": ck1, "CLife": life, "CReps": reps,
            "CRepetitions": repetitions, "Ck2": ck2, "mode": mode,
            "CInternal": si_t, "Cedge": se_t, "Ccorner": sc_t, "Csi": csi, "Cse": cse,
            "Csc": csc, "points": rows, "Csx": totals["sx"], "Csy": totals["sy"],
            "Csit": totals["sit"], "Cset": totals["set"], "Csct": totals["sct"],
            "Cst": totals["st"], "CStressP": stress_p, "CBM": bm["value"], "moment": bm,
            "Csudl": csudl, "CstressU": stress_u, "CStress": stress_p + stress_u,
            "invalid": invalid, "redc": reduce}


def _reinforcement(inputs: dict[str, Any], mat: dict[str, Any]) -> dict[str, Any]:
    cjlen = _positive(inputs, "cjlen", "Length between construction joints")
    dragu = _positive(inputs, "dragu", "Subgrade drag coefficient")
    fsy = _from_set(inputs, "fsy", "Steel yield strength fsy", YIELD_STRENGTHS)
    method = _option(inputs, "reom", "Method for reinforcement", tuple(REINFORCEMENT_METHODS))
    h, density = mat["h"], mat["density"]
    ast3600 = 1.75 * 1000 * (250 if h > 500 else h) / 1000
    ast_min = 0.0014 * h * 1000
    ast_t48 = density * 9.81 * dragu * h * cjlen / 2 / 1000000 / (fsy * 0.67)
    ast_aust = dragu * h * cjlen / 2000 * 9.81 * density / (fsy * 1000 * 0.6)
    ast_max = max(ast3600, ast_min, ast_t48, ast_aust)
    reo1 = shrinkage_steel(ast3600) + (" Top & Bottom" if h > 250 else " Top") + " (Unrestrained)"
    reo2 = shrinkage_steel(ast_max) + " Top"
    reo3 = shrinkage_steel(ast_min) + " Top"
    reo4 = shrinkage_steel(ast_t48) + " Top"
    reo5 = shrinkage_steel(ast_aust) + " Top"
    chosen = {"A": reo1, "N": reo3, "M": reo2, "T": reo4, "R": reo5}[method]
    return {"cjlen": cjlen, "dragu": dragu, "fsy": fsy, "method": method,
            "methodLabel": REINFORCEMENT_METHODS[method], "Ast3600": ast3600, "reo1": reo1,
            "AstMin": ast_min, "reo3": reo3, "AstT48": ast_t48, "reo4": reo4,
            "AstAustroads": ast_aust, "reo5": reo5, "AstMax": ast_max, "reo2": reo2,
            "ReoDesc": chosen, "perFace250": h > 500}


def _location(inputs: dict[str, Any], where: str, l: float, radii: dict[str, float]) -> dict[str, Any]:
    """Load position applicability after the generic Tedds ground-floor classification."""
    dx = _positive(inputs, "edgeDistX", "Distance from load centre to nearest edge or joint")
    dy = _positive(inputs, "edgeDistY", "Distance from load centre to second edge or joint")
    governing = max(radii, key=radii.get)
    a = radii[governing]
    required = a + l
    near, far = min(dx, dy), max(dx, dy)
    classified = "I" if near >= required else "E" if far >= required else "C"
    ratio = {"I": required / near, "E": required / far, "C": 0.0}[where]
    return {"edgeDistX": dx, "edgeDistY": dy, "a": a, "load": governing, "required": required,
            "classified": classified, "ratio": ratio}


def compute(inputs: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []
    mat = _material(inputs, warnings)
    where = _option(inputs, "whereinput", "Point under consideration", tuple(POSITIONS))
    transfer = _option(inputs, "Transfer", "Load transfer at joint", ("Y", "N")) == "Y"
    consider = _option(inputs, "consider", "Consider distance reduction", ("Y", "N")) == "Y"
    include_negative = _option(inputs, "Includeneg", "Include negative chart values",
                               ("Y", "N")) == "Y"
    overlap_where = _option(inputs, "overlapwhere", "Check for overlap at", tuple(OVERLAP_LEVELS))
    subgrade = _subgrade(inputs, mat["K"])
    uniform = _uniform(inputs, mat)
    racking = _racking(inputs, mat, where, transfer, consider, include_negative, uniform,
                       warnings)
    wheels = _wheels(inputs, mat, where, transfer, consider, include_negative, overlap_where,
                     warnings)
    reinforcement = _reinforcement(inputs, mat)
    enabled = inputs.get("checks") if isinstance(inputs.get("checks"), dict) else {}
    custom = (_custom(inputs, mat, where, transfer, consider, include_negative, uniform)
              if enabled.get("custom") else None)
    fcf = mat["fcf"]

    r_min = racking["Rmin"][overlap_where]
    if min(racking["dBC"], racking["dAB"]) < r_min:
        warnings.append(f"Rack post loaded areas overlap {OVERLAP_LEVELS[overlap_where]}: points "
                        f"closer than {r_min:.0f} mm should be checked as a single load.")
    if where != "I":
        warnings.append("Warning - consider using the custom layout: the rack and wheel layouts "
                        "assume the adjacent loads of an internal position.")
    if racking["invalid"]:
        warnings.append("Error - invalid stresses (racking): a Chandler stress per tonne is "
                        "negative for this geometry.")
    if wheels["invalid"]:
        warnings.append("Error - invalid stresses (wheel): a Chandler stress per tonne is "
                        "negative for this geometry.")
    if custom and custom["invalid"]:
        warnings.append("Error - invalid stresses (custom): a Chandler stress per tonne is "
                        "negative for this geometry.")
    for label, moment in (("rack", racking["moment"]),
                          ("custom", custom["moment"] if custom else None)):
        if not moment:
            continue
        if moment["clamped"]:
            warnings.append(f"The {label} aisle width is outside 1500 to 4500 mm; the Chandler "
                            "Fig 3 curves are applied at the nearest limit.")
        if moment["note"] == "below450":
            warnings.append(f"The radius of relative stiffness is below 450 mm; the {label} aisle "
                            "moment uses the 450 mm curve (the workbook returns zero).")
        elif moment["note"] == "above1800":
            warnings.append(f"The radius of relative stiffness exceeds 1800 mm; the {label} aisle "
                            "moment is extrapolated as l / 1800 times the 1800 mm curve.")
    if mat["abrasion"].startswith("Unsuitable"):
        warnings.append("f'c below 25 MPa is unsuitable for abrasion and has no exposure "
                        "classification (T48 Tables 1.6 and 1.7).")

    util = {
        "rackBearing": _ratio(racking["bearings"], racking["allowbs"]),
        "rackPunching": _ratio(racking["VPstar"], racking["fVu"]),
        "rackFlexure": math.inf if racking["invalid"] else _ratio(racking["racks"], fcf),
        "wheelFlexure": math.inf if wheels["invalid"] else _ratio(wheels["stress"], fcf),
        "uniformVariable": _ratio(uniform["UDL"], uniform["UDLall"]),
        "uniformAisle": _ratio(uniform["pata"], fcf),
        "uniformCritical": _ratio(uniform["patc"], fcf),
        "abrasionGrade": ABRASION_MIN_FC / mat["fc"],
    }
    if custom:
        util["customFlexure"] = math.inf if custom["invalid"] else _ratio(custom["CStress"], fcf)
    location = None
    if enabled.get("location"):
        radii = {}
        if racking["RPL"] > 0:
            radii["rack post"] = racking["RRadius"]
        if wheels["AxleP"] > 0:
            radii["wheel"] = wheels["WRadius"]
        if custom:
            radii["custom load"] = custom["CRadius"]
        if radii:
            location = _location(inputs, where, mat["l"], radii)
            util["positionApplicability"] = location["ratio"]
            if location["classified"] != where:
                warnings.append(f"The load position classifies as {POSITIONS[location['classified']]}"
                                f" (a + l = {location['required']:.0f} mm); "
                                f"{POSITIONS[where]} was selected.")
    finite = [value for value in util.values() if math.isfinite(value)]
    worst = max(finite) if finite else 0.0
    checks = {key: True for key in util}
    return {
        "module": MODULE_ID, "version": VERSION,
        "inputs": {"fc": mat["fc"], "h": mat["h"], "K": mat["K"], "where": where,
                   "position": POSITIONS[where], "transfer": transfer, "consider": consider,
                   "includeNegative": include_negative, "overlapWhere": overlap_where,
                   "Tc": TRANSFER_CORNER if transfer else 1.0,
                   "Te": TRANSFER_EDGE if transfer else 1.0},
        "material": mat, "subgrade": subgrade, "racking": racking, "wheels": wheels,
        "uniform": uniform, "reinforcement": reinforcement, "custom": custom,
        "location": location,
        "util": util, "worstUtil": worst, "checks": checks,
        "warnings": warnings, "assumptions": list(ASSUMPTIONS),
        "limitations": list(LIMITATIONS),
    }
