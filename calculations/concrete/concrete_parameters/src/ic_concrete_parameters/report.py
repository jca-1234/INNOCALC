"""Calculation-pad presentation for the concrete parameter module."""

from __future__ import annotations

from html import escape
from typing import Any

import calcpad

from .engine import CEMENTS, FCMI_SOURCES, SECTION_TYPES

DATA_ID = "concrete-parameters-inputs"
DEFAULT_SUBJECT = "Concrete design parameters"


def _paragraphs(items: list[str]) -> str:
    return "".join(f"<p>{escape(str(item))}</p>" for item in items)


def render(inputs: dict[str, Any], result: dict[str, Any], *, standalone: bool = False,
           appendix: list[str] | None = None, anchor_prefix: str = "",
           contents_href: str = "") -> str:
    blocks = [_basis(result), _material(result), _stress_block(result), _strength(result)]
    if result["minimumSteel"]:
        blocks.append(_minimum_steel(result))
    if result["cracking"]:
        blocks.append(_cracking(result))
    return calcpad.render(inputs, blocks, standalone=standalone, appendix=appendix,
                          anchor_prefix=anchor_prefix, contents_href=contents_href,
                          default_subject=DEFAULT_SUBJECT, data_id=DATA_ID)


def _basis(result: dict[str, Any]) -> str:
    body = ("<p><strong>This sheet reports parameters only. It contains no strength, "
            "serviceability or detailing check and no utilisation.</strong></p>"
            "<p><strong>Assumptions</strong></p>" + _paragraphs(result["assumptions"])
            + "<p><strong>Limitations and exclusions</strong></p>"
            + _paragraphs(result["limitations"]))
    return calcpad.prose("Design basis", body,
                         weight=8 + len(result["assumptions"]) + len(result["limitations"]))


def _material(result: dict[str, Any]) -> str:
    material = result["material"]
    table_value = (f"{calcpad.number(material['fcmiTable'], 0)} MPa"
                   if material["fcmiTable"] is not None else "not tabulated at this grade")
    rows = [
        calcpad.row("Characteristic compressive strength", "f'c",
                    f"{calcpad.number(material['fc'], 0)} MPa", "Cl 1.1.2, 20 to 120 MPa"),
        calcpad.row("Density", "rho", f"{calcpad.number(material['density'], 0)} kg/m3",
                    "Cl 3.1.3"),
        calcpad.row("Characteristic flexural tensile strength", "f'ct.f = 0.6 sqrt(f'c)",
                    f"{calcpad.number(material['fctf'], 4)} MPa", "Cl 3.1.1.3"),
        calcpad.row("Characteristic principal tensile strength", "f'ct = 0.36 sqrt(f'c)",
                    f"{calcpad.number(material['fct'], 4)} MPa", "Cl 3.1.1.3"),
        calcpad.row("Mean in-situ strength", "fcmi from Table 3.1.2", table_value,
                    "AS 3600 Table 3.1.2"),
        calcpad.row("Mean in-situ strength", "fcmi = -0.0015 f'c^2 + 1.1429 f'c - 0.0614",
                    f"{calcpad.number(material['fcmiCurve'], 4)} MPa",
                    "Workbook curve fit, not a code equation"),
        calcpad.row("Mean in-situ strength", "fcmi = 0.9 (1.2875 - 0.001875 f'c) f'c",
                    f"{calcpad.number(material['fcmiAs2327'], 4)} MPa",
                    "AS 2327:2017 Table 3.6.2.3"),
        calcpad.row("Adopted mean in-situ strength",
                    escape(FCMI_SOURCES[material["fcmiSource"]]),
                    f"fcmi = {calcpad.number(material['fcmi'], 4)} MPa"),
        calcpad.row("Modulus of elasticity",
                    "Ec = rho^1.5 (0.043 sqrt(fcmi)) for fcmi <= 40, else "
                    "rho^1.5 (0.024 sqrt(fcmi) + 0.12)",
                    f"{calcpad.number(material['Ec'], 0)} MPa", "Cl 3.1.2"),
        calcpad.row("Modulus of elasticity range", "Ec plus or minus 20 per cent",
                    f"{calcpad.number(material['EcLower'], 0)} to "
                    f"{calcpad.number(material['EcUpper'], 0)} MPa", "Cl 3.1.2"),
    ]
    return calcpad.table("Material properties", rows)


def _stress_block(result: dict[str, Any]) -> str:
    block = result["stressBlock"]
    rows = [
        calcpad.row("Column stress block factor", "alpha1 = 1.0 - 0.003 f'c",
                    calcpad.number(block["alpha1"], 4), "Eq 10.6.2.2, 0.72 to 0.85"),
        calcpad.row("Unbounded value", "1.0 - 0.003 f'c",
                    calcpad.number(block["alpha1Unbounded"], 4),
                    "Also the AS 3600:2009 alpha2"),
        calcpad.row("Stress block intensity", "alpha2 = 0.85 - 0.0015 f'c",
                    calcpad.number(block["alpha2"], 4),
                    "Eq 8.1.3(1), Eq 10.6.2.5(1), not less than 0.67"),
        calcpad.row("Stress block depth ratio", "gamma = 0.97 - 0.0025 f'c",
                    calcpad.number(block["gamma"], 4),
                    "Eq 8.1.3(2), Eq 10.6.2.5(2), not less than 0.67"),
        calcpad.row("Maximum concrete compressive strain", "epsilon.c",
                    calcpad.number(block["epsilonC"], 4), "Cl 10.6.1(d)"),
    ]
    return calcpad.table("Rectangular stress block parameters", rows)


def _strength(result: dict[str, Any]) -> str:
    strength = result["strength"]
    headers = ["Age (days)", "Normal ratio", "Normal f'c (MPa)",
               "High early ratio", "High early f'c (MPa)"]
    rows = [[str(entry["day"]), calcpad.number(entry["ratioNormal"], 2),
             calcpad.number(entry["normal"], 1), calcpad.number(entry["ratioHighEarly"], 2),
             calcpad.number(entry["highEarly"], 1)] for entry in strength["ages"]]
    note = (f"Adopted: {escape(CEMENTS[strength['cement']])} at {strength['age']} days, "
            f"f'c = {calcpad.number(strength['design'], 1)} MPa. The ratios are the source "
            "workbook's own table and carry no AS 3600 clause reference.")
    return calcpad.grid("Gain in compressive strength with time", headers, rows, note)


def _minimum_steel(result: dict[str, Any]) -> str:
    minimum = result["minimumSteel"]
    rows = [
        calcpad.row("Section", escape(SECTION_TYPES[minimum["section"]]), "",
                    minimum["reference"]),
        calcpad.row("Web width", "bw", f"{calcpad.number(minimum['bw'], 0)} mm"),
        calcpad.row("Overall depth", "D", f"{calcpad.number(minimum['D'], 0)} mm"),
        calcpad.row("Depth to the tensile steel", "ds", f"{calcpad.number(minimum['ds'], 0)} mm"),
        calcpad.row("Yield strength", "fsy", f"{calcpad.number(minimum['fsy'], 0)} MPa"),
        calcpad.row("Minimum reinforcement factor", "alpha.b",
                    calcpad.number(minimum["alphaB"], 4), minimum["reference"]),
        calcpad.row("Minimum reinforcement",
                    "Ast.min = alpha.b (D/ds)^2 f'ct.f / fsy bw ds",
                    f"{calcpad.number(minimum['Astmin'], 1)} mm2", minimum["reference"]),
    ]
    return calcpad.table("Minimum flexural reinforcement", rows)


def _cracking(result: dict[str, Any]) -> str:
    cracking = result["cracking"]
    rows = [
        calcpad.row("Section modulus, top fibre", "Zt = Ig / ytop",
                    f"{calcpad.number(cracking['Zt'], 0)} mm3"),
        calcpad.row("Section modulus, bottom fibre", "Zb = Ig / ybot",
                    f"{calcpad.number(cracking['Zb'], 0)} mm3"),
        calcpad.row("Minimum moment, top in tension", "Muo = 1.2 Zt f'ct.f",
                    f"{calcpad.moment(cracking['MuoTop'])} kNm", "Cl 8.1.6.1"),
        calcpad.row("Minimum moment, bottom in tension", "Muo = 1.2 Zb f'ct.f",
                    f"{calcpad.moment(cracking['MuoBottom'])} kNm", "Cl 8.1.6.1"),
    ]
    return calcpad.table("Minimum cracking moment", rows)
