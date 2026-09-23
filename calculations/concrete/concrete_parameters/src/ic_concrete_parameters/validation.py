"""Validation tool for the Concrete Design Parameters module.

* ``self_check()`` - sweeps grades, densities, sources and optional groups and
                     proves the engine completes, stays finite and consistent.
* ``baseline()``   - replays the retained Structural Toolkit FORMULA V5.02 tables
                     bundled at ``data/workbook-baseline.json``.
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
    "sectionType": "rect", "bw": 300, "D": 600, "ds": 550, "fsy": 500,
    "bef": 900, "Ds": 150, "Zt": 1.8e7, "Zb": 1.8e7,
}
SWEEP_GRADES = [20, 25, 32, 40, 50, 65, 80, 100, 120]
SWEEP_SOURCES = ["table", "curve", "as2327"]
SWEEP_AGES = [1, 3, 7, 28, 90, 365]


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

    for grade in SWEEP_GRADES:
        for source in SWEEP_SOURCES:
            for age in SWEEP_AGES:
                inputs = {**SWEEP_BASE, "fc": grade, "density": 2400, "fcmiSource": source,
                          "cement": "N", "age": age,
                          "checks": {"minimumSteel": True, "cracking": True}}
                label = f"f'c {grade}, {source}, {age} days"
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
                block, material = result["stressBlock"], result["material"]
                if not engine.FACTOR_FLOOR <= block["alpha2"] <= 0.85:
                    problems.append(f"{label}: alpha2 is outside its Eq 8.1.3(1) bounds")
                if not engine.FACTOR_FLOOR <= block["gamma"] <= 0.97:
                    problems.append(f"{label}: gamma is outside its Eq 8.1.3(2) bounds")
                if not engine.ALPHA1_MIN <= block["alpha1"] <= engine.ALPHA1_MAX:
                    problems.append(f"{label}: alpha1 is outside its Eq 10.6.2.2 bounds")
                if material["Ec"] <= 0 or not math.isfinite(material["Ec"]):
                    problems.append(f"{label}: the modulus of elasticity is not a positive value")
                # Table 3.1.2 gives fcmi below f'c at 100 and 120 MPa, so only a band is checked.
                if not 0.9 <= material["fcmi"] / material["fc"] <= 1.25:
                    problems.append(f"{label}: the mean in-situ strength is outside 0.9 to 1.25 f'c")
                if result["minimumSteel"]["Astmin"] <= 0:
                    problems.append(f"{label}: the minimum reinforcement area is not positive")
                if result["util"] or result["worstUtil"] != 0.0:
                    problems.append(f"{label}: a parameter sheet must report no utilisation")
                summary = headless.summarise(result)
                if summary["worstUtil"] != 0.0:
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
        "approval": "Independent engineering review of the FORMULA V5.02 transcription is "
                    "outstanding, including the provenance of the strength gain table. The "
                    "module stays status=planned and enabled=false.",
    }
