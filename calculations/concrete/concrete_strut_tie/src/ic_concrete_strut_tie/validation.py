"""Validation for the Concrete Strut-and-Tie module.

* ``self_check()`` - sweeps geometry, angle modes, strength and reinforcement and
  proves the engine completes, stays finite, repeatable and leaves inputs alone.
* ``baseline()``   - replays the retained STRUT & TIE V5.04 saved example in
  ``data/workbook-baseline.json``.

Run standalone: ``python -m ic_concrete_strut_tie.dev --validate``.
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
    "Vrserv": 0.0, "thetaMode": "S", "theta": 45.0, "aMode": "C", "aManual": 1.0,
    "zMode": "C", "zManual": 1.0, "dcMode": "C", "dcManual": 1.0, "lbMode": "C",
    "lbManual": 1.0, "betasMode": "C", "betasManual": 0.5, "tanAlphaMode": "C",
    "tanAlphaManual": 0.2, "tanAlphaServMode": "C", "tanAlphaServManual": 0.5, "crack": "O",
    "fsic": 250.0, "layer1": 2, "fsy1": 500, "layer2": 2, "fsy2": 500, "useRef2": "Y",
    "tieBar": 28, "tieBars": 8, "tieLayers": 2, "fsy": 500, "ek": "N", "lk": "N", "sk": "N",
    "cogged": "Y", "below": 350, "bundle": 1, "cover": 40, "covera": 100, "dzMode": "C",
    "dzManual": 1.0, "ntype": "CCT", "stresso": 5.0, "bearingMode": "C", "Bstar": 0.0,
    "areaMode": "D", "A1": 1.0, "A2": 1.0, "tieHeightMode": "H", "tieHeight": 300.0,
    "checks": {"nodeFaces": True},
}
SWEEP_GEOMETRY = [(3000, 3000, 400, 800), (3500, 3660, 600, 600), (2600, 4000, 300, 1600),
                  (5000, 2500, 300, 900)]
SWEEP_MODES = [("S", "C", "C"), ("S", "M", "C"), ("S", "C", "M"), ("G", "C", "C")]
SWEEP_STRENGTHS = [(25, 1000), (50, 5000), (100, 12000)]
SWEEP_REINFORCEMENT = [(16, 200, 16, 200, 0), (20, 150, 0, 200, 500)]


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
    for (L, D, bc, Lr), (theta_mode, a_mode, z_mode), (fc, cstar), reo in itertools.product(
            SWEEP_GEOMETRY, SWEEP_MODES, SWEEP_STRENGTHS, SWEEP_REINFORCEMENT):
        bar1, cts1, bar2, cts2, vr = reo
        inputs = {**SWEEP_BASE, "checks": dict(SWEEP_BASE["checks"]), "Lstrut": L, "D": D,
                  "bc": bc, "Lr": Lr, "thetaMode": theta_mode, "aMode": a_mode,
                  "aManual": 0.9 * L, "zMode": z_mode, "zManual": 0.85 * D, "fc": fc,
                  "Cstar": cstar, "Cserv": 0.7 * cstar, "Tstar": 0.8 * cstar, "Vrstar": vr,
                  "Vrserv": 0.7 * vr, "bar1": bar1, "cts1": cts1, "bar2": bar2, "cts2": cts2}
        label = (f"{L}x{D}x{bc} Lr {Lr}, modes {theta_mode}{a_mode}{z_mode}, f'c {fc}, "
                 f"C* {cstar}, bars {bar1}/{bar2}")
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
        if any(math.isnan(value) or value < 0 for value in util.values()):
            problems.append(f"{label}: a utilisation is NaN or negative")
        finite = [value for value in util.values() if math.isfinite(value)]
        if result["worstUtil"] != (max(finite) if finite else 0.0):
            problems.append(f"{label}: worstUtil does not match the maximum finite utilisation")
        if any(not math.isfinite(value) for value in util.values()) and not result["unattainable"]:
            problems.append(f"{label}: an infinite utilisation has no unattainable reason")
        geometry = result["geometry"]
        if theta_mode == "S" and geometry["solver"]["converged"] and not geometry["compatible"]:
            problems.append(f"{label}: the solved strut angle is not compatible with theta_az")
        if theta_mode == "S" and abs(geometry["angleError"]) > engine.ANGLE_TOLERANCE \
                and util["angleCompatibility"] != math.inf:
            problems.append(f"{label}: an incompatible angle was not reported")
        strut = result["strut"]
        if not math.isclose(strut["Cmax"], strut["Cstar"], rel_tol=1e-12):
            problems.append(f"{label}: dc = dc.max does not reproduce phiC = C*")
        summary = headless.summarise(result)
        if summary["status"] == "OK" and (result["worstUtil"] > 1.0 or len(finite) < len(util)):
            problems.append(f"{label}: an overloaded or unattainable strut was reported OK")
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
        "approval": "Independent engineering review of the STRUT & TIE V5.04 transcription "
                    "is outstanding. The module stays status=planned and enabled=false.",
    }
