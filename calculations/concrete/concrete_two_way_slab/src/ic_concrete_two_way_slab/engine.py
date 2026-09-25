"""AS 3600:2018 (Amendments 1 and 2) two-way slab engine - simplified method.

Working units are kN, m-run, mm and MPa: slab loads are area loads in kPa and
moments are per metre width in kNm/m, which is how the design method is framed.

The design basis is a transcription of the retained Structural Toolkit workbook
``Concrete_TwoWaySlab_502.xls`` (TWO-WAY SLABS V5.02, sheets ``Analysis`` and
``Settings``).  The workbook's ``Prelim`` sheet is hidden in V5.02 with the note
"Removed 2018 code" and is not transcribed.
"""

from __future__ import annotations

import math
from typing import Any

from .version import VERSION

MODULE_ID = "concrete-two-way-slab"

FC_MIN, FC_MAX = 20.0, 120.0  # Cl 1.1.2
ES = 200000.0  # Cl 3.2.2, MPa
SELF_WEIGHT_DENSITY = 25.0  # kN/m3, reinforced concrete, Settings/Analysis!D23
K3_TWO_WAY = 1.0  # Cl 9.4.4.2 (workbook Analysis!D63)

BAR_SIZES = (8.0, 10.0, 12.0, 16.0, 20.0)
YIELD_STRENGTHS = (500.0, 400.0)
LOAD_TYPES = {"N": "Normal", "S": "Storage", "R": "Roof"}
# AS/NZS 1170.0 Table 4.1 short-term and long-term imposed action factors.
PSI_SHORT = {"N": 0.7, "S": 1.0, "R": 0.7}
PSI_LONG = {"N": 0.4, "S": 0.6, "R": 0.0}

RATIO_COLUMNS = (1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.75, 2.0)

KU_LIMIT = 0.36  # Cl 8.1.5, singly reinforced without compression steel
FLEXURE_LAYERS = {
    "Xb": "Short span, midspan bottom", "Yb": "Long span, midspan bottom",
    "Xtc": "Short span, continuous edge top", "Xtd": "Short span, discontinuous edge top",
    "Ytc": "Long span, continuous edge top", "Ytd": "Long span, discontinuous edge top",
}
# Cl 9.4.3 shrinkage and temperature reinforcement ratios, applied at 75 % in each
# direction of a two-way slab (Cl 9.4.3.3), following Tedds RC slab design 1.0.21.
SHRINKAGE_RATIOS = {"UNRESTRAINED": 0.00175, "MINOR": 0.00175, "MODERATE": 0.0035,
                    "STRONG": 0.006}
SHRINKAGE_LABELS = {"UNRESTRAINED": "Unrestrained",
                    "MINOR": "Restrained, minor crack control",
                    "MODERATE": "Restrained, moderate crack control",
                    "STRONG": "Restrained, strong crack control"}
TWO_WAY_SHRINKAGE_SHARE = 0.75

# Edge code = discontinuous long edges + 3 x discontinuous short edges + 1.
EDGE_LABELS = {
    1: "All edges continuous", 2: "1 long edge discontinuous",
    3: "2 long edges discontinuous", 4: "1 short edge discontinuous",
    5: "2 adjacent edges continuous", 6: "1 short edge continuous",
    7: "2 short edges discontinuous", 8: "1 long edge continuous",
    9: "All edges discontinuous",
}

# Table 6.10.3.2(A), Settings!P39:Y47: beta_x at the RATIO_COLUMNS, beta_x for
# Ly/Lx > 2, then beta_y.  Class N reinforcement with redistribution.
TABLE_A = {
    1: ((0.024, 0.028, 0.032, 0.035, 0.037, 0.040, 0.044, 0.048), 0.048, 0.024),
    2: ((0.028, 0.035, 0.041, 0.046, 0.050, 0.054, 0.061, 0.066), 0.066, 0.028),
    3: ((0.034, 0.046, 0.056, 0.065, 0.072, 0.078, 0.091, 0.100), 0.100, 0.034),
    4: ((0.028, 0.032, 0.036, 0.038, 0.041, 0.043, 0.047, 0.050), 0.050, 0.028),
    5: ((0.035, 0.041, 0.046, 0.051, 0.055, 0.058, 0.065, 0.070), 0.070, 0.035),
    6: ((0.043, 0.054, 0.064, 0.072, 0.078, 0.084, 0.096, 0.105), 0.105, 0.043),
    7: ((0.034, 0.038, 0.040, 0.043, 0.045, 0.047, 0.050, 0.053), 0.053, 0.034),
    8: ((0.043, 0.049, 0.053, 0.057, 0.061, 0.064, 0.069, 0.074), 0.074, 0.043),
    9: ((0.056, 0.066, 0.074, 0.081, 0.087, 0.093, 0.103, 0.111), 0.111, 0.056),
}

# Table 6.10.3.2(B), Settings!P52:Y60.  Class L reinforcement or no redistribution.
TABLE_B = {
    1: ((0.021, 0.025, 0.029, 0.032, 0.034, 0.036, 0.039, 0.041), 0.042, 0.020),
    2: ((0.024, 0.028, 0.034, 0.038, 0.043, 0.047, 0.056, 0.061), 0.070, 0.028),
    3: ((0.024, 0.028, 0.035, 0.042, 0.049, 0.056, 0.071, 0.085), 0.125, 0.039),
    4: ((0.027, 0.030, 0.033, 0.035, 0.037, 0.039, 0.041, 0.042), 0.042, 0.024),
    5: ((0.031, 0.036, 0.041, 0.046, 0.050, 0.053, 0.060, 0.064), 0.070, 0.034),
    6: ((0.033, 0.039, 0.047, 0.054, 0.061, 0.067, 0.082, 0.093), 0.125, 0.046),
    7: ((0.032, 0.035, 0.037, 0.038, 0.039, 0.040, 0.042, 0.042), 0.042, 0.024),
    8: ((0.039, 0.044, 0.048, 0.052, 0.055, 0.058, 0.063, 0.066), 0.070, 0.035),
    9: ((0.044, 0.052, 0.059, 0.066, 0.073, 0.079, 0.091, 0.100), 0.125, 0.049),
}

# Table 6.10.3.2(B) negative moment factors, Settings!P65:Y73: alpha_x at the
# RATIO_COLUMNS, alpha_x for Ly/Lx > 2, then alpha_y.  Zero where no edge in that
# direction is continuous.
TABLE_B_ALPHA = {
    1: ((2.31, 2.22, 2.14, 2.10, 2.06, 2.03, 2.00, 2.00), 2.00, 2.69),
    2: ((2.22, 2.17, 2.09, 2.03, 1.97, 1.93, 1.86, 1.81), 1.80, 2.46),
    3: ((0.0,) * 8, 0.0, 2.31),
    4: ((2.20, 2.14, 2.10, 2.06, 2.04, 2.02, 2.00, 2.00), 2.00, 2.29),
    5: ((2.13, 2.07, 2.01, 1.96, 1.92, 1.89, 1.83, 1.80), 1.80, 2.13),
    6: ((0.0,) * 8, 0.0, 2.12),
    7: ((2.09, 2.05, 2.03, 2.01, 2.00, 2.00, 2.00, 2.00), 2.00, 0.0),
    8: ((2.04, 1.97, 1.93, 1.89, 1.86, 1.84, 1.80, 1.80), 1.80, 0.0),
    9: ((0.0,) * 8, 0.0, 0.0),
}

# Table 9.4.4.2 k4 for two-way slabs at Ly/Lx = 1.0, 1.25, 1.5, 2.0 (Settings!P80:S88).
K4_RATIOS = (1.0, 1.25, 1.5, 2.0)
TABLE_K4 = {
    1: (3.6, 3.1, 2.8, 2.5), 2: (3.4, 2.65, 2.4, 2.1), 3: (3.2, 2.5, 2.0, 1.6),
    4: (3.4, 2.9, 2.7, 2.4), 5: (2.95, 2.5, 2.25, 2.0), 6: (2.7, 2.1, 1.9, 1.6),
    7: (3.2, 2.8, 2.6, 2.4), 8: (2.7, 2.3, 2.2, 1.95), 9: (2.25, 1.9, 1.7, 1.5),
}

ASSUMPTIONS = [
    "The slab is a rectangular panel supported on four sides by walls or beams, carrying "
    "uniformly distributed actions, with corners held down against uplift and torsional "
    "reinforcement provided at discontinuous corners as the simplified method requires.",
    "Loads are unfactored area actions; the module forms the AS/NZS 1170.0 Cl 4.2.2 "
    "strength combination and the Table 4.1 serviceability factors.",
    "Self weight is taken as 25 kN/m3 times the slab thickness when included.",
    "The short span Lx is used as the effective span Lef in the deemed-to-comply "
    "deflection check; enter effective spans, not clear spans.",
    "Ast and Asc are the tensile and compression reinforcement per metre in the positive "
    "moment region used for the deflection check.",
]

LIMITATIONS = [
    "Transcribed from Structural Toolkit TWO-WAY SLABS V5.02. Independent engineering review "
    "has not been completed and the module is not approved for design.",
    "Flexural capacity is checked only when the optional flexure group is enabled. Shear, "
    "crack width, torsional corner reinforcement and detailing are not checked.",
    "Adjacent-span conditions for the simplified method and for the deemed-to-comply "
    "span-to-depth rule are not checked and must be confirmed by the designer.",
    "Coefficients for Ly/Lx greater than 2 are taken from the tables' '> 2' column, which "
    "is a step change at Ly/Lx = 2 for Table 6.10.3.2(B).",
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


def _from_set(inputs: dict[str, Any], key: str, label: str,
              permitted: tuple[float, ...]) -> float:
    value = _number(inputs, key, label)
    if value not in permitted:
        allowed = ", ".join(f"{item:g}" for item in permitted)
        raise ValueError(f"{label} ({key}) must be one of {allowed}, not {value:g}")
    return value


def _edge_count(inputs: dict[str, Any], key: str, label: str) -> int:
    value = _number(inputs, key, label)
    if value not in (0.0, 1.0, 2.0):
        raise ValueError(f"{label} ({key}) must be 0, 1 or 2")
    return int(value)


def _ratio(action: float, capacity: float) -> float:
    if capacity <= 0:
        return math.inf if action > 0 else 0.0
    return action / capacity


# ---------------------------------------------------------------------------
#  Table interpolation
# ---------------------------------------------------------------------------
def table_value(row: tuple[tuple[float, ...], float, float], ratio: float) -> float:
    """Linear interpolation across Ly/Lx, reproducing the workbook ``Interp`` routine.

    At or below 1.0 the first column is used; above 2.0 the separate '> 2' column
    is used without interpolation.
    """
    values, beyond, _ = row
    if ratio <= RATIO_COLUMNS[0]:
        return values[0]
    if ratio > RATIO_COLUMNS[-1]:
        return beyond
    for index in range(1, len(RATIO_COLUMNS)):
        if ratio <= RATIO_COLUMNS[index]:
            low, high = RATIO_COLUMNS[index - 1], RATIO_COLUMNS[index]
            return (ratio - low) / (high - low) * (values[index] - values[index - 1]) + values[index - 1]
    return beyond


def k4_value(row: tuple[float, float, float, float], ratio: float) -> float:
    """Table 9.4.4.2 interpolation, reproducing the workbook ``Getk4`` routine."""
    if ratio < K4_RATIOS[0]:
        return row[0]
    for index in range(1, len(K4_RATIOS)):
        if ratio < K4_RATIOS[index]:
            low, high = K4_RATIOS[index - 1], K4_RATIOS[index]
            return (ratio - low) / (high - low) * (row[index] - row[index - 1]) + row[index - 1]
    return row[-1]


def formula_coefficients(delta_x: float, delta_y: float, lx_ly: float) -> tuple[float, float]:
    """Closed-form beta_y and beta_x (Warner, Rangan and Hall), Class N with redistribution."""
    ratio = delta_x / delta_y
    beta_y = 2.0 * (math.sqrt(3.0 + ratio ** 2) - ratio) ** 2 / (9.0 * delta_y ** 2)
    beta_x = lx_ly * beta_y + 2.0 * (1.0 - lx_ly) / (3.0 * delta_y ** 2)
    return beta_x, beta_y


def _delta(discontinuous: int) -> float:
    return {2: 2.0, 1: 2.5}.get(discontinuous, 3.1)


def ec_from_fcmi(fcmi: float, density: float) -> float:
    """Cl 3.1.2 mean modulus of elasticity."""
    if fcmi <= 40.0:
        return density ** 1.5 * 0.043 * math.sqrt(fcmi)
    return density ** 1.5 * (0.024 * math.sqrt(fcmi) + 0.12)


def fcmi_curve(fc: float) -> float:
    """Workbook curve fit to Table 3.1.2 mean in-situ strength."""
    return -0.0015 * fc ** 2 + 1.1429 * fc - 0.0614


# ---------------------------------------------------------------------------
#  Calculation
# ---------------------------------------------------------------------------
def section_capacity(*, As: float, d: float, fc: float, fsy: float, klass: str) -> dict[str, float]:
    """Singly reinforced rectangular stress block per metre width, Cl 8.1."""
    alpha2 = max(0.67, 0.85 - 0.0015 * fc)
    gamma = max(0.67, 0.97 - 0.0025 * fc)
    ku = As * fsy / (alpha2 * fc * gamma * 1000.0 * d)
    phi = max(0.65, min(0.85, 1.24 - 13.0 * ku / 12.0)) if klass == "N" else 0.65
    phiMu = phi * As * fsy * d * (1.0 - As * fsy / (2.0 * alpha2 * fc * 1000.0 * d)) / 1e6
    return {"alpha2": alpha2, "gamma": gamma, "ku": ku, "phi": phi, "phiMu": phiMu}


def _bar_layer(inputs: dict[str, Any], prefix: str, label: str) -> tuple[float, float, float]:
    bar = _from_set(inputs, f"bar{prefix}", f"{label} bar size", BAR_SIZES)
    spacing = _positive(inputs, f"s{prefix}", f"{label} bar spacing")
    return bar, spacing, math.pi * bar ** 2 / 4.0 * 1000.0 / spacing


def _flexure(inputs: dict[str, Any], *, th: float, cover: float, fc: float, fsy: float,
             klass: str, moments: dict[str, float], long_disc: int, short_disc: int,
             fctf: float, as_crack: float) -> dict[str, Any]:
    """Capacity at each panel location; short-span bars form the outer layer top and bottom."""
    cover_top = _non_negative(inputs, "coverTop", "Cover to top steel")
    layers = {key: _bar_layer(inputs, key, label) for key, label in FLEXURE_LAYERS.items()}
    x_top = max(layers["Xtc"][0], layers["Xtd"][0])
    depths = {
        "Xb": th - cover - layers["Xb"][0] / 2.0,
        "Yb": th - cover - layers["Xb"][0] - layers["Yb"][0] / 2.0,
        "Xtc": th - cover_top - layers["Xtc"][0] / 2.0,
        "Xtd": th - cover_top - layers["Xtd"][0] / 2.0,
        "Ytc": th - cover_top - x_top - layers["Ytc"][0] / 2.0,
        "Ytd": th - cover_top - x_top - layers["Ytd"][0] / 2.0,
    }
    demand = {"Xb": moments["Mx"], "Yb": moments["My"], "Xtc": moments["MxCont"],
              "Xtd": moments["MxDisc"], "Ytc": moments["MyCont"], "Ytd": moments["MyDisc"]}
    present = {"Xb": True, "Yb": True, "Xtc": long_disc < 2, "Xtd": long_disc > 0,
               "Ytc": short_disc < 2, "Ytd": short_disc > 0}
    s_max = min(300.0, 2.0 * th)
    locations = []
    for key, label in FLEXURE_LAYERS.items():
        if not present[key]:
            continue
        bar, spacing, As = layers[key]
        d = depths[key]
        if d <= 0:
            raise ValueError(f"{label}: cover and bar sizes leave no positive effective depth")
        capacity = section_capacity(As=As, d=d, fc=fc, fsy=fsy, klass=klass)
        as_min = max(as_crack, 0.19 * (th / d) ** 2 * fctf / fsy * 1000.0 * d)
        locations.append({
            "key": key, "label": label, "bar": bar, "spacing": spacing, "As": As, "d": d,
            "Mstar": demand[key], **capacity, "AsMin": as_min, "sMax": s_max,
            "ratioMoment": _ratio(demand[key], capacity["phiMu"]),
            "ratioDuctility": capacity["ku"] / KU_LIMIT,
            "ratioMinimum": _ratio(as_min, As),
            "ratioSpacing": spacing / s_max,
        })
    return {"coverTop": cover_top, "sMax": s_max, "locations": locations}


def compute(inputs: dict[str, Any]) -> dict[str, Any]:
    fc = _number(inputs, "fc", "Concrete strength f'c")
    if not FC_MIN <= fc <= FC_MAX:
        raise ValueError(f"Concrete strength f'c (fc) must be between {FC_MIN:g} and "
                         f"{FC_MAX:g} MPa (Cl 1.1.2)")
    th = _positive(inputs, "th", "Slab thickness th")
    span_a = _positive(inputs, "Ly", "Long edge length Ly")
    span_b = _positive(inputs, "Lx", "Short edge length Lx")
    Ly, Lx = max(span_a, span_b), min(span_a, span_b)
    reo = _option(inputs, "reo", "Reinforcement ductility class", ("N", "L"))
    redist = _option(inputs, "redist", "Allow redistribution", ("Y", "N"))
    cont_long = _edge_count(inputs, "contLong", "Continuous long edges")
    cont_short = _edge_count(inputs, "contShort", "Continuous short edges")
    include_sw = _option(inputs, "includeSW", "Include self weight", ("Y", "N"))
    load_type = _option(inputs, "loadType", "Live load type", tuple(LOAD_TYPES))
    wsdl = _non_negative(inputs, "wsdl", "Superimposed dead load")
    wll = _non_negative(inputs, "wll", "Live load")
    use_formula = _option(inputs, "useFormula", "Use closed-form coefficients", ("Y", "N"))
    Ast = _positive(inputs, "Ast", "Tensile steel Ast")
    fsy = _from_set(inputs, "fsy", "Yield strength fsy", YIELD_STRENGTHS)
    cover = _non_negative(inputs, "cover", "Cover to bottom steel")
    dia = _from_set(inputs, "dia", "Bar size", BAR_SIZES)
    dc = _non_negative(inputs, "dc", "Depth to compression steel")
    Asc = _non_negative(inputs, "Asc", "Compression steel Asc")
    use_fcmi = _option(inputs, "useFcmi", "Use fcmi curve", ("Y", "N"))
    density = _positive(inputs, "density", "Concrete density")
    lef_total = _positive(inputs, "lefDelta", "Total deflection limit Lef/Delta")
    lef_inc = _positive(inputs, "lefDeltaInc", "Incremental deflection limit Lef/Delta")

    ds = th - cover - dia / 2.0
    if ds <= 0:
        raise ValueError("Cover and bar size leave no positive effective depth ds")
    if dc >= ds:
        raise ValueError("Depth to compression steel dc must be less than ds")

    warnings: list[str] = []
    if span_b > span_a:
        warnings.append("The entered long edge was shorter than the short edge; the spans "
                        "have been sorted so that Ly >= Lx.")

    # Loading, AS/NZS 1170.0.
    swt = SELF_WEIGHT_DENSITY * th / 1000.0
    wdl = (swt if include_sw == "Y" else 0.0) + wsdl
    strength_a, strength_b = 1.35 * wdl, 1.2 * wdl + 1.5 * wll
    Fd = max(strength_a, strength_b)
    loads = {
        "swt": swt, "includeSW": include_sw == "Y", "wsdl": wsdl, "wdl": wdl, "wll": wll,
        "Fd": Fd, "case": "1.35G" if strength_a > strength_b else "1.2G + 1.5Q",
        "psiS": PSI_SHORT[load_type], "psiL": PSI_LONG[load_type],
        "loadType": load_type,
    }

    # Moment coefficients, Cl 6.10.3.2.
    long_disc, short_disc = 2 - cont_long, 2 - cont_short
    code = long_disc + short_disc * 3 + 1
    klass = "L" if reo == "L" or redist == "N" else "N"
    yx = Ly / Lx
    if yx > 2.0:
        warnings.append(f"Ly/Lx = {yx:.2f} exceeds 2.0: the panel acts predominantly one-way and "
                        "the '> 2' table column is applied without interpolation.")
    lx_ly = 1.0 / min(yx, 2.0)
    delta_y, delta_x = _delta(long_disc), _delta(short_disc)
    formula_bx, formula_by = formula_coefficients(delta_x, delta_y, lx_ly)
    table_a_bx, table_a_by = table_value(TABLE_A[code], yx), TABLE_A[code][2]
    table_b_bx, table_b_by = table_value(TABLE_B[code], yx), TABLE_B[code][2]
    alpha_x, alpha_y = table_value(TABLE_B_ALPHA[code], yx), TABLE_B_ALPHA[code][2]
    if klass == "N":
        source = "formula" if use_formula == "Y" else "A"
        beta_x, beta_y = ((formula_bx, formula_by) if use_formula == "Y"
                          else (table_a_bx, table_a_by))
        disc_factor, cont_x, cont_y = 0.5, 1.33, 1.33
    else:
        source = "B"
        beta_x, beta_y = table_b_bx, table_b_by
        disc_factor, cont_x, cont_y = 0.8, alpha_x, alpha_y
        if use_formula == "Y":
            warnings.append("The closed-form coefficients apply only to Class N reinforcement "
                            "with redistribution; Table 6.10.3.2(B) has been used.")

    Mx = Fd * beta_x * (Lx / 1000.0) ** 2
    My = Fd * beta_y * (Lx / 1000.0) ** 2
    moments = {
        "Mx": Mx, "My": My, "MxDisc": disc_factor * Mx, "MyDisc": disc_factor * My,
        "MxCont": cont_x * Mx, "MyCont": cont_y * My,
        "discFactor": disc_factor, "contFactorX": cont_x, "contFactorY": cont_y,
    }
    # Edge moments as drawn by the workbook: discontinuous edges are taken first as
    # the top long edge and the left short edge.
    edges = {
        "longTop": -(moments["MxDisc"] if long_disc > 0 else moments["MxCont"]),
        "longBottom": -(moments["MxDisc"] if long_disc > 1 else moments["MxCont"]),
        "shortLeft": -(moments["MyDisc"] if short_disc > 0 else moments["MyCont"]),
        "shortRight": -(moments["MyDisc"] if short_disc > 1 else moments["MyCont"]),
        "longTopContinuous": long_disc == 0, "longBottomContinuous": long_disc <= 1,
        "shortLeftContinuous": short_disc == 0, "shortRightContinuous": short_disc <= 1,
    }
    analysis = {
        "code": code, "edgeLabel": EDGE_LABELS[code], "class": klass, "source": source,
        "longDiscontinuous": long_disc, "shortDiscontinuous": short_disc,
        "Ly": Ly, "Lx": Lx, "yx": yx, "lxly": lx_ly, "deltaX": delta_x, "deltaY": delta_y,
        "betaX": beta_x, "betaY": beta_y, "alphaX": alpha_x, "alphaY": alpha_y,
        "formulaBx": formula_bx, "formulaBy": formula_by,
        "tableABx": table_a_bx, "tableABy": table_a_by,
        "tableBBx": table_b_bx, "tableBBy": table_b_by,
    }

    # Minimum strength requirements, Cl 9.1.1.
    fctf = 0.6 * math.sqrt(fc)
    ast_min = 0.19 * (th / ds) ** 2 * fctf / fsy * 1000.0 * ds
    minimum = {
        "fctf": fctf, "ds": ds, "Astmin": ast_min,
        "AstminOneWay": 0.20 * (th / ds) ** 2 * fctf / fsy * 1000.0 * ds,
        "AstminColumns": 0.24 * (th / ds) ** 2 * fctf / fsy * 1000.0 * ds,
    }

    # Deemed-to-comply span-to-depth ratio, Cl 9.4.4.2.
    fcmi = fcmi_curve(fc) if use_fcmi == "Y" else fc
    Ec = ec_from_fcmi(fcmi, density)
    n = ES / Ec
    p, pc = Ast / 1000.0 / ds, Asc / 1000.0 / ds
    term = n * p + (n - 1.0) * pc
    ku = math.sqrt(term ** 2 + 2.0 * (n * p + (n - 1.0) * pc * dc / ds)) - term
    NA = ku * ds
    asc_ignored = NA - dia / 2.0 < dc
    if asc_ignored and Asc > 0:
        warnings.append("Compression steel lies in the tension zone and is ignored for kcs.")
    kcs = max(0.8, 2.0 - 1.2 * ((0.0 if asc_ignored else Asc) / Ast))
    psi_s, psi_l = loads["psiS"], loads["psiL"]
    Fdef = (1.0 + kcs) * wdl + (psi_s + psi_l * kcs) * wll
    Fdefi = kcs * wdl + (psi_s + psi_l * kcs) * wll
    k4 = k4_value(TABLE_K4[code], yx)

    def d_required(limit: float, load: float) -> float:
        if load <= 0:
            return 0.0
        return Lx / (K3_TWO_WAY * k4 * (Ec / limit / (load / 1000.0)) ** (1.0 / 3.0))

    dmin, dmini = d_required(lef_total, Fdef), d_required(lef_inc, Fdefi)
    deflection = {
        "fcmi": fcmi, "useFcmi": use_fcmi == "Y", "density": density, "Ec": Ec, "n": n,
        "p": p, "pc": pc, "dcds": dc / ds, "ku": ku, "NA": NA, "ascIgnored": asc_ignored,
        "kcs": kcs, "Fdef": Fdef, "Fdefi": Fdefi, "k3": K3_TWO_WAY, "k4": k4,
        "lefDelta": lef_total, "lefDeltaInc": lef_inc, "dmin": dmin, "dmini": dmini,
        "thmin": dia / 2.0 + cover + dmin, "thmininc": dia / 2.0 + cover + dmini,
        "ds": ds, "Ast": Ast, "Asc": Asc, "dc": dc,
    }

    util = {
        "deflectionTotal": _ratio(dmin, ds),
        "deflectionIncremental": _ratio(dmini, ds),
        "minimumSteel": _ratio(ast_min, Ast),
        "liveLoadLimit": _ratio(wll, wdl),
    }
    enabled = inputs.get("checks") if isinstance(inputs.get("checks"), dict) else {}
    shrinkage = None
    if enabled.get("shrinkage"):
        restraint = _option(inputs, "restraint", "Degree of restraint", tuple(SHRINKAGE_RATIOS))
        ratio = SHRINKAGE_RATIOS[restraint]
        shrinkage = {"restraint": restraint, "label": SHRINKAGE_LABELS[restraint],
                     "p": ratio, "AsCrack": TWO_WAY_SHRINKAGE_SHARE * ratio * th * 1000.0}
    flexure = None
    if enabled.get("flexure"):
        flexure = _flexure(inputs, th=th, cover=cover, fc=fc, fsy=fsy, klass=klass,
                           moments=moments, long_disc=long_disc, short_disc=short_disc,
                           fctf=fctf, as_crack=shrinkage["AsCrack"] if shrinkage else 0.0)
        governing = {key: max(item[key] for item in flexure["locations"])
                     for key in ("ratioMoment", "ratioDuctility", "ratioMinimum", "ratioSpacing")}
        util.update({"flexure": governing["ratioMoment"],
                     "ductility": governing["ratioDuctility"],
                     "flexuralMinimum": governing["ratioMinimum"],
                     "barSpacing": governing["ratioSpacing"]})
    elif shrinkage:
        util["shrinkage"] = _ratio(shrinkage["AsCrack"], Ast)
    if util["liveLoadLimit"] > 1.0:
        warnings.append("Live load exceeds the dead load, outside the deemed-to-comply "
                        "span-to-depth method (Cl 9.4.4.2).")
    finite = [value for value in util.values() if math.isfinite(value)]
    worst = max(finite) if finite else 0.0
    checks = {key: True for key in util}
    return {
        "module": MODULE_ID, "version": VERSION,
        "inputs": {"fc": fc, "th": th, "Ly": Ly, "Lx": Lx, "reo": reo, "redist": redist,
                   "contLong": cont_long, "contShort": cont_short, "fsy": fsy,
                   "cover": cover, "dia": dia, "useFormula": use_formula},
        "loads": loads, "analysis": analysis, "moments": moments, "edges": edges,
        "minimum": minimum, "deflection": deflection,
        "flexure": flexure, "shrinkage": shrinkage,
        "util": util, "worstUtil": worst, "checks": checks,
        "warnings": warnings, "assumptions": list(ASSUMPTIONS),
        "limitations": list(LIMITATIONS),
    }
