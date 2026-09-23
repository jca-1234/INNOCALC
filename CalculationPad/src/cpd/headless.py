"""Headless entry point for the Calculation Pad module.

Implements the same contract as the steel and concrete modules so InnoCalc
Manager hosts all three identically.  See ``docs/MODULE-SPECIFICATION.md``.
"""

from __future__ import annotations

import html
import math
import re
from pathlib import Path
from typing import Any

import calcpad

from . import environment, notebook, symbolic, units
from .evaluator import FUNCTIONS, declarations, retype, run, to_html
from .version import VERSION

MODULE_DIR = Path(__file__).resolve().parent.parent
MODULE_ID = "calculation-pad"

DESCRIPTOR: dict[str, Any] = {
    "id": MODULE_ID,
    "name": "Calculation Pad",
    "short": "Calc Pad",
    "standard": "Engineer defined",
    "folder": "90 - CALCULATION PAD",
    "status": "available",
    "version": VERSION,
    "defaultSubject": "Engineering calculation",
    "calcType": "Calculation pad",
    "description": ("Free-form interactive calculation sheet with symbolic display, "
                    "physical units, narrative, drawing and Bluebeam markup inserts, "
                    "and blank A4 or A3 sheets, printed on the Innovis calculation pad."),
    "capabilities": ["compute", "render", "cells", "notebook", "attachments",
                     "liveEditing", "declaredVariables", "units"],
    "entry": "cpd.headless",
    "editor": "cells",
}

CELL_TYPES = [
    {"id": "heading", "label": "Section heading"},
    {"id": "text", "label": "Narrative / assumptions"},
    {"id": "calc", "label": "Calculation"},
    {"id": "image", "label": "Figure or sketch"},
    {"id": "pdf", "label": "PDF drawing or Bluebeam markup"},
    {"id": "blank", "label": "Blank sheet for hand additions"},
]

STARTER_CELLS = [
    {"id": "c1", "type": "heading", "title": "Design basis"},
    {"id": "c2", "type": "text",
     "source": "State the design intent, standards, assumptions and references here.\n"
               "Each line becomes a paragraph; a line starting with - becomes a bullet."},
    {"id": "c3", "type": "calc", "title": "Worked calculation",
     "source": "# Simply supported beam, uniformly distributed load\n"
               "w = 5.0 kN/m\n"
               "L = 6.0 m\n"
               "M_max = w * L^2 / 8   # kNm\n"
               "V_max = w * L / 2     # kN"},
]


def descriptor() -> dict[str, Any]:
    return dict(DESCRIPTOR)


def schema() -> dict[str, Any]:
    libraries = environment.ensure()
    return {
        **descriptor(),
        "identity": {"typeLabel": "Calculation type", "numberLabel": "Calculation number",
                     "typeOptions": ["Calculation", "Design note", "Assessment",
                                     "Load takedown", "Assumptions", "Sketch"]},
        "cellTypes": CELL_TYPES,
        "learning": notebook.learning(),
        "functions": sorted(FUNCTIONS),
        "libraries": libraries,
        "liveEditing": True,
        "groups": [
            {"id": "sheet", "title": "Sheet", "fields": [
                {"id": "paper", "label": "Sheet size", "type": "select", "default": "A4",
                 "options": [{"value": "A4", "label": "A4 portrait"},
                             {"value": "A3", "label": "A3 landscape"}]},
                {"id": "unitMode", "label": "Units", "type": "select", "default": "on",
                 "options": [{"value": "on", "label": "Track units (Pint)"},
                             {"value": "off", "label": "Plain numbers, units as labels"}]},
                {"id": "typeset", "label": "Typeset equations (SymPy)", "type": "checkbox",
                 "default": False},
                {"id": "showSource", "label": "Print the calculation source", "type": "checkbox",
                 "default": False, "width": "full"},
            ]},
        ],
        "optional": [],
        "actions": [
            {"id": "export-notebook", "label": "Export as Jupyter notebook"},
            {"id": "check-libraries", "label": "Check Pint and SymPy"},
            {"id": "add-blank-a4", "label": "Insert blank A4 sheet"},
            {"id": "add-blank-a3", "label": "Insert blank A3 sheet"},
        ],
    }


def defaults() -> dict[str, Any]:
    return {"memberType": "Calculation", "memberNumber": "0001", "package": "Unallocated",
            "level": "", "subject": DESCRIPTOR["defaultSubject"], "paper": "A4",
            "unitMode": "on", "typeset": False,
            "showSource": False, "checks": {},
            "cells": [dict(cell) for cell in STARTER_CELLS]}


# ---------------------------------------------------------------------------
#  Calculation
# ---------------------------------------------------------------------------
def compute(inputs: dict[str, Any]) -> dict[str, Any]:
    """Evaluate every calculation cell in order, sharing one variable scope."""
    use_units = str(inputs.get("unitMode", "on")) != "off"
    typeset = bool(inputs.get("typeset"))
    libraries = environment.ensure(install=False)
    required = {"pint"} if use_units else set()
    if typeset:
        required.add("sympy")
    missing = [item["package"] for item in libraries["packages"]
               if item["package"] in required and not item["installed"]]
    if missing:
        raise ValueError("Required calculation libraries are missing: " + ", ".join(missing)
                         + ". Run the suite setup command.")
    scope: dict[str, Any] = {}
    cells: list[dict[str, Any]] = []
    declared: list[dict[str, Any]] = []
    errors = 0
    for index, cell in enumerate(inputs.get("cells") or []):
        record = {"index": index, "id": cell.get("id") or f"c{index + 1}",
                  "type": cell.get("type", "text"), "title": cell.get("title", "")}
        if record["type"] == "calc":
            source = str(cell.get("source") or "")
            outcome = run(source, scope, use_units=use_units, typeset=typeset)
            scope = outcome["scope"]
            record["source"] = source
            record["lines"] = outcome["lines"]
            record["ok"] = outcome["ok"]
            declared.extend({"cellId": record["id"], "cellTitle": record["title"], **item}
                            for item in declarations(outcome["lines"]))
            errors += 0 if outcome["ok"] else 1
        elif record["type"] == "pdf":
            record.update({"path": str(cell.get("path") or ""),
                           "pages": str(cell.get("pages") or ""),
                           "size": cell.get("size", "A4"),
                           "exists": bool(cell.get("path")) and Path(str(cell["path"])).is_file()})
            if not record["exists"]:
                errors += 1
        elif record["type"] == "image":
            record["data"] = str(cell.get("data") or "")
        elif record["type"] == "blank":
            record.update({"size": cell.get("size", "A4"),
                           "orientation": cell.get("orientation", "portrait")})
        else:
            record["source"] = str(cell.get("source") or "")
        cells.append(record)
    variables = _variables(cells)
    labels = _labels(cells)
    utilisation = variables.get("utilisation", variables.get("util", 0.0))
    return {"module": MODULE_ID, "cells": cells, "variables": variables,
            "variableUnits": labels, "declared": declared,
            "libraries": environment.ensure(),
            "errors": errors, "checks": inputs.get("checks") or {},
            "util": {"declared": float(utilisation)} if utilisation else {},
            "worstUtil": float(utilisation or 0.0),
            "attachments": [cell for cell in cells if cell["type"] == "pdf"]}


def _variables(cells: list[dict[str, Any]]) -> dict[str, float]:
    """Every resolved value as a plain number, in the unit the engineer wrote."""
    values: dict[str, float] = {}
    for cell in cells:
        for line in cell.get("lines", []):
            if line.get("kind") == "assign" and isinstance(line.get("numeric"), float) \
                    and math.isfinite(line["numeric"]):
                values[line["name"]] = line["numeric"]
    return values


def _labels(cells: list[dict[str, Any]]) -> dict[str, str]:
    return {line["name"]: line.get("unitText", "")
            for cell in cells for line in cell.get("lines", [])
            if line.get("kind") == "assign" and line.get("unitText")}


def set_declared(inputs: dict[str, Any], cell_id: str, line_index: int,
                 literal: str) -> dict[str, Any]:
    """Retype one declared value in place, leaving the rest of the line alone."""
    try:
        value = float(str(literal).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{literal}' is not a number") from exc
    values = dict(inputs)
    cells = [dict(cell) for cell in values.get("cells") or []]
    for cell in cells:
        if cell.get("id") != cell_id or cell.get("type") != "calc":
            continue
        lines = str(cell.get("source") or "").splitlines()
        if not 0 <= line_index < len(lines):
            raise ValueError("That line is no longer in the cell")
        text = str(int(value)) if value == int(value) else f"{value:g}"
        rewritten = retype(lines[line_index], text)
        if rewritten is None:
            raise ValueError("That line is not a declared value")
        lines[line_index] = rewritten
        cell["source"] = "\n".join(lines)
        values["cells"] = cells
        return values
    raise ValueError(f"No calculation cell '{cell_id}'")


def summarise(result: dict[str, Any]) -> dict[str, Any]:
    worst = float(result.get("worstUtil") or 0.0)
    if result.get("errors"):
        return {"worstUtil": worst, "criticalCheck": "Unresolved cells", "status": "FAIL",
                "headline": f"{result['errors']} cell(s) could not be resolved"}
    if worst:
        return {"worstUtil": worst, "criticalCheck": "Declared utilisation",
                "status": "OK" if worst <= 1.0 else "FAIL",
                "headline": f"{worst * 100:.1f}% - declared utilisation"}
    return {"worstUtil": 0.0, "criticalCheck": "", "status": "OK",
            "headline": f"{len(result.get('cells', []))} cell(s) complete"}


def identity(inputs: dict[str, Any]) -> dict[str, Any]:
    return {"memberType": str(inputs.get("memberType") or "Calculation"),
            "memberNumber": str(inputs.get("memberNumber") or ""),
            "package": str(inputs.get("package") or "Unallocated"),
            "level": str(inputs.get("level") or ""),
            "calcType": DESCRIPTOR["calcType"],
            "title": str(inputs.get("subject") or DESCRIPTOR["defaultSubject"])}


# ---------------------------------------------------------------------------
#  Presentation
# ---------------------------------------------------------------------------
_BULLET = re.compile(r"^\s*[-*]\s+")


def _narrative(source: str) -> str:
    paragraphs: list[str] = []
    bullets: list[str] = []
    for line in source.splitlines():
        if _BULLET.match(line):
            bullets.append(f"<li>{html.escape(_BULLET.sub('', line).strip())}</li>")
            continue
        if bullets:
            paragraphs.append(f"<ul>{''.join(bullets)}</ul>")
            bullets = []
        if line.strip():
            paragraphs.append(f"<p>{html.escape(line.strip())}</p>")
    if bullets:
        paragraphs.append(f"<ul>{''.join(bullets)}</ul>")
    return "".join(paragraphs)


def _calculation_block(cell: dict[str, Any], *, show_source: bool, typeset: bool,
                       interactive: bool) -> str:
    """A calculation cell, editable in place when the sheet is on screen."""
    title = cell.get("title", "")
    body = to_html(cell.get("lines", []), typeset=typeset)
    source = cell.get("source", "")
    if not interactive:
        if show_source and source:
            body = f'<pre class="pad-source">{html.escape(source)}</pre>{body}'
        return calcpad.prose(title, body, weight=3 + 2 * len(cell.get("lines", [])))
    identifier = html.escape(cell["id"])
    rows = max(3, source.count("\n") + 2)
    weight = 6 + rows + 2 * len(cell.get("lines", []))
    return (f'<!--weight:{weight}--><section class="prose pad-live" data-pad-cell="{identifier}">'
            f'<h2><input class="pad-live-title" data-pad-title="{identifier}" '
            f'placeholder="Untitled calculation" value="{html.escape(title)}"></h2>'
            f'<textarea class="pad-live-source" spellcheck="false" rows="{rows}" '
            f'data-pad-source="{identifier}" placeholder="w = 5 kN/m">'
            f'{html.escape(source)}</textarea>'
            f'<div class="pad-live-result">{body}</div>'
            f'<div class="pad-live-tools">'
            f'<button type="button" data-pad-add="{identifier}">+ calculation below</button>'
            f'<button type="button" data-pad-delete="{identifier}">delete cell</button>'
            f'</div></section>')


def _blocks(inputs: dict[str, Any], result: dict[str, Any], *,
            interactive: bool = False) -> list[str]:
    show_source = bool(inputs.get("showSource"))
    typeset = bool(inputs.get("typeset"))
    blocks: list[str] = []
    for cell in result["cells"]:
        title = cell.get("title", "")
        if cell["type"] == "heading":
            blocks.append(calcpad.prose(title, "", weight=3))
        elif cell["type"] == "text":
            blocks.append(calcpad.prose(title, _narrative(cell.get("source", "")),
                                        weight=4 + cell.get("source", "").count("\n")))
        elif cell["type"] == "calc":
            blocks.append(_calculation_block(cell, show_source=show_source, typeset=typeset,
                                             interactive=interactive))
        elif cell["type"] == "image":
            blocks.append(calcpad.prose(
                title, f'<p><img src="{html.escape(cell.get("data", ""))}" '
                       'style="max-width:100%;max-height:150mm" alt="figure"></p>', weight=40))
        elif cell["type"] == "pdf":
            note = ("attached at export" if cell.get("exists")
                    else "FILE NOT FOUND - the insert will be omitted")
            blocks.append(
                f'<!--weight:44--><section class="prose pdf-insert" '
                f'data-insert-pdf="{html.escape(cell.get("path", ""))}" '
                f'data-insert-pages="{html.escape(cell.get("pages", ""))}">'
                f'<h2>{html.escape(title or "Drawing / markup insert")}</h2>'
                f'<p>{html.escape(Path(cell.get("path", "")).name)} '
                f'(pages {html.escape(cell.get("pages") or "all")}) - {note}</p></section>')
        elif cell["type"] == "blank":
            size = cell.get("size", "A4")
            blocks.append(
                f'<!--weight:44--><section class="prose pad-blank-sheet" '
                f'data-blank="{html.escape(size)}">'
                f'<h2>{html.escape(title or f"Blank {size} sheet")}</h2>'
                f'<div class="pad-blank"></div></section>')
    if not blocks:
        blocks.append(calcpad.prose("Calculation Pad", "<p>This pad is empty.</p>"))
    if interactive:
        blocks.append('<!--weight:6--><section class="prose pad-live-add">'
                      '<button type="button" data-pad-add="">+ calculation</button>'
                      '</section>')
    return blocks


def render(inputs: dict[str, Any], result: dict[str, Any], *, standalone: bool = False,
           appendix: list[str] | None = None, anchor_prefix: str = "",
           contents_href: str = "", interactive: bool = False) -> str:
    """The calculation sheet; ``interactive`` makes the calculations typeable."""
    return calcpad.render(inputs, _blocks(inputs, result, interactive=interactive),
                          default_subject=DESCRIPTOR["defaultSubject"],
                          appendix=appendix, standalone=standalone,
                          title=f"{identity(inputs)['title']} - Calculation Pad {VERSION}",
                          module_dir=MODULE_DIR, data_id="cpd-inputs",
                          anchor_prefix=anchor_prefix, contents_href=contents_href)


# ---------------------------------------------------------------------------
#  Exchange, actions, validation
# ---------------------------------------------------------------------------
def exchange(inputs: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    variables = result.get("variables") or {}
    return {"schema": "innocalc.exchange/1",
            "source": {"module": MODULE_ID, "version": VERSION, **identity(inputs)},
            "axial": {"compression_kN": variables.get("N_c", 0.0),
                      "tension_kN": variables.get("N_t", 0.0)},
            "moments": {"Mx_kNm": variables.get("M_x", variables.get("M_max", 0.0)),
                        "My_kNm": variables.get("M_y", 0.0)},
            "reactions": {"support_kN": variables.get("R", variables.get("V_max", 0.0))},
            "geometry": {"length_mm": variables.get("L_mm", 0.0)},
            "variables": variables,
            "utilisation": summarise(result)}


ACCEPTS = ["variables", "axial", "moments", "reactions", "geometry"]


def accepts() -> list[str]:
    return list(ACCEPTS)


def apply_exchange(inputs: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Bring another calculation's values in as a read-only preamble cell."""
    source = payload.get("source", {})
    lines = [f"# Imported from {source.get('module', '')} {source.get('title', '')}"]
    for group in ("axial", "moments", "reactions", "geometry"):
        for key, value in (payload.get(group) or {}).items():
            if isinstance(value, (int, float)) and value:
                lines.append(f"{re.sub(r'[^A-Za-z0-9_]', '_', key)} = {value}")
    for key, value in (payload.get("variables") or {}).items():
        lines.append(f"{re.sub(r'[^A-Za-z0-9_]', '_', key)} = {value}")
    values = dict(inputs)
    cells = list(values.get("cells") or [])
    cells.insert(0, {"id": f"import-{len(cells)}", "type": "calc",
                     "title": "Imported values", "source": "\n".join(lines)})
    values["cells"] = cells
    values.setdefault("linkedFrom", []).append(source)
    return values


def run_action(action_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    if action_id == "export-notebook":
        return {"file": {"name": f"{identity(inputs)['title']}.ipynb",
                         "content": notebook.notebook_text(inputs),
                         "type": "application/x-ipynb+json"},
                "message": "Notebook exported; open it with Jupyter, Pint and handcalcs"}
    if action_id == "check-libraries":
        report = environment.ensure(refresh=True)
        missing = [item["package"] for item in report["packages"]
                   if item["required"] and not item["installed"]]
        spare = [item["package"] for item in report["packages"]
                 if not item["required"] and not item["installed"]]
        if missing:
            message = "Not installed: " + ", ".join(missing)
        else:
            message = "Pint and SymPy are ready"
            if spare:
                message += f"; {', '.join(spare)} are only needed once a pad is exported"
        return {"libraries": report, "message": message}
    if action_id in {"add-blank-a4", "add-blank-a3"}:
        size = "A3" if action_id.endswith("a3") else "A4"
        cells = list(inputs.get("cells") or [])
        cells.append({"id": f"blank-{len(cells) + 1}", "type": "blank", "size": size,
                      "title": f"Blank {size} sheet"})
        return {"inputs": {**inputs, "cells": cells}, "message": f"Blank {size} sheet added"}
    raise ValueError(f"Unknown action '{action_id}'")


def validate(cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Prove the evaluator computes correctly, keeps units and rejects unsafe input."""
    checks: list[dict[str, Any]] = [
        {"source": "a = 2\nb = 3\nc = a * b ^ 2", "expect": {"c": 18.0}},
        {"source": "x = sqrt(16) + max(1, 2)", "expect": {"x": 6.0}},
        {"source": "w = 5\nL = 6\nM = w * L ^ 2 / 8", "expect": {"M": 22.5}},
        {"source": "import os", "reject": True},
        {"source": "open('x')", "reject": True},
        {"source": "().__class__", "reject": True},
        {"source": "[i for i in range(3)]", "reject": True},
    ]
    if units.available():
        checks += [
            {"source": "w = 5 kN/m\nL = 6 m\nM = w * L^2 / 8   # kNm",
             "expect": {"M": 22.5}, "expectUnit": {"M": "kNm"}},
            {"source": "L = 6 m\nx = L / 2   # mm", "expect": {"x": 3000.0},
             "expectUnit": {"x": "mm"}},
            {"source": "t = 30 deg\nc = cos(t)", "expect": {"c": 0.8660254038}},
            {"source": "L = 6 m / 2", "expect": {"L": 3.0}, "expectUnit": {"L": "m"}},
            {"source": "F = 10 kN\nd = 2 m\nbad = F + d", "reject": True},
            {"source": "b = 250 mm\nd = 400 mm\nZ = b * d^2 / 6   # mm**3",
             "expect": {"Z": 6666666.666666667}},
        ]
    if symbolic.available():
        checks += [
            {"source": "x = sym(\"x\")\nr = solve(x^2 - 3*x - 10, x)", "declared": []},
            {"source": "x = sym(\"x\")\ny = simplify((x^2 - 1) / (x - 1))", "declared": []},
        ]
    checks += [
        {"source": "w = 5.0 kN/m\nL = 6 m\nM = w * L^2 / 8", "declared": ["w", "L"]},
    ]
    checks.extend(cases or [])

    rows = []
    for case in checks:
        outcome = run(case["source"])
        if case.get("reject"):
            rows.append({"source": case["source"], "ok": not outcome["ok"],
                         "note": "rejected" if not outcome["ok"] else "ACCEPTED UNSAFE INPUT"})
            continue
        problems = []
        for name, expected in (case.get("expect") or {}).items():
            actual = _plain(outcome["scope"].get(name))
            if actual is None or not math.isclose(actual, float(expected),
                                                  rel_tol=1e-9, abs_tol=1e-9):
                problems.append(f"{name} = {actual} expected {expected}")
        for name, expected in (case.get("expectUnit") or {}).items():
            actual = units.format_plain_unit(outcome["scope"].get(name))
            if actual != expected:
                problems.append(f"{name} in '{actual}' expected '{expected}'")
        if "declared" in case:
            found = [item["name"] for item in declarations(outcome["lines"])]
            if found != case["declared"]:
                problems.append(f"declared {found} expected {case['declared']}")
        rows.append({"source": case["source"], "ok": outcome["ok"] and not problems,
                     "note": "; ".join(problems) or "computed"})
    return {"ok": all(row["ok"] for row in rows), "mode": "evaluator",
            "module": MODULE_ID, "version": VERSION, "tested": len(rows), "cases": rows,
            "libraries": environment.ensure()}


def _plain(value: Any) -> float | None:
    value = units.magnitude(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
