"""Engineering notation and number formatting for Innovis calculation sheets.

Shared by every calculation module so that a symbol printed by the steel module
looks identical to the same symbol printed by the concrete module or the
calculation pad.
"""

from __future__ import annotations

import html
import math
import re
from typing import Any

GREEK = {"phi": "\u03c6", "alpha": "\u03b1", "beta": "\u03b2", "gamma": "\u03b3",
         "lambda": "\u03bb", "delta": "\u03b4", "psi": "\u03c8", "rho": "\u03c1",
         "theta": "\u03b8", "eps": "\u03b5", "sigma": "\u03c3", "mu": "\u03bc",
         "tau": "\u03c4", "omega": "\u03c9", "nu": "\u03bd", "pi": "\u03c0"}
GREEK_PATTERN = "|".join(sorted(GREEK, key=len, reverse=True))
MATH_CHARS = set("=+*/^<>")
# Short capitalised words that are prose rather than symbols.
NOT_SYMBOLS = {"Eq", "Cl", "Sec", "Not", "Use", "The", "And", "For", "Min", "Max",
               "Fig", "Tab", "All", "Yes", "No", "Per", "Of", "In", "At", "To",
               "Its", "Non", "One", "Two", "Bar", "Bars", "Web", "Ast"}


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def number(value: Any, digits: int = 1) -> str:
    """Thousands-separated value that keeps meaningful precision on small numbers."""
    try:
        numeric = float(value)
        if not math.isfinite(numeric):
            return "inf"
        decimals = digits
        if numeric and round(numeric, decimals) == 0:
            decimals = min(6, max(decimals, -int(f"{abs(numeric):e}".split("e")[1]) + 1))
        rendered = f"{numeric:,.{decimals}f}"
        if "." in rendered:
            rendered = rendered.rstrip("0").rstrip(".")
        return rendered
    except (TypeError, ValueError):
        return "-"


def force(value: Any, digits: int = 1) -> str:
    """N -> kN."""
    try:
        return number(float(value) / 1e3, digits)
    except (TypeError, ValueError):
        return "-"


def moment(value: Any, digits: int = 1) -> str:
    """N mm -> kN m."""
    try:
        return number(float(value) / 1e6, digits)
    except (TypeError, ValueError):
        return "-"


def badge(ratio: Any) -> str:
    """Pass/fail chip carrying the utilisation that produced it."""
    try:
        value = float(ratio)
    except (TypeError, ValueError):
        return '<span class="status fail">FAIL</span>'
    if not math.isfinite(value):
        return '<span class="status fail">FAIL</span>'
    status = "OK" if value <= 1.0 else "FAIL"
    return f'<span class="status {status.lower()}">{status} ({number(value, 3)})</span>'


def notation(expression: Any) -> str:
    """Render a trusted calculation expression using engineering notation.

    Descriptive wording is passed through untouched so plain-language bases are
    not mangled into subscripts.
    """
    text = str(expression if expression is not None else "")
    formula = (any(char in MATH_CHARS for char in text)
               or re.search(rf"\b({GREEK_PATTERN})\b", text))
    value = esc(text)
    if not formula:
        return value
    value = value.replace(" x ", " \u00d7 ")
    value = re.sub(r"\b([A-Za-z]+)\*([A-Za-z]+)\b", r"\1[[SUP:*]][[SUB:\2]]", value)

    def subscript(match: re.Match) -> str:
        word = match.group(0)
        if word in NOT_SYMBOLS:
            return word
        return f"{match.group(1)}[[SUB:{match.group(2)}]]"

    value = re.sub(r"\b([A-Z])([a-z][A-Za-z0-9]{0,2})\b", subscript, value)
    value = re.sub(r"\b([A-Za-z0-9]+)\^([0-9.]+)", r"\1[[SUP:\2]]", value)
    value = re.sub(r"(?<=\))\^([0-9.]+)", r"[[SUP:\1]]", value)
    value = re.sub(rf"\b({GREEK_PATTERN})([A-Z][A-Za-z0-9,.]*)", lambda match: (
        GREEK[match.group(1)] + match.group(2)[0]
        + (f"[[SUB:{match.group(2)[1:]}]]" if len(match.group(2)) > 1 else "")), value)
    value = re.sub(rf"\b({GREEK_PATTERN})(?:_([A-Za-z0-9,.]+))?", lambda match: (
        GREEK[match.group(1)] + (f"[[SUB:{match.group(2)}]]" if match.group(2) else "")), value)
    value = re.sub(r"\[\[(SUB|SUP):([^]]+)]]",
                   lambda match: f"<{match.group(1).lower()}>{match.group(2)}"
                                 f"</{match.group(1).lower()}>", value)
    return value
