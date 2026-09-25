from __future__ import annotations

import importlib
import argparse
import json
import os
import sys
import threading
import urllib.parse
import urllib.request
import uuid
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-pdf", action="store_true")
    parser.add_argument("--output", type=Path, help="working folder (default artifacts/smoke-<id>)")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = arguments.output or root / "artifacts" / f"smoke-{uuid.uuid4().hex[:8]}"
    project_folder = output / "projects" / "J9999 - TEST - SMOKE"
    project_folder.mkdir(parents=True)
    sys.path.insert(0, str(root / "apps/manager"))
    with patch.dict(os.environ, {"ICM_DATA_DIR": str(output / "manager-data"),
                                 "ICM_ROOT": str(output / "projects"), "ICM_SSO_ENABLED": "0"}):
        server = importlib.import_module("server")
    if arguments.no_pdf:
        server.PDF_WORKER.submit = lambda *args: None

    class QuietHandler(server.Handler):
        def log_message(self, format, *args):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{httpd.server_port}"

    def request(path, payload=None):
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        message = urllib.request.Request(origin + path, data=body,
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(message, timeout=60) as response:
            document = json.loads(response.read())
        if not document.get("ok"):
            raise AssertionError(document.get("error", "Request failed"))
        return document

    try:
        modules = request("/api/modules")
        assert not modules["problems"], modules["problems"]
        session = request("/api/auth/signin", {"email": "smoke.test@innovis.com.au",
                                               "fullName": "Smoke Test", "initials": "TEST"})
        token = session["token"]
        project = request("/api/projects/create", {"token": token, "path": str(project_folder)})["project"]
        selection = []
        checked = []
        for descriptor in modules["modules"]:
            module_id = descriptor["id"]
            schema = request("/api/module/schema?" + urllib.parse.urlencode({"module": module_id}))
            inputs = {**schema["defaults"], "date": "01/01/2026"}
            calculated = request("/api/calculate", {"token": token, "module": module_id, "inputs": inputs})
            assert 'class="calc-page"' in calculated["reportHtml"]
            saved = request("/api/calculation/save", {"token": token, "projectId": project["id"],
                                                       "module": module_id, "inputs": inputs})
            selection.append(saved["calculationId"])
            query = urllib.parse.urlencode({"token": token, "project": project["id"], "id": saved["calculationId"]})
            reopened = request("/api/calculation?" + query)["calculation"]
            assert reopened["module"] == module_id
            assert reopened["revisions"][-1]["snapshotSha256"]
            checked.append({"module": module_id, "status": calculated["summary"]["status"],
                            "saved": True, "reopened": True})
        if arguments.no_pdf:
            report = {"ok": True, "modules": checked, "pdfChecked": False, "output": str(output)}
            (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(json.dumps(report, indent=2))
            return 0
        queue = server.PDF_WORKER.queue
        with queue.all_tasks_done:
            if not queue.all_tasks_done.wait_for(lambda: queue.unfinished_tasks == 0, timeout=300):
                raise TimeoutError("Saved-sheet PDF printing did not finish in 300 seconds")
        for calculation_id in selection:
            status = server.PDF_WORKER.status(calculation_id)
            assert status["status"] == "ready", status

        from icm.collate import build_pdf
        from icm.library import Library
        from pypdf import PdfReader

        library = Library(project_folder)
        built = build_pdf(library, server.MODULES, selection,
                          {"title": "Infrastructure smoke", "designer": "TEST", "project": "Smoke test"},
                          output / "package.pdf", purpose="TEST")
        document = PdfReader(built["pdfPath"])
        text = "\n".join(page.extract_text() or "" for page in document.pages)
        links = sum(len(page.get("/Annots", [])) for page in document.pages)
        assert "Calculation Index" in text
        assert len(document.pages) == built["sheets"], (len(document.pages), built["sheets"])
        assert len(text) > 1000 and links >= len(selection)
        report = {"ok": True, "modules": checked, "pdfChecked": True, "pdfPages": len(document.pages),
                  "pdfAnnotations": links, "pdfTextCharacters": len(text),
                  "flattened": built["flattened"], "browser": server.pdf_tools.available()["browser"],
                  "output": str(output)}
        (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=10)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())