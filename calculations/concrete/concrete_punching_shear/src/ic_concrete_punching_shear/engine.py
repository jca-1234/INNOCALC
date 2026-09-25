"""AS 3600:2018 (Amendments 1 and 2) punching shear engine for slabs, Section 9.3.

Working units are N, mm and MPa.  Actions are entered in kN and kNm and converted
once at the input boundary; the Cl 6.10.4.5 area loads are in kPa.

The design basis is a transcription of the retained Structural Toolkit workbook
``Concrete_Punching_506.xls`` (PUNCHING SHEAR V5.06, sheets ``Design`` and
``Settings``).  The GoalSeek macro ``Module1.RecalcDom`` that averages dom around a
perimeter crossing a spandrel beam is replaced by a bounded bisection.
"""

from __future__ import annotations

import math
from typing import Any, Callable

from .version import VERSION

MODULE_ID = "concrete-punching-shear"

FC_MIN, FC_MAX = 20.0, 120.0  # Cl 1.1.2, Design!F16
DOM_MIN = 20.0  # workbook revision 5.03b
PHI_SHEAR = 0.7  # Table 2.2.2, Design!F46
PHI_INTEGRITY = 0.7  # Design!F91 as cited by the workbook
MAX_FITMENT_SPACING = 300.0  # Design!F64
TIE_SIZES = (0.0, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0)
BAR_SIZES = (10.0, 12.0, 16.0, 20.0, 24.0, 28.0, 32.0, 36.0)
YIELD_STRENGTHS = (500.0, 400.0, 250.0)
POSITIONS = {"I": "internal location", "E": "edge", "C": "corner"}
POSITION_TITLES = {"I": "Interior", "E": "Edge", "C": "Corner"}
SOLVER_ITERATIONS = 200
SOLVER_RESIDUAL = 1e-6

ASSUMPTIONS = [
    "V* is the design punching shear force at the critical shear perimeter and Mv* is the "
    "design bending moment transferred from the slab to the support in the direction of a.",
    "At edge and corner positions the column face is flush with the free edge; a circular "
    "column is tangent to the edge. The critical perimeter runs square to the free edge.",
    "The circular perimeter at an edge or corner uses straight legs from the quadrant to the "
    "edge (workbook setting Curved = N), which the workbook author notes is conservative.",
    "A spandrel beam of width bw runs along the free edge. The mean depth dom is averaged "
    "along the perimeter using do in the spandrel and in the slab unless the spandrel is "
    "ignored for dom.",
    "Closed fitments are fully anchored and extend along the torsion strip or spandrel as "
    "Cl 9.3.6 requires. A shear head, when selected, is designed separately.",
    "Openings and other critical perimeter reductions are entered as an ineffective length.",
]

LIMITATIONS = [
    "Transcribed from Structural Toolkit PUNCHING SHEAR V5.06. Independent engineering review "
    "has not been completed and the module is not approved for design.",
    "Only one direction of moment transfer is checked; check the orthogonal direction "
    "separately.",
    "The shear head itself, flexural reinforcement, and the anchorage and extent of the "
    "fitments along the torsion strip are not designed.",
    "Columns set back from a free edge, re-entrant corners and non-rectangular loaded areas "
    "are not modelled.",
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
    # Excel compares text case-insensitively; the saved workbook stores 'n', 'y' and 'l'.
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


def _ratio(action: float, capacity: float) -> float:
    if capacity <= 0:
        return math.inf if action > 0 else 0.0
    return action / capacity


# ---------------------------------------------------------------------------
#  Critical shear perimeter geometry (Settings!S42:AE95)
# ---------------------------------------------------------------------------
def rectangular_perimeters(*, pX: float, pY: float, domc: float, bw: float, do_slab: float,
                           do_spandrel: float, both_sides: bool) -> dict[str, float]:
    """Edge and corner perimeters and depth-weighted surfaces, Settings!T64:U67.

    pX is the column face parallel to the (spandrel) edge and pY the face away from it.
    """
    half = domc / 2.0
    if both_sides:
        corner_u = bw + (pY + half - bw) + bw + (pX + half - bw)
        if (half + pX) < bw or (half + pY) < bw:
            corner_surface = (pX + half + pY + half) * do_spandrel
        else:
            corner_surface = (bw * do_spandrel + (pY + half - bw) * do_slab
                              + bw * do_spandrel + (pX + half - bw) * do_slab)
    else:
        corner_u = bw + (pY + half - bw) + (pX + half)
        if (half + pY) < bw:
            corner_surface = (pX + half + pY + half) * do_spandrel
        else:
            corner_surface = bw * do_spandrel + (pY + half - bw) * do_slab + (pX + half) * do_slab
    edge_u = 2.0 * (bw + (pY + half - bw)) + (pX + domc)
    if (half + pY) < bw:
        edge_surface = (pX + domc + pY * 2.0 + domc) * do_spandrel
    else:
        edge_surface = 2.0 * (bw * do_spandrel + (pY + half - bw) * do_slab) + (pX + domc) * do_slab
    return {"cornerU": corner_u, "cornerSurface": corner_surface,
            "domCorner": corner_surface / corner_u, "edgeU": edge_u,
            "edgeSurface": edge_surface, "domEdge": edge_surface / edge_u}


def circular_perimeters(*, D: float, domc: float, bw: float, do_slab: float,
                        do_spandrel: float, both_sides: bool, corner: bool) -> dict[str, float]:
    """Straight-leg (Curved = N) edge and corner perimeters, Settings!T72:AE95."""
    r_col = D / 2.0
    r_dom = D / 2.0 + domc / 2.0
    full = math.pi * 2.0 * r_dom
    top_theta = math.acos(r_col / r_dom)
    if bw <= D / 2.0:
        spandrel_theta = 0.0
    elif bw >= D + domc / 2.0:
        spandrel_theta = math.radians(90.0)
    else:
        spandrel_theta = math.radians(90.0 - math.degrees(math.acos((bw - r_col) / r_dom)))
    straight = min(bw, r_col)
    curved = spandrel_theta * r_dom
    if corner and not both_sides and r_dom * math.sin(top_theta) + r_col < bw < r_col + r_dom:
        curved2 = math.radians(90.0 - math.degrees(top_theta)
                               - math.degrees(math.acos((bw - r_col) / r_dom))) * r_dom
    else:
        curved2 = 0.0

    edge_curved_slab = full / 2.0 - curved * 2.0
    edge_straight_slab = 2.0 * (D / 2.0 - straight)
    edge_u = full / 2.0 + 2.0 * D / 2.0
    if edge_curved_slab <= 0:
        edge_surface = do_spandrel * curved * 2.0 + D * do_spandrel
    else:
        edge_surface = ((edge_curved_slab + edge_straight_slab) * do_slab
                        + 2.0 * (curved + straight) * do_spandrel)

    corner_u = full / 4.0 + D
    if (domc / 2.0 + D) < bw:
        corner_curved_slab = 0.0
    else:
        corner_curved_slab = full / 4.0 - (2.0 * curved if both_sides else curved)
    if both_sides:
        corner_straight_slab = 2.0 * (D / 2.0 - straight)
        corner_spandrel_curved = min(full / 4.0, curved * 2.0)
    else:
        corner_straight_slab = 0.0 if corner_curved_slab <= 0 else D / 2.0 + (D / 2.0 - straight)
        corner_spandrel_curved = min(full / 4.0, curved)
    if corner_curved_slab <= 0:
        corner_surface = (full / 4.0 + D) * do_spandrel
    else:
        straight_spandrel = straight * 2.0 if both_sides else straight
        corner_surface = ((corner_spandrel_curved + straight_spandrel) * do_spandrel
                          + (corner_curved_slab + corner_straight_slab) * do_slab)
    return {
        "Rcol": r_col, "Rdom": r_dom, "fullLength": full, "topTheta": top_theta,
        "topS": 2.0 * top_theta * r_dom, "spandrelTheta": spandrel_theta,
        "spandrelStraight": straight, "spandrelCurved": curved, "spandrelCurved2": curved2,
        "edgeCurvedSlab": edge_curved_slab, "edgeStraightSlab": edge_straight_slab,
        "edgeU": edge_u, "edgeSurface": edge_surface, "domEdge": edge_surface / edge_u,
        "cornerTheta": math.radians(90.0), "cornerCurvedSlab": corner_curved_slab,
        "cornerCurvedSlab2": -curved2, "cornerStraightSlab": corner_straight_slab,
        "cornerSpandrelCurved": corner_spandrel_curved, "cornerU": corner_u,
        "cornerSurface": corner_surface, "domCorner": corner_surface / corner_u,
    }


def solve_mean_depth(average: Callable[[float], float], low: float,
                     high: float) -> dict[str, Any]:
    """Fixed point dom = average(dom) by bisection, replacing the GoalSeek in RecalcDom.

    ``average`` is a depth-weighted mean of the slab and spandrel depths, so the root lies
    between them.  Where the perimeter jumps across the spandrel boundary there may be no
    exact root; the bisection then converges on the jump and ``exact`` is False.
    """
    low, high = min(low, high), max(low, high)
    if high - low <= 1e-12 * max(1.0, high):
        return {"dom": low, "residual": abs(low - average(low)), "exact": True, "iterations": 0}
    residual_low = low - average(low)
    if abs(residual_low) <= SOLVER_RESIDUAL:
        return {"dom": low, "residual": abs(residual_low), "exact": True, "iterations": 0}
    residual_high = high - average(high)
    if abs(residual_high) <= SOLVER_RESIDUAL:
        return {"dom": high, "residual": abs(residual_high), "exact": True, "iterations": 0}
    iterations = 0
    while iterations < SOLVER_ITERATIONS and high - low > 1e-11 * max(1.0, high):
        iterations += 1
        middle = (low + high) / 2.0
        if middle - average(middle) > 0:
            high = middle
        else:
            low = middle
    dom = (low + high) / 2.0
    residual = abs(dom - average(dom))
    return {"dom": dom, "residual": residual, "exact": residual <= SOLVER_RESIDUAL,
            "iterations": iterations}


# ---------------------------------------------------------------------------
#  Calculation
# ---------------------------------------------------------------------------
def mean_depth_from_layers(Ds: float, cover: float, outer: float, inner: float) -> float:
    """Mean of the outer and inner layer depths (Tedds RC slab design 1.0.21)."""
    return ((Ds - cover - outer / 2.0) + (Ds - cover - outer - inner / 2.0)) / 2.0


def compute(inputs: dict[str, Any]) -> dict[str, Any]:
    enabled = inputs.get("checks") if isinstance(inputs.get("checks"), dict) else {}
    fc = _number(inputs, "fc", "Concrete strength f'c")
    if not FC_MIN <= fc <= FC_MAX:
        raise ValueError(f"Concrete strength f'c (fc) must be between {FC_MIN:g} and "
                         f"{FC_MAX:g} MPa (Cl 1.1.2)")
    V_kN = _non_negative(inputs, "Vstar", "Design shear V*")
    Mv_kNm = _non_negative(inputs, "Mvstar", "Moment transferred Mv*")
    ps = _non_negative(inputs, "ps", "Average prestress sigma.cp")
    Ds = _positive(inputs, "Ds", "Slab depth Ds")
    circular = _yes(inputs, "col", "Circular column")
    pL = _positive(inputs, "pL", "Larger column dimension L")
    pW_input = pL if circular else _positive(inputs, "pW", "Shorter column dimension W")
    if not circular and pL < pW_input:
        raise ValueError("Larger column dimension L (pL) must be at least W (pW)")
    pm_dir = _option(inputs, "pmDir", "Direction of moment", ("L", "W"))
    position = _option(inputs, "pPos", "Position", tuple(POSITIONS))
    face = _option(inputs, "pface", "Face on edge", ("L", "W"))
    both_sides = _yes(inputs, "spanbothsides", "Spandrel both sides of corner")
    shear_head = _yes(inputs, "shearhead", "Shear head")
    spandrel = _yes(inputs, "span", "Spandrel")
    ignore_spandrel = _yes(inputs, "ignorespan", "Ignore spandrel for dom")
    Db = _positive(inputs, "Db", "Spandrel depth Db")
    bw = _positive(inputs, "bw", "Spandrel width bw")
    if spandrel and Ds >= Db:
        raise ValueError("Spandrel depth Db must exceed the slab depth Ds (Design!E22)")
    cover = _non_negative(inputs, "cover", "Cover for y1")
    wcl = _non_negative(inputs, "wcl", "Width of closed fitment")
    dialp = _from_set(inputs, "dialp", "Fitment bar size", TIE_SIZES)
    ctsp = _non_negative(inputs, "ctsp", "Fitment spacing s")
    fyp = _from_set(inputs, "fyp", "Fitment yield strength fsy.f", YIELD_STRENGTHS)
    ineff = _non_negative(inputs, "ineffU", "Ineffective perimeter length")
    N_kN = _non_negative(inputs, "Nstar", "Column reaction N*")
    fsy = _from_set(inputs, "fsy", "Integrity bar yield strength fsy", YIELD_STRENGTHS)
    ductility = _option(inputs, "ductility", "Ductility class", ("N", "L"))
    ibar = _from_set(inputs, "ibar", "Integrity bar size", BAR_SIZES)
    beams = _yes(inputs, "beams", "Beams with shear reinforcement in all spans")
    n_bars = _non_negative(inputs, "nIntegrity", "Integrity bars provided")
    if n_bars != int(n_bars):
        raise ValueError("Integrity bars provided (nIntegrity) must be a whole number")
    pLo = _non_negative(inputs, "pLo", "Larger adjoining span Lo")
    pLod = _non_negative(inputs, "pLod", "Smaller adjoining span Lo'")
    if pLod > pLo:
        raise ValueError("Smaller adjoining span Lo' (pLod) must not exceed Lo (pLo)")
    pLt = _non_negative(inputs, "pLt", "Design strip width Lt")
    Vdl = _non_negative(inputs, "Vdl", "Dead load G")
    Vll = _non_negative(inputs, "Vll", "Live load Q")
    simplified = _yes(inputs, "simplifiedMethod", "Slab designed by the simplified method")

    layers = None
    if enabled.get("effectiveDepth"):
        layer_cover = _non_negative(inputs, "domCover", "Cover to tension reinforcement")
        outer = _from_set(inputs, "barOuter", "Outer layer bar size", BAR_SIZES)
        inner = _from_set(inputs, "barInner", "Inner layer bar size", BAR_SIZES)
        dom = mean_depth_from_layers(Ds, layer_cover, outer, inner)
        layers = {"cover": layer_cover, "outer": outer, "inner": inner,
                  "doOuter": Ds - layer_cover - outer / 2.0,
                  "doInner": Ds - layer_cover - outer - inner / 2.0, "dom": dom}
    else:
        dom = _positive(inputs, "dom", "Slab distance do")
    if not DOM_MIN <= dom < Ds:
        raise ValueError(f"Slab distance do (dom) must be at least {DOM_MIN:g} mm and less "
                         "than the slab depth Ds")

    V, Mv = V_kN * 1000.0, Mv_kNm * 1e6
    warnings: list[str] = []

    # Geometry, Design!D22:I32 and Settings!O22:T57.
    pW = pL if circular else pW_input
    pX = pL if face == "L" else pW
    pY = pW if face == "L" else pL
    do_slab = dom
    coverbar2 = Ds - dom
    dom_required = spandrel and position != "I" and not ignore_spandrel
    if spandrel and position == "I":
        warnings.append("A spandrel beam has been selected at an internal position; the "
                        "internal perimeter is used and only Eq 9.3.4(3) reflects the spandrel.")

    def perimeters(trial: float, do_spandrel: float) -> dict[str, float]:
        if circular:
            return circular_perimeters(D=pL, domc=trial, bw=bw, do_slab=do_slab,
                                       do_spandrel=do_spandrel, both_sides=both_sides,
                                       corner=position == "C")
        return rectangular_perimeters(pX=pX, pY=pY, domc=trial, bw=bw, do_slab=do_slab,
                                      do_spandrel=do_spandrel, both_sides=both_sides)

    solution = None
    if dom_required:
        do_spandrel = Db - coverbar2
        key = "domEdge" if position == "E" else "domCorner"
        solution = solve_mean_depth(lambda trial: perimeters(trial, do_spandrel)[key],
                                    do_slab, do_spandrel)
        domc = solution["dom"]
        if not solution["exact"]:
            warnings.append("No exact mean depth exists for this spandrel width: the critical "
                            "perimeter meets the spandrel boundary. dom is taken where the "
                            "average changes sign (workbook Design!K19:K20).")
    else:
        domc = dom
        do_spandrel = Db - coverbar2 if spandrel else domc
    shape = perimeters(domc, do_spandrel)

    u_internal = math.pi * (pL + domc) if circular else 2.0 * ((pL + domc) + (pW + domc))
    u_value = {"I": u_internal, "E": shape["edgeU"], "C": shape["cornerU"]}[position]
    u = max(0.0, u_value - ineff)
    if ineff > u_value:
        warnings.append("The ineffective portion exceeds the critical shear perimeter "
                        "(Design!F35); u is taken as zero.")
    elif u_value > 0 and ineff / u_value > 0.1:
        warnings.append("The ineffective portion of the shear perimeter exceeds 10% of u; "
                        "confirm the perimeter geometry (Design!F35).")
    edge_note = "" if circular else (" - W on edge" if face == "W" else " - L on edge")
    shape_label = "Circular column on " if circular else "Rectangular column on "
    udesc = shape_label + (POSITIONS[position] + edge_note if position == "E"
                           else POSITIONS[position])

    if circular:
        aL = pL + domc
        aW = aL
        if position != "I":
            warnings.append("For a circular column at an edge or corner the workbook takes "
                            "a = D + dom regardless of the free edge; see TECHNICAL-README C8.")
    elif position == "I":
        aL, aW = pL + domc, pW + domc
    elif position == "C":
        aL, aW = pL + 0.5 * domc, pW + 0.5 * domc
    elif face == "W":
        aL, aW = pL + 0.5 * domc, pW + domc
    else:
        aL, aW = pL + domc, pW + 0.5 * domc
    a = aL if pm_dir == "L" else aW
    beta_h = 1.0 if circular else max(pL, pW) / min(pL, pW)
    geometry = {
        "circular": circular, "position": position, "positionTitle": POSITION_TITLES[position],
        "face": face, "bothSides": both_sides, "spandrel": spandrel,
        "ignoreSpandrel": ignore_spandrel, "pL": pL, "pW": pW, "pX": pX, "pY": pY,
        "Ds": Ds, "Db": Db, "bw": bw, "domInput": dom, "domSource": "layers" if layers else "input",
        "doSlab": do_slab, "doSpandrel": do_spandrel, "coverbar2": coverbar2,
        "domRequired": dom_required, "domc": domc, "solution": solution,
        "uInternal": u_internal, "uEdge": shape["edgeU"], "uCorner": shape["cornerU"],
        "uval": u_value, "ineffU": ineff, "u": u, "udesc": udesc,
        "aL": aL, "aW": aW, "a": a, "pmDir": pm_dir, "betaH": beta_h,
    }
    perimeter = {"circle" if circular else "rectangular": shape}

    # Cl 9.3.3, Design!F46:F56.
    root_fc = math.sqrt(fc)
    fcv_max = 0.34 * root_fc
    fcv1 = 0.17 * (1.0 + 2.0 / beta_h) * root_fc
    fcv = min(fcv1, fcv_max)
    phi = PHI_SHEAR
    phiVuo_plain = phi * u * domc * (fcv + 0.3 * ps)
    phiVuo_max = phi * 0.2 * u * domc * fc
    phiVuo_1 = phi * u * domc * (0.5 * root_fc + 0.3 * ps)
    phiVuo_head = min(phiVuo_max, phiVuo_1)
    phiVuo = phiVuo_head if shear_head else phiVuo_plain
    strength = {"phi": phi, "fcvMax": fcv_max, "fcv1": fcv1, "fcv": fcv, "ps": ps,
                "shearHead": shear_head, "phiVuoPlain": phiVuo_plain, "phiVuoMax": phiVuo_max,
                "phiVuo1": phiVuo_1, "phiVuoHead": phiVuo_head, "phiVuo": phiVuo}

    # Cl 6.10.4.5 minimum transferred moment, Design!F97:F105.
    v1 = 1.2 * Vdl + 0.75 * Vll
    v2 = 1.2 * Vdl
    Mv_min = 0.06 * (v1 * pLt * pLo ** 2 - v2 * pLt * pLod ** 2) / 1000.0
    apply_min = simplified and position == "I"
    M = max(Mv, Mv_min) if apply_min else Mv
    if simplified and position != "I":
        warnings.append("The Cl 6.10.4.5 minimum transferred moment applies at interior "
                        "supports only and has not been applied.")
    elif not simplified and position == "I" and Mv_min > Mv:
        warnings.append(f"Mv* = {Mv_kNm:.1f} kNm is less than the Cl 6.10.4.5 minimum "
                        f"{Mv_min / 1e6:.1f} kNm. The minimum governs where the slab is designed "
                        "by the simplified method (select it to apply).")
    moment = {"Mv": Mv, "MvMin": Mv_min, "Mdesign": M, "applied": apply_min and Mv_min > Mv,
              "simplified": simplified, "v1": v1, "v2": v2, "Lo": pLo, "Lod": pLod, "Lt": pLt,
              "G": Vdl, "Q": Vll, "zero": M == 0}

    def reduced(base: float, denominator: float) -> float:
        if M == 0:
            return base
        if V <= 0 or denominator <= 0:
            return 0.0
        return base / (1.0 + u * M / denominator)

    # Cl 9.3.4(a), Design!F61.
    phiVu_a = reduced(phiVuo, 8.0 * V * a * domc)

    # Closed fitments, Cl 9.3.4(b) to (d), Cl 9.3.5, Cl 9.3.6, Design!F64:F78.
    provided = dialp > 0 and ctsp > 0
    asw_actual = math.pi * dialp ** 2 / 4.0 if provided else 0.0
    max_cts = min(Db, MAX_FITMENT_SPACING) if spandrel else min(Ds, MAX_FITMENT_SPACING)
    if spandrel:
        y1 = max(max(bw - 2.0 * cover - dialp, Db - 2.0 * cover - dialp), 0.0)
    else:
        y1 = max(min(a, max(wcl - dialp, Ds - 2.0 * cover - dialp)), 0.0)
    asw_min = 0.2 * y1 / fyp * ctsp
    less_than_min = y1 == 0 or asw_actual < asw_min
    if not provided:
        error = ""
    elif less_than_min:
        error = "Error - Ligs less than min."
    elif ctsp > max_cts:
        error = f"Error - Lig cts > max. of {max_cts:g}mm"
    else:
        error = ""
    valid = provided and error == ""
    asw = asw_actual if valid else 0.0
    if asw == 0:
        if asw_actual == 0:
            asw0 = "No ligs"
        elif less_than_min:
            asw0 = "Ligs < Min."
        elif ctsp > max_cts:
            asw0 = "Lig cts > Max"
        else:
            asw0 = "??"
    else:
        asw0 = ""
    min_rate = 0.2 * y1 / fyp
    s_max_area = 0.0 if min_rate == 0 else asw / min_rate
    phiVu_b = reduced(1.2 * phiVuo, 2.0 * V * a ** 2) if valid else 0.0
    phiVu_c = reduced(1.2 * phiVuo * (Db / Ds), 2.0 * V * a * bw) if (spandrel and valid) else 0.0
    phiVu_min = phiVu_c if spandrel else phiVu_b
    x = min(Db, bw) if spandrel else min(Ds, a)
    y = max(bw, Db) if spandrel else max(a, Ds)
    phiVu_max = 3.0 * phiVu_min * math.sqrt(x / y)
    if y1 == 0 or ctsp == 0:
        phiVu_d = 0.0
    else:
        phiVu_d = min(max(phiVu_min, phiVu_min * math.sqrt(asw / ctsp / min_rate)), phiVu_max)
    s_for_V = 0.0 if phiVu_min == 0 else asw / (min_rate * (V / phiVu_min) ** 2)
    if dialp == 0:
        ties_label = "None"
    elif not valid:
        ties_label = "Invalid"
    else:
        grade = ("Y" if dialp > 10 else "R") if fyp == 400 else ("R" if fyp == 250 else "N")
        ties_label = f"{grade}{dialp:.0f}-{ctsp:.0f} cts"
    fitments = {
        "provided": provided, "valid": valid, "dialp": dialp, "ctsp": ctsp, "fyp": fyp,
        "cover": cover, "wcl": wcl, "AswActual": asw_actual, "Asw": asw, "y1": y1,
        "maxcts": max_cts, "AswMin": asw_min, "sMaxArea": s_max_area,
        "lessThanMin": less_than_min, "error": error, "Asw0desc": asw0, "label": ties_label,
        "phiVuB": phiVu_b, "phiVuC": phiVu_c, "phiVuMin": phiVu_min, "x": x, "y": y,
        "phiVuMax": phiVu_max, "phiVuD": phiVu_d, "sForVstar": s_for_V,
    }
    if provided and not valid:
        warnings.append(f"The closed fitments do not satisfy Cl 9.3.5 / Cl 9.3.6 ({asw0}) and "
                        "are ignored in the punching strength.")

    # Governing strength for the reinforcement provided.
    if M == 0:
        governing = {"case": "Cl 9.3.3(b)" if shear_head else "Cl 9.3.3(a)",
                     "equation": "Eq 9.3.3(2)" if shear_head else "Eq 9.3.3(1)",
                     "label": "Mv* = 0" + (", shear head" if shear_head else ""),
                     "capacity": phiVuo}
        if valid:
            warnings.append("Closed fitments do not increase the punching strength when "
                            "Mv* = 0 (Cl 9.3.3).")
    elif valid:
        governing = {"case": "Cl 9.3.4(c) and (d)" if spandrel else "Cl 9.3.4(b) and (d)",
                     "equation": "Eq 9.3.4(4)",
                     "label": "Closed fitments in the " + ("spandrel" if spandrel
                                                           else "torsion strip"),
                     "capacity": phiVu_d}
        if phiVu_a > phiVu_d:
            warnings.append("Eq 9.3.4(1) without fitments exceeds the strength with the "
                            "fitments provided; the fitment case has been used (see "
                            "TECHNICAL-README C10).")
    else:
        governing = {"case": "Cl 9.3.4(a)", "equation": "Eq 9.3.4(1)",
                     "label": "No closed fitments", "capacity": phiVu_a}
    if V == 0:
        warnings.append("V* is zero; punching shear does not govern.")
    cases = [
        {"label": label, "equation": equation, "capacity": capacity,
         "ratio": _ratio(V, capacity) if capacity > 0 else None,
         "governs": equation == governing["equation"]}
        for label, equation, capacity in (
            ("Mv* = 0, no shear head", "Eq 9.3.3(1)", phiVuo_plain),
            ("Mv* = 0, shear head", "Eq 9.3.3(2)", phiVuo_head),
            ("(a) No closed fitments", "Eq 9.3.4(1)", phiVu_a),
            ("(b) Minimum fitments, torsion strip", "Eq 9.3.4(2)", phiVu_b),
            ("(c) Minimum fitments, spandrel", "Eq 9.3.4(3)", phiVu_c),
            ("(d) Fitments provided", "Eq 9.3.4(4)", phiVu_d))
    ]
    governing["ratioNoMoment"] = _ratio(V, phiVuo)
    governing["ratioNoFitments"] = _ratio(V, phiVu_a)

    # Integrity reinforcement, Design!F82:F93.
    required = not beams
    area_bar = math.pi * ibar ** 2 / 4.0
    N = N_kN * 1000.0
    as_min = 2.0 * N / (PHI_INTEGRITY * fsy)
    count = as_min / area_bar
    bar_class = ("L" if ductility == "L" else "N") if fsy == 500 else ("Y" if fsy == 400 else "R")
    integrity = {
        "required": required, "N": N, "fsy": fsy, "ductility": ductility, "barClass": bar_class,
        "phi": PHI_INTEGRITY, "ibar": ibar, "Ab": area_bar, "AsMin": as_min,
        "numBars": count, "desc": f"{count:.1f}-{bar_class}{ibar:g}",
        "provided": int(n_bars), "AsProvided": n_bars * area_bar,
    }

    util: dict[str, float] = {"punching": 0.0 if V == 0 else _ratio(V, governing["capacity"])}
    if provided:
        util["fitmentArea"] = math.inf if y1 <= 0 else _ratio(asw_min, asw_actual)
        util["fitmentSpacing"] = ctsp / max_cts
        if not spandrel:
            util["fitmentWidth"] = _ratio(wcl, a)
    if ps > 0:
        util["prestressDepth"] = 0.8 * Ds / dom
        if dom < 0.8 * Ds:
            warnings.append("do is less than 0.8 Ds for a prestressed slab (Design!F16, Cl 1.7).")
    if required:
        util["integrity"] = _ratio(as_min, integrity["AsProvided"])
    finite = [value for value in util.values() if math.isfinite(value)]
    worst = max(finite) if finite else 0.0
    return {
        "module": MODULE_ID, "version": VERSION,
        "inputs": {"fc": fc, "Vstar": V, "Mvstar": Mv, "ps": ps, "Ds": Ds, "dom": dom,
                   "col": "Y" if circular else "N", "pL": pL, "pW": pW, "pmDir": pm_dir,
                   "pPos": position, "pface": face, "shearhead": "Y" if shear_head else "N",
                   "span": "Y" if spandrel else "N", "Db": Db, "bw": bw},
        "layers": layers, "geometry": geometry, "perimeter": perimeter, "strength": strength,
        "moment": moment, "transfer": {"phiVuA": phiVu_a}, "fitments": fitments,
        "integrity": integrity, "governing": governing, "cases": cases,
        "util": util, "worstUtil": worst, "checks": {key: True for key in util},
        "warnings": warnings, "assumptions": list(ASSUMPTIONS),
        "limitations": list(LIMITATIONS),
    }
