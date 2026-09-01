"""Innovis A4 calculation-pad sheet construction.

Every calculation module renders through this package so all output shares one
template: the Innovis header block, the 5 mm grid, the four-column calculation
table, page numbering and the standalone document wrapper.
"""

from __future__ import annotations

import base64
import json
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from .notation import esc, notation

PACKAGE_DIR = Path(__file__).resolve().parent
# Rows of a calculation table that fit on one sheet below the header block.
SHEET_CAPACITY = 44


@lru_cache(maxsize=8)
def logo_data_uri(logo_path: str | None = None) -> str:
    """Base64 logo so a saved sheet is a single self-contained file."""
    candidates = [Path(logo_path)] if logo_path else []
    candidates.append(PACKAGE_DIR / "assets" / "innovis-logo.png")
    for candidate in candidates:
        if candidate.is_file():
            return "data:image/png;base64," + base64.b64encode(candidate.read_bytes()).decode("ascii")
    return ""


@lru_cache(maxsize=4)
def theme_css() -> str:
    return (PACKAGE_DIR / "theme.css").read_text(encoding="utf-8")


def stylesheet(module_dir: Path | str | None = None) -> str:
    """A module's own stylesheet when present, otherwise the shared theme."""
    if module_dir:
        local = Path(module_dir) / "styles.css"
        if local.is_file():
            return local.read_text(encoding="utf-8")
    return theme_css()


# ---------------------------------------------------------------------------
#  Table primitives
# ---------------------------------------------------------------------------
def row(label: str, equation: str, value: str, reference: str = "") -> str:
    """One line of the calculation audit trail."""
    return (f"<tr><td>{label}</td><td>{notation(equation)}</td>"
            f'<td class="num">{value}</td><td>{reference}</td></tr>')


def table(title: str, rows: Iterable[str]) -> str:
    return (f'<h2>{title}</h2><table class="calc"><colgroup><col class="item-col">'
            '<col class="basis-col"><col class="result-col"><col class="reference-col"></colgroup>'
            '<thead><tr><th>Item</th><th>Expression / basis</th>'
            '<th>Result</th><th>Reference</th></tr></thead>'
            f"<tbody>{''.join(rows)}</tbody></table>")


def grid(title: str, headers: list[str], rows: Iterable[Iterable[str]], note: str = "") -> str:
    """Free-form numeric table (bar schedules, capacity tables, registers)."""
    head = "".join(f'<th class="num">{esc(name)}</th>' for name in headers[1:])
    body = "".join(
        "<tr>" + f"<td>{cells[0]}</td>"
        + "".join(f'<td class="num">{cell}</td>' for cell in cells[1:]) + "</tr>"
        for cells in (list(item) for item in rows))
    caption = f'<p class="dct-caption">{esc(note)}</p>' if note else ""
    return (f'<h2>{title}</h2>{caption}<table class="calc dct">'
            f'<thead><tr><th>{esc(headers[0])}</th>{head}</tr></thead>'
            f"<tbody>{body}</tbody></table>")


def prose(title: str, body_html: str, *, weight: int = 12) -> str:
    """Narrative block; ``weight`` declares how many table rows of depth it uses."""
    heading = f"<h2>{esc(title)}</h2>" if title else ""
    return f'<!--weight:{weight}--><section class="prose">{heading}{body_html}</section>'


# ---------------------------------------------------------------------------
#  Sheet assembly
# ---------------------------------------------------------------------------
def identity(inputs: dict[str, Any], page_number: int, total: int,
             default_subject: str = "Calculation", logo_path: str | None = None) -> str:
    """Innovis calculation-pad header block."""
    member = "-".join(part for part in (str(inputs.get("memberType", "")).strip(),
                                        str(inputs.get("memberNumber", "")).strip()) if part)
    subject = inputs.get("subject") or default_subject
    heading = f"{member} - {subject}" if member else str(subject)
    date = inputs.get("date") or datetime.now().strftime("%d/%m/%Y")
    logo = logo_data_uri(logo_path)
    brand = f'<img src="{logo}" alt="Innovis">' if logo else "INNOVIS"
    return f"""
        <div class="brand">{brand}</div>
    <table class="identity">
            <colgroup><col class="identity-main"><col class="identity-mid"><col class="identity-end"></colgroup>
            <tr><td><b>Client:</b> {esc(inputs.get('client', ''))}</td><td colspan="2"><b>Project No:</b> {esc(inputs.get('projectno', ''))}</td></tr>
            <tr><td><b>Project:</b> {esc(inputs.get('project', ''))}</td><td><b>By:</b> {esc(inputs.get('designer', ''))}</td><td><b>Date:</b> {esc(date)}</td></tr>
            <tr><td><b>Subject:</b> {esc(heading)}</td><td><b>Chk:</b> {esc(inputs.get('checker', ''))}</td><td><b>Sheet No:</b> {page_number} of {total}</td></tr>
    </table>"""


def page(inputs: dict[str, Any], page_number: int, total: int, body: str, *,
         default_subject: str = "Calculation", anchor: str = "",
         contents_href: str = "", logo_path: str | None = None) -> str:
    """One A4 sheet."""
    anchor_attr = f' id="{esc(anchor)}"' if anchor else ""
    back = (f'<a class="contents-link" href="{esc(contents_href)}">Contents</a>'
            if contents_href else "")
    return (f'<section class="calc-page"{anchor_attr} data-sheet="{page_number}">'
            f'{identity(inputs, page_number, total, default_subject, logo_path)}'
            f'<div class="sheet-body">{body}</div>{back}</section>')


def pack_pages(blocks: Iterable[str], capacity: int = SHEET_CAPACITY) -> list[str]:
    """Fill sheets without splitting a calculation section across a page break.

    A block may declare its own depth with an ``<!--weight:n-->`` comment;
    otherwise its table-row count is used.
    """
    pages: list[str] = []
    current: list[str] = []
    used = 0
    for block in filter(None, blocks):
        declared = re.search(r"<!--weight:(\d+)-->", block)
        weight = (int(declared.group(1)) if declared else block.count("<tr>")) + 3
        if current and used + weight > capacity:
            pages.append("".join(current))
            current, used = [], 0
        current.append(block)
        used += weight
    if current:
        pages.append("".join(current))
    return pages


def render(inputs: dict[str, Any], blocks: list[str], *,
           default_subject: str = "Calculation",
           appendix: list[str] | None = None,
           standalone: bool = False,
           title: str | None = None,
           module_dir: Path | str | None = None,
           data_id: str = "calcpad-inputs",
           anchor_prefix: str = "",
           contents_href: str = "",
           capacity: int = SHEET_CAPACITY,
           logo_path: str | None = None) -> str:
    """Assemble calculation blocks into a paginated calculation-pad document."""
    bodies = pack_pages(blocks, capacity)
    # Appendices (verification extracts, markups) always start a fresh sheet.
    bodies.extend(pack_pages(appendix or [], capacity))
    total = len(bodies) or 1
    sheets = "".join(
        page(inputs, index + 1, total, body, default_subject=default_subject,
             anchor=f"{anchor_prefix}{'' if index == 0 else f'-p{index + 1}'}" if anchor_prefix else "",
             contents_href=contents_href, logo_path=logo_path)
        for index, body in enumerate(bodies or [""]))
    machine_data = json.dumps(inputs, ensure_ascii=True, default=str).replace("</", "<\\/")
    content = (f'<div class="report-document">{sheets}</div>'
               f'<script id="{esc(data_id)}" type="application/json">{machine_data}</script>')
    if not standalone:
        return content
    heading = title or str(inputs.get("subject") or default_subject)
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{esc(heading)}</title>"
            f"<style>{stylesheet(module_dir)}</style></head><body>{content}</body></html>")
