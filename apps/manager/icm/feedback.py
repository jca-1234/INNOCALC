"""Bug reports and improvement requests from the people using InnoCalc.

Reports are kept centrally in the data folder (``feedback.json``), not in a
project, so they are backed up with the rest of the manager's data and one list
serves everybody once InnoCalc runs on the server.  Anyone signed in may raise a
report and add their vote to someone else's; only admins triage them.
"""

from __future__ import annotations

import csv
import io
import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

KINDS = {"bug": "BUG", "improvement": "IMP"}
STATUSES = ("new", "triaged", "in progress", "done", "won't do")
PRIORITIES = ("low", "medium", "high", "critical")
LIMITS = {"title": 140, "description": 5000, "steps": 3000, "expected": 2000,
          "response": 3000}
CONTEXT_KEYS = ("view", "module", "moduleVersion", "project", "calculation", "version",
                "browser", "page")


def _text(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class FeedbackStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()

    # -- persistence --------------------------------------------------------
    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_bytes())
        except FileNotFoundError:
            data = {}
        except ValueError as exc:
            raise ValueError("The feedback register is damaged; restore it from a backup") from exc
        data = data if isinstance(data, dict) else {}
        data.setdefault("schema", 1)
        data.setdefault("reports", [])
        data.setdefault("counters", {})
        return data

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")
        temporary.replace(self.path)

    # -- reading ------------------------------------------------------------
    def reports(self, *, kind: str = "", status: str = "", search: str = "") -> list[dict[str, Any]]:
        needle = str(search or "").strip().casefold()
        reports = [report for report in self._read()["reports"]
                   if (not kind or report["kind"] == kind)
                   and (not status or report["status"] == status)
                   and (not needle or needle in " ".join(
                       str(report.get(key, "")) for key in
                       ("reference", "title", "description", "steps", "response",
                        "reporterName")).casefold())]
        return sorted(reports, key=lambda item: item["createdAt"], reverse=True)

    def as_csv(self) -> str:
        buffer = io.StringIO()
        columns = ["reference", "kind", "status", "priority", "title", "description", "steps",
                   "expected", "reporterName", "createdAt", "votes", "response", "updatedAt"]
        writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for report in self.reports():
            row = {**report, "votes": len(report.get("votes", []))}
            # Stop spreadsheet software treating free text as a formula.
            writer.writerow({key: f"'{value}" if isinstance(value, str) and value[:1] in "=+-@\t\r"
                             and value else value for key, value in row.items()})
        return buffer.getvalue()

    # -- writing ------------------------------------------------------------
    def submit(self, fields: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        kind = str(fields.get("kind", "")).lower()
        if kind not in KINDS:
            raise ValueError("Choose whether this is a bug or an improvement")
        title = _text(fields.get("title"), LIMITS["title"])
        description = _text(fields.get("description"), LIMITS["description"])
        if not title or not description:
            raise ValueError("Give the report a short title and describe it")
        priority = str(fields.get("priority") or "medium").lower()
        if priority not in PRIORITIES:
            raise ValueError(f"Priority must be one of {', '.join(PRIORITIES)}")
        context = fields.get("context") if isinstance(fields.get("context"), dict) else {}
        with self._lock:
            data = self._read()
            number = int(data["counters"].get(kind, 0)) + 1
            data["counters"][kind] = number
            report = {"id": uuid.uuid4().hex[:12], "reference": f"{KINDS[kind]}-{number:04d}",
                      "kind": kind, "status": "new", "priority": priority, "title": title,
                      "description": description,
                      "steps": _text(fields.get("steps"), LIMITS["steps"]),
                      "expected": _text(fields.get("expected"), LIMITS["expected"]),
                      "context": {key: _text(context.get(key), 200) for key in CONTEXT_KEYS
                                  if context.get(key)},
                      "reporter": actor.get("email", ""),
                      "reporterName": actor.get("displayName", ""),
                      "createdAt": _now(), "updatedAt": _now(),
                      "votes": [], "response": "", "history": []}
            data["reports"].append(report)
            self._write(data)
        return report

    def vote(self, report_id: str, actor: dict[str, Any]) -> dict[str, Any]:
        """Toggle 'this affects me too'."""
        with self._lock:
            data = self._read()
            report = self._find(data, report_id)
            votes = report.setdefault("votes", [])
            who = actor.get("email", "")
            if who in votes:
                votes.remove(who)
            else:
                votes.append(who)
            self._write(data)
        return report

    def update(self, report_id: str, fields: dict[str, Any],
               actor: dict[str, Any]) -> dict[str, Any]:
        """Admin triage: status, priority and a response to the reporter."""
        with self._lock:
            data = self._read()
            report = self._find(data, report_id)
            changes = {}
            if "status" in fields:
                status = str(fields["status"]).lower()
                if status not in STATUSES:
                    raise ValueError(f"Status must be one of {', '.join(STATUSES)}")
                changes["status"] = status
            if "priority" in fields:
                priority = str(fields["priority"]).lower()
                if priority not in PRIORITIES:
                    raise ValueError(f"Priority must be one of {', '.join(PRIORITIES)}")
                changes["priority"] = priority
            if "response" in fields:
                changes["response"] = _text(fields["response"], LIMITS["response"])
            changed = {key: value for key, value in changes.items() if report.get(key) != value}
            if changed:
                report.update(changed)
                report["updatedAt"] = _now()
                report.setdefault("history", []).append(
                    {"at": report["updatedAt"], "by": actor.get("displayName", ""),
                     "changes": changed})
                self._write(data)
        return report

    @staticmethod
    def _find(data: dict[str, Any], report_id: str) -> dict[str, Any]:
        report = next((item for item in data["reports"] if item["id"] == str(report_id)), None)
        if not report:
            raise ValueError("That report no longer exists")
        return report
