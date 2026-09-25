from __future__ import annotations

import copy
import inspect
import math
from typing import Any

from . import versioning

REQUIRED = ("descriptor", "schema", "defaults", "compute", "render", "summarise", "identity")


def check_contract(adapter: Any) -> dict[str, Any]:
    failures: list[str] = []
    for name in REQUIRED:
        if not callable(getattr(adapter, name, None)):
            failures.append(f"Missing function: {name}")
    if failures:
        return {"ok": False, "failures": failures}
    try:
        descriptor = adapter.descriptor()
        for key in ("id", "name", "entry", "folder", "version", "standard", "status"):
            if not descriptor.get(key):
                failures.append(f"Missing descriptor value: {key}")
        if descriptor.get("version"):
            try:
                versioning.parse(descriptor["version"])
            except ValueError as exc:
                failures.append(str(exc))
        schema, inputs = adapter.schema(), adapter.defaults()
        fields = [field for group in schema.get("groups", []) + schema.get("optional", [])
                  for field in group.get("fields", [])]
        identifiers = [field["id"] for field in fields]
        if len(set(identifiers)) != len(identifiers):
            failures.append("Duplicate schema field IDs")
        for identifier in identifiers:
            if identifier not in inputs:
                failures.append(f"Missing default: {identifier}")
        before = copy.deepcopy(inputs)
        result = adapter.compute(inputs)
        if inputs != before:
            failures.append("compute mutated its input document")
        if adapter.compute(copy.deepcopy(before)) != result:
            failures.append("compute is not deterministic for defaults")
        for key in ("util", "worstUtil", "checks"):
            if key not in result:
                failures.append(f"Missing result key: {key}")
        utilisation = result.get("util", {})
        if not isinstance(utilisation, dict) or any(not isinstance(value, (int, float)) for value in utilisation.values()):
            failures.append("util must map names to numbers")
        else:
            worst = max((value for value in utilisation.values() if math.isfinite(value)), default=0.0)
            if result.get("worstUtil") != worst:
                failures.append("worstUtil is not the maximum finite utilisation")
            summary = adapter.summarise(result)
            for key in ("status", "headline", "criticalCheck", "worstUtil"):
                if key not in summary:
                    failures.append(f"Missing summary key: {key}")
            if any(not math.isfinite(value) or value > 1 for value in utilisation.values()) and summary.get("status") == "OK":
                failures.append("Failing or unattainable utilisation reports OK")
        inspect.signature(adapter.render).bind(inputs, result, standalone=True, appendix=None,
                                               anchor_prefix="contract-probe", contents_href="#contents-probe")
        document = adapter.render(inputs, result, standalone=True, anchor_prefix="contract-probe",
                                  contents_href="#contents-probe")
        if 'class="calc-page"' not in document or "contract-probe" not in document or "#contents-probe" not in document:
            failures.append("render must produce calculation pages and forward navigation anchors")
        identity = adapter.identity(inputs)
        for key in ("memberType", "memberNumber", "package", "level", "calcType", "title"):
            if key not in identity:
                failures.append(f"Missing identity key: {key}")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")
    return {"ok": not failures, "failures": failures}