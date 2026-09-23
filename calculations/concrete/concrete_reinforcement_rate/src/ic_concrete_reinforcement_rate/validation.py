"""Validation tool for the Reinforcement Rate module.

* ``self_check()`` - sweeps member sizes and schedules and proves the engine
                     completes, stays finite and stays internally consistent.
* ``baseline()``   - replays the retained Structural Toolkit REINFORCEMENT RATE
                     V5.00 member geometry, plus derived schedule cases.
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

SWEEP_MEMBERS = [
    {"L": 1000, "rb": 1000, "rd": 150, "cover": 30, "ligs": 8},
    {"L": 8100, "rb": 2400, "rd": 450, "cover": 30, "ligs": 12},
    {"L": 6000, "rb": 400, "rd": 900, "cover": 40, "ligs": 16},
]
SWEEP_SCHEDULES = [
    "",
    "B, 200, 12, 1000, Bottom bars",
    "B, 200, 16, 6000, Bottom\nB, 300, 12, 6000, Top\nL, 200, 10, 6000, Ligatures",
    "T, 400, 12, 6000, Transverse sets\nB, 8, 20, 6000, Eight bars",
]
SWEEP_DENSITIES = [7850, 7860]


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
                         "failures": failures, "derived": bool(case.get("derived"))})
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

    for member in SWEEP_MEMBERS:
        for density in SWEEP_DENSITIES:
            for schedule in SWEEP_SCHEDULES:
                inputs = {**member, "density": density, "title": "Sweep",
                          "schedule": schedule}
                label = (f"{member['rb']}x{member['rd']}, rho {density}, "
                         f"{len(schedule.splitlines())} rows")
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
                totals, member_out = result["totals"], result["member"]
                if totals["weight"] < 0 or not math.isfinite(totals["weight"]):
                    problems.append(f"{label}: the total weight is not a finite positive value")
                if member_out["volume"] <= 0:
                    problems.append(f"{label}: the concrete volume is not positive")
                expected_rate = (totals["weight"] / member_out["volume"]
                                 if member_out["volume"] else 0.0)
                if abs(totals["rate"] - expected_rate) > 1e-9 * max(1.0, expected_rate):
                    problems.append(f"{label}: the rate is not the weight over the volume")
                summed = sum(row["weight"] for row in result["schedule"])
                if abs(totals["weight"] - summed) > 1e-9 * max(1.0, summed):
                    problems.append(f"{label}: the total weight is not the sum of the rows")
                if result["util"] or result["worstUtil"] != 0.0:
                    problems.append(f"{label}: a quantity sheet must report no utilisation")
                if headless.summarise(result)["worstUtil"] != 0.0:
                    problems.append(f"{label}: the summary invented a utilisation")
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
        "approval": "The saved workbook schedule is empty, so only the member geometry chain "
                    "has published evidence; the schedule cases are derived. Independent "
                    "engineering review is outstanding and the module stays status=planned "
                    "and enabled=false.",
    }
