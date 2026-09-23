from __future__ import annotations

import json
import keyword
import re
from pathlib import Path
from string import Template

from packages.innocalc_sdk.manifest import load_manifest


def create_module(root: Path, *, module_id: str, name: str, category: str,
                  standard: str, filing_folder: str, owner: str) -> Path:
    manifest = load_manifest(root)
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", module_id):
        raise ValueError("Use a lower-case kebab-case module ID")
    package = "ic_" + module_id.replace("-", "_")
    if keyword.iskeyword(package) or not all(str(value).strip() for value in (name, standard, owner)):
        raise ValueError("Name, design standard and maintainer are required")
    if category not in manifest["categories"]:
        raise ValueError("Choose a category declared in suite.toml")
    if re.search(r'[<>:"/\\|?*\x00-\x1f]', filing_folder) or not filing_folder.strip(" .") or filing_folder.strip(" .") != filing_folder:
        raise ValueError("Filing folder must be one valid Windows folder name")
    for module in manifest["modules"]:
        if module["id"].casefold() == module_id.casefold() or module["filing_folder"].casefold() == filing_folder.casefold():
            raise ValueError("Module ID or filing folder is already registered")
    discipline = re.sub(r"[^a-z0-9]+", "_", category.lower()).strip("_")
    relative = Path("calculations") / discipline / module_id.replace("-", "_")
    destination = root / relative
    if destination.exists():
        raise ValueError(f"Refusing to overwrite {destination}")
    values = {"package": package, "module_id": module_id,
              "name_json": json.dumps(name), "standard_json": json.dumps(standard),
              "folder_json": json.dumps(filing_folder), "owner_json": json.dumps(owner),
              "category_json": json.dumps(category), "name": name,
              "standard": standard, "owner": owner}
    templates = Path(__file__).resolve().parent / "templates" / "module"
    generated = {}
    for template in templates.rglob("*.tmpl"):
        target = str(template.relative_to(templates))[:-5].replace("__package__", package)
        generated[target] = Template(template.read_text(encoding="utf-8")).substitute(values)
    entry = ("\n[[modules]]\n" + f"id = {json.dumps(module_id)}\n"
             + f"path = {json.dumps(relative.as_posix() + '/src')}\n"
             + f"entry = {json.dumps(package + '.headless')}\n"
             + f"category = {json.dumps(category)}\nfiling_folder = {json.dumps(filing_folder)}\n"
             + "enabled = false\n")
    for target, content in generated.items():
        path = destination / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    with (root / "suite.toml").open("a", encoding="utf-8") as handle:
        handle.write(entry)
    return destination