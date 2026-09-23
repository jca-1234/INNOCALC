"""Validation tool for the Concrete Corbel Design module.

Two levels of assurance, both callable headlessly:

* ``self_check()``  - sweeps geometry, strength and load levels and proves the
                      engine completes, stays finite, stays internally consistent
                      and leaves its inputs alone.  Needs no reference data.
* ``baseline()``    - replays the retained Structural Toolkit CORBEL V5.06
                      worked example in ``reference/workbook-baseline.json``.

``run_cases(cases)`` compares the engine against worked examples supplied as
``{"name", "inputs", "expect": {"dotted.path": value}}``.

Run standalone::

    python -m ic_concrete_corbel.dev --validate
    python -m ic_concrete_corbel.dev --validate my-cases.json
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
    "df": 150, "bw": 40, "th": 200, "scond": "R", "loadtype": "N", "mlt": 1.0,
    "bar": "16", "fsy": "500", "cover": 40, "reoMode": "count", "reoValue": 6,
    "mu": 0.7, "kco": 0.4,
}
SWEEP_GEOMETRY = [
    {"b": 600, "D": 300, "av": 105},
    {"b": 1000, "D": 450, "av": 150},
    {"b": 400, "D": 600, "av": 250},
]
SWEEP_LOADS = [
    {"Vdl": 0, "Vll": 0, "Ndl": 0, "Nll": 0},
    {"Vdl": 60, "Vll": 60, "Ndl": 6, "Nll": 6},
    {"Vdl": 400, "Vll": 300, "Ndl": 80, "Nll": 40},
]
SWEEP_STRENGTHS = [20, 40, 65, 100]


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
    """Compare ``engine.compute`` against supplied worked examples."""
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


def run_strut_cases(cases: list[dict[str, Any]],
                    *, default_tolerance: float = DEFAULT_TOLERANCE) -> list[dict[str, Any]]:
    """Check the Cl 7.2.3 strut chain and the Cl 7.3.2 tie force at a pinned ``dc``."""
    outcomes: list[dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        name = str(case.get("name") or f"Strut case {index}")
        values = dict(case["inputs"])
        try:
            state = dict(engine.strut_state(
                values["dc"], lever=values["lever"], av=values["av"], b=values["b"],
                fc=values["fc"], Vstar=values["Vstar"]))
            state["Ftstar"] = engine.tie_force(
                Vstar=values["Vstar"], av=values["av"], lever=values["lever"],
                x=state["x"], Ndstar=values["Ndstar"])
        except (KeyError, TypeError, ValueError) as exc:
            outcomes.append({"name": name, "ok": False, "checks": [],
                             "failures": [f"strut_state raised {type(exc).__name__}: {exc}"]})
            continue
        checks = _compare(state, case, default_tolerance)
        failures = [f"{item['path']}: {item['actual']} != {item['expected']}"
                    for item in checks if not item["ok"]]
        outcomes.append({"name": name, "ok": not failures, "checks": checks,
                         "failures": failures})
    return outcomes


def self_check() -> dict[str, Any]:
    """Internal consistency sweep; no reference data required."""
    problems: list[str] = []
    tested = 0
    from . import headless

    for strength in SWEEP_STRENGTHS:
        for geometry in SWEEP_GEOMETRY:
            for loads in SWEEP_LOADS:
                inputs = {**SWEEP_BASE, **geometry, **loads, "fc": strength}
                label = (f"f'c {strength}, b {geometry['b']}, D {geometry['D']}, "
                         f"av {geometry['av']}, V {loads['Vdl']}+{loads['Vll']}")
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
                if not math.isfinite(expected_worst) or expected_worst < 0:
                    problems.append(f"{label}: worstUtil is not a finite non-negative number")
                strut = result["strut"]
                if strut["converged"]:
                    if abs(strut["residual"]) > 1e-3:
                        problems.append(f"{label}: the strut solve residual is "
                                        f"{strut['residual']:.6g} N")
                    if not 0.0 < strut["dc"] < result["geometry"]["lever"]:
                        problems.append(f"{label}: the solved strut width is outside the bracket")
                elif not result["unattainable"]:
                    problems.append(f"{label}: the strut did not converge but nothing was "
                                    "reported as unattainable")
                summary = headless.summarise(result)
                if result["unattainable"] and summary["status"] != "FAIL":
                    problems.append(f"{label}: an unattainable check did not force FAIL")
                if summary["status"] == "OK" and result["worstUtil"] > 1.0:
                    problems.append(f"{label}: an overloaded corbel was reported OK")
    return {"ok": not problems, "tested": tested, "failures": problems}


def _trace(result: dict[str, Any]) -> str:
    return json.dumps(result, sort_keys=True, default=repr)


def baseline() -> dict[str, Any]:
    """Replay the retained CORBEL V5.06 evidence bundled with the package."""
    resource = files(__package__).joinpath(BASELINE_RESOURCE)
    if not resource.is_file():
        return {"ok": False, "mode": "baseline", "module": engine.MODULE_ID, "version": VERSION,
                "tested": 0, "compared": 0, "cases": [],
                "failures": [f"Reference evidence missing: {BASELINE_RESOURCE}"]}
    data = json.loads(resource.read_text(encoding="utf-8"))
    tolerance = float(data.get("tolerance", DEFAULT_TOLERANCE))
    compute_report = run_cases(data.get("computeCases") or [], default_tolerance=tolerance,
                               mode="baseline")
    strut_outcomes = run_strut_cases(data.get("strutCases") or [], default_tolerance=tolerance)
    strut_compared = sum(len(item["checks"]) for item in strut_outcomes)
    failures = list(compute_report["failures"]) + [
        f"{item['name']}: {problem}" for item in strut_outcomes for problem in item["failures"]]
    if not strut_outcomes:
        failures.append("The retained baseline supplied no strut cases")
    return {"ok": not failures, "mode": "baseline", "module": engine.MODULE_ID,
            "version": VERSION, "source": data.get("source", {}),
            "tested": compute_report["tested"] + len(strut_outcomes),
            "compared": compute_report["compared"] + strut_compared,
            "failures": failures, "cases": compute_report["cases"] + strut_outcomes}


def validate(cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Module release validation.

    With no cases this runs the internal sweep and the retained CORBEL V5.06
    baseline.  Passing this does not constitute engineering approval; see the
    module README for the outstanding release gates.
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
        "cases": ([{"name": "Internal consistency sweep", "ok": sweep["ok"],
                    "checks": [], "failures": sweep["failures"],
                    "sweptCases": sweep["tested"]}]
                  + reference["cases"]),
        "source": reference.get("source", {}),
        "approval": "Independent engineering review of the CORBEL V5.06 transcription is "
                    "outstanding. The module stays status=planned and enabled=false.",
    }
