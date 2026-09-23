"""Validation tool for the Reinforcement Tables module.

* ``self_check()`` - sweeps bar sizes, counts, spacings and fabric designations
                     and proves the engine completes and stays self consistent.
* ``baseline()``   - replays the retained Structural Toolkit REINFORCEMENT V5.00
                     bar area and fabric tables.
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

SWEEP_BARS = [12, 16, 20, 24, 28, 32, 40]
SWEEP_COUNTS = [1, 4, 12, 30]
SWEEP_CENTRES = [60, 200, 1000]
SWEEP_ROUNDINGS = ["-1", "0"]


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

    for size in SWEEP_BARS:
        for count in SWEEP_COUNTS:
            for centres in SWEEP_CENTRES:
                for rounding in SWEEP_ROUNDINGS:
                    inputs = {"db": size, "count": count, "centres": centres,
                              "rounding": rounding, "mesh": "SL82"}
                    label = f"N{size} x {count} at {centres} cts, rounding {rounding}"
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
                    selected = result["selected"]
                    if selected["countAreaRounded"] > selected["countArea"] + 1e-9:
                        problems.append(f"{label}: the rounded area exceeds the exact area")
                    if selected["centresAreaRounded"] > selected["centresArea"] + 1e-9:
                        problems.append(f"{label}: the rounded area per metre exceeds the "
                                        "exact value")
                    if selected["single"] <= 0:
                        problems.append(f"{label}: the bar area is not positive")
                    if len(result["numberTable"]) != len(engine.BAR_COUNTS):
                        problems.append(f"{label}: the number table is incomplete")
                    if len(result["centresTable"]) != len(engine.BAR_CENTRES):
                        problems.append(f"{label}: the centres table is incomplete")
                    if len(result["fabricTable"]) != len(engine.FABRIC):
                        problems.append(f"{label}: the fabric table is incomplete")
                    for row in result["numberTable"]:
                        if sorted(row["areas"]) != row["areas"]:
                            problems.append(f"{label}: the number table is not increasing "
                                            "with bar size")
                            break
                    if result["util"] or result["worstUtil"] != 0.0:
                        problems.append(f"{label}: a reference sheet must report no utilisation")
                    if headless.summarise(result)["worstUtil"] != 0.0:
                        problems.append(f"{label}: the summary invented a utilisation")
    for entry in engine.FABRIC:
        tested += 1
        properties = engine.fabric_properties(entry)
        if properties["longArea"] <= 0:
            problems.append(f"{entry['name']}: the longitudinal area is not positive")
        if properties["perMetre"] and properties["crossArea"] <= 0:
            problems.append(f"{entry['name']}: the cross area is not positive")
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
        "approval": "The fabric properties have not been checked against a current "
                    "manufacturer's catalogue and the prestressing tendon table is not "
                    "transcribed. Independent review is outstanding and the module stays "
                    "status=planned and enabled=false.",
    }
