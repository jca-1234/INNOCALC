"""Calculation-pad presentation for the reinforcement rate module."""

from __future__ import annotations

from html import escape
from typing import Any

import calcpad

DATA_ID = "concrete-reinforcement-rate-inputs"
DEFAULT_SUBJECT = "Reinforcement rate"


def _paragraphs(items: list[str]) -> str:
    return "".join(f"<p>{escape(str(item))}</p>" for item in items)


def render(inputs: dict[str, Any], result: dict[str, Any], *, standalone: bool = False,
           appendix: list[str] | None = None, anchor_prefix: str = "",
           contents_href: str = "") -> str:
    blocks = [_basis(result), _member(result)]
    blocks.extend(_schedule(result))
    blocks.append(_totals(result))
    notes = list(result.get("warnings") or [])
    if notes:
        blocks.append(calcpad.prose("Warnings", _paragraphs(notes), weight=2 + 2 * len(notes)))
    return calcpad.render(inputs, blocks, standalone=standalone, appendix=appendix,
                          anchor_prefix=anchor_prefix, contents_href=contents_href,
                          default_subject=DEFAULT_SUBJECT, data_id=DATA_ID)


def _basis(result: dict[str, Any]) -> str:
    body = ("<p><strong>This sheet is a quantity calculation. It contains no strength, "
            "serviceability or detailing check and no utilisation.</strong></p>"
            "<p><strong>Assumptions</strong></p>" + _paragraphs(result["assumptions"])
            + "<p><strong>Limitations and exclusions</strong></p>"
            + _paragraphs(result["limitations"]))
    return calcpad.prose("Basis", body,
                         weight=8 + len(result["assumptions"]) + len(result["limitations"]))


def _member(result: dict[str, Any]) -> str:
    member = result["member"]
    rows = [
        calcpad.row("Description", "", escape(result["inputs"]["title"])),
        calcpad.row("Length", "L", f"{calcpad.number(member['L'], 0)} mm"),
        calcpad.row("Width", "rb", f"{calcpad.number(member['rb'], 0)} mm"),
        calcpad.row("Depth", "rd", f"{calcpad.number(member['rd'], 0)} mm"),
        calcpad.row("Cover", "cover", f"{calcpad.number(member['cover'], 0)} mm"),
        calcpad.row("Cross sectional area", "A = rb rd / 10^6",
                    f"{calcpad.number(member['area'], 4)} m2"),
        calcpad.row("Concrete volume", "V = A L / 1000",
                    f"{calcpad.number(member['volume'], 4)} m3"),
        calcpad.row("Ligature size", "ligs", f"{calcpad.number(member['ligs'], 0)} mm"),
        calcpad.row("Hook length", "hook", f"{calcpad.number(member['hook'], 0)} mm",
                    "Tabulated by ligature diameter"),
        calcpad.row("Number of transverse ligatures",
                    "roundup[(rb - 2 cover - 12) / min(600, rd)] - 1",
                    calcpad.number(member["ties"], 0), "Cl 8.3.2.2"),
        calcpad.row("One ligature length",
                    "2(rb - 2 cover - 10) + 2(rd - 2 cover - 10) + 2 hook",
                    f"{calcpad.number(member['ligature'], 3)} m"),
        calcpad.row("Transverse ligature set length",
                    "ties x (rd - cover - 10 + 2 hook)",
                    f"{calcpad.number(member['tieSet'], 3)} m"),
        calcpad.row("Reinforcement density", "rho",
                    f"{calcpad.number(member['density'], 0)} kg/m3"),
    ]
    return calcpad.table("Member", rows)


def _schedule(result: dict[str, Any]) -> list[str]:
    rows = result["schedule"]
    if not rows:
        return [calcpad.prose("Reinforcement schedule",
                              "<p>The schedule is empty.</p>", weight=3)]
    headers = ["Mark", "Type", "Description", "Interpretation", "Number",
               "Length (m)", "Weight (kg)"]
    body = [[escape(row["mark"]), escape(row["label"]), escape(row["description"]),
             escape(row["reading"]), calcpad.number(row["count"], 2),
             calcpad.number(row["totalLength"], 3), calcpad.number(row["weight"], 2)]
            for row in rows]
    note = ("Laps and ligature cogs are excluded. A number of 100 or more in the schedule is "
            "read as centres in millimetres; a smaller number is read as a count.")
    blocks: list[str] = []
    for start in range(0, len(body), 12):
        chunk = body[start:start + 12]
        title = ("Reinforcement schedule" if start == 0
                 else f"Reinforcement schedule continued, rows {start + 1} onwards")
        blocks.append(calcpad.grid(title, headers, chunk,
                                   note if start + 12 >= len(body) else ""))
    return blocks


def _totals(result: dict[str, Any]) -> str:
    totals, member = result["totals"], result["member"]
    rows = [
        calcpad.row("Schedule rows", "", calcpad.number(totals["rows"], 0)),
        calcpad.row("Total bar length", "sum of the schedule lengths",
                    f"{calcpad.number(totals['length'], 3)} m"),
        calcpad.row("Total steel weight", "sum of the schedule weights",
                    f"{calcpad.number(totals['weight'], 2)} kg"),
        calcpad.row("Concrete volume", "V", f"{calcpad.number(member['volume'], 4)} m3"),
        calcpad.row("Reinforcement rate", "weight / volume",
                    f"{calcpad.number(totals['rate'], 1)} kg/m3"),
    ]
    return calcpad.table("Reinforcement rate", rows)
