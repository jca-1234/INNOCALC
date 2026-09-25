"""Validation for the Concrete Wall module.

* ``self_check()`` - sweeps geometry, restraint, reinforcement, strength and actions
  and proves the engine completes, stays consistent, repeatable and leaves inputs alone.
* ``baseline()``   - replays the retained CONCRETE WALLS V5.11 saved example in
  ``data/workbook-baseline.json``.

Run standalone: ``python -m ic_concrete_wall.dev --validate``.
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
MAY_BE_INFINITE = {"designMethod", "axial", "barGap", "singleLayer", "ductileWall",
                   "fireResistance", "cover"}

SWEEP_BASE: dict[str, Any] = {
    "cover": 30.0, "formwork": "S", "braced": "Y", "designAsWall": "Y", "dwall": "N",
    "kMode": "CALC", "k": 1.0, "openings": "N", "Aopen": 0.0, "Sopen": 0.0, "Neu": 0.0,
    "includeSW": "Y", "loadType": "F", "psiLOther": 1.0, "psiEOther": 1.0, "wallecc": 30.0,
    "Mstar": 0.0, "Vstar": 300.0, "reoClass": "N", "fsy": 500, "dbv": 12, "sv": 250,
    "dbh": 12, "sh": 250, "unrest": "N",
    "checks": {"fire": True, "crackControl": True, "durability": True},
    "exposed1side": "Y", "lat1side": "N", "frlTop": "Y", "ll07": "N", "frlRequired": 60.0,
    "crackDegree": "MINOR", "exposureClass": "A2",
}
SWEEP_GEOMETRY = [(150, 2800, 3000), (200, 3600, 6000), (250, 6000, 2500)]
SWEEP_RESTRAINT = [("Y", 0), ("N", 1), ("Y", 2)]
SWEEP_LAYERS = [1, 2]
SWEEP_ACTIONS = [(32, 150.0, 40.0, 0.0), (40, 600.0, 150.0, 0.0), (65, 80.0, 20.0, 400.0)]


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
                ok = _matches(actual, value, applied)
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                actual, ok = f"path not found: {exc}", False
            checks.append({"path": path, "expected": value, "actual": actual,
                           "tolerance": applied, "ok": ok})
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
    for (tw, hw, lw), (rot, sides), layers, (fc, ndl, nll, mi) in itertools.product(
            SWEEP_GEOMETRY, SWEEP_RESTRAINT, SWEEP_LAYERS, SWEEP_ACTIONS):
        inputs = {**SWEEP_BASE, "tw": tw, "Hw": hw, "Lw": lw, "H": hw, "rotRestraint": rot,
                  "wallIntersect": sides, "layers": layers, "fc": fc, "Ndl": ndl, "Nll": nll,
                  "Mstari": mi}
        label = f"{tw}x{hw}x{lw} rot {rot} sides {sides} layers {layers} f'c {fc} N {ndl}/{nll}"
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
        for key, value in util.items():
            if math.isnan(value) or value < 0 or (not math.isfinite(value) and key not in MAY_BE_INFINITE):
                problems.append(f"{label}: utilisation {key} = {value} is invalid")
        finite = [value for value in util.values() if math.isfinite(value)]
        if result["worstUtil"] != max(finite, default=0.0):
            problems.append(f"{label}: worstUtil does not match the maximum finite utilisation")
        heights, axial, shear = result["effectiveHeight"], result["axial"], result["shear"]
        if not 0.0 < heights["kCalc"] <= 1.0:
            problems.append(f"{label}: k outside 0 to 1.0")
        if axial["fNu"] < 0 or (layers == 1 and axial["fNus"] > axial["fNuMax1"] + 1e-9):
            problems.append(f"{label}: design axial strength out of range")
        if shear["Vu"] > shear["Vumax"] + 1e-9 or shear["Vuc"] < shear["Vucmin"] - 1e-9:
            problems.append(f"{label}: shear strength bounds violated")
        failing = any(not math.isfinite(value) or value > 1.0 for value in util.values())
        if failing and headless.summarise(result)["status"] == "OK":
            problems.append(f"{label}: a failing wall was reported OK")
    return {"ok": not problems, "tested": tested, "failures": problems}


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
        "approval": "Independent engineering review of the CONCRETE WALLS V5.11 transcription "
                    "is outstanding. The module stays status=planned and enabled=false.",
    }
