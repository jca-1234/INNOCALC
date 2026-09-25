"""AS 3600:2018 (Amendments 1 and 2) flat slab engine - simplified method, Cl 6.10.4.

Working units are kPa for area loads, mm for lengths, kNm for strip moments and kNm/m
for moments per metre width, which is how the workbook frames the method.

The design basis is a transcription of the retained Structural Toolkit workbook
``Concrete_FlatSlab_504.xls`` (FLAT SLABS V5.04, sheets ``Analysis`` and ``Settings``).
The ``Prelim`` sheet is marked "Removed 2018 standard" and is not transcribed.
"""

from __future__ import annotations

import math
from typing import Any

from .version import VERSION

MODULE_ID = "concrete-flat-slab"

FC_MIN, FC_MAX = 20.0, 120.0  # Cl 1.1.2
ES = 200000.0  # Cl 3.2.2, MPa
SELF_WEIGHT_DENSITY = 25.0  # kN/m3, Analysis!F28
DROP_DEPTH_RATIO = 0.3  # Analysis!H20, overall depth 1.3 D at the drop
LO_MIN_RATIO = 0.65  # Cl 6.10.4.2, Lo >= 0.65 L
MIN_STEEL_COEFF = 0.24  # Cl 9.1.1(a), Analysis!D164
K3_NO_DROP, K3_DROP = 0.95, 1.05  # Cl 9.4.4.1, Analysis!C185 and G185
K4 = {"I": 2.1, "E": 1.75}  # Cl 9.4.4.1, Analysis!C186
SPAN_RATIO_LIMIT = 2.0  # Cl 6.10.4.1(c)
KU_LIMIT = 0.36  # Cl 8.1.5

BAR_SIZES = (10.0, 12.0, 16.0, 20.0, 24.0)  # Settings!I29:I33
YIELD_STRENGTHS = (500.0, 400.0)  # Settings!I39:I40
LOAD_TYPES = {"N": "Normal", "S": "Storage"}
PSI_SHORT = {"N": 0.7, "S": 1.0}  # AS/NZS 1170.0 Table 4.1, Analysis!H30
PSI_LONG = {"N": 0.4, "S": 0.6}  # Analysis!H31
SPAN_TYPES = {"I": "Interior span", "E": "End span"}

SLAB_TYPES = {"S": 1, "I": 2, "C": 3, "F": 4}
SLAB_TYPE_LABELS = {1: "Exterior edge unrestrained (simple)", 2: "Integral columns",
                    3: "Columns and edge beam", 4: "Exterior edge fully restrained (walls)"}
# Text of Analysis!B8, reproduced including the workbook's capitalisation.
WORKBOOK_TYPE_TEXT = {1: "simple Spans", 2: "Integral columns", 3: "Column & Edge beam",
                      4: "Fully restrained"}

POSITIONS = ("End support", "End span midspan", "First interior support (end span)",
             "First interior support (interior span)", "Interior span midspan",
             "Interior support")
POSITION_KIND = ("negExt", "pos", "negInt", "negInt", "pos", "negInt")

# Table 6.10.4.3 static moment coefficients, Analysis!M45:R48.
COEFF = {
    1: (0.0, 0.6, -0.8, -0.65, 0.35, -0.65),
    2: (-0.25, 0.5, -0.75, -0.65, 0.35, -0.65),
    3: (-0.3, 0.5, -0.7, -0.65, 0.35, -0.65),
    4: (-0.65, 0.35, -0.65, -0.65, 0.35, -0.65),
}
# Column strip share of the interior design strip, Analysis!M71:R74.
COEFF_COLUMN = {
    1: (0.0, 0.5, 0.75, 0.75, 0.5, 0.75),
    2: (1.0, 0.5, 0.75, 0.75, 0.5, 0.75),
    3: (0.75, 0.5, 0.75, 0.75, 0.5, 0.75),
    4: (1.0, 0.5, 0.75, 0.75, 0.5, 0.75),
}
# Edge column strip share of the edge design strip, Analysis!M81:R84.
COEFF_EDGE = {
    1: (0.0, 0.5, 0.75, 0.75, 0.5, 0.75),
    2: (1.0, 0.5, 0.75, 0.75, 0.5, 0.75),
    3: (1.0, 0.7, 1.0, 1.0, 0.7, 1.0),
    4: (1.0, 0.5, 0.75, 0.75, 0.5, 0.75),
}
# Table 6.9.5.3 column strip share, strength limit state, Analysis!M58:N61.
DISTRIBUTION_RANGES = {"negInt": (0.60, 1.00), "negExt": (0.75, 1.00), "pos": (0.50, 0.70)}

# Order of the 16 columns of the workbook's support-width table astable (Analysis!M:AB).
SUPPORT_KEYS = ("asy1", "asx1", "asy", "asx", "asy1e", "asx1e", "asye", "asxe")
SUPPORT_COLUMNS = {"asy1": 1, "asx1": 2, "asy": 5, "asx": 6,
                   "asy1e": 9, "asx1e": 10, "asye": 13, "asxe": 14}
SUPPORT_LABELS = {
    "asy1": "Interior strip, end span, Ly", "asx1": "Interior strip, end span, Lx",
    "asy": "Interior strip, interior span, Ly", "asx": "Interior strip, interior span, Lx",
    "asy1e": "Edge strip, end span, Ly", "asx1e": "Edge strip, end span, Lx",
    "asye": "Edge strip, interior span, Ly", "asxe": "Edge strip, interior span, Lx",
}
CUSTOM_SUPPORT_FIELDS = {"asy1": "asY1", "asx1": "asX1", "asy": "asY", "asx": "asX",
                         "asy1e": "asY1e", "asx1e": "asX1e", "asye": "asYe", "asxe": "asXe"}

# Cl 6.10.4.5 minimum moment transferred to an interior support, as transcribed in
# PUNCHING SHEAR V5.06 (Design!F97:F105).
MV_COEFF, MV_DEAD, MV_LIVE = 0.06, 1.2, 0.75

FLEXURE_LAYERS = {
    "Ct": "Column strip, top (negative)", "Cb": "Column strip, bottom (positive)",
    "Mt": "Middle strip, top (negative)", "Mb": "Middle strip, bottom (positive)",
    "Et": "Edge column strip, top (negative)", "Eb": "Edge column strip, bottom (positive)",
}
SHRINKAGE_RATIOS = {"UNRESTRAINED": 0.00175, "MINOR": 0.00175, "MODERATE": 0.0035,
                    "STRONG": 0.006}
SHRINKAGE_LABELS = {"UNRESTRAINED": "Unrestrained",
                    "MINOR": "Restrained, minor crack control",
                    "MODERATE": "Restrained, moderate crack control",
                    "STRONG": "Restrained, strong crack control"}
TWO_WAY_SHRINKAGE_SHARE = 0.75

ASSUMPTIONS = [
    "The slab system satisfies Cl 6.10.4.1: at least two continuous spans in each direction, "
    "a rectangular support grid with offsets not exceeding 10 % of the span, successive spans "
    "differing by no more than one-third of the longer, an end span no longer than the "
    "adjacent interior span, and lateral actions not resisted by slab-column frame action.",
    "All spans in each direction are equal, as the workbook assumes. Spans are support "
    "centreline dimensions; Ly is the longer and Lx the shorter.",
    "Loads are uniformly distributed, unfactored area actions. The dead load includes the slab "
    "self weight (25 kN/m3); the weight of drop panels is not added.",
    "Drop panels, where present, extend L/6 each way from the column centreline and are "
    "0.3 D deep (overall 1.3 D), the minimum for k3 = 1.05 in Cl 9.4.4.1.",
    "The support length a_sup is half the column dimension at each column, plus the drop "
    "depth where a drop panel is present, and zero at an unrestrained or wall-supported edge, "
    "following the workbook's support-width table.",
    "Ast and Asc are the tensile and compression reinforcement per metre in the positive "
    "moment region used for the deflection check.",
]

LIMITATIONS = [
    "Transcribed from Structural Toolkit FLAT SLABS V5.04. Independent engineering review has "
    "not been completed and the module is not approved for design.",
    "Punching shear is not checked. Design the columns with the concrete-punching-shear module "
    "using the Cl 6.10.4.5 transferred moment reported here.",
    "Beam shear, crack width, torsion at edges, detailing, fire and vibration are not checked. "
    "Edge beams are not designed.",
    "Flexural capacity is checked only when the optional flexure group is enabled, and ignores "
    "the additional depth of drop panels.",
    "The Prelim sheet (WRH Chapter 16 preliminary thickness) is marked 'Removed 2018 standard' "
    "and is not transcribed.",
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


def _ratio(action: float, capacity: float) -> float:
    if capacity <= 0:
        return math.inf if action > 0 else 0.0
    return action / capacity


def excel_roundup_10(value: float) -> float:
    """ROUNDUP(value, -1) for positive values."""
    return math.ceil(round(value / 10.0, 9)) * 10.0


def excel_text0(value: float) -> str:
    """TEXT(value, "0"): nearest integer with halves away from zero."""
    rounded = math.floor(abs(value) + 0.5)
    return f"{-rounded if value < 0 else rounded:.0f}"


# ---------------------------------------------------------------------------
#  Material helpers
# ---------------------------------------------------------------------------
def fcmi_curve(fc: float) -> float:
    """Workbook curve fit to Table 3.1.2 mean in-situ strength (Analysis!I181)."""
    return -0.0015 * fc ** 2 + 1.1429 * fc - 0.0614


def ec_from_fcmi(fcmi: float, density: float) -> float:
    """Cl 3.1.2 mean modulus of elasticity (Analysis!D182)."""
    if fcmi <= 40.0:
        return density ** 1.5 * 0.043 * math.sqrt(fcmi)
    return density ** 1.5 * (0.024 * math.sqrt(fcmi) + 0.12)


def section_capacity(*, As: float, d: float, fc: float, fsy: float, klass: str) -> dict[str, float]:
    """Singly reinforced rectangular stress block per metre width, Cl 8.1."""
    alpha2 = max(0.67, 0.85 - 0.0015 * fc)
    gamma = max(0.67, 0.97 - 0.0025 * fc)
    ku = As * fsy / (alpha2 * fc * gamma * 1000.0 * d)
    phi = max(0.65, min(0.85, 1.24 - 13.0 * ku / 12.0)) if klass == "N" else 0.65
    phiMu = phi * As * fsy * d * (1.0 - As * fsy / (2.0 * alpha2 * fc * 1000.0 * d)) / 1e6
    return {"alpha2": alpha2, "gamma": gamma, "ku": ku, "phi": phi, "phiMu": phiMu}


# ---------------------------------------------------------------------------
#  Support widths and strips
# ---------------------------------------------------------------------------
def support_table(fstype: int, cy: float, cx: float, thd: float,
                  Ly: float, Lx: float) -> tuple[float, ...]:
    """The 16 sums of support lengths (2 a_sup) of Analysis!M32:AB35 for one slab type."""
    if fstype == 1:
        return (0.0,) * 16
    if fstype == 2:
        block = (0.5 * cy * 2, 0.5 * cx * 2, (0.5 * cy + thd) * 2, (0.5 * cx + thd) * 2)
        return block * 4
    if fstype == 3:
        return (0.5 * cy * 2, 0.5 * cx * 2, 0.5 * cy * 2 + thd, 0.5 * cx * 2 + thd,
                0.5 * cy * 2, 0.5 * cx * 2, (0.5 * cy + thd) * 2, (0.5 * cx + thd) * 2,
                0.5 * cy * 2, 0.5 * cx * 2, 0.5 * cy * 2, 0.5 * cx * 2,
                0.5 * cy * 2, 0.5 * cx * 2, (0.5 * cy) * 2, (0.5 * cx) * 2)
    wall_y, wall_x = Ly / 0.7, Lx / 0.7
    return (0.5 * cy, 0.5 * cx, 0.5 * cy + thd, 0.5 * cx + thd,
            0.5 * cy * 2, 0.5 * cx * 2, (0.5 * cy + thd) * 2, (0.5 * cx + thd) * 2,
            wall_y, wall_x, wall_y, wall_x, wall_y, wall_x, wall_y, wall_x)


def distribute(total: list[float], factors: tuple[float, ...], cs_width: float,
               ms_width: float, *, halves: bool) -> dict[str, Any]:
    """Column strip and middle strip moments; ``halves`` splits the remainder over two halves."""
    cs = [moment * factor for moment, factor in zip(total, factors)]
    ms = [(moment - share) / 2 if halves else moment - share for moment, share in zip(total, cs)]
    return {
        "total": total, "factor": list(factors), "msFactor": [1 - factor for factor in factors],
        "csWidth": cs_width, "cs": cs, "csPerM": [1000 / cs_width * value for value in cs],
        "msWidth": ms_width, "ms": ms, "msPerM": [1000 / ms_width * value for value in ms],
    }


def _custom_factors(inputs: dict[str, Any], prefix: str, label: str) -> tuple[float, ...]:
    values = []
    for index, position in enumerate(POSITIONS, start=1):
        value = _number(inputs, f"{prefix}{index}", f"{label}, {position}")
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{label}, {position} ({prefix}{index}) must be between 0 and 1")
        values.append(value)
    return tuple(values)


def _distribution_ratio(factors: tuple[float, ...], coefficients: tuple[float, ...]) -> float:
    """Largest departure from the Table 6.9.5.3 ranges; 1.0 at a range limit."""
    worst = 0.0
    for factor, coefficient, kind in zip(factors, coefficients, POSITION_KIND):
        if coefficient == 0:
            continue
        low, high = DISTRIBUTION_RANGES[kind]
        ratio = math.inf if factor <= 0 else max(low / factor, factor / high)
        worst = max(worst, ratio)
    return worst


# ---------------------------------------------------------------------------
#  Optional flexure
# ---------------------------------------------------------------------------
def _bar_layer(inputs: dict[str, Any], prefix: str, label: str) -> tuple[float, float, float]:
    bar = _from_set(inputs, f"bar{prefix}", f"{label} bar size", BAR_SIZES)
    spacing = _positive(inputs, f"s{prefix}", f"{label} bar spacing")
    return bar, spacing, math.pi * bar ** 2 / 4.0 * 1000.0 / spacing


def _governing(strips: list[tuple[str, dict[str, Any], str]], sign: int) -> tuple[float, str]:
    """Largest moment per metre of one sign among the named strip series."""
    best, where = 0.0, "no moment of this sign"
    for name, strip, series in strips:
        for position, value in zip(POSITIONS, strip[series]):
            magnitude = sign * value
            if magnitude > best:
                best, where = magnitude, f"{name}, {position.lower()}"
    return best, where


def _flexure(inputs: dict[str, Any], *, th: float, cover: float, inside: bool, fc: float,
             fsy: float, klass: str, strips: dict[str, dict[str, Any]], fstype: int,
             fctf: float, as_crack: float) -> dict[str, Any]:
    cover_top = _non_negative(inputs, "coverTop", "Cover to top steel")
    interior = [("My*", strips["y"], "csPerM"), ("Mx*", strips["x"], "csPerM")]
    middle = [("My*", strips["y"], "msPerM"), ("Mx*", strips["x"], "msPerM"),
              ("My* edge strip", strips["edgeY"], "msPerM"),
              ("Mx* edge strip", strips["edgeX"], "msPerM")]
    edge = [("My* edge strip", strips["edgeY"], "csPerM"),
            ("Mx* edge strip", strips["edgeX"], "csPerM")]
    demand = {"Ct": _governing(interior, -1), "Cb": _governing(interior, 1),
              "Mt": _governing(middle, -1), "Mb": _governing(middle, 1),
              "Et": _governing(edge, -1), "Eb": _governing(edge, 1)}
    # An edge beam carries the edge column strip (type 3); a wall carries it (type 4).
    present = {key: key[0] != "E" or fstype in (1, 2) for key in FLEXURE_LAYERS}
    s_max = min(300.0, 2.0 * th)
    locations = []
    for key, label in FLEXURE_LAYERS.items():
        if not present[key]:
            continue
        bar, spacing, As = _bar_layer(inputs, key, label)
        face_cover = cover_top if key.endswith("t") else cover
        d = th - face_cover - (bar if inside else 0.0) - bar / 2.0
        if d <= 0:
            raise ValueError(f"{label}: cover and bar size leave no positive effective depth")
        capacity = section_capacity(As=As, d=d, fc=fc, fsy=fsy, klass=klass)
        as_min = max(as_crack, MIN_STEEL_COEFF * (th / d) ** 2 * fctf / fsy * 1000.0 * d)
        moment, where = demand[key]
        locations.append({
            "key": key, "label": label, "bar": bar, "spacing": spacing, "As": As, "d": d,
            "Mstar": moment, "governs": where, **capacity, "AsMin": as_min, "sMax": s_max,
            "ratioMoment": _ratio(moment, capacity["phiMu"]),
            "ratioDuctility": capacity["ku"] / KU_LIMIT,
            "ratioMinimum": _ratio(as_min, As),
            "ratioSpacing": spacing / s_max,
        })
    return {"coverTop": cover_top, "sMax": s_max, "locations": locations}


# ---------------------------------------------------------------------------
#  Calculation
# ---------------------------------------------------------------------------
def compute(inputs: dict[str, Any]) -> dict[str, Any]:
    fc = _number(inputs, "fc", "Concrete strength f'c")
    if not FC_MIN <= fc <= FC_MAX:
        raise ValueError(f"Concrete strength f'c (fc) must be between {FC_MIN:g} and "
                         f"{FC_MAX:g} MPa (Cl 1.1.2)")
    th = _positive(inputs, "th", "Slab thickness th")
    span_y = _positive(inputs, "Ly", "Longer span Ly")
    span_x = _positive(inputs, "Lx", "Shorter span Lx")
    over_y = _non_negative(inputs, "Oy", "Edge overhang Oy")
    over_x = _non_negative(inputs, "Ox", "Edge overhang Ox")
    col_y = _positive(inputs, "Cy", "Column dimension Cy")
    col_x = _positive(inputs, "Cx", "Column dimension Cx")
    has_drop = _option(inputs, "hasDrop", "Drop panels", ("Y", "N")) == "Y"
    slab_code = _option(inputs, "slabType", "Slab type", tuple(SLAB_TYPES))
    limit = _option(inputs, "limitStrip", "Limit interior column strip to L/2", ("Y", "N")) == "Y"
    reo = _option(inputs, "reo", "Reinforcement ductility class", ("N", "L"))
    wdl = _non_negative(inputs, "wdl", "Dead load wdl")
    wsdl = _non_negative(inputs, "wsdl", "Superimposed dead load wsdl")
    wll = _non_negative(inputs, "wll", "Live load wll")
    load_type = _option(inputs, "loadType", "Live load type", tuple(LOAD_TYPES))
    span_type = _option(inputs, "spanType", "Span type for deflection", tuple(SPAN_TYPES))
    bar = _from_set(inputs, "bar", "Nominal bar size", BAR_SIZES)
    cover = _non_negative(inputs, "cover", "Cover to bottom steel")
    inside = _option(inputs, "insideLayer", "Base ds on inside layer", ("Y", "N")) == "Y"
    Ast = _positive(inputs, "Ast", "Tensile steel Ast")
    fsy = _from_set(inputs, "fsy", "Yield strength fsy", YIELD_STRENGTHS)
    dc = _non_negative(inputs, "dc", "Depth to compression steel dc")
    Asc = _non_negative(inputs, "Asc", "Compression steel Asc")
    use_fcmi = _option(inputs, "useFcmi", "Use fcmi curve", ("Y", "N")) == "Y"
    density = _positive(inputs, "density", "Concrete density")
    lef_total = _positive(inputs, "lefDelta", "Total deflection limit Lef/Delta")
    lef_inc = _positive(inputs, "lefDeltaInc", "Incremental deflection limit Lef/Delta")
    enabled = inputs.get("checks") if isinstance(inputs.get("checks"), dict) else {}
    custom_supports = bool(enabled.get("customSupports"))
    custom_distribution = bool(enabled.get("customDistribution"))
    custom = ({key: _non_negative(inputs, field, f"Custom support length {SUPPORT_LABELS[key]}")
               for key, field in CUSTOM_SUPPORT_FIELDS.items()} if custom_supports else {})

    warnings: list[str] = []
    swapped = span_x > span_y
    if swapped:
        span_y, span_x, over_y, over_x, col_y, col_x = (span_x, span_y, over_x, over_y,
                                                        col_x, col_y)
        custom = {key.replace("y", "#").replace("x", "y").replace("#", "x"): value
                  for key, value in custom.items()}
        warnings.append("The entered Ly was shorter than Lx; the two directions (spans, "
                        "overhangs, column dimensions and custom supports) have been swapped "
                        "so that Ly >= Lx.")
    Ly, Lx, Oy, Ox, Cy, Cx = span_y, span_x, over_y, over_x, col_y, col_x
    if Cy >= Ly or Cx >= Lx:
        raise ValueError("Column dimensions (Cy, Cx) must be smaller than the spans")
    ds = th - cover - (bar if inside else 0.0) - bar / 2
    if ds <= 0:
        raise ValueError("Cover and bar size leave no positive effective depth ds")
    if dc >= ds:
        raise ValueError("Depth to compression steel dc must be less than ds")
    fstype = SLAB_TYPES[slab_code]

    # Geometry, Analysis!D12:H22.
    thd = DROP_DEPTH_RATIO * th if has_drop else 0.0
    drop_y, drop_x = excel_roundup_10(Ly / 6), excel_roundup_10(Lx / 6)
    description = WORKBOOK_TYPE_TEXT[fstype] + (
        f", drop panel size 2*DLy = {excel_text0(2 * drop_y)}mm, 2*DLx = "
        f"{excel_text0(2 * drop_x)}mm, Thickness (inc drop) = {excel_text0(th + thd)}mm "
        f"({excel_text0(thd)}mm drop)" if has_drop else "")

    # Loading, Analysis!D28:H31.
    g = wdl + wsdl
    Fd = max(1.35 * g, 1.2 * g + 1.5 * wll)
    lc135 = 1.35 * g > 1.2 * g + 1.5 * wll
    self_weight = th / 1000 * SELF_WEIGHT_DENSITY
    loads = {"wdl": wdl, "wsdl": wsdl, "g": g, "wll": wll, "selfWeight": self_weight,
             "Fd": Fd, "lc135Governs": lc135, "case": "1.35G" if lc135 else "1.2G + 1.5Q",
             "loadType": load_type, "psiS": PSI_SHORT[load_type], "psiL": PSI_LONG[load_type],
             "liveMoreThanTwiceDead": wll > 2 * g}
    if wdl < self_weight:
        warnings.append(f"The dead load wdl = {wdl:.2f} kPa is less than the slab self weight "
                        f"{self_weight:.2f} kPa (25 kN/m3); wdl must include self weight.")

    # Support lengths and effective spans, Cl 6.10.4.2, Analysis!D36:H39 and D95:H98.
    table = support_table(fstype, Cy, Cx, thd, Ly, Lx)
    offset = 2 if has_drop else 0
    supports = (dict(custom) if custom_supports else
                {key: table[column - 1 + offset] for key, column in SUPPORT_COLUMNS.items()})
    wall_edge = fstype == 4 and not custom_supports
    spans: dict[str, Any] = {"raw": {}, "floorApplied": []}
    for key in SUPPORT_KEYS:
        span = Ly if key[2] == "y" else Lx
        raw = span - 0.7 * supports[key]
        lo_key = "Lo" + key[2:]
        spans["raw"][lo_key] = raw
        if wall_edge and key.endswith("e"):
            spans[lo_key] = 0.0
        elif raw < LO_MIN_RATIO * span:
            spans[lo_key] = LO_MIN_RATIO * span
            spans["floorApplied"].append(lo_key)
        else:
            spans[lo_key] = raw
    if spans["floorApplied"]:
        warnings.append("Lo = L - 0.7 (a_sup1 + a_sup2) fell below 0.65 L for "
                        f"{', '.join(spans['floorApplied'])}; Lo = 0.65 L has been used "
                        "(Cl 6.10.4.2).")
    spans["wallEdge"] = wall_edge
    Loy1, Loy, Lox1, Lox = spans["Loy1"], spans["Loy"], spans["Lox1"], spans["Lox"]
    Loy1e, Loye, Lox1e, Loxe = spans["Loy1e"], spans["Loye"], spans["Lox1e"], spans["Loxe"]

    # Total static moments, Eq 6.10.4.2, Analysis!C44:H45 and C102:H104.
    Ltxe, Ltye = Lx / 2 + Ox, Ly / 2 + Oy
    static = {
        "Moy1": Fd * Lx * Loy1 ** 2 / 8e9, "Moy": Fd * Lx * Loy ** 2 / 8e9,
        "Mox1": Fd * Ly * Lox1 ** 2 / 8e9, "Mox": Fd * Ly * Lox ** 2 / 8e9,
        "Ltxe": Ltxe, "Ltye": Ltye,
        "Moy1e": Fd * Ltxe * Loy1e ** 2 / 8e9, "Moye": Fd * Ltxe * Loye ** 2 / 8e9,
        "Mox1e": Fd * Ltye * Lox1e ** 2 / 8e9, "Moxe": Fd * Ltye * Loxe ** 2 / 8e9,
    }

    # Design strip moments, Table 6.10.4.3 and Table 6.9.5.3, Analysis!D48:I126.
    coeff = COEFF[fstype]
    if custom_distribution:
        column_factors = _custom_factors(inputs, "cf", "Column strip factor")
        edge_factors = _custom_factors(inputs, "ef", "Edge column strip factor")
    else:
        column_factors, edge_factors = COEFF_COLUMN[fstype], COEFF_EDGE[fstype]

    def totals(first: float, middle: float) -> list[float]:
        return [(first if index < 3 else middle) * c for index, c in enumerate(coeff)]

    Ltxx = min(Lx / 2, Ly / 2) if limit else Lx / 2
    Ltyy = min(Ly / 2, Lx / 2) if limit else Ly / 2
    Ltxxe, Ltyye = Ltxe - Lx / 4, Ltye - Ly / 4
    strips = {
        "y": {"span": Ly, "width": Lx,
              **distribute(totals(static["Moy1"], static["Moy"]), column_factors, Ltxx,
                           (Lx - Ltxx) / 2, halves=True)},
        "x": {"span": Lx, "width": Ly,
              **distribute(totals(static["Mox1"], static["Mox"]), column_factors, Ltyy,
                           (Ly - Ltyy) / 2, halves=True)},
        "edgeY": {"span": Ly, "width": Ltxe,
                  **distribute(totals(static["Moy1e"], static["Moye"]), edge_factors, Ltxxe,
                               Ltxe - Ltxxe, halves=False)},
        "edgeX": {"span": Lx, "width": Ltye,
                  **distribute(totals(static["Mox1e"], static["Moxe"]), edge_factors, Ltyye,
                               Ltye - Ltyye, halves=False)},
    }
    for strip in strips.values():
        strip["firstInteriorGoverns"] = strip["total"][2] <= strip["total"][3]
    if not limit and Lx != Ly:
        warnings.append("The interior column strip is Lt/2 wide. WRH recommends limiting it to "
                        "L/2 where the spans differ (select 'Limit interior column strip').")
    for name, over, span in (("Oy", Oy, Ly), ("Ox", Ox, Lx)):
        if over > span / 4:
            warnings.append(f"Edge overhang {name} = {over:.0f} mm exceeds L/4 = {span / 4:.0f} mm, "
                            "the workbook's limit for the edge strip layout.")
    if fstype == 1 and (Oy > supports["asy1"] or Ox > supports["asx1"]):
        warnings.append("The exterior edge is unrestrained and overhangs the supports: "
                        "calculate the cantilever moments separately (Analysis!E128).")
    if fstype == 3:
        warnings.append("The edge column strips include the edge beams, which must be designed "
                        "for the edge column strip moments.")

    analysis = {
        "fstype": fstype, "slabType": slab_code, "typeLabel": SLAB_TYPE_LABELS[fstype],
        "description": description, "coefficients": list(coeff), "limitStrip": limit,
        "spanRatio": Ly / Lx, "spanDepth": max(Lox / th, Loy / th),
        "customSupports": custom_supports, "customDistribution": custom_distribution,
    }
    geometry = {"Ly": Ly, "Lx": Lx, "Oy": Oy, "Ox": Ox, "Cy": Cy, "Cx": Cx, "th": th,
                "hasDrop": has_drop, "thd": thd, "dropY": drop_y, "dropX": drop_x,
                "swapped": swapped}

    # Cl 6.10.4.5 moment transferred to interior columns (for punching shear).
    def transfer(Lt: float, lo_long: float, lo_short: float) -> float:
        return MV_COEFF * ((MV_DEAD * g + MV_LIVE * wll) * Lt * lo_long ** 2
                           - MV_DEAD * g * Lt * lo_short ** 2) / 1e9

    transfer_moments = {
        "firstY": transfer(Lx, max(Loy1, Loy), min(Loy1, Loy)),
        "interiorY": transfer(Lx, Loy, Loy),
        "firstX": transfer(Ly, max(Lox1, Lox), min(Lox1, Lox)),
        "interiorX": transfer(Ly, Lox, Lox),
    }

    # Minimum strength requirements, Cl 9.1.1(a), Analysis!D164.
    fctf = 0.6 * math.sqrt(fc)
    ast_min = MIN_STEEL_COEFF * (th / ds) ** 2 * fctf / fsy * 1000 * ds
    minimum = {"fctf": fctf, "ds": ds, "Astmin": ast_min, "Ast": Ast}

    # Deemed-to-comply span-to-depth, Cl 9.4.4.1, Analysis!I171:G193.
    fcmi = fcmi_curve(fc) if use_fcmi else fc
    Ec = ec_from_fcmi(fcmi, density)
    n = ES / Ec
    p, pc, delp = Ast / 1000 / ds, Asc / 1000 / ds, dc / ds
    term = n * p + (n - 1) * pc
    ku = math.sqrt(term ** 2 + 2 * (n * p + (n - 1) * pc * delp)) - term
    NA = ku * ds
    comp_depth = NA - bar / 2 - (bar if inside else 0.0)
    asc_ignored = comp_depth < dc
    if asc_ignored and Asc > 0:
        warnings.append("Compression steel lies in the tension zone and is ignored for kcs.")
    kcs = max(0.8, 2 - 1.2 * ((0.0 if asc_ignored else Asc) / Ast))
    psi_s, psi_l = PSI_SHORT[load_type], PSI_LONG[load_type]
    Fdef = (1 + kcs) * g + (psi_s + psi_l * kcs) * wll
    Fdefi = kcs * g + (psi_s + psi_l * kcs) * wll
    k4 = K4[span_type]
    lo_deflection = (max(Lox1, Loy1, Lox1e, Loy1e) if span_type == "E"
                     else max(Lox, Loy, Loxe, Loye))
    lef_y, lef_x = min(Ly - Cy + th, Ly), min(Lx - Cx + th, Lx)
    Lef = max(lef_y, lef_x)

    def d_required(length: float, k3: float, limit_ratio: float, load: float) -> float:
        if load <= 0:
            return 0.0
        return length / (k3 * k4 * (Ec / limit_ratio / (load / 1000)) ** (1 / 3))

    k3 = K3_DROP if has_drop else K3_NO_DROP
    layer = (bar if inside else 0.0) + bar / 2 + cover
    wb = {
        "dmin": d_required(lo_deflection, K3_NO_DROP, lef_total, Fdef),
        "dminDrop": d_required(lo_deflection, K3_DROP, lef_total, Fdef),
        "dmini": d_required(lo_deflection, K3_NO_DROP, lef_inc, Fdefi),
        "dminiDrop": d_required(lo_deflection, K3_DROP, lef_inc, Fdefi),
    }
    wb.update({"thmin": layer + wb["dmin"], "thminDrop": layer + wb["dminDrop"],
               "thmini": layer + wb["dmini"], "thminiDrop": layer + wb["dminiDrop"]})
    wb["slabOk"] = (max(wb["thminDrop"], wb["thminiDrop"]) <= th if has_drop
                    else max(wb["thmin"], wb["thmini"]) <= th)
    dmin = d_required(Lef, k3, lef_total, Fdef)
    dmini = d_required(Lef, k3, lef_inc, Fdefi)
    deflection = {
        "fcmi": fcmi, "useFcmi": use_fcmi, "density": density, "Ec": Ec, "n": n,
        "p": p, "pc": pc, "dcds": delp, "ku": ku, "NA": NA, "compDepth": comp_depth,
        "ascIgnored": asc_ignored, "kcs": kcs, "Fdef": Fdef, "Fdefi": Fdefi,
        "spanType": span_type, "k3": k3, "k4": k4, "lefDelta": lef_total, "lefDeltaInc": lef_inc,
        "LefY": lef_y, "LefX": lef_x, "Lef": Lef, "LoWorkbook": lo_deflection,
        "dmin": dmin, "dmini": dmini, "thmin": layer + dmin, "thmini": layer + dmini,
        "ds": ds, "Ast": Ast, "Asc": Asc, "dc": dc, "workbook": wb,
    }

    util = {
        "deflectionTotal": _ratio(dmin, ds),
        "deflectionIncremental": _ratio(dmini, ds),
        "minimumSteel": _ratio(ast_min, Ast),
        "spanRatio": Ly / Lx / SPAN_RATIO_LIMIT,
        "liveLoadRatio": _ratio(wll, 2 * g),
        "liveLoadDeflection": _ratio(wll, g),
        "ductilityClass": math.inf if reo == "L" else 0.0,
    }
    if custom_distribution:
        util["distributionRange"] = max(_distribution_ratio(column_factors, coeff),
                                        _distribution_ratio(edge_factors, coeff))
        if util["distributionRange"] > 1.0:
            warnings.append("A custom column strip factor lies outside the Table 6.9.5.3 range.")
    if reo == "L":
        warnings.append("Class L reinforcement must not be used as flexural reinforcement with "
                        "the simplified method (Cl 6.10.4.1(i)).")
    if util["spanRatio"] > 1.0:
        warnings.append(f"Ly/Lx = {Ly / Lx:.2f} exceeds 2.0, outside Cl 6.10.4.1(c).")
    if loads["liveMoreThanTwiceDead"]:
        warnings.append("The live load exceeds twice the dead load, outside Cl 6.10.4.1(g).")
    if util["liveLoadDeflection"] > 1.0:
        warnings.append("The live load exceeds the dead load, outside the deemed-to-comply "
                        "span-to-depth method (Cl 9.4.4.1).")

    shrinkage = None
    if enabled.get("shrinkage"):
        restraint = _option(inputs, "restraint", "Degree of restraint", tuple(SHRINKAGE_RATIOS))
        ratio = SHRINKAGE_RATIOS[restraint]
        shrinkage = {"restraint": restraint, "label": SHRINKAGE_LABELS[restraint],
                     "p": ratio, "AsCrack": TWO_WAY_SHRINKAGE_SHARE * ratio * th * 1000.0}
    flexure = None
    if enabled.get("flexure"):
        flexure = _flexure(inputs, th=th, cover=cover, inside=inside, fc=fc, fsy=fsy,
                           klass=reo, strips=strips, fstype=fstype, fctf=fctf,
                           as_crack=shrinkage["AsCrack"] if shrinkage else 0.0)
        governing = {key: max(item[key] for item in flexure["locations"])
                     for key in ("ratioMoment", "ratioDuctility", "ratioMinimum", "ratioSpacing")}
        util.update({"flexure": governing["ratioMoment"],
                     "ductility": governing["ratioDuctility"],
                     "flexuralMinimum": governing["ratioMinimum"],
                     "barSpacing": governing["ratioSpacing"]})
    elif shrinkage:
        util["shrinkage"] = _ratio(shrinkage["AsCrack"], Ast)

    finite = [value for value in util.values() if math.isfinite(value)]
    worst = max(finite) if finite else 0.0
    return {
        "module": MODULE_ID, "version": VERSION,
        "inputs": {"fc": fc, "th": th, "Ly": Ly, "Lx": Lx, "Oy": Oy, "Ox": Ox, "Cy": Cy,
                   "Cx": Cx, "slabType": slab_code, "hasDrop": has_drop, "reo": reo,
                   "fsy": fsy, "bar": bar, "cover": cover, "insideLayer": inside},
        "geometry": geometry, "loads": loads, "analysis": analysis, "supports": supports,
        "spans": spans, "static": static, "strips": strips, "transfer": transfer_moments,
        "minimum": minimum, "deflection": deflection, "flexure": flexure,
        "shrinkage": shrinkage, "util": util, "worstUtil": worst,
        "checks": {key: True for key in util},
        "warnings": warnings, "assumptions": list(ASSUMPTIONS),
        "limitations": list(LIMITATIONS),
    }
