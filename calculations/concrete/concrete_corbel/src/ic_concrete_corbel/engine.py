"""AS 3600:2018 (Amendments 1 and 2) reinforced concrete corbel design engine.

Working units are N, mm and MPa throughout.  Forces are supplied by the form in
kN and converted once, here, at the input boundary.

The design basis is a transcription of the retained Structural Toolkit workbook
``Concrete_Corbel_506.xls`` (CORBEL V5.06, sheet ``Design``).  Every capacity
equation below carries the clause the workbook cites.  The workbook solved the
strut width ``dc`` with an Excel ``GoalSeek`` macro; that macro is replaced here
by a bounded bisection on the same residual so the result is deterministic and
reproducible.
"""

from __future__ import annotations

import math
from typing import Any

from .version import VERSION

MODULE_ID = "concrete-corbel"

# AS 3600:2018 Table 8.4.3 interface friction and cohesion constants.
SURFACE_CONDITIONS: dict[str, dict[str, Any]] = {
    "S": {"label": "Smooth cast against formwork", "mu": 0.6, "kco": 0.1},
    "T": {"label": "Trowelled", "mu": 0.6, "kco": 0.2},
    "R": {"label": "Roughened", "mu": 0.7, "kco": 0.4},
    "M": {"label": "Monolithic", "mu": 0.9, "kco": 0.5},
    "O": {"label": "Other - manually assessed", "mu": None, "kco": None},
}

# AS/NZS 1170.0 Table 4.1 long term imposed action factor.  "M" is a manual entry.
LONG_TERM_FACTORS: dict[str, float | None] = {"N": 0.4, "S": 0.6, "M": None}

LOAD_TYPE_LABELS = {"N": "Normal", "S": "Storage", "M": "Manual factor"}

REINFORCEMENT_MODES = {
    "count": "Number of bars across the corbel length",
    "centres": "Bar centres",
    "area": "Steel area",
}

BAR_SIZES = (12.0, 16.0, 20.0, 24.0, 28.0)
YIELD_STRENGTHS = (400.0, 500.0)

# Capacity reduction and node factors held as constants by the workbook.
PHI_STRUT = 0.65  # Table 2.2.4 - strut and node of a strut-and-tie model
PHI_SHEAR = 0.70  # Table 2.2.2(e) - shear friction across an interface
PHI_TIE = 0.85  # Table 2.2.4 - tensile tie of a strut-and-tie model
BETA_N_CCT = 0.80  # Cl 7.4.2(b) - node anchoring one tie

FC_MIN = 20.0  # Cl 1.1.2
FC_MAX = 120.0  # Cl 1.1.2
TAU_ABSOLUTE_LIMIT = 10.0  # Cl 8.4.3 upper bound on the interface shear stress
DEPTH_TO_ECCENTRICITY = 1.7  # Dmin = 1.7 av, corbel proportioning limit

# The workbook drives its GoalSeek to ``Cf* + 0.01 kN - phiCa = 0`` so that the
# solved strut is marginally inside its capacity.  Retained exactly, in newtons.
STRUT_RESIDUAL_OFFSET_N = 10.0
STRUT_SOLVER_ITERATIONS = 200

ASSUMPTIONS = [
    "Actions are unfactored service dead and imposed actions; the module forms the "
    "AS/NZS 1170.0 Cl 4.2.2 strength combinations.",
    "V* acts downwards on the corbel bearing and N* acts outwards as tension on the tie.",
    "The bearing strip runs the full corbel length, so its length bl equals the corbel length b.",
    "Two anchored cross bars of the nominated bar size cross the vertical shear plane "
    "(Asf = 2 Abar) and the shear plane width bf equals the overall depth D.",
    "The strut width dc is sized so that the compression strut is fully utilised; the "
    "resulting strut depth x sets the tie lever arm.",
    "The favourable strut compression contribution of N* is ignored, as in the source workbook.",
]

LIMITATIONS = [
    "Transcribed from Structural Toolkit CORBEL V5.06. Independent engineering review of "
    "this transcription has not been completed and the module is not approved for design.",
    "The node coefficient is fixed at the Cl 7.4.2(b) CCT value of 0.80; CCC and CTT nodes "
    "are not offered.",
    "The AS 3600:2009 tau_u limit is applied unconditionally, matching CORBEL V5.06 after "
    "AS 3600:2018 Amendment 2 reinstated it. The workbook's retired 'limittu' switch is not offered.",
    "Anchorage and development of the tie and cross bars, bearing plate design, the bending "
    "induced in the supporting wall or column, fire, durability and serviceability are excluded.",
    "Corbel lengths other than b = 1000 mm are designed as a discrete corbel; b = 1000 mm is "
    "designed per metre run, reproducing the source workbook's unit switch.",
]


# ---------------------------------------------------------------------------
#  Input reading
# ---------------------------------------------------------------------------
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
    if value not in permitted:
        raise ValueError(f"{label} ({key}) must be one of {', '.join(permitted)}, not '{value}'")
    return value


def _from_set(inputs: dict[str, Any], key: str, label: str, permitted: tuple[float, ...]) -> float:
    value = _number(inputs, key, label)
    if value not in permitted:
        allowed = ", ".join(f"{item:g}" for item in permitted)
        raise ValueError(f"{label} ({key}) must be one of {allowed}, not {value:g}")
    return value


def _ratio(action: float, capacity: float) -> float:
    """Utilisation with the zero and unattainable conventions stated in the README."""
    if not math.isfinite(capacity) or capacity <= 0:
        return math.inf if action > 0 else 0.0
    return action / capacity


# ---------------------------------------------------------------------------
#  Compression strut, Cl 7.2.3
# ---------------------------------------------------------------------------
def strut_state(dc: float, *, lever: float, av: float, b: float, fc: float,
                Vstar: float) -> dict[str, float]:
    """Every strut quantity for one trial strut width ``dc`` (mm).

    All of the workbook's strut cells are explicit functions of ``dc`` alone, so
    this is a pure evaluation and the solver below only has to find its root.
    """
    if not math.isfinite(dc) or dc <= 0:
        raise ValueError("Strut width dc must be a finite value greater than zero")
    H = math.hypot(lever, av)
    if dc / 2.0 >= H:
        raise ValueError("Strut width dc must be less than twice the diagonal length H")
    ang1 = math.atan(av / lever)
    lg = math.sqrt(H * H - (dc / 2.0) ** 2)
    ang2 = math.atan((dc / 2.0) / lg)
    theta = math.pi / 2.0 - (ang1 + ang2)
    if theta <= 0:
        raise ValueError("The corbel eccentricity leaves no positive strut inclination")
    betas = max(0.3, min(1.0, 1.0 / (1.0 + 0.66 / math.tan(theta) ** 2)))
    x = dc / math.cos(theta)
    sigma_max = PHI_STRUT * betas * 0.9 * fc
    phiCa = sigma_max * b * dc
    w = dc * math.sin(theta)
    dl = lever - math.sin(math.pi / 2.0 - theta) * dc / 2.0
    if dl <= 0:
        raise ValueError("The trial strut width leaves no positive strut lever length dl")
    Cf = max(0.0, lg / dl * Vstar)
    return {
        "dc": dc, "H": H, "ang1": ang1, "ang2": ang2, "theta": theta, "betas": betas,
        "x": x, "sigmaMax": sigma_max, "phiCa": phiCa, "w": w, "lg": lg, "dl": dl,
        "Cf": Cf, "residual": Cf + STRUT_RESIDUAL_OFFSET_N - phiCa,
    }


def tie_force(*, Vstar: float, av: float, lever: float, x: float, Ndstar: float) -> float:
    """Cl 7.3.2 horizontal tie force acting at the solved strut depth ``x``."""
    arm = lever - x / 2.0
    if arm <= 0:
        return math.inf
    return Vstar * av / arm + Ndstar


def solve_strut(*, lever: float, av: float, b: float, fc: float,
                Vstar: float) -> dict[str, Any]:
    """Bisect ``Cf*(dc) + 0.01 kN - phiCa(dc) = 0`` between zero and the lever arm.

    Replaces the workbook's ``Range("error").GoalSeek`` macro.  The residual is
    positive as ``dc`` tends to zero because the strut capacity vanishes while the
    strut force stays finite, so a sign change inside the bracket is a genuine root.
    """
    upper = lever * 0.999
    lower = min(1e-6, upper * 1e-9)
    try:
        low_state = strut_state(lower, lever=lever, av=av, b=b, fc=fc, Vstar=Vstar)
        high_state = strut_state(upper, lever=lever, av=av, b=b, fc=fc, Vstar=Vstar)
    except ValueError as exc:
        return {"converged": False, "reason": str(exc), "iterations": 0,
                "bracket": [lower, upper], "state": None}
    if low_state["residual"] <= 0:
        return {"converged": False, "iterations": 0, "bracket": [lower, upper], "state": None,
                "reason": "The strut is adequate at a vanishing width; the corbel geometry or "
                          "actions are outside the transcribed model"}
    if high_state["residual"] > 0:
        return {"converged": False, "iterations": 0, "bracket": [lower, upper], "state": None,
                "reason": "No strut width up to the lever arm can carry the strut force; "
                          "increase f'c, the corbel length or the overall depth"}
    iterations = 0
    while iterations < STRUT_SOLVER_ITERATIONS and (upper - lower) > 1e-12 * lever:
        middle = 0.5 * (lower + upper)
        state = strut_state(middle, lever=lever, av=av, b=b, fc=fc, Vstar=Vstar)
        if state["residual"] > 0:
            lower = middle
        else:
            upper = middle
        iterations += 1
    state = strut_state(0.5 * (lower + upper), lever=lever, av=av, b=b, fc=fc, Vstar=Vstar)
    return {"converged": True, "iterations": iterations, "bracket": [lower, upper],
            "state": state, "reason": ""}


# ---------------------------------------------------------------------------
#  Main calculation
# ---------------------------------------------------------------------------
def compute(inputs: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(inputs, dict):
        raise ValueError("An input dictionary is required")

    # -- Materials and geometry, Design sheet rows 15 to 25 ------------------
    fc = _number(inputs, "fc", "Concrete strength f'c")
    if not FC_MIN <= fc <= FC_MAX:
        raise ValueError(
            f"Concrete strength f'c must be between {FC_MIN:g} and {FC_MAX:g} MPa (Cl 1.1.2)")
    b = _positive(inputs, "b", "Corbel length b")
    df = _positive(inputs, "df", "Corbel depth df")
    D = _positive(inputs, "D", "Overall depth D")
    if D < df:
        raise ValueError("Overall depth D must not be less than the corbel depth df")
    av = _positive(inputs, "av", "Eccentricity av")
    bw = _positive(inputs, "bw", "Bearing strip width bw")
    th = _positive(inputs, "th", "Supporting wall thickness th")
    bl = b  # Design!G17 - the bearing strip runs the full corbel length
    Ab = bw * bl
    Dmin = DEPTH_TO_ECCENTRICITY * av
    per_metre = b == 1000.0

    surface = _option(inputs, "scond", "Corbel casting condition", SURFACE_CONDITIONS)
    if surface == "O":
        mu = _positive(inputs, "mu", "Frictional constant mu")
        kco = _non_negative(inputs, "kco", "Cohesion coefficient kco")
    else:
        mu = float(SURFACE_CONDITIONS[surface]["mu"])
        kco = float(SURFACE_CONDITIONS[surface]["kco"])

    # -- Design actions, Design sheet rows 28 to 35 --------------------------
    Vdl = _non_negative(inputs, "Vdl", "Vertical dead load Vdl") * 1e3
    Vll = _non_negative(inputs, "Vll", "Vertical live load Vll") * 1e3
    Ndl = _non_negative(inputs, "Ndl", "Horizontal dead load Ndl") * 1e3
    Nll = _non_negative(inputs, "Nll", "Horizontal live load Nll") * 1e3
    load_type = _option(inputs, "loadtype", "Load type", LONG_TERM_FACTORS)
    if load_type == "M":
        psiL = _non_negative(inputs, "mlt", "Long term live load factor psi_l")
    else:
        psiL = float(LONG_TERM_FACTORS[load_type])

    Vstar = max(1.35 * Vdl, 1.2 * Vdl + 1.5 * Vll)
    Vcase = "1.35 G" if 1.35 * Vdl > 1.2 * Vdl + 1.5 * Vll else "1.2 G + 1.5 Q"
    Nstar = max(1.35 * Ndl, 1.2 * Ndl + 1.5 * Nll)
    Ncase = "1.35 G" if 1.35 * Ndl > 1.2 * Ndl + 1.5 * Nll else "1.2 G + 1.5 Q"
    Ndstar = max(Nstar, 0.2 * Vstar)  # Cl 12.3(b) minimum horizontal action
    gpt = -max(Ndl + psiL * Nll, 0.2 * (Vdl + psiL * Vll))
    gp = gpt / b  # permanent clamping action across the shear plane, N/mm

    # -- Reinforcement, Design sheet rows 38 to 47 ---------------------------
    bar = _from_set(inputs, "bar", "Bar size", BAR_SIZES)
    fsy = _from_set(inputs, "fsy", "Yield strength fsy", YIELD_STRENGTHS)
    cover = _non_negative(inputs, "cover", "Cover")
    mode = _option(inputs, "reoMode", "Reinforcement entry", REINFORCEMENT_MODES)
    quantity = _positive(inputs, "reoValue", "Reinforcement quantity")
    Abar = math.pi * bar ** 2 / 4.0
    if mode == "count":
        nbars = quantity
        As = nbars * Abar
    elif mode == "centres":
        nbars = b / quantity if per_metre else b / quantity + 1.0
        As = nbars * Abar
    else:
        nbars = 1.0
        As = quantity
    if nbars <= 0 or As <= 0:
        raise ValueError("The reinforcement entry gives no horizontal tie steel")
    if mode == "area":
        cts = b / (As / Abar)
    elif per_metre:
        cts = b / nbars
    elif nbars == 1.0:
        cts = b
    else:
        cts = (b - 2.0 * cover - bar) / (nbars - 1.0)
    if cts <= 0:
        raise ValueError("Cover and bar size leave no room for the tie bars across the corbel")

    lever = D - cover - bar / 2.0  # Design!E69 - depth to the tie
    if lever <= 0:
        raise ValueError("Cover and bar size leave no positive lever arm d = D - cover - db/2")
    fctf = 0.6 * math.sqrt(fc)  # Cl 3.1.1.3
    fct = 0.36 * math.sqrt(fc)  # Cl 3.1.1.3
    Asmin = 0.2 * (D / lever) ** 2 * fctf / fsy * lever * b  # Eq 8.1.6.1(2)

    # -- Bearing, Cl 7.4.2 ---------------------------------------------------
    Bstar = Vstar / Ab
    phiBmax = PHI_STRUT * 1.8 * fc
    phiBa = PHI_STRUT * BETA_N_CCT * 0.9 * fc
    phiB = min(phiBmax, phiBa)

    # -- Shear friction on the vertical face, Cl 8.4.3 -----------------------
    Asf = 2.0 * Abar
    bf = D
    s = cts
    tau_calc = mu * (Asf * fsy / (s * bf) + gp / bf) + kco * fct
    tau_max = 0.2 * fc
    tau = min(tau_max, TAU_ABSOLUTE_LIMIT, tau_calc)
    phiVu = PHI_SHEAR * tau * D * b

    # -- Compression strut, Cl 7.2.3 -----------------------------------------
    strut = solve_strut(lever=lever, av=av, b=b, fc=fc, Vstar=Vstar)
    state = strut["state"]
    unattainable: list[str] = []

    # -- Horizontal tensile tie, Cl 7.3.2 ------------------------------------
    phiFt = PHI_TIE * fsy * As
    if state is None:
        Ftstar = math.inf
        tie_lever = math.nan
        unattainable.append(f"Compression strut (Cl 7.2.3): {strut['reason']}")
    else:
        tie_lever = lever - state["x"] / 2.0
        Ftstar = tie_force(Vstar=Vstar, av=av, lever=lever, x=state["x"], Ndstar=Ndstar)
        if not math.isfinite(Ftstar):
            unattainable.append(
                "Tensile tie (Cl 7.3.2): the solved strut depth leaves no positive tie lever arm")

    if tau <= 0:
        unattainable.append(
            "Shear friction (Cl 8.4.3): the permanent clamping action leaves no positive "
            "interface shear stress tau_u")

    util = {
        "bearing": _ratio(Bstar, phiB),
        "shearFriction": _ratio(Vstar, phiVu),
        "tensileTie": math.inf if not math.isfinite(Ftstar) else _ratio(Ftstar, phiFt),
        "minimumSteel": _ratio(Asmin, As),
        "depthLimit": _ratio(Dmin, D),
        "wallThickness": math.inf if state is None else _ratio(state["w"], th),
    }
    finite = [value for value in util.values() if math.isfinite(value)]

    warnings: list[str] = []
    if df < D / 2.0:
        warnings.append("df is less than D/2; confirm the corbel outline suits the strut model")
    if tau_calc > tau:
        warnings.append(
            "tau_u is limited by min(0.2 f'c, 10 MPa); the unlimited value is "
            f"{tau_calc:.3f} MPa (AS 3600:2009 limit reinstated by AS 3600:2018 Amendment 2)")

    return {
        "module": MODULE_ID,
        "version": VERSION,
        "inputs": {
            "fc": fc, "b": b, "df": df, "D": D, "av": av, "bw": bw, "th": th,
            "scond": surface, "mu": mu, "kco": kco,
            "Vdl": Vdl, "Vll": Vll, "Ndl": Ndl, "Nll": Nll,
            "loadtype": load_type, "psiL": psiL,
            "bar": bar, "fsy": fsy, "cover": cover, "reoMode": mode, "reoValue": quantity,
        },
        "geometry": {"bl": bl, "Ab": Ab, "Dmin": Dmin, "lever": lever, "perMetre": per_metre},
        "material": {"fc": fc, "fctf": fctf, "fct": fct, "fsy": fsy},
        "interface": {"condition": surface, "label": SURFACE_CONDITIONS[surface]["label"],
                      "mu": mu, "kco": kco},
        "loads": {"Vdl": Vdl, "Vll": Vll, "Ndl": Ndl, "Nll": Nll, "psiL": psiL,
                  "Vstar": Vstar, "Vcase": Vcase, "Nstar": Nstar, "Ncase": Ncase,
                  "Ndstar": Ndstar, "gpt": gpt, "gp": gp},
        "reinforcement": {"bar": bar, "Abar": Abar, "nbars": nbars, "cts": cts, "As": As,
                          "Asmin": Asmin, "cover": cover, "mode": mode},
        "bearing": {"Bstar": Bstar, "phiBmax": phiBmax, "phiBa": phiBa, "phiB": phiB,
                    "betan": BETA_N_CCT, "phist": PHI_STRUT},
        "shearFriction": {"Asf": Asf, "bf": bf, "s": s, "tauCalc": tau_calc, "tauMax": tau_max,
                          "tau": tau, "phiVu": phiVu, "phiv": PHI_SHEAR},
        "strut": {"converged": strut["converged"], "iterations": strut["iterations"],
                  "reason": strut["reason"], "bracket": list(strut["bracket"]),
                  **({} if state is None else state)},
        "tie": {"Ftstar": Ftstar, "phiFt": phiFt, "lever": tie_lever, "phis": PHI_TIE},
        "factors": {"phist": PHI_STRUT, "phiv": PHI_SHEAR, "phis": PHI_TIE,
                    "betan": BETA_N_CCT},
        "checks": {"bearing": True, "shearFriction": True, "strut": True, "tensileTie": True,
                   "minimumSteel": True, "depthLimit": True, "wallThickness": True},
        "util": util,
        "worstUtil": max(finite) if finite else 0.0,
        "unattainable": unattainable,
        "warnings": warnings,
        "assumptions": list(ASSUMPTIONS),
        "limitations": list(LIMITATIONS),
    }