"""Collate finalised calculations into one PDF with a linked contents page.

The native calculation body is rendered as a single HTML document and printed
once, so the contents entries and the ``Contents`` link on every sheet become
genuine PDF links.  Calculations imported as PDF, drawing sets and PDF inserts
are spliced into their proper place afterwards, and the issued package is
watermarked and flattened.
"""

from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import calcpad

from . import pdf as pdf_tools
from .library import IMPORTED, Library, safe_name

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
            "description": record.get("description", ""),
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
        label = html.escape(entry["title"] or entry["memberType"])
        name = (f'<a href="#{html.escape(entry["anchor"])}">{label}</a>'
                if entry.get("anchor") else label)
        rows.append(
            f'<tr><td>{name}</td>'
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
    """Plan the package: the printable body, and where every PDF part belongs.

    Calculations produced in other software are held as PDF only, so the body is
    printed from the native calculations alone and the imported sheets are
    spliced into their proper place afterwards.  ``inserts`` records where each
    one goes, which is what keeps the contents page sheet numbers honest.
    """
    wanted = list(dict.fromkeys(selection or []))
    available = {item["id"]: item for item in selectable(library, include_superseded=include_superseded)}
    entries = order([available[item] for item in wanted if item in available], sort_fields)
    if not entries:
        raise ValueError("Select at least one calculation to export")

    sheets: list[str] = []
    inserts: list[dict[str, Any]] = []
    body_page = 1          # the contents sheet is body page 1
    sheet_number = 2
    for position, entry in enumerate(entries, start=1):
        record = library.calculation(entry["id"])
        entry["startSheet"] = sheet_number
        if record.get("module") == IMPORTED:
            source = library.folder_of(record) / record["revisions"][-1]["filename"]
            count = pdf_tools.page_count(source) or 1
            entry["imported"] = True
            entry["sheets"] = count
            inserts.append({"path": str(source), "pages": "", "after": body_page})
            sheet_number += count
            continue

        module = registry.get(record["module"])
        anchor = f"calc-{position:03d}"
        entry["anchor"] = anchor
        inputs = {**(record.get("inputs") or {}), **{key: meta[key] for key in
                                                     ("client", "project", "projectno",
                                                      "designer") if key in meta},
                  "checker": record.get("checker", "")}
        result = module.call("compute", inputs)
        body = module.call("render", inputs, result, standalone=False,
                           anchor_prefix=anchor, contents_href="#innocalc-contents")
        sheets.append(body)
        printed = body.count('class="calc-page"') or 1
        body_page += printed
        entry["sheets"] = printed
        for cell in result.get("attachments") or []:
            if not cell.get("exists"):
                continue
            pages = pdf_tools.parse_pages(cell.get("pages"), pdf_tools.page_count(cell["path"]))
            inserts.append({"path": cell["path"], "pages": cell.get("pages", ""),
                            "title": cell.get("title", ""), "after": body_page})
            entry["sheets"] += len(pages) or 1
        sheet_number += entry["sheets"]

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
            "bodyPages": body_page, "sheets": sheet_number - 1}


def drawings_name(reference: str, title: str, initials: str) -> str:
    """'JXXXX-STR-VER-0001 - TITLE - DRAWINGS - AB'."""
    reference = str(reference or "").strip() or "PACKAGE"
    initials = re.sub(r"[^A-Za-z]", "", str(initials)).upper()[:4] or "XX"
    return safe_name(f"{reference} - {str(title or 'PACKAGE').upper()} - DRAWINGS - {initials}")


def watermark_text(purpose: str, when: datetime | None = None) -> str:
    stamp = (when or datetime.now()).strftime("%d/%m/%Y")
    return f"PACKAGE PREPARED {stamp} FOR {str(purpose or 'ISSUE').upper()}"


def build_pdf(library: Library, registry: Any, selection: list[str], meta: dict[str, Any],
              destination: Path, *, sort_fields: list[str] | None = None,
              include_superseded: bool = False,
              drawings: list[dict[str, Any]] | None = None,
              reference: str = "", purpose: str = "",
              verifier_initials: str = "") -> dict[str, Any]:
    """Write the collated calculation package as HTML and PDF.

    Drawings are issued twice: once as a flattened standalone file named for the
    package, and again appended to the rear of the combined document.  The
    combined document is watermarked with the issue purpose and flattened, so an
    issued package cannot be edited and is ready for the verifier's markups.
    """
    built = build_html(library, registry, selection, meta, sort_fields=sort_fields,
                       include_superseded=include_superseded)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    html_path = destination.with_suffix(".html")
    html_path.write_text(built["html"], encoding="utf-8")
    body_pdf = destination.with_name(destination.stem + " - body.pdf")
    pdf_tools.export_pdf(html_path, body_pdf)

    inserts = list(built["inserts"])
    drawing_parts = [{"path": str(item.get("path", "")), "pages": item.get("pages", "")}
                     for item in (drawings or []) if item.get("path")]
    drawings_path = ""
    if drawing_parts:
        drawings_path = str(destination.with_name(
            drawings_name(reference, meta.get("title", ""), verifier_initials) + ".pdf"))
        try:
            pdf_tools.merge(drawing_parts, drawings_path)
            pdf_tools.flatten(drawings_path)
        except RuntimeError:
            drawings_path = ""
        # The same drawings also go on the back of the combined document.
        inserts.extend({**part, "after": built["bodyPages"]} for part in drawing_parts)

    stamp = watermark_text(purpose)
    combined = True
    try:
        if inserts:
            pdf_tools.splice(body_pdf, inserts, destination)
            body_pdf.unlink(missing_ok=True)
        else:
            body_pdf.replace(destination)
    except RuntimeError:
        body_pdf.replace(destination)
        combined = False
    flattened = False
    try:
        pdf_tools.stamp(destination, stamp)
        pdf_tools.flatten(destination)
        if drawings_path:
            pdf_tools.stamp(drawings_path, stamp)
        flattened = True
    except (RuntimeError, OSError, ValueError):
        flattened = False
    return {"pdfPath": str(destination), "htmlPath": str(html_path),
            "drawingsPath": drawings_path, "watermark": stamp, "flattened": flattened,
            "entries": [{key: value for key, value in entry.items()} for entry in built["entries"]],
            "sheets": built["sheets"], "attachments": len(inserts), "combined": combined}
