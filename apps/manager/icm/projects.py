"""Project discovery, registry and navigation.

The previous tool resolved a project by walking the network projects root on
every miss, which made opening and switching projects slow and unreliable.  Here
the durable registry is the source of truth, a project has a stable id that does
not depend on path spelling or case, and every filesystem scan runs on a
background thread behind a hard deadline so the interface never blocks.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from .paths import is_absolute, locate, relative

# A project code is an optional letter prefix, three to six digits, optional suffix.
_CODE_SHAPE = re.compile(r"^[A-Z]{0,2}\d{3,6}[A-Z]?$")
# 'J3601 to J3700' style block folders are containers, not projects.
_GROUP_SHAPE = re.compile(r"^[A-Z]?\d+\s*(?:to|-)\s*[A-Z]?\d+$", re.I)
_NOT_ALNUM = re.compile(r"[^A-Za-z0-9]")
_SKIP = {"$recycle.bin", "system volume information", "09-doc_wrk", "01-cal", "06-qa",
         "superseded", "superseeded", "node_modules", ".git", "archive", "archived"}
MAX_DEPTH = 3
SCAN_SECONDS = 25.0

# Innovis project folder skeleton created for a new project.
PROJECT_SKELETON = [
    Path("09-Doc_WRK") / "01-CAL" / "10-IN_TOOL",
    Path("06-QA") / "03-Verification",
]


def normalise_code(value: Any) -> str:
    """'j3657', ' J3657 ', '3657' -> 'J3657'."""
    text = _NOT_ALNUM.sub("", str(value or "")).upper()
    if not text:
        raise ValueError("Enter a project number")
    return f"J{text}" if text.isdigit() else text


def code_variants(code: str) -> set[str]:
    digits = re.sub(r"\D", "", code)
    return {value for value in {code, digits, f"J{digits}" if digits else ""} if value}


def folder_code(folder_name: str) -> str:
    token = re.split(r"[\s\-_]+", str(folder_name).strip(), maxsplit=1)[0]
    return _NOT_ALNUM.sub("", token).upper()


def looks_like_project(folder_name: str) -> bool:
    name = str(folder_name).strip()
    if _GROUP_SHAPE.fullmatch(name):
        return False
    return bool(_CODE_SHAPE.fullmatch(folder_code(name)))


def group_for(code: str) -> str:
    """100-code block folder name, e.g. J3657 -> 'J3601 to J3700'."""
    digits = re.sub(r"\D", "", code)
    if not digits:
        return ""
    start = ((int(digits) - 1) // 100) * 100 + 1
    return f"J{start} to J{start + 99}"


def parse_folder_name(name: str) -> tuple[str, str, str]:
    """Split 'JXXXX - CCC - ZZZZ' into (code, clientRef, projectName)."""
    parts = [part.strip() for part in str(name).split(" - ")]
    code = parts[0] if parts else str(name)
    return code, (parts[1] if len(parts) > 1 else ""), (" - ".join(parts[2:]) if len(parts) > 2 else "")


def describe(folder_path: str) -> dict[str, Any]:
    folder_path = str(folder_path).strip().rstrip("\\/")
    folder_name = os.path.basename(folder_path)
    code, client, project = parse_folder_name(folder_name)
    return {"folderPath": folder_path, "folderName": folder_name,
            "group": os.path.basename(os.path.dirname(folder_path)),
            "code": code, "clientRef": client, "projectName": project}


def project_root(folder_path: Any) -> str:
    """Climb a chosen folder back up to the project's own top level folder.

    Picking ``...\\J3657 - ABC - Warehouse\\09-Doc_WRK\\01-CAL`` must register the
    project, not the sub-folder, so the Innovis skeleton is never built in the
    wrong place.
    """
    path = str(folder_path or "").strip().rstrip("\\/")
    if not path:
        return path
    current = os.path.normpath(path)
    best = ""
    while True:
        if looks_like_project(os.path.basename(current)):
            best = current
        parent = os.path.dirname(current)
        if not parent or parent == current:
            break
        current = parent
    return best or path


def _child_dirs(path: str) -> Iterator[os.DirEntry]:
    try:
        with os.scandir(path) as entries:
            for entry in sorted(entries, key=lambda item: item.name.casefold()):
                if entry.is_dir(follow_symlinks=False) and entry.name.casefold() not in _SKIP:
                    yield entry
    except OSError:
        return


def _key(folder_path: Any) -> str:
    key = str(folder_path or "").strip().rstrip("\\/")
    if not key:
        raise ValueError("A project folder is required")
    return os.path.normpath(key).casefold()


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=True, default=str),
                         encoding="utf-8")
    temporary.replace(path)


def under_root(folder_path: Any, root: Any, legacy_roots: tuple[str, ...] = ()) -> str | None:
    """A folder's location relative to the projects root ('/' separated), or None if outside.

    A path written on a PC under a legacy root such as ``J:\\Active Projects`` is
    recognised on any host, so a Linux server can adopt a PC's records.
    """
    for base in (root, *legacy_roots):
        found = relative(folder_path, base)
        if found is not None:
            return found
    return None


# ---------------------------------------------------------------------------
#  Background discovery
# ---------------------------------------------------------------------------
class Discovery:
    """Cached index of project folders under the projects root.

    Scans never run on the request thread. ``find`` answers from the cache
    immediately and schedules a refresh when the cache cannot answer.
    """

    def __init__(self, path: Path, root: str, legacy_roots: tuple[str, ...] = ()):
        self.path = Path(path)
        self.root = str(root)
        self.legacy_roots = tuple(legacy_roots)
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        self.data: dict[str, Any] = data if isinstance(data, dict) else {}
        self.data.setdefault("schema", 1)
        self.data.setdefault("projects", {})
        self.data.setdefault("scannedAt", "")
        # Older releases stored absolute paths under a recorded root; adopt them.
        stored_root = str(self.data.pop("root", "") or "")
        roots = tuple(item for item in (stored_root, *self.legacy_roots) if item)
        self.data["projects"] = {
            code: [self._absolute(item, roots) for item in paths]
            for code, paths in self.data["projects"].items()}

    def _absolute(self, stored: str, roots: tuple[str, ...] = ()) -> str:
        if is_absolute(stored):
            found = under_root(stored, self.root, roots)
            return stored if found is None else str(locate(found, self.root))
        return str(locate(stored, self.root))

    # -- persistence --------------------------------------------------------
    def write(self) -> None:
        with self._lock:
            _atomic_json(self.path, {**self.data, "projects": {
                code: [self._stored(item) for item in paths]
                for code, paths in self.data["projects"].items()}})

    def _stored(self, folder_path: str) -> str:
        found = under_root(folder_path, self.root)
        return folder_path if found is None else found

    def remember(self, folder_path: str) -> None:
        """Record a folder permanently, including one chosen outside the root."""
        folder_path = str(folder_path).rstrip("\\/")
        code = folder_code(os.path.basename(folder_path))
        if not (folder_path and code):
            return
        paths = self.data["projects"].setdefault(code, [])
        if not any(_key(existing) == _key(folder_path) for existing in paths):
            paths.append(folder_path)
            self.write()

    # -- scanning -----------------------------------------------------------
    def status(self) -> dict[str, Any]:
        return {"root": self.root, "rootExists": os.path.isdir(self.root),
                "scannedAt": self.data.get("scannedAt", ""),
                "scanning": bool(self._thread and self._thread.is_alive()),
                "folders": sum(len(paths) for paths in self.data["projects"].values())}

    def refresh_async(self) -> dict[str, Any]:
        if self._thread and self._thread.is_alive():
            return self.status()
        self._thread = threading.Thread(target=self._scan, name="icm-project-scan", daemon=True)
        self._thread.start()
        return self.status()

    def _scan(self) -> None:
        if not os.path.isdir(self.root):
            return
        deadline = time.monotonic() + SCAN_SECONDS
        found: dict[str, list[str]] = {}

        def walk(path: str, depth: int) -> None:
            if depth > MAX_DEPTH or time.monotonic() > deadline:
                return
            for entry in _child_dirs(path):
                if time.monotonic() > deadline:
                    return
                if looks_like_project(entry.name):
                    found.setdefault(folder_code(entry.name), []).append(entry.path)
                walk(entry.path, depth + 1)

        walk(self.root, 1)
        if not found:
            return
        # Keep hand-added folders that live outside the root.
        merged = {code: list(paths) for code, paths in found.items()}
        for code, paths in self.data["projects"].items():
            for path in paths:
                if not any(_key(path) == _key(known) for known in merged.get(code, [])):
                    merged.setdefault(code, []).append(path)
        self.data["projects"] = merged
        self.data["scannedAt"] = datetime.now().isoformat(timespec="seconds")
        self.data["partial"] = time.monotonic() > deadline
        self.write()

    # -- lookup -------------------------------------------------------------
    def cached(self, code: str) -> list[str]:
        variants = code_variants(code)
        paths: list[str] = []
        for key, known in self.data["projects"].items():
            if not (key in variants or any(key.startswith(item) for item in variants)):
                continue
            for path in known:
                if os.path.isdir(path) and path not in paths:
                    paths.append(path)
        return paths

    def targeted(self, code: str) -> list[str]:
        """Cheap look in the expected block folder; never walks the whole root."""
        variants = code_variants(code)
        found: list[str] = []
        for parent in (os.path.join(self.root, group_for(code)), self.root):
            if not os.path.isdir(parent):
                continue
            for entry in _child_dirs(parent):
                if not looks_like_project(entry.name):
                    continue
                name_code = folder_code(entry.name)
                if name_code in variants or any(name_code.startswith(item) for item in variants):
                    found.append(entry.path)
        return found

    def find(self, value: Any) -> dict[str, Any]:
        """Resolve a project number without ever blocking on a full scan."""
        code = normalise_code(value)
        paths = self.cached(code)
        source = "index"
        if not paths:
            paths = self.targeted(code)
            source = "folder"
            for path in paths:
                self.remember(path)
        scanning = False
        if not paths:
            scanning = True
            self.refresh_async()
            source = "scanning"
        ordered = sorted(set(paths), key=lambda path: (os.path.basename(path).casefold(), path))
        return {"code": code, "source": source, "scanning": scanning,
                "matches": [describe(path) for path in ordered]}

    def search(self, value: Any, limit: int = 40) -> dict[str, Any]:
        """Find by project number or by any part of the client or project name."""
        needle = str(value or "").strip()
        if len(needle) < 2:
            return {"query": needle, "scanning": False, "matches": []}
        if re.fullmatch(r"[A-Za-z]?\d{2,6}[A-Za-z]?", needle):
            return {"query": needle, **self.find(needle)}
        folded = needle.casefold()
        hits = [path for paths in self.data["projects"].values() for path in paths
                if folded in os.path.basename(path).casefold()]
        scanning = False
        if not hits and not self.data.get("scannedAt"):
            scanning = True
            self.refresh_async()
        ordered = sorted(set(hits), key=lambda path: os.path.basename(path).casefold())
        return {"query": needle, "source": "index", "scanning": scanning,
                "matches": [describe(path) for path in ordered[:limit]
                            if os.path.isdir(path)]}


# ---------------------------------------------------------------------------
#  Registry
# ---------------------------------------------------------------------------
class ProjectRegistry:
    """Durable list of projects and each person's view of them."""

    def __init__(self, path: Path, root: str = "", legacy_roots: tuple[str, ...] = ()):
        self.path = Path(path)
        self.root = str(root)
        self.legacy_roots = tuple(legacy_roots)
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        self.data: dict[str, Any] = data if isinstance(data, dict) else {}
        self.data.setdefault("schema", 1)
        self.data.setdefault("projects", {})
        self.data.setdefault("members", {})
        for project in self.data["projects"].values():
            self._place(project)
        self._lock = threading.Lock()

    def _place(self, project: dict[str, Any]) -> None:
        """Set ``folderPath`` for this machine from the stored, root-relative ``location``."""
        if "location" not in project:
            found = under_root(project.get("folderPath", ""), self.root, self.legacy_roots)
            project["location"] = "" if found is None else found
        if project["location"]:
            project["folderPath"] = str(locate(project["location"], self.root))

    def _locate_new(self, project: dict[str, Any]) -> None:
        found = under_root(project["folderPath"], self.root)
        project["location"] = "" if found is None else found

    def write(self) -> None:
        """Projects under the root are stored by location only; no drive letter is written."""
        with self._lock:
            stored = {project_id: ({key: value for key, value in project.items()
                                    if key != "folderPath"} if project.get("location")
                                   else project)
                      for project_id, project in self.data["projects"].items()}
            _atomic_json(self.path, {**self.data, "projects": stored})

    # -- lookup -------------------------------------------------------------
    def by_path(self, folder_path: Any) -> dict[str, Any] | None:
        target = _key(folder_path)
        return next((project for project in self.data["projects"].values()
                     if _key(project["folderPath"]) == target), None)

    def get(self, project_id: Any) -> dict[str, Any]:
        project = self.data["projects"].get(str(project_id or ""))
        if not project:
            raise ValueError("That project is no longer in your list; open it again")
        return project

    # -- mutation -----------------------------------------------------------
    def register(self, folder_path: str, actor: dict[str, Any],
                 create_folders: bool = True) -> dict[str, Any]:
        """Add (or return) a project, creating the folder and skeleton as needed.

        A folder chosen below the project's own level is walked back up, so the
        registered project is always ``...\\JXXXX - CLIENT - PROJECT NAME``.
        """
        folder = Path(project_root(folder_path))
        if not str(folder):
            raise ValueError("A project folder is required")
        if not folder.is_absolute():
            raise ValueError("The project folder must be a full path")
        if create_folders:
            folder.mkdir(parents=True, exist_ok=True)
        if not folder.is_dir():
            raise ValueError(f"The folder does not exist: {folder}")
        if create_folders:
            for branch in PROJECT_SKELETON:
                (folder / branch).mkdir(parents=True, exist_ok=True)
        existing = self.by_path(folder)
        if existing:
            existing.update(describe(str(folder)))
            self._locate_new(existing)
            self.write()
            return existing
        project = {"id": uuid.uuid4().hex[:12], **describe(str(folder)),
                   "createdAt": datetime.now().isoformat(timespec="seconds"),
                   "createdBy": actor.get("email", ""), "designers": [], "verifiers": []}
        self._locate_new(project)
        self.data["projects"][project["id"]] = project
        self.write()
        return project

    def relink(self, project_id: str, folder_path: str) -> dict[str, Any]:
        """Point an existing project at a new folder after a move or a broken link."""
        project = self.get(project_id)
        folder = Path(project_root(folder_path))
        if not folder.is_dir():
            raise ValueError(f"The folder does not exist: {folder}")
        clash = self.by_path(folder)
        if clash and clash["id"] != project["id"]:
            raise ValueError("Another project in your list already uses that folder")
        for branch in PROJECT_SKELETON:
            (folder / branch).mkdir(parents=True, exist_ok=True)
        described = describe(str(folder))
        project["folderPath"] = described["folderPath"]
        project["folderName"] = described["folderName"]
        project["group"] = described["group"]
        self._locate_new(project)
        self.write()
        return project

    def rename(self, project_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        project = self.get(project_id)
        for key in ("code", "clientRef", "projectName"):
            if key in fields:
                project[key] = str(fields[key]).strip()
        self.write()
        return project

    def set_people(self, project_id: str, designers: list[str], verifiers: list[str]) -> dict[str, Any]:
        project = self.get(project_id)
        project["designers"] = sorted({str(item).strip().lower() for item in designers if item})
        project["verifiers"] = sorted({str(item).strip().lower() for item in verifiers if item})
        self.write()
        return project

    def touch(self, project_id: str, actor: dict[str, Any]) -> None:
        member = self.data["members"].setdefault(actor["email"], {})
        entry = member.setdefault(project_id, {"archived": False})
        entry["lastOpened"] = datetime.now().isoformat(timespec="seconds")
        project = self.get(project_id)
        if actor["email"] not in project["designers"] and actor["email"] not in project["verifiers"]:
            project["designers"].append(actor["email"])
        self.write()

    def set_archived(self, project_id: str, actor: dict[str, Any], archived: bool) -> None:
        self.get(project_id)
        member = self.data["members"].setdefault(actor["email"], {})
        member.setdefault(project_id, {})["archived"] = bool(archived)
        self.write()

    def forget(self, project_id: str, actor: dict[str, Any]) -> None:
        """Remove a project from one person's list; the folder is never touched.

        Opening a project adds you to its designers, so the membership record
        alone is not enough - the person has to come off the project's own lists
        as well or it reappears at the next refresh.
        """
        self.data["members"].get(actor["email"], {}).pop(project_id, None)
        project = self.data["projects"].get(str(project_id))
        if project:
            for role in ("designers", "verifiers"):
                project[role] = [item for item in project.get(role, [])
                                 if str(item).casefold() != str(actor["email"]).casefold()]
        self.write()

    # -- presentation -------------------------------------------------------
    def for_user(self, actor: dict[str, Any], directory: Any = None) -> list[dict[str, Any]]:
        member = self.data["members"].get(actor["email"], {})
        listed = []
        for project_id, project in self.data["projects"].items():
            view = member.get(project_id)
            involved = (actor["email"] in project.get("designers", [])
                        or actor["email"] in project.get("verifiers", []))
            if view is None and not involved:
                continue
            role = "Verifier" if actor["email"] in project.get("verifiers", []) else "Designer"
            listed.append({**project, "role": role,
                           "archived": bool((view or {}).get("archived")),
                           "lastOpened": (view or {}).get("lastOpened", ""),
                           "exists": os.path.isdir(project["folderPath"])})
        # Stable sorts compose: active first, then most recently opened, then code.
        listed.sort(key=lambda item: str(item.get("code", "")).casefold())
        listed.sort(key=lambda item: item["lastOpened"], reverse=True)
        listed.sort(key=lambda item: item["archived"])
        return listed
