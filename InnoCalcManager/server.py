#!/usr/bin/env python3
"""
InnoCalc Manager - calculation management for Innovis projects.

A browser cannot read or write the network projects drive, so this small local
service does it and serves the web application from the same origin.  It binds
to localhost only and uses the Python standard library plus the optional
``pypdf`` package.

The front end knows nothing about any individual calculation: it renders the
input form from the schema each module publishes and displays the HTML each
module returns.  Adding a design module therefore needs no front-end change.

Run:    python server.py            (opens http://127.0.0.1:8125/)
Config: ICM_ROOT   projects root, default J:\\Active Projects
        ICM_PORT   listening port, default 8125
"""

from __future__ import annotations

import json
import math
import mimetypes
import os
import queue
import string
import subprocess
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

from icm import VERSION, VERSION_HISTORY
from icm import auth as auth_module
from icm import collate, mail, pdf as pdf_tools, qa as qa_module
from icm.library import Library
from icm.projects import Discovery, ProjectRegistry, normalise_code, project_root
from icm.registry import CATEGORIES, Registry

HOST = "127.0.0.1"
PORT = int(os.environ.get("ICM_PORT", "8125"))
ROOT = os.environ.get("ICM_ROOT", r"J:\Active Projects")
APP_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("ICM_DATA_DIR", str(APP_DIR / "data")))

DATA_DIR.mkdir(parents=True, exist_ok=True)
DIRECTORY = auth_module.Directory(DATA_DIR / "people.json")
SESSIONS = auth_module.Sessions()
PROJECTS = ProjectRegistry(DATA_DIR / "projects.json")
DISCOVERY = Discovery(DATA_DIR / "project-index.json", ROOT)
MODULES = Registry()

STATIC_TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8",
                ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon",
                ".woff2": "font/woff2"}


def finite(value: Any) -> Any:
    """Replace infinities and NaN with null so the response parses in a browser.

    A utilisation of infinity is a real result - a member with no capacity, or
    no demand - but JSON has no literal for it and ``JSON.parse`` rejects the
    ones Python writes, which surfaced as an unreadable reply rather than a
    calculation.  The printed sheet is rendered server side and is unaffected.
    """
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {key: finite(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [finite(item) for item in value]
    return value


# --------------------------------------------------------------------------
#  Background PDF printing
# --------------------------------------------------------------------------
class PdfWorker:
    """Prints saved calculations to PDF away from the request thread.

    Printing runs headless Chromium, which costs a few seconds of process start
    every time and is serialised by a lock inside ``calcpad``.  Saving therefore
    returns as soon as the calculation and its index entry are on the drive, and
    the sheet is printed behind it; the interface shows the state of both.
    """

    def __init__(self) -> None:
        self.queue: queue.Queue[tuple[str, str, str]] = queue.Queue()
        self.state: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, name="icm-pdf", daemon=True)
        self._thread.start()

    def submit(self, key: str, html_path: str, pdf_path: str) -> None:
        with self._lock:
            self.state[key] = {"status": "printing", "pdfPath": pdf_path, "error": ""}
        self.queue.put((key, html_path, pdf_path))

    def status(self, key: str) -> dict[str, Any]:
        with self._lock:
            return dict(self.state.get(key) or {"status": "unknown", "error": ""})

    def pending(self) -> int:
        with self._lock:
            return sum(1 for item in self.state.values() if item["status"] == "printing")

    def _run(self) -> None:
        while True:
            key, html_path, pdf_path = self.queue.get()
            try:
                pdf_tools.export_pdf(html_path, pdf_path)
                outcome = {"status": "ready", "pdfPath": pdf_path, "error": ""}
            except (RuntimeError, OSError) as exc:
                outcome = {"status": "failed", "pdfPath": pdf_path, "error": str(exc)}
            with self._lock:
                self.state[key] = outcome
            self.queue.task_done()


PDF_WORKER = PdfWorker()


# --------------------------------------------------------------------------
#  Helpers
# --------------------------------------------------------------------------
def list_drives() -> list[str]:
    if os.name != "nt":
        return ["/"]
    return [f"{letter}:\\" for letter in string.ascii_uppercase if os.path.exists(f"{letter}:\\")]


def browse(path: str) -> dict[str, Any]:
    if not path:
        return {"ok": True, "path": "", "parent": None,
                "dirs": [{"name": item, "path": item} for item in list_drives()]}
    path = os.path.abspath(path)
    parent = os.path.dirname(path.rstrip("\\/")) or None
    if parent == path:
        parent = None
    dirs = []
    try:
        with os.scandir(path) as entries:
            for entry in sorted(entries, key=lambda item: item.name.casefold()):
                if entry.is_dir():
                    dirs.append({"name": entry.name, "path": entry.path})
    except OSError as exc:
        return {"ok": False, "path": path, "parent": parent, "dirs": [], "error": str(exc)}
    return {"ok": True, "path": path, "parent": parent, "dirs": dirs}


def list_files(path: str, suffix: str = "") -> dict[str, Any]:
    if not path or not os.path.isdir(path):
        return {"ok": False, "error": "folder not found", "files": []}
    files = []
    try:
        with os.scandir(path) as entries:
            for entry in sorted(entries, key=lambda item: item.name.casefold()):
                if entry.is_file() and (not suffix or entry.name.lower().endswith(suffix.lower())):
                    stat = entry.stat()
                    files.append({"name": entry.name, "path": entry.path, "size": stat.st_size,
                                  "modified": int(stat.st_mtime * 1000)})
    except OSError as exc:
        return {"ok": False, "error": str(exc), "files": []}
    return {"ok": True, "path": path, "files": files}


def native_pick(title: str = "Select project folder", file_mode: bool = False) -> dict[str, Any]:
    """Native OS picker on its own thread. Best effort; the browser has a fallback."""
    result: dict[str, str] = {}

    def run() -> None:
        try:
            import tkinter
            from tkinter import filedialog

            window = tkinter.Tk()
            window.withdraw()
            window.attributes("-topmost", True)
            start = ROOT if os.path.isdir(ROOT) else os.path.expanduser("~")
            if file_mode:
                result["path"] = filedialog.askopenfilename(
                    initialdir=start, title=title,
                    filetypes=[("PDF documents", "*.pdf"), ("All files", "*.*")])
            else:
                result["path"] = filedialog.askdirectory(initialdir=start, title=title)
            window.destroy()
        except Exception as exc:  # noqa: BLE001 - headless, cancelled or no tkinter
            result["error"] = str(exc)

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(180)
    return {"ok": bool(result.get("path")), "path": result.get("path", ""),
            "error": result.get("error", "")}


def library_for(project: dict[str, Any]) -> Library:
    return Library(project["folderPath"])


def project_meta(project: dict[str, Any], actor: dict[str, Any],
                 overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Identity block shared by every calculation in a project.

    ``checker`` is deliberately absent from the overrides a caller may supply:
    it is written by :meth:`icm.qa.QAStore.endorse` when the verifier closes the
    verification out, and never typed by the designer.
    """
    meta = {"client": project.get("clientRef", ""), "project": project.get("projectName", ""),
            "projectno": project.get("code", ""), "designer": actor.get("initials", ""),
            "checker": "", "projectFolder": project.get("folderPath", "")}
    meta.update({key: value for key, value in (overrides or {}).items()
                 if key in {"client", "project", "projectno", "designer", "title"}})
    return meta


def reveal(path: str) -> dict[str, Any]:
    """Show a file or folder in Windows Explorer."""
    if not path or not within_project(path):
        raise ValueError("That location is not inside one of your projects")
    target = Path(path)
    if not target.exists():
        raise ValueError(f"Not found: {path}")
    if os.name != "nt":
        return {"ok": False, "error": "Explorer is only available on Windows"}
    if target.is_dir():
        subprocess.Popen(["explorer", str(target)])  # noqa: S603,S607 - fixed command
    else:
        subprocess.Popen(["explorer", "/select,", str(target)])  # noqa: S603,S607
    return {"ok": True, "path": str(target)}


def within_project(path: str) -> bool:
    """A generated file may only be served from a registered project or the app data."""
    try:
        target = Path(path).resolve()
    except OSError:
        return False
    roots = [DATA_DIR.resolve()] + [Path(project["folderPath"]).resolve()
                                    for project in PROJECTS.data["projects"].values()]
    for root in roots:
        try:
            target.relative_to(root)
            return True
        except ValueError:
            continue
    return False


# --------------------------------------------------------------------------
#  HTTP handler
# --------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = f"InnoCalcManager/{VERSION}"
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):  # keep the console readable
        pass

    # -- plumbing -----------------------------------------------------------
    def _send(self, code: int, body: Any, ctype: str = "application/json; charset=utf-8") -> None:
        if isinstance(body, (dict, list)):
            body = json.dumps(finite(body), default=str, allow_nan=False)
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                pass

    def _actor(self, token: Any) -> dict[str, Any]:
        return SESSIONS.actor(token)

    def _project(self, token: Any, project_id: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        actor = self._actor(token)
        return actor, PROJECTS.get(project_id)

    def _origin(self) -> str:
        return f"http://{HOST}:{PORT}"

    # -- GET ----------------------------------------------------------------
    def do_GET(self):
        parsed = urlparse(self.path)
        route, query = parsed.path, parse_qs(parsed.query)
        token = query.get("token", [""])[0]
        try:
            handler = {
                "/api/ping": self._ping,
                "/api/auth/config": self._auth_config,
                "/api/modules": self._modules,
                "/api/module/schema": self._module_schema,
                "/api/projects": self._projects,
                "/api/projects/discovery": self._discovery_status,
                "/api/library": self._library,
                "/api/calculation": self._calculation,
                "/api/calculation/pdf": self._pdf_status,
                "/api/browse": lambda q: browse(q.get("path", [""])[0]),
                "/api/files": lambda q: list_files(q.get("path", [""])[0],
                                                   q.get("suffix", [""])[0]),
                "/api/pick": self._pick,
                "/api/reveal": self._reveal,
                "/api/file": None,
                "/api/qa": self._qa_list,
                "/api/qa/status": self._qa_status,
                "/api/versions": lambda q: {"ok": True, "version": VERSION,
                                            "history": VERSION_HISTORY},
                "/auth/sso/start": self._sso_start,
                "/auth/sso/callback": self._sso_callback,
            }.get(route, "static")
            if handler == "static":
                self._serve_static(route)
                return
            if route == "/api/file":
                self._serve_generated(token, query.get("path", [""])[0])
                return
            if handler is None:
                self._send(404, {"ok": False, "error": "unknown endpoint"})
                return
            self._send(200, handler(query))
        except PermissionError as exc:
            self._send(401, {"ok": False, "error": str(exc)})
        except (ValueError, OSError, RuntimeError) as exc:
            self._send(400, {"ok": False, "error": str(exc)})

    # -- POST ---------------------------------------------------------------
    ROUTES = {
        "/api/auth/signin", "/api/auth/signout",
        "/api/projects/create", "/api/projects/open", "/api/projects/find",
        "/api/projects/search", "/api/projects/relink",
        "/api/projects/refresh", "/api/projects/archive", "/api/projects/forget",
        "/api/projects/people", "/api/projects/adopt", "/api/projects/rename",
        "/api/calculate", "/api/module/action", "/api/module/validate",
        "/api/calculation/save", "/api/calculation/update", "/api/calculation/delete",
        "/api/calculation/exchange", "/api/calculation/import",
        "/api/package/preview", "/api/package/build",
        "/api/qa/create", "/api/qa/update", "/api/qa/comment/add", "/api/qa/comment/update",
        "/api/qa/markups", "/api/qa/endorse", "/api/qa/export", "/api/qa/scan",
    }

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path not in self.ROUTES:
            self._send(404, {"ok": False, "error": "unknown endpoint"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        except (ValueError, TypeError) as exc:
            self._send(400, {"ok": False, "error": f"bad request: {exc}"})
            return
        try:
            self._send(200, {
                "/api/auth/signin": self._sign_in,
                "/api/auth/signout": self._sign_out,
                "/api/projects/create": self._create_project,
                "/api/projects/open": self._open_project,
                "/api/projects/find": self._find_project,
                "/api/projects/search": self._search_projects,
                "/api/projects/relink": self._relink_project,
                "/api/projects/refresh": self._refresh_projects,
                "/api/projects/archive": self._archive_project,
                "/api/projects/forget": self._forget_project,
                "/api/projects/people": self._project_people,
                "/api/projects/rename": self._rename_project,
                "/api/projects/adopt": self._adopt_existing,
                "/api/calculate": self._calculate,
                "/api/module/action": self._module_action,
                "/api/module/validate": self._module_validate,
                "/api/calculation/save": self._save_calculation,
                "/api/calculation/update": self._update_calculation,
                "/api/calculation/delete": self._delete_calculation,
                "/api/calculation/exchange": self._exchange_calculation,
                "/api/calculation/import": self._import_calculation,
                "/api/package/preview": self._package_preview,
                "/api/package/build": self._package_build,
                "/api/qa/create": self._qa_create,
                "/api/qa/update": self._qa_update,
                "/api/qa/comment/add": self._qa_add_comment,
                "/api/qa/comment/update": self._qa_update_comment,
                "/api/qa/markups": self._qa_markups,
                "/api/qa/endorse": self._qa_endorse,
                "/api/qa/export": self._qa_export,
                "/api/qa/scan": self._qa_scan,
            }[parsed.path](payload))
        except PermissionError as exc:
            self._send(401, {"ok": False, "error": str(exc)})
        except (ValueError, OSError, RuntimeError, KeyError, TypeError) as exc:
            self._send(400, {"ok": False, "error": str(exc)})

    # ---------------------------------------------------------------- status
    def _ping(self, _query) -> dict[str, Any]:
        return {"ok": True, "version": VERSION, "root": ROOT,
                "rootExists": os.path.isdir(ROOT),
                "modules": len(MODULES.modules), "moduleProblems": MODULES.problems,
                "pdf": pdf_tools.available(), "sso": auth_module.sso_status()}

    def _auth_config(self, _query) -> dict[str, Any]:
        return {"ok": True, "sso": auth_module.sso_status(), "people": DIRECTORY.everyone(),
                "version": VERSION}

    def _modules(self, _query) -> dict[str, Any]:
        return {"ok": True, "modules": MODULES.catalogue(), "categories": CATEGORIES,
                "problems": MODULES.problems}

    def _module_schema(self, query) -> dict[str, Any]:
        module = MODULES.get(query.get("module", [""])[0])
        return {"ok": True, "schema": module.call("schema"), "defaults": module.call("defaults")}

    # -------------------------------------------------------------- identity
    def _sign_in(self, payload) -> dict[str, Any]:
        if auth_module.SSO_ENABLED:
            raise PermissionError("Sign in with your Office 365 account")
        user = DIRECTORY.upsert(payload.get("email"), str(payload.get("fullName", "")),
                                str(payload.get("initials", "")))
        return {"ok": True, "token": SESSIONS.issue(user), "user": user,
                "people": DIRECTORY.everyone()}

    def _sign_out(self, payload) -> dict[str, Any]:
        SESSIONS.revoke(payload.get("token"))
        return {"ok": True}

    def _sso_start(self, _query) -> dict[str, Any]:
        return {"ok": True, **auth_module.start_sso(self._origin())}

    def _sso_callback(self, query) -> dict[str, Any]:
        profile = auth_module.complete_sso(query.get("code", [""])[0],
                                           query.get("state", [""])[0], self._origin())
        user = DIRECTORY.upsert(profile["email"], profile.get("displayName", ""))
        return {"ok": True, "token": SESSIONS.issue(user), "user": user}

    # -------------------------------------------------------------- projects
    def _projects(self, query) -> dict[str, Any]:
        actor = self._actor(query.get("token", [""])[0])
        return {"ok": True, "projects": PROJECTS.for_user(actor),
                "discovery": DISCOVERY.status(), "people": DIRECTORY.everyone()}

    def _discovery_status(self, query) -> dict[str, Any]:
        self._actor(query.get("token", [""])[0])
        return {"ok": True, "discovery": DISCOVERY.status()}

    def _create_project(self, payload) -> dict[str, Any]:
        actor = self._actor(payload.get("token"))
        project = PROJECTS.register(str(payload.get("path", "")), actor)
        fields = {key: payload[key] for key in ("code", "clientRef", "projectName")
                  if payload.get(key)}
        if fields:
            PROJECTS.rename(project["id"], fields)
        PROJECTS.touch(project["id"], actor)
        DISCOVERY.remember(project["folderPath"])
        return {"ok": True, "project": PROJECTS.get(project["id"]),
                "projects": PROJECTS.for_user(actor)}

    def _open_project(self, payload) -> dict[str, Any]:
        actor = self._actor(payload.get("token"))
        project_id = str(payload.get("projectId", ""))
        if not project_id and payload.get("path"):
            project = PROJECTS.by_path(payload["path"]) or PROJECTS.register(
                str(payload["path"]), actor)
            project_id = project["id"]
        project = PROJECTS.get(project_id)
        if not os.path.isdir(project["folderPath"]):
            raise ValueError(f"The project folder is not reachable: {project['folderPath']}")
        PROJECTS.touch(project_id, actor)
        library = library_for(project)
        return {"ok": True, "project": PROJECTS.get(project_id),
                "library": library.index(),
                "meta": project_meta(project, actor),
                "qa": [self._qa_public(item) for item in library.data.get("qaPackages", [])],
                "projects": PROJECTS.for_user(actor)}

    def _find_project(self, payload) -> dict[str, Any]:
        self._actor(payload.get("token"))
        return {"ok": True, **DISCOVERY.find(normalise_code(payload.get("code")))}

    def _search_projects(self, payload) -> dict[str, Any]:
        """Resolve a project by number or by any part of its name."""
        self._actor(payload.get("token"))
        return {"ok": True, **DISCOVERY.search(payload.get("query"))}

    def _relink_project(self, payload) -> dict[str, Any]:
        actor = self._actor(payload.get("token"))
        project = PROJECTS.relink(str(payload.get("projectId", "")),
                                  str(payload.get("path", "")))
        DISCOVERY.remember(project["folderPath"])
        return {"ok": True, "project": project, "projects": PROJECTS.for_user(actor)}

    def _refresh_projects(self, payload) -> dict[str, Any]:
        self._actor(payload.get("token"))
        return {"ok": True, "discovery": DISCOVERY.refresh_async()}

    def _archive_project(self, payload) -> dict[str, Any]:
        actor = self._actor(payload.get("token"))
        PROJECTS.set_archived(str(payload.get("projectId", "")), actor,
                              bool(payload.get("archived")))
        return {"ok": True, "projects": PROJECTS.for_user(actor)}

    def _forget_project(self, payload) -> dict[str, Any]:
        actor = self._actor(payload.get("token"))
        PROJECTS.forget(str(payload.get("projectId", "")), actor)
        return {"ok": True, "projects": PROJECTS.for_user(actor)}

    def _rename_project(self, payload) -> dict[str, Any]:
        actor = self._actor(payload.get("token"))
        project = PROJECTS.rename(str(payload.get("projectId", "")), payload)
        return {"ok": True, "project": project, "projects": PROJECTS.for_user(actor)}

    def _project_people(self, payload) -> dict[str, Any]:
        actor = self._actor(payload.get("token"))
        project = PROJECTS.set_people(str(payload.get("projectId", "")),
                                      list(payload.get("designers", [])),
                                      list(payload.get("verifiers", [])))
        return {"ok": True, "project": project, "projects": PROJECTS.for_user(actor)}

    def _adopt_existing(self, payload) -> dict[str, Any]:
        actor, project = self._project(payload.get("token"), payload.get("projectId"))
        library = library_for(project)
        adopted = library.adopt_existing()
        return {"ok": True, "adopted": adopted, "library": library.index()}

    def _pick(self, query) -> dict[str, Any]:
        self._actor(query.get("token", [""])[0])
        picked = native_pick(query.get("title", ["Select project folder"])[0],
                             query.get("mode", [""])[0] == "file")
        if picked.get("path") and query.get("scope", [""])[0] == "project":
            picked["path"] = project_root(picked["path"])
        return picked

    def _reveal(self, query) -> dict[str, Any]:
        self._actor(query.get("token", [""])[0])
        return reveal(query.get("path", [""])[0])

    # ----------------------------------------------------------- calculation
    def _calculate(self, payload) -> dict[str, Any]:
        self._actor(payload.get("token"))
        module = MODULES.get(payload.get("module"))
        inputs = payload.get("inputs")
        if not isinstance(inputs, dict):
            raise ValueError("An inputs object is required")
        result = module.call("compute", inputs)
        # A module may offer an editable on-screen sheet; the printed one never is.
        render_options = {"interactive": True} if module.takes("render", "interactive") else {}
        return {"ok": True, "result": result,
                "summary": module.call("summarise", result),
                "identity": module.call("identity", inputs),
                "reportHtml": module.call("render", inputs, result, **render_options)}

    def _module_action(self, payload) -> dict[str, Any]:
        self._actor(payload.get("token"))
        module = MODULES.get(payload.get("module"))
        outcome = module.call("run_action", str(payload.get("action", "")),
                              payload.get("inputs") or {})
        return {"ok": True, **outcome}

    def _module_validate(self, payload) -> dict[str, Any]:
        self._actor(payload.get("token"))
        module = MODULES.get(payload.get("module"))
        return {"ok": True, "validation": module.call("validate", payload.get("cases"))}

    def _library(self, query) -> dict[str, Any]:
        actor, project = self._project(query.get("token", [""])[0],
                                       query.get("project", [""])[0])
        library = library_for(project)
        # Repeated query keys carry the multi-select filters, e.g. package=A&package=B.
        return {"ok": True, "library": library.index(
            show_superseded=query.get("showSuperseded", ["0"])[0] == "1",
            search=query.get("search", [""])[0],
            package=query.get("package", []),
            module_id=query.get("module", []),
            level=query.get("level", []),
            calc_type=query.get("calcType", []))}

    def _calculation(self, query) -> dict[str, Any]:
        actor, project = self._project(query.get("token", [""])[0],
                                       query.get("project", [""])[0])
        library = library_for(project)
        record = library.calculation(query.get("id", [""])[0])
        return {"ok": True,
                "calculation": {**record, "folder": str(library.folder_of(record)),
                                "pdfPath": str(library.pdf_of(record) or "")},
                "meta": project_meta(project, actor)}

    def _save_calculation(self, payload) -> dict[str, Any]:
        actor, project = self._project(payload.get("token"), payload.get("projectId"))
        module = MODULES.get(payload.get("module"))
        inputs = dict(payload.get("inputs") or {})
        inputs.update(project_meta(project, actor, payload.get("meta")))
        library = library_for(project)
        # The verifier owns 'Checked by'; carry forward whatever they endorsed.
        existing = str(payload.get("calculationId", ""))
        if existing:
            try:
                inputs["checker"] = library.calculation(existing).get("checker", "")
            except ValueError:
                inputs["checker"] = ""
        result = module.call("compute", inputs)
        summary = module.call("summarise", result)
        identity = module.call("identity", inputs)
        html_text = module.call("render", inputs, result, standalone=True)
        saved = library.save(module_id=module.id, module_folder=MODULES.folder_for(module.id),
                             inputs=inputs, identity=identity, summary=summary,
                             result=result, descriptor=module.descriptor,
                             html_text=html_text, initials=actor.get("initials", ""),
                             calculation_id=existing,
                             supersede=bool(payload.get("supersede", True)))
        if saved.get("conflict"):
            return {"ok": True, **saved}
        # Printing takes seconds; the drive already holds the calculation, so the
        # sheet is printed behind the response and the interface tracks it.
        PDF_WORKER.submit(saved["calculationId"], saved["htmlPath"], saved["pdfPath"])
        return {"ok": True, **saved, "pdf": "printing", "summary": summary,
                "identity": identity, "library": library.index()}

    def _pdf_status(self, query) -> dict[str, Any]:
        self._actor(query.get("token", [""])[0])
        return {"ok": True, "pending": PDF_WORKER.pending(),
                **PDF_WORKER.status(query.get("id", [""])[0])}

    def _import_calculation(self, payload) -> dict[str, Any]:
        """Index a calculation prepared in other software, held as PDF only."""
        actor, project = self._project(payload.get("token"), payload.get("projectId"))
        library = library_for(project)
        imported = library.import_pdf(
            source=str(payload.get("path", "")),
            member_type=str(payload.get("memberType", "")),
            number=str(payload.get("memberNumber", "")),
            package=str(payload.get("package", "")),
            level=str(payload.get("level", "")),
            title=str(payload.get("title", "")),
            description=str(payload.get("description", "")),
            calc_type=str(payload.get("calcType", "")),
            initials=actor.get("initials", ""),
            origin=str(payload.get("origin", "")))
        return {"ok": True, **imported, "library": library.index()}

    def _update_calculation(self, payload) -> dict[str, Any]:
        actor, project = self._project(payload.get("token"), payload.get("projectId"))
        library = library_for(project)
        library.update(str(payload.get("id", "")), payload.get("fields") or {})
        return {"ok": True, "library": library.index()}

    def _delete_calculation(self, payload) -> dict[str, Any]:
        actor, project = self._project(payload.get("token"), payload.get("projectId"))
        library = library_for(project)
        library.delete(str(payload.get("id", "")))
        return {"ok": True, "library": library.index()}

    def _exchange_calculation(self, payload) -> dict[str, Any]:
        """Pass one calculation's published values into another module's inputs."""
        actor, project = self._project(payload.get("token"), payload.get("projectId"))
        library = library_for(project)
        record = library.calculation(str(payload.get("sourceId", "")))
        source = MODULES.get(record["module"])
        result = source.call("compute", record["inputs"])
        parcel = source.call("exchange", record["inputs"], result)
        target = MODULES.get(payload.get("targetModule") or record["module"])
        if not target.has("apply_exchange"):
            raise ValueError(f"{target.descriptor['name']} cannot receive linked values")
        inputs = target.call("apply_exchange", payload.get("inputs") or target.call("defaults"),
                             parcel)
        return {"ok": True, "inputs": inputs, "exchange": parcel,
                "targetModule": target.id}

    # --------------------------------------------------------------- package
    def _package_preview(self, payload) -> dict[str, Any]:
        actor, project = self._project(payload.get("token"), payload.get("projectId"))
        library = library_for(project)
        rows = collate.selectable(library, include_superseded=bool(payload.get("includeSuperseded")))
        filters = payload.get("filters") or {}
        for key in ("package", "level", "calcType", "memberType", "module"):
            if filters.get(key):
                rows = [item for item in rows if str(item.get(key, "")) == str(filters[key])]
        if filters.get("finalisedOnly"):
            rows = [item for item in rows if item.get("finalised")]
        return {"ok": True, "sortFields": collate.SORT_FIELDS,
                "entries": collate.order(rows, payload.get("sort"))}

    def _package_build(self, payload) -> dict[str, Any]:
        actor, project = self._project(payload.get("token"), payload.get("projectId"))
        library = library_for(project)
        meta = project_meta(project, actor, payload.get("meta"))
        meta["title"] = str((payload.get("meta") or {}).get("title") or "Calculation package")
        purpose = str((payload.get("meta") or {}).get("reason") or "Internal Review")
        ref = qa_module.next_reference(library, project, "STR")
        folder = Path(project["folderPath"]) / "09-Doc_WRK" / "01-CAL" / "10-IN_TOOL" / "packages"
        destination = folder / f"{qa_module.safe_name(ref + ' - ' + meta['title'])}.pdf"
        built = collate.build_pdf(library, MODULES, list(payload.get("selection") or []), meta,
                                  destination, sort_fields=payload.get("sort"),
                                  include_superseded=bool(payload.get("includeSuperseded")),
                                  drawings=payload.get("drawings"), reference=ref,
                                  purpose=purpose,
                                  verifier_initials=str((payload.get("meta") or {})
                                                        .get("verifierInitials", "")))
        issue = library.record_issue({
            "ref": ref, "title": meta["title"], "reason": purpose,
            "issuedBy": actor.get("initials", ""), "sheets": built["sheets"],
            "pdfPath": built["pdfPath"], "drawingsPath": built["drawingsPath"],
            "folder": str(folder), "calculations": len(built["entries"]),
            "watermark": built["watermark"]})
        draft = self._issue_draft(project, actor, payload, issue, built)
        try:
            reveal(str(folder))
        except (ValueError, OSError):
            pass
        return {"ok": True, **built, "issue": issue, "draft": draft,
                "issues": list(reversed(library.data.get("issues", []))),
                "url": "/api/file?" + urlencode({"path": built["pdfPath"]})}

    @staticmethod
    def _issue_draft(project, actor, payload, issue, built) -> dict[str, Any]:
        """Raise a draft email to the reviewer whenever one is nominated."""
        to = str((payload.get("meta") or {}).get("reviewerEmail", "")).strip()
        if not to:
            return {"path": "", "opened": False}
        try:
            return mail.draft_for_package(
                folder=issue["folder"], name=f"{issue['ref']} - {issue['reason']}",
                to=to,
                subject=(f"{project.get('code', '')} {project.get('projectName', '')} - "
                         f"{issue['ref']} - {issue['title']} - {issue['reason']}").strip(),
                intro=(f"The calculation package below is issued for {issue['reason'].lower()}. "
                       f"Please mark any comments on the PDF and return it to the package "
                       f"folder."),
                project=project, links=[("Calculation package", built["pdfPath"]),
                                        ("Drawings", built["drawingsPath"]),
                                        ("Package folder", issue["folder"])],
                sender=actor.get("email", ""),
                closing=f"Prepared by {actor.get('displayName', '')}.")
        except OSError as exc:
            return {"path": "", "opened": False, "error": str(exc)}

    # -------------------------------------------------------------------- QA
    @staticmethod
    def _qa_public(package: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in package.items() if key != "entries"}

    def _qa_store(self, token: Any, project_id: Any) -> tuple[Any, dict, Library, qa_module.QAStore]:
        actor, project = self._project(token, project_id)
        library = library_for(project)
        return actor, project, library, qa_module.QAStore(library, project)

    def _qa_list(self, query) -> dict[str, Any]:
        actor, project, library, store = self._qa_store(query.get("token", [""])[0],
                                                        query.get("project", [""])[0])
        # A verifier returns a marked-up PDF to the package folder, so every
        # refresh reads those files rather than waiting for an explicit import.
        found = store.scan_returns(actor) if query.get("scan", ["1"])[0] == "1" else {"added": 0}
        packages = [self._qa_public(item) for item in store.packages
                    if store.can_access(item, actor)]
        return {"ok": True, "packages": packages, "template": qa_module.form_template(),
                "imported": found.get("added", 0), "summary": store.status_summary()}

    def _qa_scan(self, payload) -> dict[str, Any]:
        actor, project, library, store = self._qa_store(payload.get("token"),
                                                        payload.get("projectId"))
        found = store.scan_returns(actor)
        packages = [self._qa_public(item) for item in store.packages
                    if store.can_access(item, actor)]
        return {"ok": True, **found, "packages": packages}

    def _qa_status(self, query) -> dict[str, Any]:
        """Verification status across every project the person can see."""
        actor = self._actor(query.get("token", [""])[0])
        rows = []
        for project in PROJECTS.for_user(actor):
            if not project.get("exists"):
                rows.append({"project": project.get("code", ""),
                             "projectName": project.get("projectName", ""),
                             "folderPath": project.get("folderPath", ""),
                             "latestStatus": "Folder unreachable", "packages": 0})
                continue
            library = Library(project["folderPath"])
            rows.append(qa_module.QAStore(library, project).status_summary())
        return {"ok": True, "projects": rows}

    def _qa_create(self, payload) -> dict[str, Any]:
        actor, project, library, store = self._qa_store(payload.get("token"),
                                                        payload.get("projectId"))
        meta = project_meta(project, actor, payload.get("meta"))
        meta["title"] = str(payload.get("title") or "Calculation package")
        package = store.create(
            title=str(payload.get("title", "")), reviewer=str(payload.get("reviewer", "")),
            reviewer_email=str(payload.get("reviewerEmail", "")), actor=actor,
            registry=MODULES, selection=list(payload.get("selection") or []), meta=meta,
            sort_fields=payload.get("sort"), drawings=payload.get("drawings"),
            documents=payload.get("documents"), methods=payload.get("methods"),
            statement=payload.get("statement"),
            producer_comments=str(payload.get("producerComments", "")),
            reviewer_initials=str(payload.get("reviewerInitials", "")),
            drawing_set=payload.get("drawingSet"))
        return {"ok": True, "package": self._qa_public(package),
                "draft": package.get("draftEmail") or {},
                "url": "/api/file?" + urlencode({"path": package["calculationPdf"]})}

    def _qa_guard(self, store, package_id, actor):
        package = store.get(package_id)
        if not store.can_access(package, actor):
            raise PermissionError("You are not a designer or the verifier on this package")
        return package

    def _qa_update(self, payload) -> dict[str, Any]:
        actor, project, library, store = self._qa_store(payload.get("token"),
                                                        payload.get("projectId"))
        self._qa_guard(store, payload.get("packageId"), actor)
        package = store.update_package(str(payload.get("packageId")), payload.get("fields") or {})
        return {"ok": True, "package": self._qa_public(package)}

    def _qa_add_comment(self, payload) -> dict[str, Any]:
        actor, project, library, store = self._qa_store(payload.get("token"),
                                                        payload.get("projectId"))
        self._qa_guard(store, payload.get("packageId"), actor)
        package = store.add_comment(str(payload.get("packageId")),
                                    payload.get("comment") or {}, actor)
        return {"ok": True, "package": self._qa_public(package)}

    def _qa_update_comment(self, payload) -> dict[str, Any]:
        actor, project, library, store = self._qa_store(payload.get("token"),
                                                        payload.get("projectId"))
        self._qa_guard(store, payload.get("packageId"), actor)
        package = store.update_comment(str(payload.get("packageId")),
                                       str(payload.get("commentId")),
                                       payload.get("fields") or {}, actor)
        return {"ok": True, "package": self._qa_public(package)}

    def _qa_markups(self, payload) -> dict[str, Any]:
        actor, project, library, store = self._qa_store(payload.get("token"),
                                                        payload.get("projectId"))
        self._qa_guard(store, payload.get("packageId"), actor)
        outcome = store.import_markups(str(payload.get("packageId")),
                                       str(payload.get("path", "")), actor)
        return {"ok": True, "added": outcome["added"],
                "package": self._qa_public(outcome["package"])}

    def _qa_endorse(self, payload) -> dict[str, Any]:
        actor, project, library, store = self._qa_store(payload.get("token"),
                                                        payload.get("projectId"))
        package = self._qa_guard(store, payload.get("packageId"), actor)
        verifier = {str(package.get("reviewerEmail", "")).casefold()} | {
            str(item).casefold() for item in project.get("verifiers", [])}
        if str(actor["email"]).casefold() not in verifier:
            raise PermissionError("Only the nominated verifier may endorse this package")
        package = store.endorse(str(payload.get("packageId")), str(payload.get("action", "")),
                                actor, str(payload.get("note", "")))
        return {"ok": True, "package": self._qa_public(package)}

    def _qa_export(self, payload) -> dict[str, Any]:
        actor, project, library, store = self._qa_store(payload.get("token"),
                                                        payload.get("projectId"))
        self._qa_guard(store, payload.get("packageId"), actor)
        return {"ok": True, "files": store.export_pdf(str(payload.get("packageId")))}

    # -- files --------------------------------------------------------------
    def _serve_static(self, route: str) -> None:
        if route == "/calcpad-theme.css":
            import calcpad
            self._send(200, calcpad.theme_css(), STATIC_TYPES[".css"])
            return
        relative = route.lstrip("/") or "index.html"
        target = (APP_DIR / relative).resolve()
        if not str(target).startswith(str(APP_DIR)) or not target.is_file():
            self._send(404, {"ok": False, "error": "not found"})
            return
        ctype = STATIC_TYPES.get(target.suffix.lower(), "application/octet-stream")
        self._send(200, target.read_bytes(), ctype)

    def _serve_generated(self, token: Any, path: str) -> None:
        try:
            self._actor(token)
        except PermissionError as exc:
            self._send(401, {"ok": False, "error": str(exc)})
            return
        if not path or not within_project(path) or not os.path.isfile(path):
            self._send(404, {"ok": False, "error": "file not found"})
            return
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        self._send(200, Path(path).read_bytes(), ctype)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}/"
    print(f"InnoCalc Manager {VERSION}")
    print(f"  Projects root : {ROOT}  ({'found' if os.path.isdir(ROOT) else 'NOT found'})")
    print(f"  Modules       : {', '.join(sorted(MODULES.modules)) or 'none'}")
    for problem in MODULES.problems:
        print(f"    ! {problem['entry']}: {problem['error']}")
    print(f"  Sign-in       : {auth_module.sso_status()['mode']} (no passwords)")
    print(f"  Serving       : {url}")
    print("  Press Ctrl+C to stop.")
    if os.path.isdir(ROOT):
        DISCOVERY.refresh_async()
    try:
        webbrowser.open(url)
    except Exception:  # noqa: BLE001 - a missing browser must not stop the service
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.shutdown()


if __name__ == "__main__":
    main()
