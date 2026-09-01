"""Collate finalised calculations into one PDF with a linked contents page.

The whole calculation body is rendered as a single HTML document and printed
once, so the contents entries and the ``Contents`` link on every sheet become
genuine PDF links.  Drawing sets and PDF inserts are spliced in afterwards.
"""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from typing import Any

import calcpad

from . import pdf as pdf_tools
from .library import Library

SORT_FIELDS = [
    {"id": "package", "label": "Package"},
    {"id": "level", "label": "Level"},
    {"id": "calcType", "label": "Calculation type"},
    {"id": "memberType", "label": "Member type"},
    {"id": "memberNumber", "label": "Number"},
    {"id": "status", "label": "Status"},
]
DEFAULT_ORDER = ["package", "level", "calcType", "memberType", "memberNumber"]


def selectable(library: Library, *, include_superseded: bool = False) -> list[dict[str, Any]]:
    """Everything that could go into a package, newest revision first."""
    rows = []
    for record in library.data["calculations"]:
        revisions = [item for item in record.get("revisions", [])
                     if include_superseded or not item.get("superseded")]
        if not revisions:
            continue
        latest = revisions[-1]
        rows.append({
            "id": record["id"], "module": record.get("module", ""),
            "package": record.get("package", "Unallocated"),
            "level": record.get("level", ""), "calcType": record.get("calcType", ""),
            "memberType": record.get("memberType", ""),
            "memberNumber": record.get("memberNumber", ""),
            "title": record.get("title", ""), "status": record.get("status", ""),
            "worstUtil": record.get("worstUtil", 0.0),
            "criticalCheck": record.get("criticalCheck", ""),
            "finalised": bool(record.get("finalised")),
            "revision": latest.get("rev", 1), "savedAt": latest.get("savedAt", ""),
            "initials": latest.get("initials", ""),
            "relativePath": latest.get("relativePath", ""),
        })
    return order(rows, DEFAULT_ORDER)


def order(rows: list[dict[str, Any]], fields: list[str] | None) -> list[dict[str, Any]]:
    """Stable multi-key ordering; later keys are applied first."""
    ordered = list(rows)
    for field in reversed([item for item in (fields or DEFAULT_ORDER)
                           if item in {entry["id"] for entry in SORT_FIELDS}]):
        ordered.sort(key=lambda item: str(item.get(field, "")).casefold())
    return ordered


def _contents_sheet(meta: dict[str, Any], entries: list[dict[str, Any]]) -> str:
    rows = []
    for entry in entries:
        util = (f"{entry['worstUtil'] * 100:.0f}%" if entry.get("worstUtil") else "-")
        rows.append(
            f'<tr><td><a href="#{html.escape(entry["anchor"])}">'
            f'{html.escape(entry["title"] or entry["memberType"])}</a></td>'
            f'<td>{html.escape(entry.get("package", ""))}</td>'
            f'<td>{html.escape(entry.get("level", ""))}</td>'
            f'<td>{html.escape(entry.get("calcType", ""))}</td>'
            f'<td>{html.escape(entry.get("memberType", ""))} '
            f'{html.escape(entry.get("memberNumber", ""))}</td>'
            f'<td>{html.escape(str(entry.get("status", "")))}</td>'
            f'<td class="num">{util}</td>'
            f'<td>{html.escape(entry.get("criticalCheck", ""))}</td>'
            f'<td>{html.escape(str(entry.get("revision", "")))}</td>'
            f'<td>{html.escape(entry.get("savedAt", "").replace("T", " "))}</td>'
            f'<td class="num">{entry["startSheet"]}</td></tr>')
    summary = (f"<p>{len(entries)} calculation(s). "
               f"{sum(1 for item in entries if item.get('status') == 'FAIL')} not satisfied. "
               f"Compiled {datetime.now().strftime('%d/%m/%Y %H:%M')} by "
               f"{html.escape(str(meta.get('designer', '')))}.</p>")
    table = ('<table class="toc-table"><thead><tr>'
             '<th>Calculation</th><th>Package</th><th>Level</th><th>Type</th>'
             '<th>Member</th><th>Status</th><th class="num">Util</th>'
             '<th>Governing check</th><th>Rev</th><th>Saved</th><th class="num">Sheet</th>'
             f'</tr></thead><tbody>{"".join(rows)}</tbody></table>')
    return f'<h2>Calculation Index</h2>{summary}{table}'


def build_html(library: Library, registry: Any, selection: list[str], meta: dict[str, Any],
               *, sort_fields: list[str] | None = None,
               include_superseded: bool = False) -> dict[str, Any]:
    """One HTML document: contents sheet, then every selected calculation."""
    wanted = list(dict.fromkeys(selection or []))
    available = {item["id"]: item for item in selectable(library, include_superseded=include_superseded)}
    entries = order([available[item] for item in wanted if item in available], sort_fields)
    if not entries:
        raise ValueError("Select at least one calculation to export")

    sheets: list[str] = []
    inserts: list[dict[str, Any]] = []
    sheet_number = 2  # sheet 1 is the contents page
    for position, entry in enumerate(entries, start=1):
        record = library.calculation(entry["id"])
        module = registry.get(record["module"])
        anchor = f"calc-{position:03d}"
        entry["anchor"] = anchor
        entry["startSheet"] = sheet_number
        inputs = {**(record.get("inputs") or {}), **{key: meta[key] for key in
                                                     ("client", "project", "projectno",
                                                      "designer", "checker") if key in meta}}
        result = module.call("compute", inputs)
        body = module.call("render", inputs, result, standalone=False,
                           anchor_prefix=anchor, contents_href="#innocalc-contents")
        sheets.append(body)
        entry["sheets"] = body.count('class="calc-page"')
        sheet_number += entry["sheets"]
        for cell in result.get("attachments") or []:
            if cell.get("exists"):
                inserts.append({"path": cell["path"], "pages": cell.get("pages", ""),
                                "title": cell.get("title", "")})

    contents_inputs = {**meta, "memberType": "", "memberNumber": "",
                       "subject": meta.get("title") or "Calculation package"}
    contents = calcpad.page(contents_inputs, 1, sheet_number - 1,
                            _contents_sheet(meta, entries),
                            default_subject="Calculation package",
                            anchor="innocalc-contents")
    document = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                f'<title>{html.escape(str(meta.get("title") or "Calculation package"))}</title>'
                f"<style>{calcpad.theme_css()}</style></head><body>"
                f'<div class="report-document">{contents}{"".join(sheets)}</div>'
                "</body></html>")
    return {"html": document, "entries": entries, "inserts": inserts,
            "sheets": sheet_number - 1}


def build_pdf(library: Library, registry: Any, selection: list[str], meta: dict[str, Any],
              destination: Path, *, sort_fields: list[str] | None = None,
              include_superseded: bool = False,
              drawings: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Write the collated calculation package as HTML and PDF."""
    built = build_html(library, registry, selection, meta, sort_fields=sort_fields,
                       include_superseded=include_superseded)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    html_path = destination.with_suffix(".html")
    html_path.write_text(built["html"], encoding="utf-8")
    body_pdf = destination.with_name(destination.stem + " - body.pdf")
    pdf_tools.export_pdf(html_path, body_pdf)

    parts = [{"path": str(body_pdf)}]
    parts.extend({"path": item["path"], "pages": item.get("pages", "")}
                 for item in built["inserts"])
    parts.extend({"path": item.get("path", ""), "pages": item.get("pages", "")}
                 for item in (drawings or []))
    combined = len(parts) > 1
    if combined:
        try:
            pdf_tools.merge(parts, destination)
            body_pdf.unlink(missing_ok=True)
        except RuntimeError:
            body_pdf.replace(destination)
            combined = False
    else:
        body_pdf.replace(destination)
    return {"pdfPath": str(destination), "htmlPath": str(html_path),
            "entries": [{key: value for key, value in entry.items()} for entry in built["entries"]],
            "sheets": built["sheets"], "attachments": len(parts) - 1, "combined": combined}
