"""Validation for the Concrete Flat Slab module.

* ``self_check()`` - sweeps geometry, edge conditions, drops, strengths and loads and
  proves the engine completes, stays finite, repeatable and leaves inputs alone.
* ``baseline()``   - replays the retained FLAT SLABS V5.04 saved example in
  ``data/workbook-baseline.json``.

Run standalone: ``python -m ic_concrete_flat_slab.dev --validate``.
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
    "Oy": 200.0, "Ox": 300.0, "Cy": 400.0, "Cx": 500.0, "limitStrip": "N", "reo": "N",
    "wsdl": 1.0, "loadType": "N", "bar": 16, "cover": 25.0, "insideLayer": "Y",
    "Ast": 900.0, "fsy": 500, "Asc": 0.0, "dc": 44.0, "useFcmi": "Y", "density": 2400.0,
    "lefDelta": 250.0, "lefDeltaInc": 500.0,
}
SWEEP_SPANS = [(6000, 6000), (8000, 6500), (9000, 4600)]
SWEEP_TYPES = ["S", "I", "C", "F"]
SWEEP_DROPS = [("Y", "E"), ("N", "I")]
SWEEP_STRENGTHS = [(25, 200, 5.0, 3.0), (40, 280, 7.0, 5.0)]


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
    for (ly, lx), slab, (drop, span), (fc, th, wdl, wll) in itertools.product(
            SWEEP_SPANS, SWEEP_TYPES, SWEEP_DROPS, SWEEP_STRENGTHS):
        inputs = {**SWEEP_BASE, "Ly": ly, "Lx": lx, "slabType": slab, "hasDrop": drop,
                  "spanType": span, "fc": fc, "th": th, "wdl": wdl, "wll": wll}
        label = f"{ly}x{lx} type {slab} drop {drop} f'c {fc}"
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
        spans = result["spans"]
        for key in ("Loy1", "Loy", "Lox1", "Lox"):
            span = result["geometry"]["Ly" if key[2] == "y" else "Lx"]
            if not 0.65 * span - 1e-9 <= spans[key] <= span:
                problems.append(f"{label}: {key} lies outside 0.65 L to L")
        for name, strip in result["strips"].items():
            for total, cs, ms in zip(strip["total"], strip["cs"], strip["ms"]):
                parts = cs + (2 * ms if name in ("y", "x") else ms)
                if not math.isclose(parts, total, rel_tol=1e-12, abs_tol=1e-9):
                    problems.append(f"{label}: {name} strip shares do not sum to the strip moment")
            if strip["total"][1] <= 0 or strip["total"][4] <= 0:
                if not (spans["wallEdge"] and name.startswith("edge")):
                    problems.append(f"{label}: {name} positive moments are not positive")
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
        "approval": "Independent engineering review of the FLAT SLABS V5.04 transcription "
                    "is outstanding. The module stays status=planned and enabled=false.",
    }
