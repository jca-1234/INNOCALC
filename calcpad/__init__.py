"""Innovis calculation presentation and templating package.

Separated from the design modules so the steel, concrete, calculation-pad and
future modules - and InnoCalc Manager itself - all render on the same
Innovis A4 calculation pad without duplicating template code.

Typical use from a design module::

    from calcpad import row, table, render

    blocks = [table("Bending", [row("Capacity", "phi Ms", "125 kNm", "Cl 5.2.1")])]
    html = render(inputs, blocks, default_subject="Steel member design",
                  standalone=True, module_dir=MODULE_DIR)
"""

from __future__ import annotations

from .notation import badge, esc, force, moment, notation, number
from .export import browser_path, export_pdf
from .sheet import (SHEET_CAPACITY, grid, identity, logo_data_uri, pack_pages, page,
                    prose, render, row, stylesheet, table, theme_css)

__all__ = [
    "badge", "esc", "force", "moment", "notation", "number",
    "browser_path", "export_pdf",
    "SHEET_CAPACITY", "grid", "identity", "logo_data_uri", "pack_pages", "page",
    "prose", "render", "row", "stylesheet", "table", "theme_css",
]

VERSION = "V0.01"
