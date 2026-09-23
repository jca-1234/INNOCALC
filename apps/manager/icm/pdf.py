"""PDF production for InnoCalc Manager.

HTML is printed with an installed Chromium browser, which keeps in-document
anchors as real PDF links - that is what makes the contents page and the
per-sheet Contents link work in the exported calculation package.  ``pypdf``, if
installed, is used to splice in drawing sets and Bluebeam markups, to stamp the
issue watermark and to flatten an issued package so it cannot be edited.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any, Iterable

from calcpad.export import browser_path, export_pdf

__all__ = ["browser_path", "export_pdf", "page_count", "parse_pages", "merge", "splice",
           "flatten", "stamp", "available"]


def _pypdf() -> Any:
    try:
        import pypdf
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("Install pypdf to combine PDF documents: pip install pypdf") from exc
    return pypdf


def page_count(path: str | Path) -> int:
    try:
        return len(_pypdf().PdfReader(str(path)).pages)
    except (RuntimeError, OSError, ValueError):
        return 0


def parse_pages(specification: Any, total: int) -> list[int]:
    """'1,3-5' -> zero-based page indices, clamped to the document."""
    text = str(specification or "").strip()
    if not text:
        return list(range(total))
    wanted: list[int] = []
    for chunk in text.replace(" ", "").split(","):
        if not chunk:
            continue
        if "-" in chunk:
            start, _, end = chunk.partition("-")
            try:
                first, last = int(start), int(end or start)
            except ValueError:
                continue
            wanted.extend(range(first - 1, last))
        else:
            try:
                wanted.append(int(chunk) - 1)
            except ValueError:
                continue
    return [index for index in wanted if 0 <= index < total]


def merge(parts: Iterable[dict[str, Any]], destination: str | Path) -> Path:
    """Combine PDFs. Each part is ``{"path": ..., "pages": "1,3-5"}``.

    ``append`` is used rather than ``add_page`` because it carries the link
    annotations and their destinations across, which is what keeps the contents
    page working once drawings or imported calculations are spliced in.
    """
    pypdf = _pypdf()
    writer = pypdf.PdfWriter()
    for part in parts:
        source = Path(str(part.get("path", "")))
        if not source.is_file():
            continue
        reader = pypdf.PdfReader(str(source))
        wanted = parse_pages(part.get("pages"), len(reader.pages))
        if wanted:
            writer.append(reader, pages=wanted)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as handle:
        writer.write(handle)
    return destination


# --------------------------------------------------------------------------
#  Flattening and watermarking an issued package
# --------------------------------------------------------------------------
# Everything a reader could edit or that carries someone else's markup. Link
# annotations are deliberately kept so the contents page still works.
EDITABLE = ["/Text", "/FreeText", "/Line", "/Square", "/Circle", "/Polygon", "/PolyLine",
            "/Highlight", "/Underline", "/Squiggly", "/StrikeOut", "/Caret", "/Stamp",
            "/Ink", "/Popup", "/FileAttachment", "/Sound", "/Movie", "/Screen", "/Widget",
            "/PrinterMark", "/TrapNet", "/Redact", "/Projection", "/RichMedia"]


def flatten(path: str | Path) -> Path:
    """Make an issued PDF permanently non-editable.

    Interactive form fields and any markup carried in from a source document are
    discarded so the issued sheets are fixed content.  The contents page links
    survive, and the file stays open for the verifier's own review markups.
    """
    pypdf = _pypdf()
    path = Path(path)
    reader = pypdf.PdfReader(str(path))
    writer = pypdf.PdfWriter()
    writer.append(reader)
    writer.remove_annotations(subtypes=EDITABLE)
    root = writer._root_object  # noqa: SLF001 - pypdf exposes no public accessor
    if "/AcroForm" in root:
        del root[pypdf.generic.NameObject("/AcroForm")]
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def _escape(text: str) -> str:
    return str(text).replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _overlay(text: str, width: float, height: float, size: float = 9.0) -> bytes:
    """A one-page PDF holding red text in the bottom right corner.

    Written by hand rather than with a drawing library so no dependency beyond
    ``pypdf`` is needed to stamp an issued package.
    """
    # Helvetica-Bold averages about 0.58 em per character; ample for placement.
    inset = 18.0
    x = max(inset, width - inset - len(text) * size * 0.58)
    content = (f"q 1 0 0 rg BT /F1 {size:.1f} Tf {x:.1f} {inset:.1f} Td "
               f"({_escape(text)}) Tj ET Q").encode("latin-1", "replace")
    objects = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        (f"<</Type/Page/Parent 2 0 R/MediaBox[0 0 {width:.2f} {height:.2f}]"
         "/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>").encode("ascii"),
        b"<</Length " + str(len(content)).encode("ascii") + b">>stream\n" + content
        + b"\nendstream",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica-Bold/Encoding/WinAnsiEncoding>>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode("ascii") + body + b"\nendobj\n"
    start = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii")
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode("ascii")
    out += (f"trailer\n<</Size {len(objects) + 1}/Root 1 0 R>>\nstartxref\n"
            f"{start}\n%%EOF\n").encode("ascii")
    return bytes(out)


def stamp(path: str | Path, text: str) -> Path:
    """Stamp red issue text into the bottom right corner of every page."""
    pypdf = _pypdf()
    path = Path(path)
    reader = pypdf.PdfReader(str(path))
    writer = pypdf.PdfWriter()
    writer.append(reader)
    overlays: dict[tuple[int, int], Any] = {}
    # The overlay carries no annotations of its own, which pypdf notes on every
    # page; that would drown the console during an export.
    logger = logging.getLogger("pypdf.generic._link")
    level = logger.level
    logger.setLevel(logging.ERROR)
    try:
        for page in writer.pages:
            box = page.mediabox
            width, height = float(box.width), float(box.height)
            key = (round(width), round(height))
            if key not in overlays:
                overlays[key] = pypdf.PdfReader(io.BytesIO(_overlay(text, width, height))).pages[0]
            page.merge_page(overlays[key], over=True)
    finally:
        logger.setLevel(level)
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def splice(base: str | Path, inserts: Iterable[dict[str, Any]],
           destination: str | Path) -> Path:
    """Insert PDFs into a printed body without disturbing its own links.

    The body is cloned whole and the extra documents are pushed in from the back,
    so the contents page links and the per-sheet Contents links keep working -
    which ``merge`` cannot promise, because it rebuilds the document page by
    page.  Each insert is ``{"path": ..., "pages": "1,3-5", "after": 4}`` where
    ``after`` counts body pages.
    """
    pypdf = _pypdf()
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    writer = pypdf.PdfWriter(clone_from=str(base))
    ordered = sorted((item for item in inserts if Path(str(item.get("path", ""))).is_file()),
                     key=lambda item: int(item.get("after", 0)), reverse=True)
    for insert in ordered:
        reader = pypdf.PdfReader(str(insert["path"]))
        pages = parse_pages(insert.get("pages"), len(reader.pages))
        if pages:
            writer.merge(int(insert.get("after", 0)), reader, pages=pages,
                         import_outline=False)
    with destination.open("wb") as handle:
        writer.write(handle)
    return destination


def available() -> dict[str, Any]:
    try:
        browser = str(browser_path())
    except RuntimeError as exc:
        browser = f"unavailable: {exc}"
    try:
        _pypdf()
        combine = True
    except RuntimeError:
        combine = False
    return {"browser": browser, "canCombine": combine}
