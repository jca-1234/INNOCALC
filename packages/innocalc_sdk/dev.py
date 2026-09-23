from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from calcpad import export_pdf, trace


def main(adapter: Any, argv: list[str] | None = None, *, validation=None,
         notebook_export=None) -> int:
    parser = argparse.ArgumentParser(description=f"Develop {adapter.descriptor()['name']}")
    parser.add_argument("inputs", nargs="?")
    parser.add_argument("--schema", action="store_true")
    parser.add_argument("--trace", action="store_true")
    parser.add_argument("--trace-html")
    parser.add_argument("--html")
    parser.add_argument("--pdf")
    parser.add_argument("--validate", nargs="?", const="")
    if notebook_export:
        parser.add_argument("--notebook")
    arguments = parser.parse_args(argv)
    if arguments.schema:
        print(json.dumps(adapter.schema(), indent=2, default=str))
        return 0
    if arguments.validate is not None:
        cases = None
        if arguments.validate:
            cases = json.loads(Path(arguments.validate).read_bytes())
            if isinstance(cases, dict):
                cases = cases.get("cases", cases)
        outcome = (validation or adapter.validate)(cases)
        print(json.dumps(outcome, indent=2, default=str))
        return 0 if outcome["ok"] else 1
    inputs = adapter.defaults()
    if arguments.inputs:
        inputs.update(json.loads(Path(arguments.inputs).read_bytes()))
    result = adapter.compute(inputs)
    print(json.dumps(adapter.summarise(result), indent=2, default=str))
    if arguments.trace:
        print(trace.as_text(result))
    if arguments.html or arguments.pdf:
        path = Path(arguments.html or Path(arguments.pdf).with_suffix(".html"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(adapter.render(inputs, result, standalone=True), encoding="utf-8")
        print(f"Sheet: {path}")
        if arguments.pdf:
            print(f"PDF: {export_pdf(path, arguments.pdf)}")
    if arguments.trace_html:
        path = Path(arguments.trace_html)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(trace.report(inputs, result, title=adapter.descriptor()["name"]), encoding="utf-8")
    if notebook_export and arguments.notebook:
        path = Path(arguments.notebook)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(notebook_export(inputs), encoding="utf-8")
    return 0