"""Validation for the Concrete Beam and Slab Design module.

* ``self_check()`` - sweeps section type, moment sign, strength, shear method, torsion and
  the optional groups and proves the engine completes, stays finite where it should, is
  repeatable and leaves inputs alone.
* ``baseline()``   - replays the retained CONCRETE MEMBER V5.13 saved example in
  ``data/workbook-baseline.json``.

Run standalone: ``python -m ic_concrete_member.dev --validate``.
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

SWEEP_SECTIONS = [
    {"sectionType": "R", "D": 600, "W": 400},
    {"sectionType": "F", "D": 600, "W": 300, "Bf": 1500, "Tf": 150, "btype": "T"},
    {"sectionType": "F", "D": 500, "W": 300, "Bf": 800, "Tf": 120, "btype": "L",
     "supportType": "C"},
    {"sectionType": "S", "D": 220, "botMode": "S", "botValue": 200, "barBot": "12",
     "topMode": "S", "topValue": 250, "barTop": "12", "ligs": "0", "legs": 0, "slabType": "O"},
]
SWEEP_MOMENTS = [(1.0, 0.8), (-1.0, -0.8)]
SWEEP_STRENGTHS = [(25.0, "N"), (50.0, "L"), (80.0, "N")]
SWEEP_SHEAR = [("G", 0.0), ("S", 0.0), ("G", 15.0)]


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
        cells = case.get("cells") or {}
        checks = []
        for path, value in expected.items():
            applied = float(overrides.get(path, tolerance))
            try:
                actual = dig(result, path)
                ok = _matches(actual, value, applied)
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                actual, ok = f"path not found: {exc}", False
            checks.append({"path": path, "cell": cells.get(path, ""), "expected": value,
                           "actual": actual, "tolerance": applied, "ok": ok})
        compared += len(checks)
        failures = [f"{item['cell'] or item['path']}: {item['actual']} != {item['expected']}"
                    for item in checks if not item["ok"]]
        outcomes.append({"name": name, "ok": not failures, "checks": checks, "failures": failures})
    failures = [f"{item['name']}: {problem}" for item in outcomes for problem in item["failures"]]
    if not compared:
        failures.append("No expected values were compared")
    return {"ok": not failures, "mode": mode, "module": engine.MODULE_ID, "version": VERSION,
            "tested": len(outcomes), "compared": compared, "failures": failures,
            "cases": outcomes}


def _sweep_inputs() -> list[tuple[str, dict[str, Any]]]:
    from . import headless

    base = headless.defaults()
    for group in engine.OPTIONAL_GROUPS:
        base["checks"][group] = True
    cases = []
    for section, (sign, _), (fc, klass), (method, torsion) in itertools.product(
            SWEEP_SECTIONS, SWEEP_MOMENTS, SWEEP_STRENGTHS, SWEEP_SHEAR):
        slab = section["sectionType"] == "S"
        moment = sign * (40.0 if slab else 200.0)
        inputs = {**base, **section, "fc": fc, "classBot": klass, "classTop": klass,
                  "Mstar": moment, "MstarV": 0.6 * moment, "Vstar": 60.0 if slab else 180.0,
                  "shearMethod": method, "Tstar": 0.0 if slab else torsion,
                  "mX": moment, "msX": 0.6 * moment, "wsdl": 1.0 if slab else 8.0,
                  "wll": 3.0 if slab else 10.0}
        label = (f"{section['sectionType']}{section.get('btype', '')} M*={moment:g} f'c={fc:g} "
                 f"{klass} {method} T*={inputs['Tstar']:g}")
        cases.append((label, inputs))
    return cases


def self_check() -> dict[str, Any]:
    from . import headless

    problems: list[str] = []
    tested = 0
    for label, inputs in _sweep_inputs():
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
        if json.dumps(result, sort_keys=True, default=str) != json.dumps(
                repeated, sort_keys=True, default=str):
            problems.append(f"{label}: compute is not repeatable")
        util = result["util"]
        if any(value != value or value < 0 for value in util.values()):
            problems.append(f"{label}: a utilisation is NaN or negative")
        finite = [value for value in util.values() if math.isfinite(value)]
        if result["worstUtil"] != (max(finite) if finite else 0.0):
            problems.append(f"{label}: worstUtil does not match the maximum finite utilisation")
        flex = result["flexure"]["governing"]
        if flex["phiMu"] > 0 and not 0.65 <= flex["phi"] <= 0.85:
            problems.append(f"{label}: phi outside 0.65 to 0.85")
        if flex["Mu"] < 0 or result["shear"]["phiVu"] < 0:
            problems.append(f"{label}: negative capacity")
        if result["shear"]["phiVu"] > result["shear"]["phiVuMax"] * (1 + 1e-12):
            problems.append(f"{label}: phiVu exceeds the web crushing limit")
        summary = headless.summarise(result)
        worst = max(util.values())
        if summary["status"] == "OK" and (worst > 1.0 or not math.isfinite(worst)):
            problems.append(f"{label}: a failing member was reported OK")
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
    report["departures"] = data.get("departures", [])
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
        "departures": reference.get("departures", []),
        "approval": "Independent engineering review of the CONCRETE MEMBER V5.13 transcription "
                    "is outstanding. The module stays status=planned and enabled=false.",
    }
