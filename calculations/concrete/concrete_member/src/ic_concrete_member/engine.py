"""AS 3600:2018 (Amendments 1 and 2) beam and slab design engine.

Working units are kN, kNm, mm and MPa.  Slab quantities are per metre width (kNm/m,
kN/m, mm2/m).  A positive moment puts the bottom face in tension.

The design basis is a transcription of the retained Structural Toolkit workbook
``Concrete_Member_513.xls`` (CONCRETE MEMBER V5.13): sheets ``Design``, ``Detailed``,
``Shear``, ``Defl``, ``Creep&Shrink``, ``BeamDefl``, ``SlabDefl`` and ``Secondary``.
The engineering routines live in :mod:`section`, :mod:`flexure`, :mod:`materials`,
:mod:`crack`, :mod:`shear`, :mod:`deflection` and :mod:`detailing`; this module reads
and validates inputs, sequences the calculation and assembles the result document.
"""

from __future__ import annotations

import math
from typing import Any

from . import crack, deflection, detailing, flexure, materials, shear
from .common import non_negative, number, option, positive, from_set
from .section import FLANGED, MAX_BARS, SLAB, geometry, reinforcement
from .version import VERSION

MODULE_ID = "concrete-member"
FC_MIN, FC_MAX = 20.0, 120.0  # Cl 1.1.2
BAR_SIZES = (6.0, 8.0, 10.0, 12.0, 16.0, 20.0, 24.0, 28.0, 32.0, 36.0, 40.0)
FITMENT_SIZES = (0.0, 6.0, 8.0, 10.0, 12.0, 16.0)
YIELD_STRENGTHS = (500.0, 400.0, 250.0)
YES_NO = ("Y", "N")

CHECK_LABELS = {
    "flexure": "Bending strength",
    "ductility": "Ductility kuo",
    "minimumSteel": "Minimum strength reinforcement",
    "barSpacing": "Tension bar spacing",
    "crackStress": "Crack control steel stress",
    "crackStressYield": "Crack control stress under G + Q",
    "shear": "Shear strength",
    "shearDetailing": "Shear fitment detailing",
    "torsion": "Torsional strength",
    "torsionReinforcement": "Torsion fitment detailing",
    "webCrushing": "Web crushing, shear and torsion",
    "longitudinalTension": "Longitudinal tension from shear",
    "longitudinalCompression": "Longitudinal force, compression face",
    "shearMethod": "Simplified shear method applicability",
    "deflectionTotal": "Deemed-to-comply depth, total",
    "deflectionIncremental": "Deemed-to-comply depth, incremental",
    "liveLoadLimit": "Live load not exceeding dead load",
    "crackWidth": "Calculated crack width",
    "deflectionDead": "Calculated long-term dead load deflection",
    "deflectionLive": "Calculated live load deflection",
    "deflectionIncrementalCalc": "Calculated incremental deflection",
    "deflectionTotalCalc": "Calculated total deflection",
    "slenderness": "Lateral restraint spacing",
    "secondarySteel": "Shrinkage and temperature steel",
}
ALWAYS_ON = ("flexure", "ductility", "minimumSteel", "barSpacing", "crackStress",
             "crackStressYield", "shear", "shearDetailing", "torsion", "torsionReinforcement",
             "webCrushing", "longitudinalTension", "longitudinalCompression",
             "deflectionTotal", "deflectionIncremental", "liveLoadLimit")
OPTIONAL_GROUPS = ("crackWidth", "calcDeflection", "slenderness", "secondary")

ASSUMPTIONS = [
    "Design actions are entered directly (the workbook's manual mode). M* is positive when "
    "the bottom face is in tension; slab actions are per metre width.",
    "The rectangular stress block of Cl 8.1.3 applies with eps.cu = 0.003 and Es = 200 GPa. "
    "Compression steel is credited only where it lies inside the compression zone and is "
    "limited to the tension steel area, as in the workbook.",
    "Where Ms1* and Ms* are left to default they are estimated as 0.75 M* and 0.65 M* "
    "(Design!F34:F35) and must be verified against the serviceability analysis.",
    "Self weight uses rho/100 + 1 kN/m3 (25 kN/m3 for 2400 kg/m3), including a reinforcement "
    "allowance; the deemed-to-comply dead load is self weight plus superimposed dead load.",
    "Bars in each face are one size, laid out in layers of at most the number that fits with "
    "the entered clear gaps; multiple layers act at their centroid.",
    "Shear actions V*, M* and N* are coexisting values at the section checked; N* is positive "
    "in compression, as the workbook's Eq 8.2.8.2(1) modification assumes.",
    "The calculated-deflection group takes gross elastic deflections from a separate analysis "
    "and scales them by Iuncr / Iav, as the workbook does.",
]
LIMITATIONS = [
    "Transcribed from Structural Toolkit CONCRETE MEMBER V5.13. Independent engineering review "
    "has not been completed and the module is not approved for design.",
    "Analysis-linked design (Results and Analysis sheets), custom bar layouts and pure "
    "strain-compatibility layers (Layers sheet), prestress, AS 5100.5 bridge variants other "
    "than the Act definition, exposure classification, slab preliminary sizing and the "
    "SlabShear quick check are not transcribed.",
    "Flexure is checked at one section for one M*; the moment envelope, curtailment and "
    "anchorage (Cl 8.1.10, Cl 13) are the designer's responsibility.",
    "Fire resistance, vibration, flange-web shear transfer and bearing are not checked.",
]


# ---------------------------------------------------------------------------
#  Input reading
# ---------------------------------------------------------------------------
def _yes(inputs: dict[str, Any], key: str, label: str) -> bool:
    return option(inputs, key, label, YES_NO) == "Y"


def _face_spec(inputs: dict[str, Any], prefix: str, label: str) -> dict[str, Any]:
    bar = from_set(inputs, f"bar{prefix}", f"{label} bar size", BAR_SIZES)
    mode = option(inputs, f"{prefix.lower()}Mode", f"{label} bar specification", ("N", "S", "A"))
    value = non_negative(inputs, f"{prefix.lower()}Value", f"{label} bar number, centres or area")
    if mode == "N" and (value != int(value) or value > MAX_BARS):
        raise ValueError(f"{label} bar number ({prefix.lower()}Value) must be a whole number "
                         f"from 0 to {MAX_BARS}")
    if mode == "S" and 0 < value < bar:
        raise ValueError(f"{label} bar centres ({prefix.lower()}Value) must exceed the bar size")
    return {"bar": bar, "mode": mode, "value": value}


def _checks(inputs: dict[str, Any]) -> dict[str, bool]:
    raw = inputs.get("checks") if isinstance(inputs.get("checks"), dict) else {}
    return {name: bool(raw.get(name)) for name in OPTIONAL_GROUPS}


def _optional_value(inputs: dict[str, Any], mode_key: str, value_key: str, label: str,
                    positive_only: bool = True) -> float | None:
    mode = option(inputs, mode_key, f"{label} source", ("C", "M"))
    if mode == "C":
        return None
    return positive(inputs, value_key, label) if positive_only else non_negative(
        inputs, value_key, label)


# ---------------------------------------------------------------------------
#  Calculation
# ---------------------------------------------------------------------------
def compute(inputs: dict[str, Any]) -> dict[str, Any]:
    kind = option(inputs, "sectionType", "Section type", ("S", "R", "F"))
    fc = number(inputs, "fc", "Concrete strength f'c")
    if not FC_MIN <= fc <= FC_MAX:
        raise ValueError(f"Concrete strength f'c (fc) must be between {FC_MIN:g} and "
                         f"{FC_MAX:g} MPa (Cl 1.1.2)")
    D = positive(inputs, "D", "Overall depth D")
    W = positive(inputs, "W", "Web width W") if kind != "S" else 1000.0
    Bf = non_negative(inputs, "Bf", "Flange width Bf")
    Tf = non_negative(inputs, "Tf", "Flange thickness Tf")
    if kind == "F":
        if Bf <= W:
            raise ValueError("Flange width Bf must exceed the web width W for a flanged beam")
        if not 0 < Tf < D:
            raise ValueError("Flange thickness Tf must be greater than zero and less than D")
    btype = option(inputs, "btype", "Flanged beam type", ("T", "L"))
    Lm = positive(inputs, "Lm", "Span L")
    support = option(inputs, "supportType", "Support type for bef", ("S", "C", "M"))
    mke = positive(inputs, "mke", "Manual zero-moment length factor")
    slab_type = option(inputs, "slabType", "Slab type", tuple(flexure.SLAB_TYPES))
    density = positive(inputs, "density", "Concrete density")
    if not 1800 <= density <= 2800:
        raise ValueError("Concrete density (density) must be between 1800 and 2800 kg/m3 "
                         "(Cl 3.1.3)")
    use_fcmi = _yes(inputs, "useFcmi", "Use fcmi for Ec")

    bottom = _face_spec(inputs, "Bot", "Bottom")
    top = _face_spec(inputs, "Top", "Top")
    fsy = from_set(inputs, "fsy", "Yield strength fsy", YIELD_STRENGTHS)
    class_bot = option(inputs, "classBot", "Bottom ductility class", ("N", "L"))
    class_top = option(inputs, "classTop", "Top ductility class", ("N", "L"))
    cover = non_negative(inputs, "cover", "Bottom cover")
    cover_top = non_negative(inputs, "coverTop", "Top cover")
    cover_side = non_negative(inputs, "coverSide", "Side cover")
    ligs = from_set(inputs, "ligs", "Fitment bar size", FITMENT_SIZES)
    clear_bot = positive(inputs, "clearBot", "Bottom horizontal clear gap")
    vclear_bot = positive(inputs, "vclearBot", "Bottom vertical clear gap")
    clear_top = positive(inputs, "clearTop", "Top horizontal clear gap")
    vclear_top = positive(inputs, "vclearTop", "Top vertical clear gap")
    extend = _yes(inputs, "extend", "Top bars extend into bef")

    mstar = number(inputs, "Mstar", "Design moment M*")
    ms1 = 0.75 * mstar if option(inputs, "ms1Mode", "Ms1* source", ("D", "M")) == "D" else number(
        inputs, "Ms1", "Short-term service moment Ms1*")
    ms = 0.65 * mstar if option(inputs, "msMode", "Ms* source", ("D", "M")) == "D" else number(
        inputs, "Ms", "Service moment Ms*")
    basis = option(inputs, "astMinBasis", "Minimum steel basis", ("D", "A", "M"))

    enclosed = _yes(inputs, "enclosed", "Fully enclosed member")
    wmax = number(inputs, "wmax", "Maximum crack width w'max")
    if wmax not in crack.CRACK_WIDTHS:
        raise ValueError("Maximum crack width w'max (wmax) must be 0.2, 0.3 or 0.4 mm")
    with_steel = _yes(inputs, "withSteel", "Include reinforcement in Iuncr")
    use_bef = _yes(inputs, "useBef", "Use bef for gross properties")
    env = option(inputs, "environment", "Environment", tuple(materials.ENVIRONMENTS))
    shrinkage_mode = option(inputs, "shrinkageMode", "Basic drying shrinkage source", ("S", "T"))
    basic_tested = non_negative(inputs, "ecsdbTested", "Tested basic drying shrinkage")
    t_days = positive(inputs, "tDays", "Time after commencing drying t")
    tau = positive(inputs, "tauDays", "Age at loading tau")
    if tau < 1:
        raise ValueError("Age at loading tau (tauDays) must be at least 1 day")
    th_manual = _optional_value(inputs, "thMode", "thManual", "Hypothetical thickness th")
    ecs_manual = _optional_value(inputs, "ecsMode", "ecsManual", "Design shrinkage strain",
                                 positive_only=False)
    fcc_manual = _optional_value(inputs, "fccMode", "fccManual", "Creep coefficient",
                                 positive_only=False)
    sigma_o = non_negative(inputs, "sigmaO", "Sustained stress sigma.o")

    geom = geometry(kind=kind, D=D, W=W, Bf=Bf, Tf=Tf, btype=btype, Lm=Lm, support=support,
                    mke=mke, density=density, use_bef=use_bef)
    reo = reinforcement(
        geom, bottom={**bottom, "clear": clear_bot, "vclear": vclear_bot},
        top={**top, "clear": clear_top, "vclear": vclear_top}, cover=cover,
        cover_top=cover_top, cover_side=cover_side, ligs=ligs, extend=extend)
    mat = materials.elastic(fc, density, use_fcmi)
    creep = materials.creep_shrinkage(
        geom, mat, fc=fc, env=env, shrinkage_mode=shrinkage_mode, basic_tested=basic_tested,
        t=t_days, tau=tau, th_manual=th_manual, ecs_manual=ecs_manual, fcc_manual=fcc_manual,
        sigma_o=sigma_o)

    flex = flexure.strength(geom, reo, fc=fc, fsy=fsy, class_bot=class_bot,
                            class_top=class_top, mstar=mstar)
    uncr = crack.uncracked(geom, reo, mat["n"], with_steel)
    minimum = flexure.minimum_strength(geom, reo, flex, fc=fc, fsy=fsy, uncracked=uncr,
                                       slab_type=slab_type, basis=basis)
    duct = flexure.ductility(flex, reo)
    spacing = flexure.bar_spacing(geom, reo, mstar)
    cracking = crack.stresses(geom, reo, flex, n=mat["n"], fsy=fsy, ms=ms, ms1=ms1, wmax=wmax)

    shear_opts = {
        "fc": fc, "fsy": fsy, "V": number(inputs, "Vstar", "Design shear V*"),
        "M": number(inputs, "MstarV", "Coexisting moment M* for shear"),
        "Mmax": number(inputs, "MmaxV", "Section maximum moment Mmax*"),
        "N": number(inputs, "NstarV", "Axial force N* for shear"),
        "T": number(inputs, "Tstar", "Design torsion T*"),
        "method": option(inputs, "shearMethod", "Shear method", ("G", "S")),
        "dg": positive(inputs, "dg", "Maximum aggregate size dg"),
        "lightweight": _yes(inputs, "lightweight", "Lightweight concrete"),
        "compCracked": _yes(inputs, "compCracked", "Cracking in the compression zone"),
        "ignoreLigs": _yes(inputs, "ignoreLigs", "Ignore fitments"),
        "s": positive(inputs, "s", "Fitment spacing s"),
        "legs": int(non_negative(inputs, "legs", "Fitment legs")),
        "fsyf": from_set(inputs, "fsyf", "Fitment yield strength fsy.f", YIELD_STRENGTHS),
        "classFit": option(inputs, "classFit", "Fitment ductility class", ("N", "L")),
        "alphaV": number(inputs, "alphaV", "Fitment angle alpha.v"),
        "increaseSpacing": _yes(inputs, "increaseSpacing", "Increase spacing limit"),
        "waiveSpacing": _yes(inputs, "waiveSpacing", "Waive maximum spacing"),
        "waiveTransverse": _yes(inputs, "waiveTransverse", "Waive transverse spacing"),
        "waiveDeep": _yes(inputs, "waiveDeep", "Waive D >= 750 mm fitments"),
        "actDefinition": option(inputs, "actDefinition", "Act definition", ("AS3600", "AS5100")),
        "limitTtd": _yes(inputs, "limitTtd", "Limit Ttd to Mmax*"),
        "AstManual": non_negative(inputs, "AstManual", "Manual tension steel for shear"),
        "AscManual": non_negative(inputs, "AscManual", "Manual compression steel for shear"),
        "classBot": class_bot, "classTop": class_top, "slabType": slab_type,
        "withSteel": with_steel,
    }
    if shear_opts["legs"] != non_negative(inputs, "legs", "Fitment legs"):
        raise ValueError("Fitment legs (legs) must be a whole number")
    if not 45.0 <= shear_opts["alphaV"] <= 90.0:
        raise ValueError("Fitment angle alpha.v (alphaV) must be between 45 and 90 degrees")
    shr = shear.check(geom, reo, mat, flex, uncr, shear_opts)

    span_type = option(inputs, "spanType", "Span type (deemed to comply)", ("S", "E", "I"))
    deemed = deflection.deemed(
        geom, reo, mat, fc=fc, span_type=span_type,
        spans=option(inputs, "spans", "Number of spans", ("2", "3")),
        wsdl=non_negative(inputs, "wsdl", "Superimposed dead load"),
        wll=non_negative(inputs, "wll", "Live load"),
        load_type=option(inputs, "loadTypeDefl", "Live load type", tuple(deflection.PSI)),
        lef_total=positive(inputs, "lefDelta", "Total deflection limit Lef/Delta"),
        lef_inc=positive(inputs, "lefDeltaInc", "Incremental deflection limit Lef/Delta"),
        k3=positive(inputs, "k3", "Slab factor k3"), class_bot=class_bot, class_top=class_top)

    checks_on = _checks(inputs)
    width = None
    if checks_on["crackWidth"]:
        width = crack.width(
            geom, reo, mat, creep, cracking,
            nstar=number(inputs, "NstarCrack", "Axial force N* for crack width"),
            shape_bot=option(inputs, "barShapeBot", "Bottom bar shape", ("D", "P")),
            shape_top=option(inputs, "barShapeTop", "Top bar shape", ("D", "P")), mstar=mstar)
    calc = wrh = None
    if checks_on["calcDeflection"]:
        positions = {key: {"mstar": number(inputs, f"m{key}", f"M* at {key}"),
                           "ms": number(inputs, f"ms{key}", f"Ms* at {key}"),
                           "top_override": number(inputs, f"topAs{key}", f"Top steel at {key}"),
                           "bottom_override": number(inputs, f"botAs{key}",
                                                     f"Bottom steel at {key}")}
                     for key in deflection.POSITIONS}
        limits = {name: (positive(inputs, f"lim{tag}", f"{name} deflection span ratio"),
                         non_negative(inputs, f"abs{tag}", f"{name} deflection absolute limit"))
                  for name, tag in (("dead", "DL"), ("live", "LL"), ("incremental", "Inc"),
                                    ("total", "Total"))}
        calc = deflection.calculated(
            geom, reo, mat, flex, fc=fc, fsy=fsy, positions=positions, ecs=creep["ecs"],
            use_fcs=_yes(inputs, "useFcs", "Include sigma.cs"), with_steel=with_steel,
            delta_dl=non_negative(inputs, "deltaDL", "Gross dead load deflection"),
            delta_ll=non_negative(inputs, "deltaLL", "Gross live load deflection"),
            psi_s=non_negative(inputs, "psiSDefl", "Short-term factor psi.s"),
            psi_l=non_negative(inputs, "psiLDefl", "Long-term factor psi.l"),
            cutoff_percent=non_negative(inputs, "cutoff", "End moment cut-off"), limits=limits)
        wrh = deflection.wrh(geom, mat, creep, calc, option(
            inputs, "creepSpanType", "Span type for creep and shrinkage",
            tuple(deflection.CREEP_SPAN_TYPES)))
    slender = None
    if checks_on["slenderness"]:
        slender = detailing.slenderness(
            geom, spacing=positive(inputs, "restraintSpacing", "Lateral restraint spacing"),
            cantilever=_yes(inputs, "cantilever", "Cantilever"))
    second = None
    if checks_on["secondary"]:
        second = detailing.secondary(
            geom, restraint=option(inputs, "restraint", "Restraint condition",
                                   tuple(detailing.RESTRAINT)),
            sigma_cp=non_negative(inputs, "sigmaCp", "Average prestress sigma.cp"),
            provided=non_negative(inputs, "AsSecondary", "Secondary reinforcement provided"))

    util: dict[str, float] = {
        "flexure": _flexure_ratio(mstar, flex),
        "ductility": duct["ratio"],
        "minimumSteel": minimum["ratio"],
        "barSpacing": spacing["ratio"],
    }
    if not enclosed:
        face = cracking["governing"]
        loaded = abs(ms) > 0 or abs(ms1) > 0
        if face["Ast"] == 0 and loaded:
            util["crackStress"] = util["crackStressYield"] = math.inf
        else:
            util["crackStress"] = face["ratio"]
            util["crackStressYield"] = face["ratio1"]
    util.update({
        "shear": shr["ratioShear"], "shearDetailing": shr["ratioDetailing"],
        "torsion": shr["ratioTorsion"], "torsionReinforcement": shr["ratioTorsionMin"],
        "webCrushing": shr["ratioCrush"], "longitudinalTension": shr["ratioLongTension"],
        "longitudinalCompression": shr["ratioLongCompression"],
    })
    if shr["ratioMethod"] is not None:
        util["shearMethod"] = shr["ratioMethod"]
    util.update({"deflectionTotal": deemed["ratioTotal"],
                 "deflectionIncremental": deemed["ratioIncremental"],
                 "liveLoadLimit": deemed["ratioLive"]})
    if width is not None:
        util["crackWidth"] = width["ratio"]
    if calc is not None:
        util.update({"deflectionDead": calc["ratioDead"], "deflectionLive": calc["ratioLive"],
                     "deflectionIncrementalCalc": calc["ratioIncremental"],
                     "deflectionTotalCalc": calc["ratioTotal"]})
    if slender is not None and slender["applicable"]:
        util["slenderness"] = slender["ratio"]
    if second is not None and second["applicable"]:
        util["secondarySteel"] = second["ratio"]

    warnings = _warnings(geom, reo, flex, duct, spacing, cracking, shr, deemed, calc, creep,
                         enclosed=enclosed, derived=(inputs.get("ms1Mode"), inputs.get("msMode")),
                         slender=slender, second=second, width=width)
    finite = [value for value in util.values() if math.isfinite(value)]
    unattainable = [CHECK_LABELS[key] for key, value in util.items() if not math.isfinite(value)]
    return {
        "module": MODULE_ID, "version": VERSION,
        "inputs": {"sectionType": kind, "fc": fc, "D": D, "W": geom["W"], "Bf": geom["Bf"],
                   "Tf": geom["Tf"], "btype": btype, "Lm": Lm, "fsy": fsy, "Mstar": mstar,
                   "Ms1": ms1, "Ms": ms, "classBot": class_bot, "classTop": class_top,
                   "wmax": wmax, "enclosed": enclosed},
        "section": geom, "reinforcement": reo, "materials": mat, "creep": creep,
        "flexure": flex, "minimum": minimum, "ductility": duct, "spacing": spacing,
        "uncracked": uncr, "crack": cracking, "crackWidth": width, "shear": shr,
        "deemed": deemed, "deflection": calc, "wrh": wrh, "slenderness": slender,
        "secondary": second, "util": util, "worstUtil": max(finite) if finite else 0.0,
        "unattainable": unattainable, "checks": {key: True for key in util},
        "warnings": warnings, "assumptions": list(ASSUMPTIONS),
        "limitations": list(LIMITATIONS),
    }


def _flexure_ratio(mstar: float, flex: dict[str, Any]) -> float:
    face = flex["governing"]
    if mstar == 0:
        return 0.0
    if face["Ast"] == 0 or face["phiMu"] <= 0:
        return math.inf
    return abs(mstar) / face["phiMu"]


def _warnings(geom, reo, flex, duct, spacing, cracking, shr, deemed, calc, creep, *, enclosed,
              derived, slender, second, width) -> list[str]:
    out: list[str] = []
    face = flex["governing"]
    if face["Ast"] == 0 and flex["Mstar"] != 0:
        out.append(f"No tension reinforcement for {'positive' if flex['Mstar'] > 0 else 'negative'} "
                   "bending: the section cannot resist M*.")
    if duct["exceedsBalanced"]:
        out.append("ku exceeds the balanced value ku.b; the workbook sets Mu = 0 (Detailed!D60).")
    elif face["Ast"] and not face["steelYields"]:
        out.append("The tension steel has not yielded at the ultimate state (Detailed!F52).")
    if face["kuo"] > flexure.KU_DUCTILITY:
        out.append("kuo exceeds 0.36 (Cl 8.1.5); compression steel of at least 0.01 b kuo do "
                   "is required and must be restrained to Cl 8.1.10.")
    if any(str(item).strip().upper() == "D" for item in derived):
        out.append("Ms1* and/or Ms* are estimated as 0.75 M* and 0.65 M*; verify them against "
                   "the serviceability analysis (Design!C37).")
    if spacing["applicable"] and spacing["ratio"] > 1:
        out.append(f"{spacing['face'].capitalize()} bar centres exceed {spacing['limit']:.0f} mm "
                   f"({spacing['clause']}).")
    if enclosed:
        out.append("Crack control is not checked: the member is declared fully enclosed "
                   "where wider cracks are tolerated.")
    if geom["section"] == FLANGED and not reo["extend"] and flex["Mstar"] < 0:
        out.append("Top bars should extend into the effective flange for crack control "
                   "(Cl 8.6.1(b)).")
    if flex["governing"]["ascInCompression"] is False and face["Asc"] > 0:
        out.append("Compression steel lies in the tension zone and is ignored for strength.")
    if shr["wideRejected"]:
        out.append("The increased fitment spacing limit (0.75 D, 500 mm) is not permitted because "
                   "V* > phi.Vu.min (Cl 8.3.2.2); the standard limit has been applied.")
    if shr["flexureShortfall"]:
        out.append("The tension steel at the shear section is less than that required for the "
                   "coexisting M* (Shear!D75).")
    if shr["AsvActual"] > shr["AsvMax"] and shr["AsvActual"] > 0:
        out.append("Fitment area exceeds Asv.max; the excess is ineffective because phi.Vu is "
                   "limited to phi.Vu.max (Shear!D59).")
    if shr["compCracked"]:
        out.append("Vuc is taken as zero for cracking in the compression zone (Cl 8.2.4.5).")
    if shr["deep"] and shr["AsvActual"] < shr["AsvMin"]:
        out.append("D >= 750 mm: minimum shear fitments are required (Cl 8.2.1.6(c)).")
    if shr["ratioMethod"] is not None and shr["ratioMethod"] > 1:
        out.append("The simplified shear method is outside its limits (f'c <= 65 MPa, "
                   "fsy <= 500 MPa, dg >= 10 mm); use the general method.")
    if deemed["ratioLive"] > 1:
        out.append(f"Live load exceeds the dead load: the deemed-to-comply method of "
                   f"{deemed['clause']} does not apply.")
    if deemed["ascIgnored"]:
        out.append("Compression steel lies in the tension zone and is ignored for kcs.")
    if creep["shrinkageMode"] == "T" and creep["basicStar"] != 800:
        out.append(f"Tested basic drying shrinkage eps.csd.b* = {creep['basicStar']:.0f} x 1e-6 "
                   "differs from the 800 x 1e-6 default (Creep&Shrink!G13).")
    if calc is not None:
        if not calc["IavValid"]:
            out.append("The end moments do not identify a span type; Iav uses the interior "
                       "formula (Defl!M79 'Error - Iav Invalid').")
        if calc["compressionInTension"]:
            out.append("Compression steel entered for deflection lies in the tension zone; set it "
                       "to zero (Defl!G44).")
    if slender is not None and not slender["applicable"]:
        out.append("Lateral restraint spacing (Cl 8.9) does not apply to slabs.")
    if second is not None and not second["applicable"]:
        out.append("Shrinkage and temperature steel (Cl 9.5.3) is checked only for slabs.")
    if width is not None and width["governing"]["sr1"] < width["governing"]["sr2"]:
        out.append("Crack spacing is limited by 1.3 (D - kd).")
    return out
