from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from pathlib import Path

from packages.innocalc_sdk.manifest import load_manifest


def capture(root: Path, module_id: str) -> dict:
    source = next(module for module in load_manifest(root)["modules"] if module["id"] == module_id)
    sys.path.insert(0, str(root / source["path"]))
    adapter = importlib.import_module(source["entry"])
    inputs = adapter.defaults()
    inputs["date"] = "01/01/2026"
    result = adapter.compute(inputs)
    document = adapter.render(inputs, result, standalone=True,
                              anchor_prefix="baseline", contents_href="#contents")
    return {"module": module_id, "inputs": inputs, "result": result,
            "summary": adapter.summarise(result), "identity": adapter.identity(inputs),
            "htmlSha256": hashlib.sha256(document.encode("utf-8")).hexdigest()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("module")
    parser.add_argument("path", type=Path)
    parser.add_argument("--compare", action="store_true")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    document = json.dumps(capture(root, arguments.module), sort_keys=True, indent=2, default=str)
    if arguments.compare:
        if json.loads(arguments.path.read_bytes()) != json.loads(document):
            print("Baseline differs: inputs, results, summary, identity or rendered HTML changed")
            return 1
        print("Exact numerical and rendered HTML baseline matched")
    else:
        arguments.path.parent.mkdir(parents=True, exist_ok=True)
        arguments.path.write_text(document, encoding="utf-8")
        print(f"Baseline captured: {arguments.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())