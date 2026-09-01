"""QA verification packages, the Innovis verification form and the comment register.

A verification package is filed inside the project at::

    06-QA/03-Verification/YYMMDD - TITLE - REVIEWER/
        Calculations.pdf          the collated calculation package
        Verification Form.html    the Innovis verification form (+ .pdf)
        Comment Register.html     the tracked verifier / designer exchange
        Comment Register.csv      the same register for spreadsheets
        package.json              the machine-readable record

Comments are normally raised as PDF markups in Bluebeam Revu; they are imported
from the annotations of the returned PDF and then tracked here until each one is
closed, or the verifier agrees to defer it to a later design phase.  Deferred
comments are carried into the next package for the same project.
"""

from __future__ import annotations

import csv
import html
import io
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import calcpad

from . import pdf as pdf_tools
from .library import Library, safe_name

QA_ROOT = Path("06-QA") / "03-Verification"

STATUSES = ["Open", "Noted", "Deferred", "Closed"]
ACTIONS = [
    {"id": "resubmit", "label": "Revise & Resubmit for additional review"},
    {"id": "reviseIssue", "label": "Revise and Issue"},
    {"id": "issueAsReviewed", "label": "Issue as reviewed"},
    {"id": "notApproved", "label": "Not Approved for issue"},
]
METHODS = [
    {"id": "comparison", "label": "Comparison with Proven Design", "default": True},
    {"id": "readability", "label": "Readability / Completeness / Accuracy", "default": True},
    {"id": "checking", "label": "Checking Calculations", "default": True},
    {"id": "proof", "label": "Independent Proof Calculations", "default": False},
    {"id": "spot", "label": "Independent Spot Calculations", "default": True},
]
STATEMENT_ITEMS = [
    {"id": "brief", "label": "Project Design Brief / Preamble prepared and provided to verifier"},
    {"id": "inputs", "label": "Project Inputs are adequate and consistent"},
    {"id": "statutory", "label": "The output complies with local and statutory requirements"},
    {"id": "traceable", "label": "The output complies with and is traceable to the inputs"},
    {"id": "methods", "label": "The design methods, references, systems and equipment used are appropriate / current"},
    {"id": "client", "label": "The output complies with client specified requirements"},
    {"id": "standard", "label": "The output is of a satisfactory standard and appropriate to the project requirements"},
    {"id": "safetyInDesign", "label": "Has Safety in Design process been documented"},
    {"id": "interfaces", "label": "The interfaces with other disciplines have been considered and directly communicated and coordinated"},
    {"id": "economical", "label": "The output is economical"},
    {"id": "codes", "label": "The output complies with the relevant standards and codes"},
    {"id": "consistent", "label": "The output is consistent with other design and construction activities on the project"},
]


def form_template() -> dict[str, Any]:
    """Everything the browser needs to render the verification form."""
    return {"methods": METHODS, "statementItems": STATEMENT_ITEMS,
            "actions": ACTIONS, "statuses": STATUSES}


def initials_of(value: Any) -> str:
    """'Alex Reviewer' -> 'AR'; 'ABC' -> 'ABC'."""
    words = re.findall(r"[A-Za-z]+", str(value or ""))
    if len(words) >= 2:
        return "".join(word[0] for word in words[:4]).upper()
    return (words[0][:4].upper() if words else "XX")


def folder_name(title: str, reviewer_initials: str, when: datetime | None = None) -> str:
    """'YYMMDD - TITLE - REVIEWER'."""
    stamp = (when or datetime.now()).strftime("%y%m%d")
    initials = re.sub(r"[^A-Za-z]", "", str(reviewer_initials)).upper()[:4] or "XX"
    return f"{stamp} - {safe_name(title).upper()} - {initials}"


def reference(project_code: str, sequence: int, discipline: str = "STR") -> str:
    code = re.sub(r"[^A-Za-z0-9]", "", str(project_code or "PXXXX")).upper() or "PXXXX"
    return f"{code}-{discipline}-VER-{sequence:04d}"


# ---------------------------------------------------------------------------
#  Bluebeam / PDF markup import
# ---------------------------------------------------------------------------
def extract_comments(pdf_path: str | Path) -> list[dict[str, Any]]:
    """Read PDF markup annotations, as produced by Bluebeam Revu or Acrobat."""
    try:
        import pypdf
    except ImportError:
        return []
    path = Path(pdf_path)
    if not path.is_file():
        return []
    found: list[dict[str, Any]] = []
    reader = pypdf.PdfReader(str(path))
    for number, page in enumerate(reader.pages, start=1):
        for annotation in page.get("/Annots") or []:
            try:
                data = annotation.get_object()
            except (AttributeError, TypeError):
                continue
            subtype = str(data.get("/Subtype", ""))
            if subtype in {"/Link", "/Widget", "/Popup"}:
                continue
            text = str(data.get("/Contents", "") or "").strip()
            subject = str(data.get("/Subj", "") or "").strip()
            if not text and not subject:
                continue
            found.append({
                "source": path.name, "page": number,
                "author": str(data.get("/T", "") or "").strip(),
                "kind": subtype.lstrip("/"), "subject": subject,
                "comment": text or subject,
                "raisedAt": _annotation_date(str(data.get("/M", "") or "")),
            })
    return found


def _annotation_date(raw: str) -> str:
    match = re.search(r"D:(\d{4})(\d{2})(\d{2})(\d{2})?(\d{2})?", raw)
    if not match:
        return datetime.now().isoformat(timespec="minutes")
    year, month, day, hour, minute = match.groups()
    return f"{year}-{month}-{day}T{hour or '00'}:{minute or '00'}"


# ---------------------------------------------------------------------------
#  Package lifecycle
# ---------------------------------------------------------------------------
class QAStore:
    """Verification packages for one project."""

    def __init__(self, library: Library, project: dict[str, Any]):
        self.library = library
        self.project = project
        self.root = library.project_folder / QA_ROOT

    @property
    def packages(self) -> list[dict[str, Any]]:
        return self.library.data.setdefault("qaPackages", [])

    def get(self, package_id: Any) -> dict[str, Any]:
        package = next((item for item in self.packages if item["id"] == str(package_id)), None)
        if not package:
            raise ValueError("That verification package is not in this project")
        return package

    def can_access(self, package: dict[str, Any], actor: dict[str, Any]) -> bool:
        """Designers on the project and the nominated verifier may open a package."""
        email = str(actor.get("email", "")).casefold()
        allowed = {str(item).casefold() for item in
                   list(self.project.get("designers", [])) + list(self.project.get("verifiers", []))}
        allowed.add(str(package.get("reviewerEmail", "")).casefold())
        allowed.add(str(package.get("createdBy", "")).casefold())
        allowed.discard("")
        return email in allowed

    def deferred_carry_forward(self) -> list[dict[str, Any]]:
        """Comments a verifier agreed to defer, brought into the next package."""
        carried = []
        for package in self.packages:
            for comment in package.get("comments", []):
                if comment.get("status") == "Deferred" and not comment.get("carriedInto"):
                    carried.append({**comment, "carriedFrom": package["ref"]})
        return carried

    def create(self, *, title: str, reviewer: str, reviewer_email: str,
               actor: dict[str, Any], registry: Any, selection: list[str],
               meta: dict[str, Any], sort_fields: list[str] | None = None,
               drawings: list[dict[str, Any]] | None = None,
               documents: list[dict[str, Any]] | None = None,
               methods: dict[str, bool] | None = None,
               statement: dict[str, str] | None = None,
               producer_comments: str = "",
               reviewer_initials: str = "",
               drawing_set: dict[str, Any] | None = None) -> dict[str, Any]:
        from . import collate  # imported here to keep the module import graph flat

        if not str(title).strip():
            raise ValueError("Give the verification package a title")
        if not str(reviewer).strip():
            raise ValueError("Nominate the reviewer")
        initials = initials_of(reviewer_initials or reviewer)
        folder = self.root / folder_name(title, initials)
        folder.mkdir(parents=True, exist_ok=True)
        sequence = len(self.packages) + 1
        package = {
            "id": uuid.uuid4().hex[:12],
            "ref": reference(self.project.get("code", ""), sequence),
            "rev": "01", "title": str(title).strip(),
            "reviewer": str(reviewer).strip(),
            "reviewerInitials": initials,
            "reviewerEmail": str(reviewer_email or "").strip().lower(),
            "designer": actor.get("displayName", actor.get("email", "")),
            "designerInitials": actor.get("initials", ""),
            "createdBy": actor.get("email", ""),
            "createdAt": datetime.now().isoformat(timespec="seconds"),
            "date": datetime.now().strftime("%d/%m/%Y"),
            "folder": str(folder), "status": "Issued for verification",
            "calculations": list(selection or []),
            "documents": list(documents or []),
            "methods": {item["id"]: bool((methods or {}).get(item["id"], item["default"]))
                        for item in METHODS},
            "methodOther": str((methods or {}).get("other", "")),
            "statement": {item["id"]: str((statement or {}).get(item["id"], "")) or "  "
                          for item in STATEMENT_ITEMS},
            "producerComments": str(producer_comments or ""),
            "generalComments": "",
            "drawingSet": dict(drawing_set or {}),
            "action": "", "endorsed": None,
            "comments": self.deferred_carry_forward(),
        }
        built = collate.build_pdf(self.library, registry, selection, meta,
                                  folder / "Calculations.pdf", sort_fields=sort_fields,
                                  drawings=drawings)
        package["calculationPdf"] = built["pdfPath"]
        package["calculationSheets"] = built["sheets"]
        package["entries"] = [{key: entry.get(key) for key in
                               ("id", "title", "package", "level", "calcType", "memberType",
                                "memberNumber", "revision", "status", "worstUtil",
                                "criticalCheck", "startSheet")}
                              for entry in built["entries"]]
        if not package["documents"]:
            package["documents"] = [{"name": "Calculations.pdf", "revision": package["rev"],
                                     "date": package["date"]}]
            if drawing_set and drawing_set.get("path"):
                package["documents"].append({
                    "name": Path(str(drawing_set["path"])).name,
                    "revision": str(drawing_set.get("revision", "")),
                    "date": str(drawing_set.get("date", package["date"]))})
        self.packages.append(package)
        self._write_documents(package)
        self.library.write()
        return package

    # -- register -----------------------------------------------------------
    def import_markups(self, package_id: str, pdf_path: str, actor: dict[str, Any]) -> dict[str, Any]:
        package = self.get(package_id)
        existing = {(item.get("source"), item.get("page"), item.get("comment"))
                    for item in package["comments"]}
        added = 0
        for found in extract_comments(pdf_path):
            if (found["source"], found["page"], found["comment"]) in existing:
                continue
            package["comments"].append({
                "id": uuid.uuid4().hex[:8], "ref": f"C{len(package['comments']) + 1:03d}",
                **found, "response": "", "agreedOutcome": "", "status": "Open",
                "deferredTo": "", "history": [{"at": datetime.now().isoformat(timespec="minutes"),
                                               "by": actor.get("initials", ""),
                                               "note": "Raised from PDF markup"}]})
            added += 1
        self._write_documents(package)
        self.library.write()
        return {"added": added, "package": package}

    def add_comment(self, package_id: str, comment: dict[str, Any],
                    actor: dict[str, Any]) -> dict[str, Any]:
        package = self.get(package_id)
        package["comments"].append({
            "id": uuid.uuid4().hex[:8], "ref": f"C{len(package['comments']) + 1:03d}",
            "source": str(comment.get("source", "manual")), "page": comment.get("page", ""),
            "author": actor.get("initials", ""), "kind": "Manual",
            "subject": str(comment.get("subject", "")),
            "comment": str(comment.get("comment", "")).strip(),
            "raisedAt": datetime.now().isoformat(timespec="minutes"),
            "response": "", "agreedOutcome": "", "status": "Open", "deferredTo": "",
            "history": [{"at": datetime.now().isoformat(timespec="minutes"),
                         "by": actor.get("initials", ""), "note": "Raised"}]})
        self._write_documents(package)
        self.library.write()
        return package

    def update_comment(self, package_id: str, comment_id: str, fields: dict[str, Any],
                       actor: dict[str, Any]) -> dict[str, Any]:
        package = self.get(package_id)
        comment = next((item for item in package["comments"] if item["id"] == comment_id), None)
        if not comment:
            raise ValueError("That comment is not in this register")
        changes = []
        for key in ("comment", "response", "agreedOutcome", "deferredTo", "subject"):
            if key in fields and str(fields[key]) != comment.get(key, ""):
                comment[key] = str(fields[key])
                changes.append(key)
        if "status" in fields:
            status = str(fields["status"])
            if status not in STATUSES:
                raise ValueError(f"Status must be one of: {', '.join(STATUSES)}")
            if status != comment.get("status"):
                comment["status"] = status
                changes.append(f"status -> {status}")
        if changes:
            comment.setdefault("history", []).append({
                "at": datetime.now().isoformat(timespec="minutes"),
                "by": actor.get("initials", ""), "note": ", ".join(changes)})
        self._write_documents(package)
        self.library.write()
        return package

    def update_package(self, package_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        package = self.get(package_id)
        for key in ("generalComments", "producerComments", "action", "rev", "status"):
            if key in fields:
                package[key] = str(fields[key])
        if "methods" in fields and isinstance(fields["methods"], dict):
            package["methods"].update({key: bool(value) for key, value
                                       in fields["methods"].items() if key in package["methods"]})
            package["methodOther"] = str(fields["methods"].get("other", package.get("methodOther", "")))
        if "statement" in fields and isinstance(fields["statement"], dict):
            package["statement"].update({key: str(value) for key, value
                                         in fields["statement"].items()
                                         if key in package["statement"]})
        if "documents" in fields and isinstance(fields["documents"], list):
            package["documents"] = fields["documents"]
        self._write_documents(package)
        self.library.write()
        return package

    def endorse(self, package_id: str, action: str, actor: dict[str, Any],
                note: str = "") -> dict[str, Any]:
        package = self.get(package_id)
        if action not in {item["id"] for item in ACTIONS}:
            raise ValueError("Choose one of the verification actions")
        outstanding = [item["ref"] for item in package["comments"]
                       if item.get("status") not in {"Closed", "Deferred"}]
        if outstanding and action in {"issueAsReviewed", "reviseIssue"}:
            raise ValueError("Close or defer every comment before endorsing: "
                             + ", ".join(outstanding))
        register = self._write_register(package, final=True)
        package["action"] = action
        package["status"] = next(item["label"] for item in ACTIONS if item["id"] == action)
        package["endorsed"] = {
            "by": actor.get("displayName", actor.get("email", "")),
            "initials": actor.get("initials", ""),
            "at": datetime.now().isoformat(timespec="minutes"),
            "action": action, "note": str(note or ""),
            "registerFile": str(register)}
        for comment in package["comments"]:
            if comment.get("status") == "Deferred":
                comment["carriedInto"] = ""
        self._write_documents(package)
        self.library.write()
        return package

    def status_summary(self) -> dict[str, Any]:
        """Verification status for this project, for the business-wide QA review."""
        packages = self.packages
        return {
            "project": self.project.get("code", ""),
            "projectName": self.project.get("projectName", ""),
            "folderPath": self.project.get("folderPath", ""),
            "packages": len(packages),
            "endorsed": sum(1 for item in packages if item.get("endorsed")),
            "openComments": sum(1 for item in packages for comment in item.get("comments", [])
                                if comment.get("status") == "Open"),
            "deferredComments": sum(1 for item in packages for comment in item.get("comments", [])
                                    if comment.get("status") == "Deferred"),
            "latest": (packages[-1]["ref"] if packages else ""),
            "latestStatus": (packages[-1].get("status", "") if packages else "Not started"),
        }

    # -- documents ----------------------------------------------------------
    def _write_documents(self, package: dict[str, Any]) -> None:
        folder = Path(package["folder"])
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "package.json").write_text(
            json.dumps(package, indent=2, ensure_ascii=True, default=str), encoding="utf-8")
        form_path = folder / "Verification Form.html"
        form_path.write_text(render_form(self.project, package), encoding="utf-8")
        self._write_register(package)

    def _write_register(self, package: dict[str, Any], final: bool = False) -> Path:
        folder = Path(package["folder"])
        name = "Comment Register - FINAL" if final else "Comment Register"
        (folder / f"{name}.html").write_text(render_register(self.project, package),
                                             encoding="utf-8")
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer)
        writer.writerow(["Ref", "Source", "Page", "Raised by", "Comment", "Response",
                         "Agreed outcome", "Status", "Deferred to", "Raised at"])
        for comment in package.get("comments", []):
            writer.writerow([comment.get("ref", ""), comment.get("source", ""),
                             comment.get("page", ""), comment.get("author", ""),
                             comment.get("comment", ""), comment.get("response", ""),
                             comment.get("agreedOutcome", ""), comment.get("status", ""),
                             comment.get("deferredTo", ""), comment.get("raisedAt", "")])
        csv_path = folder / f"{name}.csv"
        csv_path.write_text(buffer.getvalue(), encoding="utf-8")
        return folder / f"{name}.html"

    def export_pdf(self, package_id: str) -> dict[str, str]:
        """Print the verification form and register to PDF."""
        package = self.get(package_id)
        folder = Path(package["folder"])
        written = {}
        for name in ("Verification Form", "Comment Register"):
            source = folder / f"{name}.html"
            if source.is_file():
                written[name] = str(pdf_tools.export_pdf(source, folder / f"{name}.pdf"))
        return written


# ---------------------------------------------------------------------------
#  Rendering - the Innovis verification form and register on the calc pad
# ---------------------------------------------------------------------------
def _tick(value: Any) -> str:
    """A mark that survives PDF export; ballot glyphs are not reliably available."""
    return '<b style="font-size:11pt">&#10005;</b>' if value else "&nbsp;"


def _identity_inputs(project: dict[str, Any], package: dict[str, Any],
                     subject: str) -> dict[str, Any]:
    return {"client": project.get("clientRef", ""),
            "project": project.get("projectName", ""),
            "projectno": project.get("code", ""),
            "designer": package.get("designerInitials", ""),
            "checker": package.get("reviewerInitials") or initials_of(package.get("reviewer", "")),
            "date": package.get("date", ""), "memberType": "", "memberNumber": "",
            "subject": subject}


def render_form(project: dict[str, Any], package: dict[str, Any],
                standalone: bool = True) -> str:
    """The Innovis verification form, populated from the package record."""
    header = (
        '<table class="vform">'
        f'<tr><td class="label">PROJECT</td><td>{html.escape(project.get("projectName", ""))}</td>'
        f'<td class="label">REF</td><td>{html.escape(package.get("ref", ""))}</td></tr>'
        f'<tr><td class="label">DESIGNER</td><td>{html.escape(package.get("designer", ""))}</td>'
        f'<td class="label">REV</td><td>{html.escape(package.get("rev", ""))}</td></tr>'
        f'<tr><td class="label">VERIFIER</td><td>{html.escape(package.get("reviewer", ""))}</td>'
        f'<td class="label">DATE</td><td>{html.escape(package.get("date", ""))}</td></tr>'
        f'<tr><td class="label">PACKAGE</td><td>{html.escape(package.get("title", ""))}</td>'
        f'<td class="label">PAGES</td><td>{html.escape(str(package.get("calculationSheets", "")))}</td>'
        "</tr></table>")

    documents = "".join(
        f'<tr><td>{html.escape(str(item.get("name", "")))}</td>'
        f'<td>{html.escape(str(item.get("revision", "")))}</td>'
        f'<td>{html.escape(str(item.get("date", "")))}</td></tr>'
        for item in package.get("documents", []))
    document_table = ('<table class="vform"><tr><th>Name of Document</th>'
                      '<th>Revision Number</th><th>Date</th></tr>'
                      f'{documents or "<tr><td>-</td><td></td><td></td></tr>"}</table>')

    method_rows = []
    chosen = package.get("methods", {})
    for left, right in zip(METHODS[0::2], METHODS[1::2] + [None] * len(METHODS)):
        cells = (f'<td class="tick">{_tick(chosen.get(left["id"]))}</td>'
                 f'<td>{html.escape(left["label"])}</td>')
        if right:
            cells += (f'<td class="tick">{_tick(chosen.get(right["id"]))}</td>'
                      f'<td>{html.escape(right["label"])}</td>')
        else:
            cells += "<td></td><td></td>"
        method_rows.append(f"<tr>{cells}</tr>")
    methods = ('<table class="vform">' + "".join(method_rows)
               + f'<tr><td class="label" colspan="2">Other</td><td colspan="2">'
                 f'{html.escape(package.get("methodOther", ""))}</td></tr></table>')

    statement = package.get("statement", {})
    statement_rows = []
    for left, right in zip(STATEMENT_ITEMS[0::2], STATEMENT_ITEMS[1::2]):
        statement_rows.append(
            f'<tr><td>{html.escape(left["label"])}</td>'
            f'<td class="tick">{html.escape(statement.get(left["id"], "  ").strip())}</td>'
            f'<td>{html.escape(right["label"])}</td>'
            f'<td class="tick">{html.escape(statement.get(right["id"], "  ").strip())}</td></tr>')
    statement_table = ('<table class="vform"><tr><th>Item</th><th>Y, N, N/A</th>'
                       '<th>Item</th><th>Y, N, N/A</th></tr>'
                       + "".join(statement_rows)
                       + '<tr><td class="label">Additional Comments by Producer of Output</td>'
                         f'<td colspan="3">{html.escape(package.get("producerComments", ""))}</td>'
                         "</tr></table>")

    action_rows = []
    for left, right in zip(ACTIONS[0::2], ACTIONS[1::2]):
        action_rows.append(
            f'<tr><td>{html.escape(left["label"])}</td>'
            f'<td class="tick">{_tick(package.get("action") == left["id"])}</td>'
            f'<td>{html.escape(right["label"])}</td>'
            f'<td class="tick">{_tick(package.get("action") == right["id"])}</td></tr>')
    endorsed = package.get("endorsed") or {}
    endorsement = (
        '<table class="vform"><tr><th>Endorsement</th><th>Name</th><th>Signature</th>'
        "<th>Date</th></tr>"
        f'<tr><td class="label">Producer of Output</td><td>{html.escape(package.get("designer", ""))}</td>'
        f'<td>{html.escape(package.get("designerInitials", ""))}</td>'
        f'<td>{html.escape(package.get("date", ""))}</td></tr>'
        f'<tr><td class="label">Verifier</td><td>{html.escape(package.get("reviewer", ""))}</td>'
        f'<td>{html.escape(endorsed.get("initials", ""))}</td>'
        f'<td>{html.escape(str(endorsed.get("at", "")).replace("T", " "))}</td></tr>'
        '<tr><td class="label">Project Lead</td><td></td><td></td><td></td></tr></table>')

    register_link = endorsed.get("registerFile", "")
    endorsement_note = ""
    if endorsed:
        label = next((item["label"] for item in ACTIONS if item["id"] == endorsed.get("action")),
                     endorsed.get("action", ""))
        endorsement_note = (
            f'<p><b>Endorsed for release:</b> {html.escape(label)} by '
            f'{html.escape(endorsed.get("by", ""))} on '
            f'{html.escape(str(endorsed.get("at", "")).replace("T", " "))}. '
            f'Final comment register: <a href="{html.escape(Path(register_link).name)}">'
            f'{html.escape(Path(register_link).name)}</a>.</p>')

    blocks = [
        calcpad.prose("Verification", header, weight=10),
        calcpad.prose("Documents to be Verified", document_table,
                      weight=6 + 2 * len(package.get("documents", []))),
        calcpad.prose("Verification Method", methods, weight=10),
        calcpad.prose("Designers Statement",
                      "<p>As the designer, I have considered the following and consider that "
                      "these items have been adequately addressed within my design:</p>"
                      + statement_table, weight=24),
        calcpad.prose("Verification Comments",
                      f'<p>{html.escape(package.get("generalComments", "")) or "-"}</p>'
                      f'<p>The tracked comment register accompanies this form '
                      f'({len(package.get("comments", []))} comment(s)).</p>', weight=8),
        calcpad.prose("Action", '<table class="vform">' + "".join(action_rows) + "</table>"
                      + endorsement_note, weight=10),
        calcpad.prose("Endorsement", endorsement, weight=10),
    ]
    inputs = _identity_inputs(project, package, f"Verification - {package.get('title', '')}")
    return calcpad.render(inputs, blocks, default_subject="Verification",
                          standalone=standalone,
                          title=f"{package.get('ref', '')} Verification Form",
                          data_id="icm-verification")


def render_register(project: dict[str, Any], package: dict[str, Any],
                    standalone: bool = True) -> str:
    """The tracked verifier / designer comment register."""
    rows = []
    for comment in package.get("comments", []):
        status = str(comment.get("status", "Open"))
        carried = (f'<br><i>carried from {html.escape(str(comment.get("carriedFrom")))}</i>'
                   if comment.get("carriedFrom") else "")
        deferred = (f'<br><i>deferred to {html.escape(str(comment.get("deferredTo")))}</i>'
                    if comment.get("deferredTo") else "")
        rows.append(
            f'<tr><td>{html.escape(comment.get("ref", ""))}</td>'
            f'<td>{html.escape(str(comment.get("source", "")))} '
            f'p{html.escape(str(comment.get("page", "")))}</td>'
            f'<td>{html.escape(comment.get("author", ""))}</td>'
            f'<td>{html.escape(comment.get("comment", ""))}{carried}</td>'
            f'<td>{html.escape(comment.get("response", ""))}</td>'
            f'<td>{html.escape(comment.get("agreedOutcome", ""))}{deferred}</td>'
            f'<td class="status-{status.lower()}">{html.escape(status)}</td></tr>')
    table = ('<table class="vform register"><tr><th>Ref</th><th>Source</th><th>Raised by</th>'
             '<th>Verifier comment</th><th>Response</th><th>Agreed outcome</th>'
             f'<th>Status</th></tr>{"".join(rows) or "<tr><td colspan=7>No comments raised</td></tr>"}'
             "</table>")
    counts = {status: sum(1 for item in package.get("comments", [])
                          if item.get("status") == status) for status in STATUSES}
    summary = ("<p>" + ", ".join(f"{status}: {count}" for status, count in counts.items())
               + f'. Package {html.escape(package.get("ref", ""))} rev '
                 f'{html.escape(package.get("rev", ""))}.</p>')
    blocks = [calcpad.prose("Verification Comment Register", summary + table,
                            weight=8 + 2 * len(package.get("comments", []) or [1]))]
    inputs = _identity_inputs(project, package, f"Comment register - {package.get('title', '')}")
    return calcpad.render(inputs, blocks, default_subject="Comment register",
                          standalone=standalone,
                          title=f"{package.get('ref', '')} Comment Register",
                          data_id="icm-register")
