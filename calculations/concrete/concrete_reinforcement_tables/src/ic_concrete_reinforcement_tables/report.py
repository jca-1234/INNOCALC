"""Calculation-pad presentation for the reinforcement tables module."""

from __future__ import annotations

from html import escape
from typing import Any

import calcpad

DATA_ID = "concrete-reinforcement-tables-inputs"
DEFAULT_SUBJECT = "Reinforcement tables"
ROWS_PER_BLOCK = 16


def _paragraphs(items: list[str]) -> str:
    return "".join(f"<p>{escape(str(item))}</p>" for item in items)


def render(inputs: dict[str, Any], result: dict[str, Any], *, standalone: bool = False,
           appendix: list[str] | None = None, anchor_prefix: str = "",
           contents_href: str = "") -> str:
    blocks = [_basis(result), _selected(result), _mesh(result)]
    blocks.extend(_split_table("Area for a number of bars", result, "numberTable",
                               "Number", "count", 0))
    blocks.extend(_split_table("Area per metre for bar centres", result, "centresTable",
                               "Centres (mm)", "centres", 0))
    blocks.append(_fabric(result))
    if result["warnings"]:
        blocks.append(calcpad.prose("Notes", _paragraphs(result["warnings"]),
                                    weight=2 + 2 * len(result["warnings"])))
    return calcpad.render(inputs, blocks, standalone=standalone, appendix=appendix,
                          anchor_prefix=anchor_prefix, contents_href=contents_href,
                          default_subject=DEFAULT_SUBJECT, data_id=DATA_ID)


def _basis(result: dict[str, Any]) -> str:
    body = ("<p><strong>These are reference tables. This sheet contains no design check and no "
            "utilisation.</strong></p>"
            "<p><strong>Assumptions</strong></p>" + _paragraphs(result["assumptions"])
            + "<p><strong>Limitations and exclusions</strong></p>"
            + _paragraphs(result["limitations"]))
    return calcpad.prose("Basis", body,
                         weight=8 + len(result["assumptions"]) + len(result["limitations"]))


def _selected(result: dict[str, Any]) -> str:
    selected = result["selected"]
    rows = [
        calcpad.row("Bar diameter", "db", f"{calcpad.number(selected['db'], 0)} mm"),
        calcpad.row("Area of one bar", "Ab = pi db^2 / 4",
                    f"{calcpad.number(selected['single'], 3)} mm2"),
        calcpad.row("Number of bars", "n", calcpad.number(selected["count"], 0)),
        calcpad.row("Area of n bars", "n Ab",
                    f"{calcpad.number(selected['countArea'], 3)} mm2"),
        calcpad.row("Tabulated value", "rounded down",
                    f"{calcpad.number(selected['countAreaRounded'], 0)} mm2"),
        calcpad.row("Bar centres", "s", f"{calcpad.number(selected['centres'], 0)} mm"),
        calcpad.row("Area per metre", "Ab x 1000 / s",
                    f"{calcpad.number(selected['centresArea'], 3)} mm2/m"),
        calcpad.row("Tabulated value", "rounded down",
                    f"{calcpad.number(selected['centresAreaRounded'], 0)} mm2/m"),
    ]
    return calcpad.table("Selected reinforcement", rows)


def _mesh(result: dict[str, Any]) -> str:
    mesh = result["mesh"]
    rows = [
        calcpad.row("Designation", escape(mesh["name"]), escape(mesh["family"])),
        calcpad.row("Longitudinal wire", "diameter",
                    f"{calcpad.number(mesh['longDia'], 2)} mm"),
    ]
    if mesh["perMetre"]:
        rows.append(calcpad.row("Longitudinal pitch", "centres",
                                f"{calcpad.number(mesh['longCts'], 0)} mm"))
        rows.append(calcpad.row("Longitudinal area", "pi d^2 / 4 x 1000 / centres",
                                f"{calcpad.number(mesh['longArea'], 3)} mm2/m"))
        rows.append(calcpad.row("Cross wire", "diameter",
                                f"{calcpad.number(mesh['crossDia'], 2)} mm"))
        rows.append(calcpad.row("Cross pitch", "centres",
                                f"{calcpad.number(mesh['crossCts'], 0)} mm"))
        rows.append(calcpad.row("Cross area", "pi d^2 / 4 x 1000 / centres",
                                f"{calcpad.number(mesh['crossArea'], 3)} mm2/m"))
    else:
        rows.append(calcpad.row("Wires in the sheet", "n",
                                calcpad.number(mesh["wires"], 0)))
        rows.append(calcpad.row("Area of the sheet", "n pi d^2 / 4",
                                f"{calcpad.number(mesh['longArea'], 3)} mm2"))
    if mesh["note"]:
        rows.append(calcpad.row("Note", escape(mesh["note"]), ""))
    return calcpad.table("Selected fabric", rows)


def _split_table(title: str, result: dict[str, Any], key: str, first_header: str,
                 first_key: str, digits: int) -> list[str]:
    headers = [first_header] + [f"N{size:g}" for size in result["barSizes"]]
    body = [[f"{row[first_key]:g}"] + [calcpad.number(area, digits) for area in row["areas"]]
            for row in result[key]]
    note = ("All areas in mm2, rounded down as the source workbook does. "
            "Bar diameters are the column headings.")
    blocks: list[str] = []
    for start in range(0, len(body), ROWS_PER_BLOCK):
        chunk = body[start:start + ROWS_PER_BLOCK]
        heading = title if start == 0 else f"{title}, continued"
        blocks.append(calcpad.grid(heading, headers, chunk,
                                   note if start + ROWS_PER_BLOCK >= len(body) else ""))
    return blocks


def _fabric(result: dict[str, Any]) -> str:
    headers = ["Mesh", "Family", "Long. dia (mm)", "Long. pitch (mm)", "Long. area",
               "Cross dia (mm)", "Cross pitch (mm)", "Cross area"]
    rows = []
    for mesh in result["fabricTable"]:
        if mesh["perMetre"]:
            rows.append([escape(mesh["name"]), escape(mesh["family"]),
                         calcpad.number(mesh["longDia"], 2),
                         calcpad.number(mesh["longCts"], 0),
                         calcpad.number(mesh["longArea"], 1),
                         calcpad.number(mesh["crossDia"], 2),
                         calcpad.number(mesh["crossCts"], 0),
                         calcpad.number(mesh["crossArea"], 1)])
        else:
            rows.append([escape(mesh["name"]), escape(mesh["family"]),
                         calcpad.number(mesh["longDia"], 2), "-",
                         calcpad.number(mesh["longArea"], 1),
                         "-", "-", "-"])
    note = ("Areas are mm2 per metre except for the trench meshes, whose area is per sheet. "
            "Calculated from the wire diameter and pitch recorded in the source workbook, "
            "which cites the OneSteel onemesh 500 publication. Confirm against a current "
            "manufacturer's catalogue before specifying.")
    return calcpad.grid("Fabric properties", headers, rows, note)
