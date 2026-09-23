from __future__ import annotations

import keyword
import re
import tomllib
from pathlib import Path
from typing import Any


def load_manifest(root: Path) -> dict[str, Any]:
    manifest = tomllib.loads((root / "suite.toml").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("contract_version") != 1:
        raise ValueError("Unsupported suite manifest or module contract version")
    seen = {key: set() for key in ("id", "entry", "filing_folder", "path")}
    for module in manifest.get("modules", []):
        for key in seen:
            value = str(module.get(key, "")).strip()
            if not value or value.casefold() in seen[key]:
                raise ValueError(f"Missing or duplicate module {key}: {value}")
            seen[key].add(value.casefold())
        if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", module["id"]):
            raise ValueError(f"Invalid module id: {module['id']}")
        if not all(part.isidentifier() and not keyword.iskeyword(part) for part in module["entry"].split(".")):
            raise ValueError(f"Invalid entry point: {module['entry']}")
        path = (root / module["path"]).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError(f"Module path escapes suite: {module['path']}")
        folder = module["filing_folder"]
        if re.search(r'[<>:"/\\|?*\x00-\x1f]', folder) or folder.strip(" .") != folder:
            raise ValueError(f"Invalid filing folder: {folder}")
        if module.get("category") not in manifest.get("categories", []):
            raise ValueError(f"Unknown module category: {module.get('category')}")
        if not isinstance(module.get("enabled"), bool):
            raise ValueError("Every module must explicitly declare enabled = true or false")
    return manifest


def sources(root: Path) -> list[dict[str, Any]]:
    return [{**module, "folder": module["path"]} for module in load_manifest(root)["modules"]
            if module["enabled"]]