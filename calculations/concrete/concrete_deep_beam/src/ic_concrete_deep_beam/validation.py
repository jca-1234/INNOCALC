"""Validation tool for the Concrete Deep Beam Design module.

* ``self_check()`` - sweeps span types, geometry and load levels and proves the
                     engine completes, stays finite and stays internally consistent.
* ``baseline()``   - replays the retained Structural Toolkit DEEP BEAMS V5.02
                     worked example bundled at ``data/workbook-baseline.json``.
"""

from __future__ import annotations

import json
import math
from importlib.resources import files
from typing import Any

from . import engine
from .version import VERSION

BASELINE_RESOURCE = "data/workbook-baseline.json"
DEFAULT_TOLERANCE = 1e-9

SWEEP_BASE: dict[str, Any] = {
    "bw": 300, "Df": 0, "fsy": 500, "bar": 20, "mesh": 9.5, "crack": "W", "fsic": 350,
    "gs": 1.15, "gc": 1.5, "Pstar": 500, "wstar": 50, "reodiste": 1,
}
SWEEP_GEOMETRY = [
    {"L": 3000, "D": 4000, "support": 500},
    {"L": 8000, "D": 4000, "support": 800},
    {"L": 12000, "D": 5000, "support": 1500},
]
SWEEP_LOADS = [
    {"Mstar": 0, "Mstarn": 0, "Vstar": 0, "Rstar": 0},
    {"Mstar": 1670, "Mstarn": 500, "Vstar": 900, "Rstar": 900},
    {"Mstar": 6000, "Mstarn": 3000, "Vstar": 5000, "Rstar": 5000},
]
SWEEP_STRENGTHS = [20, 32, 65, 120]


def dig(data: Any, path: str) -> Any:
    for key in path.split("."):
        if isinstance(data, list):
            data = data[int(key)]
        else:
            data = data[key]
    return data


def _matches(actual: Any, expected: Any, tolerance: float) -> bool:
    if isinstance(expected, str):
        if expected in ("inf", "-inf"):
            return (isinstance(actual, float) and math.isinf(actual)
                    and (actual > 0) == (expected == "inf"))
        return actual == expected
    if isinstance(expected, bool) or isinstance(actual, bool):
        return actual is expected
    actual_value, expected_value = float(actual), float(expected)
    if not math.isfinite(expected_value):
        return actual_value == expected_value
    return math.isclose(actual_value, expected_value, rel_tol=tolerance,
                        abs_tol=tolerance if expected_value == 0.0 else 0.0)


def _compare(values: Any, case: dict[str, Any], default: float) -> list[dict[str, Any]]:
    tolerance = float(case.get("tolerance", default))
    overrides = case.get("tolerances") or {}
    checks: list[dict[str, Any]] = []
    for path, expected in (case.get("expect") or {}).items():
        applied = float(overrides.get(path, tolerance))
        try:
            actual = dig(values, path)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            checks.append({"path": path, "expected": expected, "actual": None,
                           "tolerance": applied, "ok": False, "note": f"path not found: {exc}"})
            continue
        checks.append({"path": path, "expected": expected, "actual": actual,
                       "tolerance": applied, "ok": _matches(actual, expected, applied)})
    return checks


def run_cases(cases: list[dict[str, Any]], *, default_tolerance: float = DEFAULT_TOLERANCE,
              mode: str = "worked-examples") -> dict[str, Any]:
    outcomes: list[dict[str, Any]] = []
    compared = 0
    for index, case in enumerate(cases, start=1):
        name = str(case.get("name") or f"Case {index}")
        if not (case.get("expect") or {}):
            outcomes.append({"name": name, "ok": False, "checks": [],
                             "failures": ["A validation case must contain expected values"]})
            continue
        try:
            result = engine.compute(case["inputs"])
        except (KeyError, TypeError, ValueError) as exc:
            outcomes.append({"name": name, "ok": False, "checks": [],
                             "failures": [f"compute raised {type(exc).__name__}: {exc}"]})
            continue
        checks = _compare(result, case, default_tolerance)
        compared += len(checks)
        failures = [f"{item['path']}: {item['actual']} != {item['expected']}"
                    for item in checks if not item["ok"]]
        outcomes.append({"name": name, "ok": not failures, "checks": checks,
                         "failures": failures})
    failures = [f"{item['name']}: {problem}"
                for item in outcomes for problem in item["failures"]]
    if not compared:
        failures.append("No expected values were compared")
    return {"ok": not failures, "mode": mode, "module": engine.MODULE_ID, "version": VERSION,
            "tested": len(outcomes), "compared": compared, "failures": failures,
            "cases": outcomes}


def self_check() -> dict[str, Any]:
    problems: list[str] = []
    tested = 0
    from . import headless

    for span_type in engine.SPAN_TYPES:
        for strength in SWEEP_STRENGTHS:
            for geometry in SWEEP_GEOMETRY:
                for loads in SWEEP_LOADS:
                    inputs = {**SWEEP_BASE, **geometry, **loads, "fc": strength,
                              "spanType": span_type}
                    label = (f"{span_type}, f'c {strength}, L {geometry['L']}, "
                             f"V* {loads['Vstar']}")
                    tested += 1
                    snapshot = json.dumps(inputs, sort_keys=True)
                    try:
                        result = engine.compute(inputs)
                        repeated = engine.compute(inputs)
                    except ValueError as exc:
                        problems.append(f"{label}: rejected a sweep case - {exc}")
                        continue
                    if json.dumps(inputs, sort_keys=True) != snapshot:
                        problems.append(f"{label}: compute mutated its inputs")
                    if _trace(result) != _trace(repeated):
                        problems.append(f"{label}: compute is not repeatable")
                    util = result["util"]
                    finite = [value for value in util.values() if math.isfinite(value)]
                    if any(math.isnan(value) for value in util.values()):
                        problems.append(f"{label}: a utilisation is NaN")
                    if result["worstUtil"] != (max(finite) if finite else 0.0):
                        problems.append(f"{label}: worstUtil is not the finite maximum")
                    if ("externalSupport" in util) == (span_type == "C"):
                        problems.append(f"{label}: the external support check applicability "
                                        "does not follow the span type")
                    if ("internalSupport" in util) == (span_type == "S"):
                        problems.append(f"{label}: the internal support check applicability "
                                        "does not follow the span type")
                    if result["geometry"]["z"] <= 0:
                        problems.append(f"{label}: the effective lever arm is not positive")
                    if result["shear"]["phiVu"] > min(result["shear"]["phiVuDepth"],
                                                      result["shear"]["phiVuSpan"]) + 1e-9:
                        problems.append(f"{label}: the governing shear capacity is not the "
                                        "lesser of the two forms")
                    if result["serviceability"]["fsyd"] > result["serviceability"]["fsi"] + 1e-9:
                        problems.append(f"{label}: fsy.d exceeded the serviceability limit")
                    if not any("superseded" in note.lower() for note in result["warnings"]):
                        problems.append(f"{label}: the superseded method warning is missing")
                    summary = headless.summarise(result)
                    if summary["status"] == "OK" and result["worstUtil"] > 1.0:
                        problems.append(f"{label}: an overloaded deep beam was reported OK")
    return {"ok": not problems, "tested": tested, "failures": problems}


def _trace(result: dict[str, Any]) -> str:
    return json.dumps(result, sort_keys=True, default=repr)


def baseline() -> dict[str, Any]:
    resource = files(__package__).joinpath(BASELINE_RESOURCE)
    if not resource.is_file():
        return {"ok": False, "mode": "baseline", "module": engine.MODULE_ID, "version": VERSION,
                "tested": 0, "compared": 0, "cases": [],
                "failures": [f"Reference evidence missing: {BASELINE_RESOURCE}"]}
    data = json.loads(resource.read_text(encoding="utf-8"))
    report = run_cases(data.get("computeCases") or [],
                       default_tolerance=float(data.get("tolerance", DEFAULT_TOLERANCE)),
                       mode="baseline")
    report["source"] = data.get("source", {})
    return report


def validate(cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Module release validation.

    Passing this does not constitute engineering approval, and this module uses a
    method its own source declares superseded.  See the module README.
    """
    if cases is not None:
        return run_cases(cases)
    sweep = self_check()
    reference = baseline()
    failures = ([f"self check: {problem}" for problem in sweep["failures"]]
                + list(reference["failures"]))
    return {
        "ok": not failures,
        "mode": "self-check + baseline",
        "module": engine.MODULE_ID,
        "version": VERSION,
        "tested": sweep["tested"] + reference["tested"],
        "compared": reference["compared"],
        "failures": failures,
        "cases": ([{"name": "Internal consistency sweep", "ok": sweep["ok"], "checks": [],
                    "failures": sweep["failures"], "sweptCases": sweep["tested"]}]
                  + reference["cases"]),
        "source": reference.get("source", {}),
        "approval": "The CEB method transcribed here is superseded and the module is "
                    "informative only. Independent engineering review is outstanding. The "
                    "module stays status=planned and enabled=false.",
    }
