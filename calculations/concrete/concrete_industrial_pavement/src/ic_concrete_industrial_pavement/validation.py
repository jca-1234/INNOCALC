"""Validation for the Concrete Industrial Pavement module.

* ``self_check()`` - sweeps thickness, subgrade, position, flexural method and axle
  arrangements and proves the engine completes, stays finite, repeatable and leaves
  inputs alone.
* ``baseline()``   - replays the retained INDUSTRIAL FLOOR SLABS V5.07 saved example,
  the cached Chandler chart-function table and the cached VBA function results in
  ``data/workbook-baseline.json``.

Run standalone: ``python -m ic_concrete_industrial_pavement.dev --validate``.
"""

from __future__ import annotations

import itertools
import json
import math
from importlib.resources import files
from typing import Any

from . import engine
from .version import VERSION

BASELINE_RESOURCE = "data/workbook-baseline.json"
DEFAULT_TOLERANCE = 1e-9

SWEEP_THICKNESS = [(150.0, 32.0), (200.0, 40.0)]
SWEEP_SUBGRADE = [20.0, 60.0]
SWEEP_POSITIONS = ["I", "E", "C"]
SWEEP_METHODS = ["A", "T"]
SWEEP_AXLES = [(2, 0.0), (4, 0.0), (4, 1500.0)]


def dig(data: Any, path: str) -> Any:
    for key in path.split("."):
        data = data[int(key)] if isinstance(data, list) else data[key]
    return data


def _matches(actual: Any, expected: Any, tolerance: float) -> bool:
    if isinstance(expected, str):
        return actual == expected
    if isinstance(expected, bool) or isinstance(actual, bool):
        return actual is expected
    actual_value, expected_value = float(actual), float(expected)
    return math.isclose(actual_value, expected_value, rel_tol=tolerance,
                        abs_tol=tolerance if expected_value == 0.0 else 0.0)


def _check(path: str, actual: Any, expected: Any, tolerance: float) -> dict[str, Any]:
    try:
        ok = _matches(actual, expected, tolerance)
    except (TypeError, ValueError) as exc:
        actual, ok = f"not comparable: {exc}", False
    return {"path": path, "expected": expected, "actual": actual, "tolerance": tolerance, "ok": ok}


def run_cases(cases: list[dict[str, Any]], *, default_tolerance: float = DEFAULT_TOLERANCE,
              mode: str = "worked-examples") -> dict[str, Any]:
    outcomes: list[dict[str, Any]] = []
    compared = 0
    for index, case in enumerate(cases, start=1):
        name = str(case.get("name") or f"Case {index}")
        expected = case.get("expect") or {}
        if not expected:
            outcomes.append({"name": name, "ok": False, "checks": [],
                             "failures": ["A validation case must contain expected values"]})
            continue
        try:
            result = engine.compute(case["inputs"])
        except (KeyError, TypeError, ValueError) as exc:
            outcomes.append({"name": name, "ok": False, "checks": [],
                             "failures": [f"compute raised {type(exc).__name__}: {exc}"]})
            continue
        tolerance = float(case.get("tolerance", default_tolerance))
        overrides = case.get("tolerances") or {}
        checks = []
        for path, value in expected.items():
            applied = float(overrides.get(path, tolerance))
            try:
                actual = dig(result, path)
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                checks.append({"path": path, "expected": value, "actual": f"path not found: {exc}",
                               "tolerance": applied, "ok": False})
                continue
            checks.append(_check(path, actual, value, applied))
        compared += len(checks)
        failures = [f"{item['path']}: {item['actual']} != {item['expected']}"
                    for item in checks if not item["ok"]]
        outcomes.append({"name": name, "ok": not failures, "checks": checks, "failures": failures})
    failures = [f"{item['name']}: {problem}" for item in outcomes for problem in item["failures"]]
    if not compared:
        failures.append("No expected values were compared")
    return {"ok": not failures, "mode": mode, "module": engine.MODULE_ID, "version": VERSION,
            "tested": len(outcomes), "compared": compared, "failures": failures,
            "cases": outcomes}


def _chart_case(data: dict[str, Any], tolerance: float) -> dict[str, Any]:
    checks = []
    for point in data.get("points") or []:
        x = point["x"]
        for key, actual in (("radial", engine.radial(x)), ("radialEdge", engine.edge_increase(x)),
                            ("trans", engine.trans(x)), ("transEdge", engine.edge_increase(x))):
            checks.append(_check(f"{point['cell']} {key}({x!r})", actual, point[key], tolerance))
    failures = [f"{item['path']}: {item['actual']} != {item['expected']}"
                for item in checks if not item["ok"]]
    return {"name": data.get("name", "Chart functions"), "ok": not failures and bool(checks),
            "checks": checks, "failures": failures or ([] if checks else ["No chart values"])}


def _function_cases(cases: list[dict[str, Any]], tolerance: float) -> dict[str, Any]:
    checks = []
    for case in cases:
        kind = case["function"]
        if kind == "moment":
            actual = engine.chandler_moment(case["aisle"], case["l"])["value"]
        elif kind == "stressRatio":
            actual = engine.stress_ratio(case["repetitions"])
        elif kind == "msr":
            actual = engine.msr(case["value"])
        else:
            actual = engine.cbr(case["value"])
        checks.append(_check(case["name"], actual, case["expect"], tolerance))
    failures = [f"{item['path']}: {item['actual']} != {item['expected']}"
                for item in checks if not item["ok"]]
    return {"name": "VBA function results", "ok": not failures and bool(checks),
            "checks": checks, "failures": failures or ([] if checks else ["No function values"])}


def self_check() -> dict[str, Any]:
    from . import headless

    problems: list[str] = []
    tested = 0
    base = headless.defaults()
    for (h, fc), K, where, method, (wheels, bogie) in itertools.product(
            SWEEP_THICKNESS, SWEEP_SUBGRADE, SWEEP_POSITIONS, SWEEP_METHODS, SWEEP_AXLES):
        inputs = {**base, "h": h, "fc": fc, "K": K, "whereinput": where, "fmethod": method,
                  "WheelsPerAxle": str(wheels), "Bogie": bogie, "Transfer": "Y" if where != "I" else "N",
                  "checks": {**base["checks"], "custom": True}}
        label = f"h {h:g} K {K:g} {where} {method} {wheels}/axle bogie {bogie:g}"
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
        if json.dumps(result, sort_keys=True) != json.dumps(repeated, sort_keys=True):
            problems.append(f"{label}: compute is not repeatable")
        util = result["util"]
        if any(not math.isfinite(value) or value < 0 for value in util.values()):
            problems.append(f"{label}: a utilisation is not finite and non-negative")
        if result["worstUtil"] != max(util.values()):
            problems.append(f"{label}: worstUtil does not match the maximum utilisation")
        rack = result["racking"]
        if rack["Rsit"] < rack["Rsi"] or rack["fVu"] <= 0:
            problems.append(f"{label}: adjacent loads reduced the stress or punching capacity <= 0")
        if bogie and result["wheels"]["axleCase"] != "dual":
            problems.append(f"{label}: the dual axle case was not used")
        if headless.summarise(result)["status"] == "OK" and result["worstUtil"] > 1.0:
            problems.append(f"{label}: an overstressed pavement was reported OK")
    return {"ok": not problems, "tested": tested, "failures": problems}


def baseline() -> dict[str, Any]:
    resource = files(__package__).joinpath(BASELINE_RESOURCE)
    if not resource.is_file():
        return {"ok": False, "mode": "baseline", "module": engine.MODULE_ID, "version": VERSION,
                "tested": 0, "compared": 0, "cases": [],
                "failures": [f"Reference evidence missing: {BASELINE_RESOURCE}"]}
    data = json.loads(resource.read_text(encoding="utf-8"))
    tolerance = float(data.get("tolerance", DEFAULT_TOLERANCE))
    report = run_cases(data.get("computeCases") or [], default_tolerance=tolerance,
                       mode="baseline")
    extra = [_chart_case(data.get("chartCases") or {}, tolerance),
             _function_cases(data.get("functionCases") or [], tolerance)]
    report["cases"] += extra
    report["tested"] += len(extra)
    report["compared"] += sum(len(case["checks"]) for case in extra)
    report["failures"] += [f"{case['name']}: {problem}" for case in extra
                           for problem in case["failures"]]
    report["ok"] = not report["failures"]
    report["source"] = data.get("source", {})
    return report


def validate(cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Internal sweep plus the retained baseline; passing is not engineering approval."""
    if cases is not None:
        return run_cases(cases)
    sweep, reference = self_check(), baseline()
    failures = [f"self check: {item}" for item in sweep["failures"]] + list(reference["failures"])
    return {
        "ok": not failures, "mode": "self-check + baseline", "module": engine.MODULE_ID,
        "version": VERSION, "tested": sweep["tested"] + reference["tested"],
        "compared": reference["compared"], "failures": failures,
        "cases": ([{"name": "Internal consistency sweep", "ok": sweep["ok"], "checks": [],
                    "failures": sweep["failures"], "sweptCases": sweep["tested"]}]
                  + reference["cases"]),
        "source": reference.get("source", {}),
        "approval": "Independent engineering review of the INDUSTRIAL FLOOR SLABS V5.07 "
                    "transcription is outstanding. The module stays status=planned and "
                    "enabled=false.",
    }
