from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
from pathlib import Path

from packages.innocalc_sdk import check_contract, load_manifest
from packages.innocalc_sdk.dev import main as develop
from .scaffold import create_module


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tooling")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    cleanup = commands.add_parser("clean")
    cleanup.add_argument("--apply", action="store_true")
    check = commands.add_parser("check")
    check.add_argument("module", nargs="?")
    check.add_argument("--all", action="store_true")
    check.add_argument("--validate", action="store_true")
    dev = commands.add_parser("dev")
    dev.add_argument("module")
    dev.add_argument("arguments", nargs=argparse.REMAINDER)
    new = commands.add_parser("new")
    new.add_argument("module_id")
    for name in ("name", "category", "standard", "filing-folder", "owner"):
        new.add_argument("--" + name, required=True)
    release = commands.add_parser("release-check")
    release.add_argument("--output", type=Path)
    arguments = parser.parse_args(argv)
    root = arguments.root.resolve()
    manifest = load_manifest(root)
    if arguments.command == "clean":
        from .clean import clean
        paths = clean(root, apply=arguments.apply)
        print(json.dumps({"applied": arguments.apply, "generatedDirectories": paths}, indent=2))
        return 0
    if arguments.command == "new":
        print(create_module(root, module_id=arguments.module_id, name=arguments.name,
                            category=arguments.category, standard=arguments.standard,
                            filing_folder=arguments.filing_folder, owner=arguments.owner))
        return 0
    if arguments.command == "list":
        for module in manifest["modules"]:
            print(f"{module['id']:<28} {'enabled' if module['enabled'] else 'planned':<10} {module['path']}")
        return 0
    if arguments.command == "release-check":
        roots = {root}
        for module in manifest["modules"]:
            path = (root / module["path"]).resolve()
            while path != root and path.is_relative_to(root):
                if (path / ".git").exists():
                    roots.add(path)
                    break
                path = path.parent
        revisions = []
        for repository in sorted(roots):
            status = subprocess.run(["git", "-C", str(repository), "status", "--porcelain"],
                                    capture_output=True, text=True, check=True, timeout=20)
            if status.stdout.strip():
                raise ValueError(f"Release blocked: uncommitted changes in {repository}")
            revision = subprocess.run(["git", "-C", str(repository), "rev-parse", "HEAD"],
                                      capture_output=True, text=True, check=True, timeout=20)
            revisions.append({"path": repository.relative_to(root).as_posix(), "commit": revision.stdout.strip()})
        document = json.dumps({"schema": 1, "repositories": revisions, "modules": manifest["modules"]}, indent=2)
        if arguments.output:
            arguments.output.parent.mkdir(parents=True, exist_ok=True)
            arguments.output.write_text(document, encoding="utf-8")
        print(document)
        return 0
    modules = [module for module in manifest["modules"]
               if (arguments.module and module["id"] == arguments.module)
               or (not arguments.module and module["enabled"])]
    if not modules:
        raise ValueError("No matching module in the suite manifest")
    successful = True
    for module in modules:
        sys.path.insert(0, str(root / module["path"]))
        adapter = importlib.import_module(module["entry"])
        if arguments.command == "dev":
            if module["id"] == "calculation-pad":
                notebook = importlib.import_module(adapter.__package__ + ".notebook")
                return develop(adapter, arguments.arguments, notebook_export=notebook.notebook_text)
            return develop(adapter, arguments.arguments)
        report = check_contract(adapter)
        if arguments.validate:
            outcome = adapter.validate()
            report["validation"] = outcome
            report["ok"] = report["ok"] and bool(outcome["ok"])
        print(json.dumps({"module": module["id"], **report}, indent=2, default=str))
        successful = successful and report["ok"]
    return 0 if successful else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, ImportError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)