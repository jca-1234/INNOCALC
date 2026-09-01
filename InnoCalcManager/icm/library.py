"""The calculation library for one project.

Every calculation from every module is recorded in one index inside the project
folder, so the library survives the manager's own data folder being lost and can
be opened by anyone with access to the drive.  Inputs are stored with the record
so reopening a calculation is instant and never depends on parsing HTML.

Layout inside a project folder::

    09-Doc_WRK/01-CAL/10-IN_TOOL/
        innocalc-library.json
        01 - STEEL MEMBER/<Package>/Rafter-0001-260901 14-30-JA.html (+ .pdf)
        01 - STEEL MEMBER/<Package>/superseded/...
        02 - CONCRETE COLUMN/...
        90 - CALCULATION PAD/...
"""

from __future__ import annotations

import json
import re
import shutil
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

CALCULATION_ROOT = Path("09-Doc_WRK") / "01-CAL" / "10-IN_TOOL"
INDEX_NAME = "innocalc-library.json"
SUPERSEDED = "superseded"
LEGACY_SUPERSEDED = "superseeded"
# Calculations produced by other software and filed here as PDF only.
IMPORTED = "imported-pdf"
IMPORTED_FOLDER = "80 - IMPORTED"
# Kept so calculations filed by the standalone steel tool are still found.
LEGACY_ROOTS = [Path("09-Doc_WRK") / "01-CAL" / "10 - STEEL DESIGN TOOL"]


def safe_name(value: Any) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", str(value).strip())
    return re.sub(r"\s+", " ", value).strip(" .-") or "Unallocated"


def clean_initials(value: Any) -> str:
    return (re.sub(r"[^A-Za-z]", "", str(value)).upper() or "XX")[:4]


def normalise_number(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.isdigit():
        if len(text) > 4:
            raise ValueError("Numeric calculation numbers may have at most four digits")
        return text.zfill(4)
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9._-]*", text):
        raise ValueError("A calculation number must be numeric or begin with a letter")
    return text.upper()


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=True, default=str),
                         encoding="utf-8")
    temporary.replace(path)


def _matches(wanted: Any, value: Any) -> bool:
    """Filter test that accepts nothing, one value or a multi-select list."""
    if wanted is None or wanted == "" or wanted == []:
        return True
    allowed = wanted if isinstance(wanted, (list, tuple, set)) else [wanted]
    allowed = [str(item) for item in allowed if str(item) != ""]
    return not allowed or str(value or "") in allowed


class Library:
    """Reads and writes one project's calculation index."""

    _locks: dict[str, threading.Lock] = {}

    def __init__(self, project_folder: str | Path):
        self.project_folder = Path(project_folder).resolve()
        self.root = self.project_folder / CALCULATION_ROOT
        self.path = self.root / INDEX_NAME
        self.lock = Library._locks.setdefault(str(self.path).casefold(), threading.Lock())
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        self.data: dict[str, Any] = data if isinstance(data, dict) else {}
        self.data.setdefault("schema", 1)
        self.data.setdefault("calculations", [])
        self.data.setdefault("packages", ["Unallocated"])
        self.data.setdefault("levels", [])
        self.data.setdefault("register", [])
        self.data.setdefault("qaPackages", [])
        self.data.setdefault("issues", [])

    def write(self) -> None:
        with self.lock:
            _atomic_json(self.path, self.data)

    # -- reading ------------------------------------------------------------
    def calculation(self, calculation_id: Any) -> dict[str, Any]:
        record = next((item for item in self.data["calculations"]
                       if item["id"] == str(calculation_id)), None)
        if not record:
            raise ValueError("That calculation is not in this project's library")
        return record

    def match(self, module_id: str, member_type: str, number: str) -> dict[str, Any] | None:
        number = normalise_number(number)
        return next((item for item in self.data["calculations"]
                     if item["module"] == module_id
                     and item["memberType"].casefold() == str(member_type).casefold()
                     and item["memberNumber"] == number), None)

    def index(self, *, show_superseded: bool = False, search: str = "",
              package: str = "", module_id: str = "", level: str = "",
              calc_type: str = "") -> dict[str, Any]:
        """The library view the landing page renders, with filters applied.

        Every filter accepts a single value or a list, so the Calculation Index
        can offer multi-select dropdowns without a second code path.
        """
        needle = str(search or "").strip().casefold()
        rows = []
        for record in self.data["calculations"]:
            if not _matches(package, record.get("package")):
                continue
            if not _matches(module_id, record.get("module")):
                continue
            if not _matches(level, record.get("level")):
                continue
            if not _matches(calc_type, record.get("calcType")):
                continue
            if needle and needle not in self._haystack(record):
                continue
            revisions = record.get("revisions", [])
            if not show_superseded:
                revisions = [item for item in revisions if not item.get("superseded")]
            if not revisions and not show_superseded:
                continue
            latest = revisions[-1] if revisions else {}
            rows.append({**{key: value for key, value in record.items() if key != "inputs"},
                         "revisions": revisions,
                         "superseded": bool(latest.get("superseded")),
                         "folder": str(self.folder_of(record)),
                         "pdfPath": str(self.pdf_of(record) or ""),
                         "revisionCount": len(record.get("revisions", []))})
        rows.sort(key=lambda item: (str(item.get("package", "")).casefold(),
                                    str(item.get("level", "")).casefold(),
                                    str(item.get("memberType", "")).casefold(),
                                    str(item.get("memberNumber", ""))))
        return {"projectFolder": str(self.project_folder), "toolFolder": str(self.root),
                "packages": sorted(self.data["packages"], key=str.casefold),
                "levels": sorted({str(item.get("level") or "") for item in
                                  self.data["calculations"] if item.get("level")},
                                 key=str.casefold),
                "calcTypes": sorted({str(item.get("calcType") or "") for item in
                                     self.data["calculations"] if item.get("calcType")},
                                    key=str.casefold),
                "memberTypes": sorted({str(item.get("memberType") or "") for item in
                                       self.data["calculations"] if item.get("memberType")},
                                      key=str.casefold),
                "issues": list(reversed(self.data.get("issues", []))),
                "calculations": rows, "total": len(self.data["calculations"])}

    def folder_of(self, record: dict[str, Any]) -> Path:
        """The folder the calculation's files are filed in."""
        revisions = record.get("revisions") or []
        if revisions:
            return (self.root / revisions[-1].get("relativePath", "")).parent
        return self.root / safe_name(record.get("moduleFolder", "")) / record.get("package", "")

    def pdf_of(self, record: dict[str, Any]) -> Path | None:
        revisions = record.get("revisions") or []
        if not revisions:
            return None
        target = (self.root / revisions[-1].get("relativePath", "")).with_suffix(".pdf")
        return target if target.is_file() else None

    @staticmethod
    def _haystack(record: dict[str, Any]) -> str:
        return " ".join(str(record.get(key, "")) for key in
                        ("memberType", "memberNumber", "package", "level", "title",
                         "calcType", "criticalCheck", "module", "notes",
                         "description", "checker")).casefold()

    # -- writing ------------------------------------------------------------
    def add_package(self, value: Any) -> str:
        name = safe_name(value or "Unallocated")
        existing = next((item for item in self.data["packages"]
                         if item.casefold() == name.casefold()), None)
        if existing:
            return existing
        self.data["packages"].append(name)
        self.data["packages"].sort(key=str.casefold)
        self.write()
        return name

    def save(self, *, module_id: str, module_folder: str, inputs: dict[str, Any],
             identity: dict[str, Any], summary: dict[str, Any], html_text: str,
             initials: str, calculation_id: str = "", supersede: bool = True) -> dict[str, Any]:
        """File a new revision of a calculation and update the index."""
        member_type = safe_name(identity.get("memberType") or "Calculation")
        number = normalise_number(identity.get("memberNumber") or "")
        package = self.add_package(identity.get("package"))
        record = None
        if calculation_id:
            record = self.calculation(calculation_id)
        if record is None:
            record = self.match(module_id, member_type, number)
        active = [item for item in (record or {}).get("revisions", [])
                  if not item.get("superseded")]
        if active and not supersede:
            return {"conflict": True, "calculation": {
                key: value for key, value in record.items() if key != "inputs"}}

        package_folder = self.root / safe_name(module_folder) / package
        package_folder.mkdir(parents=True, exist_ok=True)
        saved_at = datetime.now()
        while True:
            stamp = saved_at.strftime("%y%m%d %H-%M")
            base = f"{member_type}-{number}-{stamp}-{clean_initials(initials)}"
            if not any(self.root.rglob(f"{base}.html")):
                break
            saved_at += timedelta(minutes=1)

        if record is None:
            record = {"id": uuid.uuid4().hex[:12], "module": module_id,
                      "moduleFolder": safe_name(module_folder), "revisions": [],
                      "finalised": False, "verifierComment": "", "designerResponse": "",
                      "notes": "", "description": "", "checker": ""}
            self.data["calculations"].append(record)

        self._supersede(record, package_folder)
        html_path = package_folder / f"{base}.html"
        html_path.write_text(html_text, encoding="utf-8")
        revision = {"rev": len(record["revisions"]) + 1, "filename": html_path.name,
                    "relativePath": str(html_path.relative_to(self.root)),
                    "savedAt": saved_at.replace(second=0, microsecond=0).isoformat(timespec="minutes"),
                    "initials": clean_initials(initials), "superseded": False,
                    "worstUtil": summary.get("worstUtil", 0.0),
                    "criticalCheck": summary.get("criticalCheck", ""),
                    "status": summary.get("status", "")}
        record["revisions"].append(revision)
        record.update({"module": module_id, "moduleFolder": safe_name(module_folder),
                       "memberType": member_type, "memberNumber": number, "package": package,
                       "level": str(identity.get("level") or ""),
                       "calcType": str(identity.get("calcType") or ""),
                       "title": str(identity.get("title") or ""),
                       "description": str(inputs.get("description")
                                          or record.get("description") or ""),
                       "worstUtil": summary.get("worstUtil", 0.0),
                       "criticalCheck": summary.get("criticalCheck", ""),
                       "status": summary.get("status", ""),
                       "headline": summary.get("headline", ""),
                       "updatedAt": revision["savedAt"], "updatedBy": clean_initials(initials),
                       "inputs": inputs})
        if record["level"] and record["level"] not in self.data["levels"]:
            self.data["levels"].append(record["level"])
        self.write()
        return {"conflict": False, "calculationId": record["id"], "revision": revision,
                "htmlPath": str(html_path), "pdfPath": str(html_path.with_suffix(".pdf"))}

    def _supersede(self, record: dict[str, Any], package_folder: Path) -> None:
        target = package_folder / SUPERSEDED
        for revision in record.get("revisions", []):
            if revision.get("superseded"):
                continue
            revision["superseded"] = True
            source = self.root / revision["relativePath"]
            if not source.exists():
                continue
            target.mkdir(parents=True, exist_ok=True)
            destination = target / source.name
            shutil.move(str(source), str(destination))
            revision["relativePath"] = str(destination.relative_to(self.root))
            source_pdf = source.with_suffix(".pdf")
            if source_pdf.exists():
                shutil.move(str(source_pdf), str(destination.with_suffix(".pdf")))

    def update(self, calculation_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        """Edit the library metadata of a calculation, moving files if repackaged."""
        record = self.calculation(calculation_id)
        if "package" in fields:
            package = self.add_package(fields["package"])
            if package != record.get("package"):
                self._repackage(record, package)
        for key in ("level", "verifierComment", "designerResponse", "notes", "title",
                    "description"):
            if key in fields:
                record[key] = str(fields[key]).strip()
        if "finalised" in fields:
            record["finalised"] = bool(fields["finalised"])
        if record.get("level") and record["level"] not in self.data["levels"]:
            self.data["levels"].append(record["level"])
        self.write()
        return record

    def set_checker(self, calculation_ids: list[str], initials: str, reference: str) -> int:
        """Record the verifier against calculations a verification package closed out.

        ``Checked by`` is never typed by the designer: it appears only once the
        verifier has endorsed the package the calculation was issued in.
        """
        marked = 0
        wanted = {str(item) for item in calculation_ids}
        for record in self.data["calculations"]:
            if record["id"] not in wanted:
                continue
            record["checker"] = clean_initials(initials)
            record["checkedIn"] = str(reference)
            record["checkedAt"] = datetime.now().isoformat(timespec="minutes")
            marked += 1
        if marked:
            self.write()
        return marked

    def import_pdf(self, *, source: str | Path, member_type: str, number: str,
                   package: str, level: str, title: str, description: str,
                   calc_type: str, initials: str, origin: str = "") -> dict[str, Any]:
        """File a calculation prepared in other software as a library record."""
        source = Path(str(source))
        if source.suffix.lower() != ".pdf" or not source.is_file():
            raise ValueError("Choose a PDF file to import")
        member_type = safe_name(member_type or source.stem)
        number = normalise_number(number)
        package = self.add_package(package)
        folder = self.root / IMPORTED_FOLDER / package
        folder.mkdir(parents=True, exist_ok=True)
        saved_at = datetime.now()
        while True:
            stamp = saved_at.strftime("%y%m%d %H-%M")
            base = f"{member_type}-{number}-{stamp}-{clean_initials(initials)}"
            if not any(self.root.rglob(f"{base}.pdf")):
                break
            saved_at += timedelta(minutes=1)
        target = folder / f"{base}.pdf"
        shutil.copy2(str(source), str(target))

        record = self.match(IMPORTED, member_type, number)
        if record is None:
            record = {"id": uuid.uuid4().hex[:12], "module": IMPORTED,
                      "moduleFolder": IMPORTED_FOLDER, "revisions": [], "finalised": False,
                      "verifierComment": "", "designerResponse": "", "notes": ""}
            self.data["calculations"].append(record)
        self._supersede(record, folder)
        revision = {"rev": len(record["revisions"]) + 1, "filename": target.name,
                    "relativePath": str(target.relative_to(self.root)),
                    "savedAt": saved_at.replace(second=0, microsecond=0).isoformat(timespec="minutes"),
                    "initials": clean_initials(initials), "superseded": False,
                    "worstUtil": 0.0, "criticalCheck": "", "status": ""}
        record["revisions"].append(revision)
        record.update({"memberType": member_type, "memberNumber": number, "package": package,
                       "level": str(level or ""),
                       "calcType": str(calc_type or "Imported PDF"),
                       "title": str(title or source.stem),
                       "description": str(description or ""),
                       "origin": str(origin or source.name),
                       "worstUtil": 0.0, "criticalCheck": "", "status": "",
                       "headline": "Imported PDF calculation",
                       "updatedAt": revision["savedAt"],
                       "updatedBy": clean_initials(initials), "inputs": {}})
        if record["level"] and record["level"] not in self.data["levels"]:
            self.data["levels"].append(record["level"])
        self.write()
        return {"calculationId": record["id"], "pdfPath": str(target),
                "revision": revision}

    def record_issue(self, entry: dict[str, Any]) -> dict[str, Any]:
        """Add an exported package to the project's issue register."""
        issue = {"id": uuid.uuid4().hex[:10],
                 "issuedAt": datetime.now().isoformat(timespec="minutes"),
                 "date": datetime.now().strftime("%d/%m/%Y"), **entry}
        self.data.setdefault("issues", []).append(issue)
        self.write()
        return issue

    def _repackage(self, record: dict[str, Any], package: str) -> None:
        destination = self.root / record.get("moduleFolder", "") / package
        for revision in record.get("revisions", []):
            source = self.root / revision["relativePath"]
            folder = destination / SUPERSEDED if revision.get("superseded") else destination
            folder.mkdir(parents=True, exist_ok=True)
            target = folder / source.name
            if source.exists() and source != target:
                shutil.move(str(source), str(target))
                source_pdf = source.with_suffix(".pdf")
                if source_pdf.exists():
                    shutil.move(str(source_pdf), str(target.with_suffix(".pdf")))
            revision["relativePath"] = str(target.relative_to(self.root))
        record["package"] = package

    def delete(self, calculation_id: str) -> None:
        """Remove a calculation from the index. Files stay on disk."""
        record = self.calculation(calculation_id)
        self.data["calculations"] = [item for item in self.data["calculations"]
                                     if item["id"] != record["id"]]
        self.write()

    def absolute(self, relative_path: str) -> Path:
        """Resolve a stored relative path, refusing anything outside the library."""
        target = (self.root / str(relative_path)).resolve()
        if not str(target).casefold().startswith(str(self.root.resolve()).casefold()):
            raise ValueError("That file is outside the project's calculation folder")
        return target

    # -- legacy discovery ---------------------------------------------------
    def adopt_existing(self) -> int:
        """Index calculations filed by the standalone tools before the manager."""
        pattern = re.compile(
            r"^(?P<type>.+)-(?P<number>\d{4}|[A-Z][A-Z0-9._-]*)"
            r"-(?P<stamp>\d{6} \d{2}-\d{2})-(?P<initials>[^.]+)\.html$", re.I)
        known = {item["relativePath"].casefold()
                 for record in self.data["calculations"]
                 for item in record.get("revisions", [])}
        roots = [self.root] + [self.project_folder / legacy for legacy in LEGACY_ROOTS]
        adopted = 0
        for root in roots:
            if not root.is_dir():
                continue
            for path in sorted(root.rglob("*.html")):
                match = pattern.match(path.name)
                if not match:
                    continue
                try:
                    relative = str(path.relative_to(self.root))
                except ValueError:
                    relative = str(path)
                if relative.casefold() in known:
                    continue
                parts = [part.casefold() for part in path.parts]
                superseded = SUPERSEDED in parts or LEGACY_SUPERSEDED in parts
                package = self.add_package(self._package_from(path, root))
                record = self.match("steel-member", match["type"], match["number"])
                if record is None:
                    record = {"id": uuid.uuid4().hex[:12], "module": "steel-member",
                              "moduleFolder": "01 - STEEL MEMBER",
                              "memberType": match["type"],
                              "memberNumber": normalise_number(match["number"]),
                              "package": package, "level": "", "calcType": "Steel member",
                              "title": f"{match['type']} {match['number']}",
                              "finalised": False, "verifierComment": "", "designerResponse": "",
                              "notes": "Adopted from the standalone tool", "revisions": [],
                              "status": "", "worstUtil": 0.0, "criticalCheck": ""}
                    self.data["calculations"].append(record)
                record["revisions"].append({
                    "rev": len(record["revisions"]) + 1, "filename": path.name,
                    "relativePath": relative,
                    "savedAt": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="minutes"),
                    "initials": clean_initials(match["initials"]), "superseded": superseded,
                    "worstUtil": 0.0, "criticalCheck": "", "status": ""})
                adopted += 1
        if adopted:
            for record in self.data["calculations"]:
                record["revisions"].sort(key=lambda item: item["savedAt"])
            self.write()
        return adopted

    @staticmethod
    def _package_from(path: Path, root: Path) -> str:
        try:
            parts = path.relative_to(root).parts
        except ValueError:
            return "Unallocated"
        candidates = [part for part in parts[:-1]
                      if part.casefold() not in {SUPERSEDED, LEGACY_SUPERSEDED}]
        return candidates[-1] if candidates else "Unallocated"
