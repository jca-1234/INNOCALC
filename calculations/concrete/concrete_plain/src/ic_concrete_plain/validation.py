"""Validation tool for the Plain Concrete Design module.

* ``self_check()`` - sweeps geometry, strength and load levels and proves the
                     engine completes, stays finite, stays internally consistent
                     and leaves its inputs alone.  Needs no reference data.
* ``baseline()``   - replays the retained Structural Toolkit PLAIN CONCRETE V5.02
                     worked example bundled at ``data/workbook-baseline.json``.
* ``run_cases()``  - compares the engine against supplied worked examples of the
                     form ``{"name", "inputs", "expect": {"dotted.path": value}}``.
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
    "B": 1000, "uMode": "calculated", "um": 0, "Dir": "L",
    "eccx": 0, "eccy": 0, "ignoreEcc": "N",
}
SWEEP_GEOMETRY = [
    {"Dt": 250, "L": 90, "W": 90, "Lpx": 400, "Wpy": 400},
    {"Dt": 400, "L": 300, "W": 300, "Lpx": 600, "Wpy": 400},
    {"Dt": 700, "L": 600, "W": 300, "Lpx": 900, "Wpy": 900},
]
SWEEP_LOADS = [
    {"Mstar": 0, "Vstar": 0, "Pstar": 0, "Mxstar": 0, "Mystar": 0},
    {"Mstar": 2, "Vstar": 7, "Pstar": 500, "Mxstar": 10, "Mystar": 5},
    {"Mstar": 60, "Vstar": 400, "Pstar": -250, "Mxstar": -50, "Mystar": -50},
]
SWEEP_STRENGTHS = [20, 32, 65, 120]


def dig(data: Any, path: str) -> Any:
    """Fetch ``result['a']['b'][0]`` with the dotted path ``a.b.0``."""
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

    for strength in SWEEP_STRENGTHS:
        for geometry in SWEEP_GEOMETRY:
            for loads in SWEEP_LOADS:
                inputs = {**SWEEP_BASE, **geometry, **loads, "fc": strength}
                label = (f"f'c {strength}, Dt {geometry['Dt']}, Lpx {geometry['Lpx']}, "
                         f"P* {loads['Pstar']}")
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
                if any(value < 0 for value in finite):
                    problems.append(f"{label}: a utilisation is negative")
                expected_worst = max(finite) if finite else 0.0
                if result["worstUtil"] != expected_worst:
                    problems.append(f"{label}: worstUtil does not match the finite maximum")
                pedestal = result["pedestal"]
                if pedestal["sigmaTc"] < 0 or pedestal["sigmaTt"] > 0:
                    problems.append(f"{label}: the pedestal stress sign convention is broken")
                if result["punching"]["phiVum"] > result["punching"]["phiVu"] + 1e-9:
                    problems.append(f"{label}: the moment reduction increased the capacity")
                summary = headless.summarise(result)
                if summary["status"] == "OK" and result["worstUtil"] > 1.0:
                    problems.append(f"{label}: an overloaded element was reported OK")
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

    Passing this does not constitute engineering approval; see the module README
    for the outstanding release gates.
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
        "approval": "Independent engineering review of the PLAIN CONCRETE V5.02 transcription "
                    "is outstanding. The module stays status=planned and enabled=false.",
    }
