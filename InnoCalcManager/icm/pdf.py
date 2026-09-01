"""PDF production for InnoCalc Manager.

HTML is printed with an installed Chromium browser, which keeps in-document
anchors as real PDF links - that is what makes the contents page and the
per-sheet Contents link work in the exported calculation package.  ``pypdf``, if
installed, is used to splice in drawing sets and Bluebeam markups.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from calcpad.export import browser_path, export_pdf

__all__ = ["browser_path", "export_pdf", "page_count", "parse_pages", "merge", "available"]


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
    """Combine PDFs. Each part is ``{"path": ..., "pages": "1,3-5"}``."""
    pypdf = _pypdf()
    writer = pypdf.PdfWriter()
    for part in parts:
        source = Path(str(part.get("path", "")))
        if not source.is_file():
            continue
        reader = pypdf.PdfReader(str(source))
        for index in parse_pages(part.get("pages"), len(reader.pages)):
            writer.add_page(reader.pages[index])
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
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
