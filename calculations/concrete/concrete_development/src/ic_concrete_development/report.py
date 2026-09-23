"""Calculation-pad presentation for the development and lap length module."""

from __future__ import annotations

from html import escape
from typing import Any

import calcpad

from .engine import ELEMENTS

DATA_ID = "concrete-development-inputs"
DEFAULT_SUBJECT = "Reinforcement development and laps"


def _paragraphs(items: list[str]) -> str:
    return "".join(f"<p>{escape(str(item))}</p>" for item in items)


def _mm(value: float, digits: int = 1) -> str:
    return f"{calcpad.number(value, digits)} mm"


def render(inputs: dict[str, Any], result: dict[str, Any], *, standalone: bool = False,
           appendix: list[str] | None = None, anchor_prefix: str = "",
           contents_href: str = "") -> str:
    blocks = [_basis(result)]
    if result["errors"]:
        blocks.append(calcpad.prose("Lapped splice validity",
                                    _paragraphs(result["errors"]),
                                    weight=2 + 2 * len(result["errors"])))
    blocks.extend([
        _factors(result),
        _tension(result),
        _tension_lap(result),
        _compression(result),
        _compression_lap(result),
        _table(result),
    ])
    if result["bends"]:
        blocks.append(_bends(result))
    if result["warnings"]:
        blocks.append(calcpad.prose("Notes", _paragraphs(result["warnings"]),
                                    weight=2 + 2 * len(result["warnings"])))
    return calcpad.render(inputs, blocks, standalone=standalone, appendix=appendix,
                          anchor_prefix=anchor_prefix, contents_href=contents_href,
                          default_subject=DEFAULT_SUBJECT, data_id=DATA_ID)


def _basis(result: dict[str, Any]) -> str:
    body = ("<p><strong>This sheet reports development and lapped splice lengths. It contains "
            "no member design check and no utilisation.</strong></p>"
            "<p><strong>Assumptions</strong></p>" + _paragraphs(result["assumptions"])
            + "<p><strong>Limitations and exclusions</strong></p>"
            + _paragraphs(result["limitations"]))
    return calcpad.prose("Basis", body,
                         weight=8 + len(result["assumptions"]) + len(result["limitations"]))


def _factors(result: dict[str, Any]) -> str:
    factors, values = result["factors"], result["inputs"]
    rows = [
        calcpad.row("Concrete strength", "f'c", f"{calcpad.number(values['fc'], 0)} MPa",
                    "Cl 1.1.2"),
        calcpad.row("Tension design strength", "min(f'c, 65)",
                    f"{calcpad.number(factors['fcTension'], 1)} MPa", "Cl 13.1.2.2"),
        calcpad.row("Compression design strength", "f'c for compression",
                    f"{calcpad.number(factors['fcCompression'], 1)} MPa", "Cl 13.1.5.2"),
        calcpad.row("Bar diameter", "db", _mm(values["db"], 0)),
        calcpad.row("Yield strength", "fsy", f"{calcpad.number(values['fsy'], 0)} MPa"),
        calcpad.row("Concrete cast below the bar", "k1 = 1.3 if more than 300 mm",
                    calcpad.number(factors["k1"], 2), "Cl 13.1.2.2"),
        calcpad.row("Bar size factor", "k2 = (132 - db) / 100",
                    calcpad.number(factors["k2"], 4), "Cl 13.1.2.2"),
        calcpad.row("Cover and spacing", "cd = min(a/2, cover)", _mm(factors["cd"], 1),
                    "Fig 13.1.2.2"),
        calcpad.row("Cover factor", "k3 = 1 - 0.15 (cd - db)/db",
                    calcpad.number(factors["k3"], 4), "Cl 13.1.2.2, 0.7 to 1.0"),
        calcpad.row("Bundled bar multiplier", "mb", calcpad.number(factors["mb"], 3),
                    "Cl 13.1.7"),
        calcpad.row("Epoxy coating multiplier", "me", calcpad.number(factors["me"], 2),
                    "Cl 13.1.2.2(a)"),
        calcpad.row("Lightweight concrete multiplier", "ml", calcpad.number(factors["ml"], 2),
                    "Cl 13.1.2.2(b)"),
        calcpad.row("Slip formed multiplier", "ms", calcpad.number(factors["ms"], 2),
                    "Cl 13.1.2.2(c), fixed at 1.0"),
        calcpad.row("Lap splice multiplier", "k7", calcpad.number(factors["k7"], 2),
                    "Cl 13.2.2"),
    ]
    return calcpad.table("Factors", rows)


def _tension(result: dict[str, Any]) -> str:
    tension = result["tension"]
    rows = [
        calcpad.row("Basic length, first term",
                    "0.5 k1 k3 fsy db / (k2 sqrt(f'c))", _mm(tension["Lsytb1"], 2),
                    "Eq 13.1.2.2"),
        calcpad.row("Basic length, lower limit", "0.058 fsy k1 db",
                    _mm(tension["Lsytb2"], 2), "Eq 13.1.2.2"),
        calcpad.row("Basic development length", "Lsy.tb = max of the two, x me ml ms x mb",
                    _mm(tension["Lsytb"], 2), "Cl 13.1.2.2"),
        calcpad.row("At the applied stress", "Lst1 = min(sigma.st, fsy)/fsy x Lsy.tb",
                    _mm(tension["Lst1"], 2), "Eq 13.1.2.4"),
        calcpad.row("Reduced stress minimum", "Lst2 = 12 db", _mm(tension["Lst2"], 2),
                    "Cl 13.1.2.4(a)"),
        calcpad.row("Deformed bar in tension", "Lsy.t", _mm(tension["Lsyt"], 2), "Cl 13.1.2"),
        calcpad.row("With a hook or cog", "0.5 Lsy.t", _mm(tension["hookAllowance"], 2),
                    "Cl 13.1.2.6"),
        calcpad.row("Plain bar in tension", "Lsy.tp = max(1.5 Lsy.t, 300)",
                    _mm(tension["Lsytp"], 2), "Cl 13.1.3"),
        calcpad.row("Plain bar with a hook or cog", "0.5 Lsy.tp",
                    _mm(tension["hookAllowancePlain"], 2), "Cl 13.1.3"),
    ]
    return calcpad.table("Development in tension", rows)


def _tension_lap(result: dict[str, Any]) -> str:
    lap, factors = result["tensionLap"], result["factors"]
    rows = [
        calcpad.row("Element", escape(ELEMENTS[lap["element"]]), ""),
        calcpad.row("Clear distance counted", "sb, only when at least 3 db",
                    _mm(lap["sb"], 1), "Fig 13.2.2"),
        calcpad.row("Lap correction", "0.116 k2 sqrt(f'c) / k3, not less than 1",
                    calcpad.number(lap["correction"], 5),
                    "Workbook note, removes the Eq 13.1.2.2 lower limit"),
        calcpad.row("Lap term 1", "k7 Lsy.t(1) / correction", _mm(lap["Lsytlap1"], 2),
                    "Cl 13.2.2"),
        calcpad.row("Lap term 2", "0.058 fsy k1 db", _mm(lap["Lsytlap2"], 2), "Cl 13.2.2"),
        calcpad.row("Lap term 3", "1.5 sb + Lsy.t(1)", _mm(lap["Lsytlap3"], 2),
                    "Narrow element only"),
        calcpad.row("Tension lapped splice", "Lsy.t.lap", _mm(lap["Lsytlap"], 2), "Cl 13.2.2"),
    ]
    return calcpad.table("Tension lapped splice - Cl 13.2.2", rows)


def _compression(result: dict[str, Any]) -> str:
    compression = result["compression"]
    rows = [
        calcpad.row("Basic length, first term", "0.22 fsy / sqrt(f'c) x db",
                    _mm(compression["Lsycb1"], 2), "Eq 13.1.5.2"),
        calcpad.row("Basic length, lower limit", "max(0.0435 fsy db, 200)",
                    _mm(compression["Lsycb2"], 2), "Eq 13.1.5.2"),
        calcpad.row("Basic development length", "Lsy.cb = max of the two x mb",
                    _mm(compression["Lsycb"], 2), "Cl 13.1.5.2"),
        calcpad.row("At the applied stress", "Lsc1 = min(sigma.sc, fsy)/fsy x Lsy.cb",
                    _mm(compression["Lsc1"], 2), "Eq 13.1.5.4"),
        calcpad.row("Deformed bar in compression", "Lsy.c",
                    _mm(compression["Lsyc"], 2), "Cl 13.1.5"),
        calcpad.row("Plain bar in compression", "Lsy.cp = 2 Lsy.c",
                    _mm(compression["Lsycp"], 2), "Cl 13.1.6"),
    ]
    return calcpad.table("Development in compression", rows)


def _compression_lap(result: dict[str, Any]) -> str:
    lap = result["compressionLap"]
    rows = [
        calcpad.row("Fitment area", "Atr = pi df^2 / 4",
                    f"{calcpad.number(lap['Atr'], 2)} mm2"),
        calcpad.row("Bar area", "Ab = pi db^2 / 4",
                    f"{calcpad.number(lap['Ab'], 2)} mm2"),
        calcpad.row("Fitment area per unit length", "Atr / s",
                    calcpad.number(lap["AtrOverS"], 5)),
        calcpad.row("Non-helical threshold", "Ab / 1000",
                    calcpad.number(lap["nonHelicalThreshold"], 5), "Cl 13.2.4(b)"),
        calcpad.row("Helical threshold", "n Ab / 6000",
                    calcpad.number(lap["helicalThreshold"], 5), "Cl 13.2.4(c)"),
        calcpad.row("Non-helical reduction", "rn", calcpad.number(lap["rn"], 2),
                    "Cl 13.2.4(b)"),
        calcpad.row("Helical reduction", "rh", calcpad.number(lap["rh"], 2), "Cl 13.2.4(c)"),
        calcpad.row("Lap term 1", "max(Lsy.c(1), 300)", _mm(lap["Lsyclap1"], 2), "Cl 13.2.4"),
        calcpad.row("Lap term 2", "40 db", _mm(lap["Lsyclap2"], 2), "Cl 13.2.4(a)"),
        calcpad.row("Compression lapped splice", "Lsy.c.lap = mb rn rh x max of the two",
                    _mm(lap["Lsyclap"], 2), "Cl 13.2.4"),
    ]
    return calcpad.table("Compression lapped splice - Cl 13.2.4", rows)


def _table(result: dict[str, Any]) -> str:
    headers = ["db (mm)", "Lsy.tb", "Lsy.tp", "Lsy.t.lap", "Lsy.cb", "Lsy.cp", "Lsy.c.lap"]
    rows = [[f"{row['db']:g}", calcpad.number(row["Lsytb"], 0),
             calcpad.number(row["Lsytp"], 0), calcpad.number(row["Lsytlap"], 0),
             calcpad.number(row["Lsycb"], 0), calcpad.number(row["Lsycp"], 0),
             calcpad.number(row["Lsyclap"], 0)] for row in result["table"]]
    note = ("All lengths in millimetres, rounded up at every step of the chain exactly as the "
            "source workbook does. A table value can therefore exceed the single bar value "
            "printed above, which carries full precision throughout.")
    return calcpad.grid("Lengths for the standard bar sizes", headers, rows, note)


def _bends(result: dict[str, Any]) -> str:
    bends = result["bends"]
    rows = [
        calcpad.row("Bar diameter", "db", _mm(bends["db"], 0)),
        calcpad.row("Nominal internal diameter", "as a multiple of db",
                    calcpad.number(bends["internalFactor"], 0), "Cl 17.2.3.3"),
        calcpad.row("Nominal diameter", "(factor + 1) db", _mm(bends["nominal"], 1)),
        calcpad.row("Straight extension", "max(4 db, 70)", _mm(bends["extension"], 1),
                    "Cl 13.1.2.7"),
        calcpad.row("180 degree hook", "pi d / 2 + extension", _mm(bends["hook180"], 3),
                    "Cl 13.1.2.7(a)"),
        calcpad.row("135 degree hook", "pi d / 2 + extension", _mm(bends["hook135"], 3),
                    "Cl 13.1.2.7(b)"),
        calcpad.row("90 degree cog total length", "pi d / 2 + extension",
                    _mm(bends["cogLength"], 3), "Cl 13.1.2.7(c)"),
        calcpad.row("90 degree cog straight length", "total - pi d / 4",
                    _mm(bends["cogStraight"], 3)),
        calcpad.row("90 degree cog height", "straight + d/2 + db/2",
                    _mm(bends["cogHeight"], 3)),
        calcpad.row("Maximum internal diameter", "as a multiple of db",
                    calcpad.number(bends["maxInternalFactor"], 0), "Cl 13.1.2.7"),
        calcpad.row("Cog total length at the maximum diameter", "pi d.max / 2 + extension",
                    _mm(bends["cogLengthMax"], 3)),
        calcpad.row("Cog height at the maximum diameter", "straight + d.max/2 + db/2",
                    _mm(bends["cogHeightMax"], 3)),
    ]
    return calcpad.table("Hooks and cogs - Cl 13.1.2.7", rows)
