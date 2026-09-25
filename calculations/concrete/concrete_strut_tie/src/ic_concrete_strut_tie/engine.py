"""AS 3600:2018 (Amendments 1 and 2) strut-and-tie engine for a single bottle-shaped strut.

Working units are N, mm and MPa.  Forces arrive from the form in kN and are
converted once, at the input boundary.

The design basis is a transcription of the retained Structural Toolkit workbook
``Concrete_NonFlexural_504.xls`` (STRUT & TIE V5.04, sheet ``Design`` with the
derived variables on ``Settings``).  The workbook's ``FindAngle`` macro
(``Range("angerror").GoalSeek``) is replaced by a deterministic bounded scan and
bisection on the same residual, ``theta - theta_az = 0``.
"""

from __future__ import annotations

import math
from typing import Any, Callable

from .version import VERSION

MODULE_ID = "concrete-strut-tie"

FC_MIN, FC_MAX = 20.0, 120.0  # Cl 1.1.2, Design!E25
FC_DEVELOPMENT_MAX = 65.0  # Cl 13.1.2.2, Design!K110
PHI_STRUT = 0.65  # Table 2.2.4 struts and nodes, Design!E126
PHI_TIE = 0.85  # Table 2.2.4 ties and bursting reinforcement, Design!E201
PHI_BEARING = 0.6  # Table 2.2.2, Design!E218
TAN_ALPHA_STRENGTH_MIN = 0.2  # Cl 7.2.4(b), Design!E138
TAN_ALPHA_SERVICE_MIN = 0.5  # Cl 7.2.4(a), Design!E142
TAN_ALPHA_BURST = 0.5  # Design!E136, reinforcement-required test
BETA_S_MIN, BETA_S_MAX = 0.3, 1.0  # Eq 7.2.2
MIN_STRUT_ANGLE = 30.0  # Cl 7.1, Design!G33
ONE_WAY_MIN_ANGLE = 40.0  # Design!C70
ANGLE_TOLERANCE = 0.001  # degrees, Design!G33
MAX_BAR = 132.0  # k2 = (132 - db) / 100 must stay positive

CRACK_CLASSES = {"M": ("Minor", 350.0), "O": ("Moderate", 250.0), "S": ("Strong", 200.0),
                 "C": ("Custom", None)}
NODE_TYPES = {
    "CCC": (1.0, "Nodal zone bounded by struts"),
    "CCT": (0.8, "Nodal zone bounded by two or more struts with a single tie passing "
                 "through the node"),
    "CTT": (0.6, "Nodal zone having two or more ties passing through the node"),
}
THETA_MODES = {"S": "Solved so that theta = theta_az (FindAngle)",
               "G": "Geometric, tan^-1(D / Lstrut)", "M": "Manual"}
CALC_MANUAL = ("C", "M")
DZ_MODES = {"C": "Calculated, 50% development length + cover",
            "O": "Developed outside the support (dz = 0)", "M": "Manual"}
BEARING_MODES = {"C": "Strut vertical component Cv*", "M": "Manual B*"}
AREA_MODES = {"D": "A1 = A2 = bc Lr", "M": "Manual A1 and A2"}
TIE_HEIGHT_MODES = {"H": "Hydrostatic node, u = dc cos(theta)", "M": "Manual u"}
YIELD_STRENGTHS = (400.0, 500.0)
BAR_CLASS = {500.0: "N", 400.0: "Y"}
BUNDLE_PERCENT = {1: 100.0, 2: 100.0, 3: 120.0, 4: 133.0}  # Cl 13.1.7, Design!E112

THETA_SCAN_STEP = 0.05  # degrees
THETA_SOLVER_ITERATIONS = 200

ASSUMPTIONS = [
    "A single bottle-shaped strut runs between a support node on the tie and a loaded node, "
    "within a panel of horizontal length Lstrut, depth D and thickness bc.",
    "C*, Cserv, T*, Vr* and Vr.serv are design actions taken from a strut-and-tie model "
    "prepared by the designer; the module does not form load combinations.",
    "Vr* is an additional vertical load, such as a uniform load, carried by the vertical "
    "bursting bars in conjunction with the strut.",
    "Unless a manual value is given the strut depth dc is dc.max, the depth that fully "
    "utilises the strut; the strut is then verified by the support length Lrg <= Lr.",
    "Bursting reinforcement is orthogonal: vertical bars at gamma1 = 90 - theta and horizontal "
    "bars at gamma2 = theta to the strut axis, counted over the bursting length lb.",
    "Capacity reduction factors are fixed at 0.65 (struts and nodes), 0.85 (ties and "
    "bursting reinforcement) and 0.6 (bearing).",
]

LIMITATIONS = [
    "Transcribed from Structural Toolkit STRUT & TIE V5.04. Independent engineering review "
    "has not been completed and the module is not approved for design.",
    "Only one strut, its end nodes and one tie are checked. The overall truss, load paths, "
    "other struts and ties, and equilibrium of the model are the designer's responsibility.",
    "The nodal stress sigma_o is entered by the user unless the optional nodal face check is "
    "enabled. Bearing B* is independent of the strut-and-tie calculation.",
    "Tie anchorage is used only to size the development zone dz; bar detailing, laps, "
    "confinement of the node and minimum wall reinforcement are not checked.",
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


def _option(inputs: dict[str, Any], key: str, label: str, permitted: Any) -> str:
    raw = inputs.get(key)
    # Excel compares text case-insensitively; the saved workbook stores 'y' for useref2.
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


def _bar(inputs: dict[str, Any], key: str, label: str) -> float:
    value = _non_negative(inputs, key, label)
    if value >= MAX_BAR:
        raise ValueError(f"{label} ({key}) must be less than {MAX_BAR:g} mm")
    return value


def _manual(inputs: dict[str, Any], mode_key: str, value_key: str, label: str) -> float:
    """0.0 for a calculated value, reproducing the workbook's blank-cell convention."""
    mode = _option(inputs, mode_key, f"{label} mode", CALC_MANUAL)
    return _positive(inputs, value_key, label) if mode == "M" else 0.0


def _ratio(action: float, capacity: float) -> float:
    if not math.isfinite(capacity) or capacity <= 0:
        return math.inf if action > 0 else 0.0
    return action / capacity


def spacing_class(spacing: float) -> str:
    """Crack control class satisfied by a bar spacing, Settings!N85."""
    if spacing <= 200:
        return "Strong"
    if spacing <= 300:
        return "Moderate"
    if spacing <= 350:
        return "Minor"
    return "None"


def stress_class(fsi: float) -> str:
    """Crack control class satisfied by a steel stress limit, Settings!N56."""
    if fsi <= 200:
        return "Strong"
    if fsi <= 250:
        return "Moderate"
    if fsi <= 350:
        return "Minor"
    return "None"


# ---------------------------------------------------------------------------
#  Strut geometry, Fig 7.2.4(A)
# ---------------------------------------------------------------------------
def strut_state(theta: float, *, Cstar: float, fc: float, bc: float, Lstrut: float, D: float,
                a_manual: float = 0.0, z_manual: float = 0.0, dc_manual: float = 0.0,
                betas_manual: float = 0.0) -> dict[str, float]:
    """Every strut quantity that depends on the adopted angle ``theta`` (degrees)."""
    angr = theta * math.pi / 180.0
    betas_calc = max(BETA_S_MIN, min(1.0 / (1.0 + 0.66 * (1.0 / math.tan(angr)) ** 2),
                                     BETA_S_MAX))
    betas = max(BETA_S_MIN, min(BETA_S_MAX, betas_manual if betas_manual else betas_calc))
    Ca = PHI_STRUT * betas * 0.9 * fc
    dcmax = Cstar / Ca / bc
    dc = dc_manual if dc_manual else dcmax
    w = dc * math.sin(angr)
    omega = dc * math.cos(angr)
    w2 = dc / 2.0 / math.sin(angr)
    w1 = w2 - w / 2.0
    a_calc = Lstrut - 2.0 * w1
    z_calc = D - omega
    a = a_manual if a_manual else a_calc
    z = z_manual if z_manual else z_calc
    theta_az = math.atan(z / a) * 180.0 / math.pi if a > 0 and z > 0 else math.nan
    return {"theta": theta, "angr": angr, "betasCalc": betas_calc, "betas": betas, "Ca": Ca,
            "dcmax": dcmax, "dc": dc, "w": w, "omega": omega, "w2": w2, "w1": w1,
            "aCalc": a_calc, "zCalc": z_calc, "a": a, "z": z, "thetaAz": theta_az}


def solve_theta(evaluate: Callable[[float], dict[str, float]]) -> dict[str, Any]:
    """Find theta = theta_az(theta), replacing the workbook's GoalSeek.

    The scan runs down from 90 degrees and bisects the first sign change of
    ``theta - theta_az``, so the steepest compatible strut is returned.
    """
    def residual(theta: float) -> float:
        value = evaluate(theta)["thetaAz"]
        return theta - value if math.isfinite(value) else math.nan

    steps = int(round(90.0 / THETA_SCAN_STEP))
    upper, g_upper = None, math.nan
    for index in range(1, steps):
        theta = 90.0 - index * THETA_SCAN_STEP
        g = residual(theta)
        if not math.isfinite(g):
            upper, g_upper = None, math.nan
            continue
        if g == 0.0:
            return {"converged": True, "theta": theta, "iterations": index, "reason": ""}
        if upper is not None and (g < 0) != (g_upper < 0):
            low, high, g_low = theta, upper, g
            iterations = 0
            while iterations < THETA_SOLVER_ITERATIONS and high - low > 1e-13:
                middle = 0.5 * (low + high)
                g_mid = residual(middle)
                if not math.isfinite(g_mid):
                    break
                if (g_mid < 0) == (g_low < 0):
                    low, g_low = middle, g_mid
                else:
                    high = middle
                iterations += 1
            return {"converged": True, "theta": 0.5 * (low + high),
                    "iterations": index + iterations, "reason": ""}
        upper, g_upper = theta, g
    return {"converged": False, "theta": math.nan, "iterations": steps,
            "reason": "No strut angle between 0 and 90 degrees satisfies theta = "
                      "tan^-1(z / a) for the entered geometry"}


# ---------------------------------------------------------------------------
#  Anchorage, Cl 13.1.2.2
# ---------------------------------------------------------------------------
def development(*, db: float, fsy: float, fc: float, k1: float, cd: float, percent: float,
                epoxy: bool, lightweight: bool, slip: bool, cogged: bool) -> dict[str, float]:
    k2 = (132.0 - db) / 100.0
    k3 = 0.0 if db == 0 else min(max(1.0 - 0.15 * (cd - db) / db, 0.7), 1.0)
    basic = 0.5 * k1 * k3 * fsy * db / (k2 * math.sqrt(min(fc, FC_DEVELOPMENT_MAX)))
    minimum = 0.058 * fsy * k1 * db
    full = (percent / 100.0 * max(basic, minimum) * (1.5 if epoxy else 1.0)
            * (1.3 if lightweight else 1.0) * (1.3 if slip else 1.0))
    developed = (0.5 if cogged else 1.0) * full
    return {"db": db, "fsy": fsy, "k1": k1, "k2": k2, "k3": k3, "basic": basic,
            "minimum": minimum, "full": full, "developed": developed, "half": 0.5 * developed}


# ---------------------------------------------------------------------------
#  Calculation
# ---------------------------------------------------------------------------
def compute(inputs: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(inputs, dict):
        raise ValueError("An input dictionary is required")

    # -- Actions, Design!E20:E24 ---------------------------------------------
    Cstar = _positive(inputs, "Cstar", "Strut compression C*") * 1e3
    Cserv = _non_negative(inputs, "Cserv", "Strut compression serviceability Cserv") * 1e3
    if Cserv > Cstar:
        raise ValueError("Strut compression serviceability Cserv must not exceed C* "
                         "(Design!E18 'Error - Cserv > C*')")
    Tstar = _non_negative(inputs, "Tstar", "Tie tension T*") * 1e3
    Vrstar = _non_negative(inputs, "Vrstar", "Additional vertical load Vr*") * 1e3
    Vrserv = _non_negative(inputs, "Vrserv", "Additional vertical load serviceability Vr.serv") * 1e3

    # -- Geometry, Design!E26:E68 --------------------------------------------
    fc = _number(inputs, "fc", "Concrete strength f'c")
    if not FC_MIN <= fc <= FC_MAX:
        raise ValueError(f"Concrete strength f'c (fc) must be between {FC_MIN:g} and "
                         f"{FC_MAX:g} MPa (Cl 1.1.2)")
    Lstrut = _positive(inputs, "Lstrut", "Horizontal length of strut Lstrut")
    D = _positive(inputs, "D", "Depth of panel D")
    bc = _positive(inputs, "bc", "Width of strut bc")
    Lr = _positive(inputs, "Lr", "Horizontal reaction length Lr")
    theta_mode = _option(inputs, "thetaMode", "Strut angle mode", THETA_MODES)
    a_manual = _manual(inputs, "aMode", "aManual", "Strut horizontal distance a")
    z_manual = _manual(inputs, "zMode", "zManual", "Strut vertical distance z")
    dc_manual = _manual(inputs, "dcMode", "dcManual", "Depth of strut dc")
    lb_manual = _manual(inputs, "lbMode", "lbManual", "Length of bursting zone lb")
    betas_manual = _manual(inputs, "betasMode", "betasManual", "Strut efficiency factor betas")
    tana_manual = _manual(inputs, "tanAlphaMode", "tanAlphaManual", "Strength tan alpha")
    tanas_manual = _manual(inputs, "tanAlphaServMode", "tanAlphaServManual",
                           "Serviceability tan alpha")

    def evaluate(theta: float) -> dict[str, float]:
        return strut_state(theta, Cstar=Cstar, fc=fc, bc=bc, Lstrut=Lstrut, D=D,
                           a_manual=a_manual, z_manual=z_manual, dc_manual=dc_manual,
                           betas_manual=betas_manual)

    warnings: list[str] = []
    unattainable: list[str] = []
    theta_geometric = math.atan(D / Lstrut) * 180.0 / math.pi
    solver = {"converged": True, "iterations": 0, "reason": "", "method": ""}
    if theta_mode == "M":
        theta = _number(inputs, "theta", "Manual strut angle theta")
        if not 0.0 < theta < 90.0:
            raise ValueError("Manual strut angle theta (theta) must be between 0 and 90 degrees")
        solver["method"] = "manual"
    elif theta_mode == "G":
        theta = theta_geometric
        solver["method"] = "geometric"
    elif a_manual and z_manual:
        theta = math.atan(z_manual / a_manual) * 180.0 / math.pi
        solver["method"] = "direct, a and z manual"
    elif not a_manual and not z_manual:
        # With a and z both calculated, theta_az(theta) = theta exactly at tan^-1(D / Lstrut).
        theta = theta_geometric
        solver["method"] = "direct, a and z calculated"
    else:
        found = solve_theta(evaluate)
        solver.update({key: found[key] for key in ("converged", "iterations", "reason")})
        solver["method"] = "scan and bisection"
        theta = found["theta"] if found["converged"] else theta_geometric
        if not found["converged"]:
            unattainable.append(f"Strut angle (Fig 7.2.2): {found['reason']}; "
                                "tan^-1(D / Lstrut) has been used for the workings")

    state = evaluate(theta)
    if state["a"] <= 0:
        raise ValueError("The strut geometry gives no positive horizontal distance a; check "
                         "Lstrut, dc and the manual a")
    if state["z"] <= 0:
        raise ValueError("The strut geometry gives no positive vertical distance z; check D, "
                         "dc and the manual z")
    angr, dc, dcmax = state["angr"], state["dc"], state["dcmax"]
    gamma1_deg = 90.0 - theta
    gamma1 = gamma1_deg * math.pi / 180.0
    gamma2_deg = theta
    gamma2 = gamma2_deg * math.pi / 180.0
    sin_g1, sin_g2 = math.sin(gamma1), math.sin(gamma2)
    theta_az = state["thetaAz"]
    angle_error = theta - theta_az
    compatible = abs(angle_error) <= ANGLE_TOLERANCE
    if not compatible and not unattainable:
        unattainable.append(f"Strut angle (Fig 7.2.2): theta = {theta:.3f} deg differs from "
                            f"theta_az = tan^-1(z / a) = {theta_az:.3f} deg")

    Ls = math.sqrt(state["a"] ** 2 + state["z"] ** 2)
    lb_calc = max(0.0, Ls - dc)
    lb = lb_manual if lb_manual else lb_calc
    if lb <= 0:
        unattainable.append("Bursting zone (Eq 7.2.4(4)): dc is not less than the strut length "
                            "Ls, so no bottle can form within the panel")
    lb1, lb2 = lb * sin_g1, lb * sin_g2
    if a_manual or z_manual or lb_manual:
        warnings.append("Manual strut geometry values are entered (Design!D41); confirm them "
                        "against a drawn strut-and-tie model.")
    if dc_manual and dc > dcmax:
        warnings.append("dc exceeds dc.max: the strut is not at full capacity (Design!G68).")
    if betas_manual and betas_manual != state["betas"]:
        warnings.append("The manual strut efficiency factor was limited to 0.3 <= betas <= 1.0.")

    # -- Anchorage and development zone, Design!E97:E119 ----------------------
    epoxy = _option(inputs, "ek", "Epoxy coated bars", ("Y", "N")) == "Y"
    lightweight = _option(inputs, "lk", "Lightweight concrete", ("Y", "N")) == "Y"
    slip = _option(inputs, "sk", "Slip formed element", ("Y", "N")) == "Y"
    cogged = _option(inputs, "cogged", "Cogged bars", ("Y", "N")) == "Y"
    below = _non_negative(inputs, "below", "Concrete cast below bars")
    bundle = _number(inputs, "bundle", "Bars in bundle")
    if bundle not in BUNDLE_PERCENT:
        raise ValueError("Bars in bundle (bundle) must be 1, 2, 3 or 4 (Cl 13.1.7)")
    cover = _non_negative(inputs, "cover", "Minimum cover")
    covera = _non_negative(inputs, "covera", "Clear distance between bars")
    dz_mode = _option(inputs, "dzMode", "Development zone mode", DZ_MODES)

    # -- Bursting reinforcement, Design!E72:H86 --------------------------------
    crack = _option(inputs, "crack", "Crack control", CRACK_CLASSES)
    if crack == "C":
        fsi = _positive(inputs, "fsic", "Custom steel stress limit fsi")
    else:
        fsi = float(CRACK_CLASSES[crack][1])
    bar1 = _bar(inputs, "bar1", "Vertical bar size")
    cts1 = _positive(inputs, "cts1", "Vertical bar centres")
    layer1 = _positive(inputs, "layer1", "Vertical bar layers")
    fsy1 = _from_set(inputs, "fsy1", "Vertical bar yield strength", YIELD_STRENGTHS)
    bar2 = _bar(inputs, "bar2", "Horizontal bar size")
    cts2 = _positive(inputs, "cts2", "Horizontal bar centres")
    layer2 = _positive(inputs, "layer2", "Horizontal bar layers")
    fsy2 = _from_set(inputs, "fsy2", "Horizontal bar yield strength", YIELD_STRENGTHS)
    use_ref2 = _option(inputs, "useRef2", "Cracking check to reference 2", ("Y", "N")) == "Y"

    k1 = 1.3 if below > 300 else 1.0
    cd = min(covera / 2.0, cover)
    percent = BUNDLE_PERCENT[int(bundle)]
    tie_bar = _bar(inputs, "tieBar", "Tie bar size")
    tie_n = _non_negative(inputs, "tieBars", "Number of tie bars per layer")
    tie_layers = _positive(inputs, "tieLayers", "Tie bar layers")
    fsy = _from_set(inputs, "fsy", "Tie yield strength", YIELD_STRENGTHS)
    common = {"fc": fc, "k1": k1, "cd": cd, "percent": percent, "epoxy": epoxy,
              "lightweight": lightweight, "slip": slip, "cogged": cogged}
    dev_h = development(db=bar2, fsy=fsy2, **common)
    dev_t = development(db=tie_bar, fsy=fsy, **common)
    dz_calc = max(dev_h["half"], dev_t["half"])
    if dz_mode == "M":
        dz = _positive(inputs, "dzManual", "Manual development zone dz")
        if dz < dz_calc + cover:
            warnings.append(f"The manual development zone dz = {dz:.0f} mm is less than 50% of "
                            f"the development length plus cover, {dz_calc + cover:.0f} mm "
                            "(Cl 7.3.3).")
    elif dz_mode == "O":
        dz = 0.0
    else:
        dz = dz_calc + cover
    if fc > FC_DEVELOPMENT_MAX:
        warnings.append("f'c is limited to 65 MPa in the development length (Cl 13.1.2.2).")
    anchorage = {"ek": epoxy, "lk": lightweight, "sk": slip, "cogged": cogged, "below": below,
                 "bundle": int(bundle), "percent": percent, "cover": cover, "covera": covera,
                 "cd": cd, "k1": k1, "horizontal": dev_h, "tie": dev_t, "dzCalc": dz_calc,
                 "dzMode": dz_mode, "dz": dz, "fcDevelopment": min(fc, FC_DEVELOPMENT_MAX)}

    # -- Strut depth and support, Design!E63:E68 -------------------------------
    Lrg = dcmax * math.sin(angr) + dz
    dcg = (Lr - dz) / math.sin(angr)
    Cmax = state["Ca"] * bc * dc
    Cvstar = Cstar * math.sin(angr)
    Chstar = Cstar * math.cos(angr)

    As1 = math.pi * bar1 ** 2 / 4.0 * layer1
    As2 = math.pi * bar2 ** 2 / 4.0 * layer2
    Am1 = As1 * 1000.0 / cts1
    Am2 = As2 * 1000.0 / cts2
    Asi1 = Am1 * lb1 / 1000.0
    Asi2 = Am2 * lb2 / 1000.0
    one_way = Asi1 <= 0 or Asi2 <= 0

    # -- Bursting forces, Design!E136:E193 ------------------------------------
    tana = max(tana_manual, TAN_ALPHA_STRENGTH_MIN) if tana_manual else TAN_ALPHA_STRENGTH_MIN
    tanas = max(tanas_manual, TAN_ALPHA_SERVICE_MIN) if tanas_manual else TAN_ALPHA_SERVICE_MIN

    Tb = Cstar * tana
    Tb1 = Tb * sin_g1 + Vrstar
    Tb2 = Tb * sin_g2
    Asvr = Vrstar / PHI_TIE / fsy1

    def spacing(required: float, provided: float, length: float) -> tuple[float, float]:
        if length <= 0:
            return math.inf, 0.0
        per_metre = required / length * 1000.0
        return per_metre, (0.0 if provided == 0 else 1000.0 / (per_metre / provided))

    strength = {"tanAlpha": tana, "Tb": Tb, "Tb1": Tb1, "Tb2": Tb2, "Asvr": Asvr,
                "AsTotal": Tb / PHI_TIE / min(fsy1, fsy2),
                "As1": Tb1 / PHI_TIE / fsy1, "As2": Tb2 / PHI_TIE / fsy2}
    strength["Am1"], strength["cts1"] = spacing(strength["As1"], As1, lb1)
    strength["Am2"], strength["cts2"] = spacing(strength["As2"], As2, lb2)
    strength["phiTb1"] = (PHI_TIE * (Asi1 - Asvr) * fsy1) * sin_g1
    strength["phiTb2"] = PHI_TIE * Asi2 * fsy2 * sin_g2
    strength["phiTb"] = strength["phiTb1"] + strength["phiTb2"]

    Tbs = Cserv * tanas
    Tbs1 = Tbs * sin_g1 + Vrserv
    Tbs2 = Tbs * sin_g2
    Asvrs = Vrserv / fsi
    service = {"tanAlpha": tanas, "fsi": fsi, "Tb": Tbs, "Tb1": Tbs1, "Tb2": Tbs2,
               "Asvr": Asvrs, "AsTotal": Tbs / fsi, "As1": Tbs1 / fsi, "As2": Tbs2 / fsi}
    service["Am1"], service["cts1"] = spacing(service["As1"], As1, lb1)
    service["Am2"], service["cts2"] = spacing(service["As2"], As2, lb2)
    service["Tbs1"] = ((Asi1 - Asvrs) * fsi) * sin_g1
    service["Tbs2"] = (Asi2 * fsi) * sin_g2
    service["TbsCapacity"] = service["Tbs1"] + service["Tbs2"]

    fct = 0.36 * math.sqrt(fc)
    Tbcr = 0.7 * bc * lb * fct
    Tbb = Cstar * TAN_ALPHA_BURST
    limit = 0.5 * Tbcr
    required = Tbb > limit
    stress1 = PHI_TIE * fsy1 if use_ref2 else fsi
    stress2 = PHI_TIE * fsy2 if use_ref2 else fsi
    cracking = {"fct": fct, "Tbcr": Tbcr, "Tbcr1": Tbcr * sin_g1 + Vrstar,
                "Tbcr2": Tbcr * sin_g2, "Tbb": Tbb, "limit": limit, "required": required,
                "useRef2": use_ref2,
                "AsTotal": Tbcr / (PHI_TIE * min(fsy1, fsy2) if use_ref2 else fsi)}
    cracking["As1"] = cracking["Tbcr1"] / stress1
    cracking["As2"] = cracking["Tbcr2"] / stress2
    cracking["Am1"], cracking["cts1"] = spacing(cracking["As1"], As1, lb1)
    cracking["Am2"], cracking["cts2"] = spacing(cracking["As2"], As2, lb2)
    cracking["Tbsc1"] = stress1 * (Asi1 - Asvr) * sin_g1
    cracking["Tbsc2"] = stress2 * Asi2 * sin_g2
    cracking["TbscCapacity"] = cracking["Tbsc1"] + cracking["Tbsc2"]

    candidates1 = {"Strength": strength["cts1"], "Serviceability": service["cts1"],
                   "Cracking": cracking["cts1"]}
    candidates2 = {"Strength": strength["cts2"], "Serviceability": service["cts2"],
                   "Cracking": cracking["cts2"]}
    governing1 = min(candidates1, key=lambda key: candidates1[key])
    governing2 = min(candidates2, key=lambda key: candidates2[key])
    reinforcement = {
        "crack": crack, "crackLabel": CRACK_CLASSES[crack][0], "fsi": fsi,
        "fsiClass": stress_class(fsi),
        "bar1": bar1, "cts1": cts1, "layer1": layer1, "fsy1": fsy1, "class1": BAR_CLASS[fsy1],
        "bar2": bar2, "cts2": cts2, "layer2": layer2, "fsy2": fsy2, "class2": BAR_CLASS[fsy2],
        "As1": As1, "As2": As2, "Am1": Am1, "Am2": Am2, "lb1": lb1, "lb2": lb2,
        "bars1": lb1 / cts1 * layer1, "bars2": lb2 / cts2 * layer2,
        "Asi1": Asi1, "Asi2": Asi2, "gamma1": gamma1_deg, "gamma2": gamma2_deg,
        "spacingClass1": spacing_class(cts1), "spacingClass2": spacing_class(cts2),
        "oneWay": one_way,
        "requiredAm1": max(strength["Am1"], service["Am1"], cracking["Am1"]),
        "requiredAm2": max(strength["Am2"], service["Am2"], cracking["Am2"]),
        "requiredCts1": candidates1[governing1], "requiredCts2": candidates2[governing2],
        "governing1": governing1, "governing2": governing2,
    }

    # -- Tension tie, Cl 7.3 --------------------------------------------------
    As3 = math.pi * tie_bar ** 2 / 4.0 * tie_layers
    Ast = tie_n * As3
    tie_required = Tstar / PHI_TIE / fsy
    tie = {"Tstar": Tstar, "bar": tie_bar, "bars": tie_n, "layers": tie_layers, "fsy": fsy,
           "class": BAR_CLASS[fsy], "As3": As3, "Ast": Ast, "AstRequired": tie_required,
           "barsRequired": 0.0 if As3 == 0 else tie_required / As3,
           "Ta": PHI_TIE * fsy, "phiT": PHI_TIE * fsy * Ast}

    # -- Node, Cl 7.4.2 and bearing, Cl 12.6 ----------------------------------
    ntype = _option(inputs, "ntype", "Node type", NODE_TYPES)
    betan, node_label = NODE_TYPES[ntype]
    sigma_o = _non_negative(inputs, "stresso", "Nodal stress sigma_o")
    sigma3 = PHI_STRUT * betan * 0.9 * fc
    node = {"type": ntype, "label": node_label, "betan": betan, "stresso": sigma_o,
            "sigma3": sigma3}

    bearing_mode = _option(inputs, "bearingMode", "Bearing force mode", BEARING_MODES)
    Bstar = Cvstar if bearing_mode == "C" else _non_negative(inputs, "Bstar", "Bearing B*") * 1e3
    area_mode = _option(inputs, "areaMode", "Bearing area mode", AREA_MODES)
    if area_mode == "M":
        A1 = _positive(inputs, "A1", "Bearing area A1")
        A2 = _positive(inputs, "A2", "Supporting area A2")
        if A2 < A1:
            raise ValueError("Supporting area A2 must not be less than the bearing area A1 "
                             "(Cl 12.6)")
    else:
        A1 = A2 = bc * Lr
    fBmax = PHI_BEARING * 1.8 * fc
    fBa = PHI_BEARING * 0.9 * fc * math.sqrt(A2 / A1)
    fB = min(fBmax, fBa)
    bearing = {"mode": bearing_mode, "Bstar": Bstar, "A1": A1, "A2": A2, "areaMode": area_mode,
               "Bs": Bstar / A1, "fBmax": fBmax, "fBa": fBa, "fB": fB, "phiB": fB * A1,
               "phi": PHI_BEARING}

    # -- Utilisation -----------------------------------------------------------
    util: dict[str, float] = {
        "strut": dcmax / dc,
        "supportLength": _ratio(Lrg, Lr),
        "strutAngle": MIN_STRUT_ANGLE / theta,
        "angleCompatibility": 0.0 if compatible else math.inf,
        "bottleLength": dc / Ls,
    }
    if required:
        util["burstingStrength"] = _ratio(Tb, strength["phiTb"])
        util["burstingService"] = _ratio(Tbs, service["TbsCapacity"])
        util["burstingCracking"] = _ratio(Tbcr, cracking["TbscCapacity"])
        if As1 == 0 and As2 == 0:
            unattainable.append("Bursting reinforcement (Cl 7.2.4): reinforcement is required "
                                "but none is provided")
        elif one_way:
            provided = gamma1_deg if Asi1 > 0 else gamma2_deg
            util["oneWayAngle"] = ONE_WAY_MIN_ANGLE / provided
            warnings.append("Bursting reinforcement is provided in one direction only "
                            "(Design!C70).")
    else:
        util["burstingThreshold"] = _ratio(Tbb, limit)
    util["verticalLoadSteel"] = _ratio(max(Asvr, Asvrs), Asi1)
    util["tie"] = _ratio(Tstar, tie["phiT"])
    util["node"] = _ratio(sigma_o, sigma3)
    util["bearing"] = _ratio(Bstar, bearing["phiB"])

    enabled = inputs.get("checks") if isinstance(inputs.get("checks"), dict) else {}
    faces = None
    if enabled.get("nodeFaces"):
        height_mode = _option(inputs, "tieHeightMode", "Tie face height mode", TIE_HEIGHT_MODES)
        height = (state["omega"] if height_mode == "H"
                  else _positive(inputs, "tieHeight", "Tie face height u"))
        faces = {"tieHeightMode": height_mode, "tieHeight": height,
                 "sigmaStrut": Cstar / (bc * dc),
                 "sigmaBearing": Cvstar / (bc * Lr), "sigmaTie": Tstar / (bc * height),
                 "sigma3": sigma3}
        util["nodeStrutFace"] = _ratio(faces["sigmaStrut"], sigma3)
        util["nodeBearingFace"] = _ratio(faces["sigmaBearing"], sigma3)
        util["nodeTieFace"] = _ratio(faces["sigmaTie"], sigma3)

    finite = [value for value in util.values() if math.isfinite(value)]
    checks = {key: True for key in util}
    geometry = {
        "Lstrut": Lstrut, "D": D, "bc": bc, "Lr": Lr, "thetaMode": theta_mode,
        "thetaGeometric": theta_geometric, "theta": theta, "angr": angr,
        "gamma1": gamma1_deg, "gamma1Rad": gamma1, "sinGamma1": sin_g1,
        "gamma2": gamma2_deg, "gamma2Rad": gamma2, "sinGamma2": sin_g2,
        "w": state["w"], "omega": state["omega"], "w2": state["w2"], "w1": state["w1"],
        "aCalc": state["aCalc"], "zCalc": state["zCalc"], "a": state["a"], "z": state["z"],
        "aManual": bool(a_manual), "zManual": bool(z_manual), "lbManual": bool(lb_manual),
        "dcManual": bool(dc_manual),
        "Ls": Ls, "lbCalc": lb_calc, "lb": lb, "lb1": lb1, "lb2": lb2,
        "thetaAz": theta_az, "angleError": angle_error, "compatible": compatible,
        "Lrg": Lrg, "dcg": dcg, "solver": solver,
    }
    strut = {"Cstar": Cstar, "Cserv": Cserv, "Cvstar": Cvstar, "Chstar": Chstar,
             "betasCalc": state["betasCalc"], "betas": state["betas"],
             "betasManual": bool(betas_manual), "phi": PHI_STRUT, "Ca": state["Ca"],
             "dcmax": dcmax, "dc": dc, "Cmax": Cmax}
    return {
        "module": MODULE_ID, "version": VERSION,
        "inputs": {"Cstar": Cstar, "Cserv": Cserv, "Tstar": Tstar, "Vrstar": Vrstar,
                   "Vrserv": Vrserv, "fc": fc, "Lstrut": Lstrut, "D": D, "bc": bc, "Lr": Lr},
        "geometry": geometry, "strut": strut, "anchorage": anchorage,
        "reinforcement": reinforcement, "strength": strength, "service": service,
        "cracking": cracking, "tie": tie, "node": node, "bearing": bearing, "nodeFaces": faces,
        "factors": {"phiStrut": PHI_STRUT, "phiTie": PHI_TIE, "phiBearing": PHI_BEARING},
        "util": util, "worstUtil": max(finite) if finite else 0.0, "checks": checks,
        "unattainable": unattainable, "warnings": warnings,
        "assumptions": list(ASSUMPTIONS), "limitations": list(LIMITATIONS),
    }
