"""Validation for the Concrete Punching Shear module.

* ``self_check()`` - sweeps shape, position, spandrel, fitments and actions and proves
  the engine completes, stays finite, repeatable and leaves inputs alone.
* ``baseline()``   - replays the retained PUNCHING SHEAR V5.06 saved example and the
  workbook author's GoalSeek harness in ``data/workbook-baseline.json``.

Run standalone: ``python -m ic_concrete_punching_shear.dev --validate``.
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

SWEEP_BASE: dict[str, Any] = {
    "fc": 32, "ps": 0, "Ds": 250, "dom": 200, "pW": 400, "pmDir": "L", "pface": "W",
    "shearhead": "N", "ignorespan": "N", "Db": 600, "bw": 400, "cover": 25, "wcl": 600,
    "fyp": 500, "ineffU": 0, "Nstar": 800, "fsy": 500, "ductility": "N", "ibar": 16,
    "beams": "N", "nIntegrity": 30, "pLo": 7000, "pLod": 6000, "pLt": 7000, "Vdl": 7,
    "Vll": 3, "simplifiedMethod": "N",
}
SWEEP_SHAPES = [("N", 600), ("Y", 500)]
SWEEP_POSITIONS = [("I", "N"), ("E", "N"), ("C", "N"), ("C", "Y")]
SWEEP_SPANDREL = ["N", "Y"]
SWEEP_FITMENTS = [(0, 0), (12, 150)]
SWEEP_ACTIONS = [(0.0, 300.0), (40.0, 300.0), (150.0, 1500.0)]


def dig(data: Any, path: str) -> Any:
    for key in path.split("."):
        data = data[int(key)] if isinstance(data, list) else data[key]
    return data


def _matches(actual: Any, expected: Any, tolerance: float, absolute: float | None) -> bool:
    if isinstance(expected, str):
        return actual == expected
    if isinstance(expected, bool) or isinstance(actual, bool):
        return actual is expected
    actual_value, expected_value = float(actual), float(expected)
    if absolute is not None:
        return abs(actual_value - expected_value) <= absolute
    return math.isclose(actual_value, expected_value, rel_tol=tolerance,
                        abs_tol=tolerance if expected_value == 0.0 else 0.0)


def run_cases(cases: list[dict[str, Any]], *, default_tolerance: float = DEFAULT_TOLERANCE,
              mode: str = "worked-examples") -> dict[str, Any]:
    """Compare each case; ``absTolerance`` switches a case to an absolute comparison."""
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
        absolute = case.get("absTolerance")
        absolute = None if absolute is None else float(absolute)
        overrides = case.get("tolerances") or {}
        checks = []
        for path, value in expected.items():
            applied = float(overrides.get(path, tolerance))
            try:
                actual = dig(result, path)
                ok = _matches(actual, value, applied, absolute)
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                actual, ok = f"path not found: {exc}", False
            checks.append({"path": path, "expected": value, "actual": actual,
                           "tolerance": absolute if absolute is not None else applied,
                           "absolute": absolute is not None, "ok": ok})
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


def self_check() -> dict[str, Any]:
    from . import headless

    problems: list[str] = []
    tested = 0
    for (col, pl), (pos, both), span, (tie, spacing), (mv, v) in itertools.product(
            SWEEP_SHAPES, SWEEP_POSITIONS, SWEEP_SPANDREL, SWEEP_FITMENTS, SWEEP_ACTIONS):
        inputs = {**SWEEP_BASE, "col": col, "pL": pl, "pPos": pos, "spanbothsides": both,
                  "span": span, "dialp": tie, "ctsp": spacing, "Mvstar": mv, "Vstar": v}
        label = f"col {col} {pos}{both} span {span} tie {tie}-{spacing} Mv {mv} V {v}"
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
        g = result["geometry"]
        low, high = sorted((g["doSlab"], g["doSpandrel"]))
        if not (g["u"] > 0 and low - 1e-9 <= g["domc"] <= high + 1e-9):
            problems.append(f"{label}: perimeter or mean depth out of range")
        if any(case["capacity"] < 0 for case in result["cases"]):
            problems.append(f"{label}: a negative strength was returned")
        ceiling = 3.6 * max(1.0, g["Db"] / g["Ds"] if g["spandrel"] else 1.0)
        if result["governing"]["capacity"] > result["strength"]["phiVuo"] * ceiling + 1e-6:
            problems.append(f"{label}: governing strength exceeds its theoretical ceiling")
        if headless.summarise(result)["status"] == "OK" and result["worstUtil"] > 1.0:
            problems.append(f"{label}: an overloaded slab was reported OK")
    return {"ok": not problems, "tested": tested, "failures": problems}


def baseline() -> dict[str, Any]:
    resource = files(__package__).joinpath(BASELINE_RESOURCE)
    if not resource.is_file():
        return {"ok": False, "mode": "baseline", "module": engine.MODULE_ID, "version": VERSION,
                "tested": 0, "compared": 0, "cases": [],
                "failures": [f"Reference evidence missing: {BASELINE_RESOURCE}"]}
    data = json.loads(resource.read_text(encoding="utf-8"))
    report = run_cases((data.get("computeCases") or []) + _harness_cases(data.get("harness") or {}),
                       default_tolerance=float(data.get("tolerance", DEFAULT_TOLERANCE)),
                       mode="baseline")
    report["source"] = data.get("source", {})
    return report


def _harness_cases(harness: dict[str, Any]) -> list[dict[str, Any]]:
    """Expand the Settings!Z139:AS178 GoalSeek harness into absolute-tolerance cases."""
    cases = []
    for series in harness.get("series", []):
        for index, expected in enumerate(series["domc"]):
            bw = harness["bwStep"] * (index + 1)
            cases.append({
                "name": f"GoalSeek harness {series['case']} bw = {bw:g} mm ({series['cells']})",
                "inputs": {**harness["inputs"], **series["inputs"], "bw": bw},
                "absTolerance": harness["absTolerance"],
                "expect": {"geometry.domc": expected},
            })
    return cases


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
        "approval": "Independent engineering review of the PUNCHING SHEAR V5.06 transcription "
                    "is outstanding. The module stays status=planned and enabled=false.",
    }
