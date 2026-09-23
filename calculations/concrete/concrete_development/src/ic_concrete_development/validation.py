"""Validation tool for the Reinforcement Development and Laps module.

* ``self_check()`` - sweeps grades, bar sizes, covers and options and proves the
                     engine completes, stays finite and stays internally consistent.
* ``baseline()``   - replays the retained Structural Toolkit REINFORCEMENT
                     DEVELOPMENT V5.06 worked example and its hook and cog block.
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
    "fsy": 500, "lightweight": "N", "epoxy": "N", "bundle": 1,
    "cover": 50, "clear": 100, "below": 50, "rounding": "-1",
    "stress": 500, "stressc": 500, "sbb": 50, "twiceProvided": "N",
    "limitCompressionFc": "N", "fitment": 12, "fitmentSpacing": 200,
    "threeFitments": "Y", "helixBars": 6,
}
SWEEP_STRENGTHS = [20, 32, 65, 100, 120]
SWEEP_BARS = [10, 16, 20, 28, 36]
SWEEP_OPTIONS = [
    {"plain": "N", "element": "W", "helical": "N"},
    {"plain": "N", "element": "N", "helical": "Y"},
    {"plain": "Y", "element": "W", "helical": "N"},
]


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

    for strength in SWEEP_STRENGTHS:
        for bar in SWEEP_BARS:
            for options in SWEEP_OPTIONS:
                inputs = {**SWEEP_BASE, **options, "fc": strength, "db": bar,
                          "checks": {"hooksAndCogs": True}, "bendDb": bar,
                          "galvanised": "N", "rebent": "N", "maxInternal": 8}
                label = f"f'c {strength}, N{bar}, {options['plain']}/{options['element']}"
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
                factors = result["factors"]
                if not 0.7 <= factors["k3"] <= 1.0:
                    problems.append(f"{label}: k3 is outside its Cl 13.1.2.2 bounds")
                if factors["fcTension"] > engine.FC_TENSION_CAP + 1e-12:
                    problems.append(f"{label}: the tension f'c cap was not applied")
                if factors["correction"] < 1.0:
                    problems.append(f"{label}: the lap correction fell below one")
                tension, compression = result["tension"], result["compression"]
                for name, value in (("Lsy.t", tension["Lsyt"]), ("Lsy.tp", tension["Lsytp"]),
                                    ("Lsy.c", compression["Lsyc"]),
                                    ("Lsy.t.lap", result["tensionLap"]["Lsytlap"]),
                                    ("Lsy.c.lap", result["compressionLap"]["Lsyclap"])):
                    if not math.isfinite(value) or value <= 0:
                        problems.append(f"{label}: {name} is not a finite positive length")
                if tension["Lsytp"] < tension["Lsyt"]:
                    problems.append(f"{label}: the plain bar length is below the deformed one")
                if compression["Lsycp"] < compression["Lsyc"]:
                    problems.append(f"{label}: the plain compression length is below the "
                                    "deformed one")
                if compression["Lsyc"] < engine.COMPRESSION_FLOOR - 1e-9:
                    problems.append(f"{label}: the compression length fell below 200 mm")
                if result["compressionLap"]["Lsyclap"] < 0.8 * 40 * bar - 1e-9:
                    problems.append(f"{label}: the compression lap fell below its Cl 13.2.4(a) "
                                    "value even after the permitted reduction")
                if len(result["table"]) != len(engine.STANDARD_BARS):
                    problems.append(f"{label}: the bar size table is incomplete")
                for row in result["table"]:
                    if row["Lsytb"] <= 0 or row["Lsyclap"] <= 0:
                        problems.append(f"{label}: a table row is not a positive length")
                if result["util"] or result["worstUtil"] != 0.0:
                    problems.append(f"{label}: a length sheet must report no utilisation")
                if headless.summarise(result)["status"] != "OK":
                    problems.append(f"{label}: a valid full stress case did not report OK")
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
        "approval": "Independent engineering review of the REINFORCEMENT DEVELOPMENT V5.06 "
                    "transcription is outstanding, including the derivation of the workbook's "
                    "LapCorrection factor. The module stays status=planned and enabled=false.",
    }
