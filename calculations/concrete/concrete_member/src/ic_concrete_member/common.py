"""Input readers and small numeric helpers shared by the engine modules."""

from __future__ import annotations

import math
from typing import Any

ES = 200000.0  # Cl 3.2.2, MPa
EPS_CU = 0.003  # Cl 8.1.3 maximum concrete compressive strain
ROUND_DIGITS = 9  # Settings!O22 "round": bar areas are ROUNDDOWN(pi db^2/4, 9)


def number(inputs: dict[str, Any], key: str, label: str) -> float:
    raw = inputs.get(key)
    if raw in (None, "") or isinstance(raw, bool):
        raise ValueError(f"{label} ({key}) must be supplied as a finite number")
    try:
        value = float(raw)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} ({key}) must be supplied as a finite number") from exc
    if not math.isfinite(value):
        raise ValueError(f"{label} ({key}) must be finite")
    return value


def positive(inputs: dict[str, Any], key: str, label: str) -> float:
    value = number(inputs, key, label)
    if value <= 0:
        raise ValueError(f"{label} ({key}) must be greater than zero")
    return value


def non_negative(inputs: dict[str, Any], key: str, label: str) -> float:
    value = number(inputs, key, label)
    if value < 0:
        raise ValueError(f"{label} ({key}) must be zero or greater")
    return value


def option(inputs: dict[str, Any], key: str, label: str, permitted: tuple[str, ...]) -> str:
    raw = inputs.get(key)
    # Excel compares text case-insensitively; the saved workbook mixes 'y', 'Y', 'n' and 'N'.
    value = str(raw).strip().upper() if isinstance(raw, (str, int, float)) and not isinstance(
        raw, bool) else None
    if value not in permitted:
        raise ValueError(f"{label} ({key}) must be one of {', '.join(permitted)}")
    return value


def from_set(inputs: dict[str, Any], key: str, label: str, permitted: tuple[float, ...]) -> float:
    value = number(inputs, key, label)
    if value not in permitted:
        allowed = ", ".join(f"{item:g}" for item in permitted)
        raise ValueError(f"{label} ({key}) must be one of {allowed}, not {value:g}")
    return value


def ratio(action: float, capacity: float) -> float:
    if capacity <= 0:
        return math.inf if action > 0 else 0.0
    return action / capacity


def rounddown(value: float, digits: int = 0) -> float:
    """Excel ROUNDDOWN: truncate towards zero at ``digits`` decimals."""
    factor = 10.0 ** digits
    scaled = value * factor
    return math.floor(scaled) / factor if value >= 0 else math.ceil(scaled) / factor


def roundup(value: float, digits: int = 0) -> float:
    """Excel ROUNDUP: away from zero at ``digits`` decimals."""
    factor = 10.0 ** digits
    scaled = value * factor
    return math.ceil(scaled) / factor if value >= 0 else math.floor(scaled) / factor


def excel_round(value: float, digits: int = 0) -> float:
    """Excel ROUND, half away from zero (negative ``digits`` rounds to tens, hundreds...)."""
    factor = 10.0 ** digits
    scaled = abs(value) * factor
    rounded = math.floor(scaled + 0.5) / factor
    return math.copysign(rounded, value)


def bar_area(diameter: float) -> float:
    return rounddown(math.pi * diameter ** 2 / 4.0, ROUND_DIGITS)


def cot(radians: float) -> float:
    return 1.0 / math.tan(radians)


def vba_mod(dividend: float, divisor: int) -> int:
    """VBA ``Mod`` rounds both operands to integers (banker's rounding) first."""
    return int(round(dividend)) % int(round(divisor))


def calc_ast(fsy: float, fc: float, b: float, d: float, mstar: float, phi: float,
             alpha2: float) -> float:
    """VBA ``CalcAst2009``: tension steel for |M*| in kNm from phi As fsy d (1 - As fsy/(2 a2 fc b d)).

    The workbook returns 0 when the quadratic has no root; the module returns infinity so an
    unattainable moment is never reported as needing no steel (deliberate departure D7).
    """
    aa = fsy / (fc * b * d * 2.0 * alpha2)
    cc = abs(mstar * 1e6) / (phi * fsy * d)
    discriminant = 1.0 - 4.0 * aa * cc
    if discriminant < 0:
        return math.inf
    return (1.0 - math.sqrt(discriminant)) / (2.0 * aa)
