"""Combine the project lists and people directories kept on each PC into one.

Every PC running InnoCalc today has its own ``projects.json`` and
``people.json``.  The server needs one of each, so this command reads the data
folder copied off each PC and writes the combined list into the server's data
folder.  Calculation libraries live in the project folders and need no merging.

    python -m icm.merge PC1-data PC2-data ...            dry run: report only
    python -m icm.merge PC1-data PC2-data ... --apply    write the combined files
    python -m icm.merge --libraries                      rewrite project files portably

Run ``--libraries`` on a PC before the cut-over: it rewrites every registered
project's calculation index and verification ``package.json`` files so they
hold no Windows paths.  Records written on a PC can only be made portable
where the PC's own drive letters still resolve.

Projects are matched by their location under the projects root, so the same
folder added on two PCs becomes one project with both teams.  A project added
from outside the projects root cannot be matched or served and is reported.
The destination's own data is always included; a backup is taken before
``--apply`` writes, and a running manager on the destination refuses the merge.
"""

from __future__ import annotations

import argparse
import json
import sys
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from . import backup
from .auth import Directory
from .library import Library
from .projects import ProjectRegistry


def _key(project: dict[str, Any]) -> str:
    return (project.get("location") or project.get("folderPath", "")).replace("\\", "/").casefold()


def merge(sources: list[Path], destination: Path, root: str,
          legacy_roots: tuple[str, ...] = ()) -> dict[str, Any]:
    """The combined registry and directory data, plus a report. Writes nothing."""
    projects: dict[str, dict[str, Any]] = {}
    by_key: dict[str, str] = {}
    members: dict[str, dict[str, dict[str, Any]]] = {}
    people: dict[str, dict[str, Any]] = {}
    report: dict[str, Any] = {"sources": [], "notPortable": [], "initialsShared": []}
    for source in [destination, *[item for item in sources if item.resolve() != destination.resolve()]]:
        registry = ProjectRegistry(source / "projects.json", root, legacy_roots)
        directory = Directory(source / "people.json")
        report["sources"].append({"folder": str(source),
                                  "projects": len(registry.data["projects"]),
                                  "people": len(directory.data)})
        renamed: dict[str, str] = {}
        for project_id, project in registry.data["projects"].items():
            if not project.get("location"):
                report["notPortable"].append(project.get("folderPath", ""))
            key = _key(project)
            if key in by_key:
                kept = projects[by_key[key]]
                for role in ("designers", "verifiers"):
                    kept[role] = sorted(set(kept.get(role, [])) | set(project.get(role, [])))
                kept["createdAt"] = min(kept.get("createdAt") or "9", project.get("createdAt") or "9")
                for field in ("code", "clientRef", "projectName"):
                    kept[field] = kept.get(field) or project.get(field, "")
                renamed[project_id] = by_key[key]
                continue
            merged_id = project_id if project_id not in projects else f"{project_id}{len(projects)}"
            projects[merged_id] = {**project, "id": merged_id}
            by_key[key] = merged_id
            renamed[project_id] = merged_id
        for email, entries in registry.data["members"].items():
            mine = members.setdefault(email, {})
            for project_id, entry in entries.items():
                target = renamed.get(project_id)
                if not target:
                    continue
                current = mine.get(target)
                if current is None or str(entry.get("lastOpened", "")) > str(current.get("lastOpened", "")):
                    mine[target] = dict(entry)
        for email, entry in directory.data.items():
            current = people.get(email)
            if current is None or str(entry.get("lastSeen", "")) > str(current.get("lastSeen", "")):
                people[email] = {**entry, "admin": bool(entry.get("admin"))
                                 or bool((current or {}).get("admin"))}
            else:
                current["admin"] = bool(current.get("admin")) or bool(entry.get("admin"))
    initials: dict[str, list[str]] = {}
    for email, entry in people.items():
        initials.setdefault(str(entry.get("initials", "")), []).append(email)
    report["initialsShared"] = {key: value for key, value in initials.items() if len(value) > 1}
    report["combined"] = {"projects": len(projects), "people": len(people)}
    return {"projects": {"schema": 1, "projects": projects, "members": members},
            "people": people, "report": report}


def apply(combined: dict[str, Any], destination: Path, root: str,
          legacy_roots: tuple[str, ...], backup_dir: Path) -> dict[str, Any]:
    with ExitStack() as stack:
        destination.mkdir(parents=True, exist_ok=True)
        backup.hold_data_lock(destination, stack)
        taken = backup.run_backup(destination, backup_dir)
        if taken.status == "failed":
            raise backup.Refused(f"could not back up {destination} first: {taken.error}")
        registry = ProjectRegistry(destination / "projects.json", root, legacy_roots)
        registry.data = combined["projects"]
        registry.write()
        directory = Directory(destination / "people.json")
        directory.data = combined["people"]
        directory.write()
    return {"backup": taken.public()}


def rewrite_libraries(registry: ProjectRegistry) -> dict[str, Any]:
    """Persist the portable path form in every reachable project's files."""
    from .qa import QAStore

    report: dict[str, Any] = {"rewritten": [], "unchanged": 0, "unreachable": [],
                              "packages": 0}
    for project in registry.data["projects"].values():
        folder = Path(project.get("folderPath", ""))
        if not (folder / "09-Doc_WRK").is_dir():
            report["unreachable"].append(str(folder))
            continue
        library = Library(folder)
        if library.rewrite_portable():
            report["rewritten"].append(project.get("code") or str(folder))
        else:
            report["unchanged"] += 1
        store = QAStore(library, project)
        for package in store.packages:
            target = store.folder(package) / "package.json"
            if package.get("folder") and target.is_file():
                target.write_text(json.dumps(package, indent=2, ensure_ascii=True, default=str),
                                  encoding="utf-8")
                report["packages"] += 1
    return report


def main(argv: list[str] | None = None) -> int:
    from . import config

    settings = config.load()
    parser = argparse.ArgumentParser(prog="python -m icm.merge",
                                     description=__doc__.split("\n")[0])
    parser.add_argument("sources", nargs="*", type=Path,
                        help="data folders copied from each PC (apps/manager/data)")
    parser.add_argument("--into", type=Path, default=settings.data_dir,
                        help="the data folder to write (default: this instance's)")
    parser.add_argument("--apply", action="store_true", help="write the combined files")
    parser.add_argument("--libraries", action="store_true",
                        help="rewrite this instance's project files without Windows paths")
    arguments = parser.parse_args(argv)
    if arguments.libraries:
        registry = ProjectRegistry(arguments.into / "projects.json", settings.root,
                                   settings.legacy_roots)
        print(json.dumps(rewrite_libraries(registry), indent=2))
        return 0
    if not arguments.sources:
        parser.error("name at least one data folder to merge, or use --libraries")
    missing = [str(item) for item in arguments.sources if not item.is_dir()]
    if missing:
        print(f"not a folder: {', '.join(missing)}", file=sys.stderr)
        return 2
    combined = merge(arguments.sources, arguments.into, settings.root, settings.legacy_roots)
    print(json.dumps(combined["report"], indent=2))
    if not arguments.apply:
        print("dry run: nothing written; add --apply to write the combined lists")
        return 0
    try:
        outcome = apply(combined, arguments.into, settings.root, settings.legacy_roots,
                        settings.backup_dir)
    except backup.Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(outcome, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
