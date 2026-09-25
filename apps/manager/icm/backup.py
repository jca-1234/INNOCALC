"""Restorable snapshots of the manager's own data directory.

Calculations, revisions and QA records live in each project folder on the
projects share and are protected by that share's backups.  What this module
protects is ``ICM_DATA_DIR``: the people directory, the project registry and
the discovery index.  Snapshots are written as
``innocalc-<UTC stamp>.tar.gz`` into ``ICM_BACKUP_DIR`` beside a
``manifest.jsonl`` of SHA-256 hashes, staged in the same directory and renamed
into place so a partial file is never mistaken for a snapshot.

    python -m icm.backup create  [--data-dir DIR] [--backup-dir DIR]
    python -m icm.backup restore ARCHIVE [--data-dir DIR] [--force]

Restore exit codes: 0 restored, 1 refused, 2 snapshot failed verification.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import sys
import tarfile
import threading
import uuid
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from .locking import project_lock

PREFIX = "innocalc-"
SUFFIX = ".tar.gz"
MANIFEST = "manifest.jsonl"
LOCK_NAME = "manager.lock"
FIRST_DELAY_SECONDS = 30.0
EXIT_OK, EXIT_REFUSED, EXIT_INVALID = 0, 1, 2


@dataclass
class BackupResult:
    status: str
    path: str = ""
    sha256: str = ""
    files: int = 0
    error: str = ""
    finished: str = ""

    def public(self) -> dict[str, Any]:
        return {"status": self.status, "file": Path(self.path).name if self.path else "",
                "files": self.files, "error": self.error, "finished": self.finished}


class Refused(Exception):
    """Restoring now would damage live data."""


class Invalid(Exception):
    """The snapshot cannot be trusted."""


def hold_data_lock(data_dir: Path, stack: ExitStack) -> None:
    """Hold the data directory for as long as ``stack`` is open, or raise Refused."""
    try:
        stack.enter_context(project_lock(Path(data_dir) / LOCK_NAME))
    except ValueError:
        raise Refused(f"InnoCalc Manager is running against {data_dir}; stop it first") from None


def _is_member(path: Path, data_dir: Path) -> bool:
    relative = path.relative_to(data_dir)
    return (path.is_file() and path.name != LOCK_NAME and not path.name.endswith(".tmp")
            and not relative.parts[0].startswith((".restore-", ".pre-restore-")))


def _members(data_dir: Path) -> list[Path]:
    return sorted(path for path in data_dir.rglob("*") if _is_member(path, data_dir))


def _check_json(name: str, content: bytes) -> None:
    if name.lower().endswith(".json"):
        try:
            json.loads(content.decode("utf-8"))
        except (UnicodeError, ValueError) as exc:
            raise Invalid(f"{name} is not valid JSON: {exc}") from None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _stamp(now: datetime) -> str:
    return now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_backup(data_dir: Path, backup_dir: Path, retention_days: int = 14,
               now: datetime | None = None) -> BackupResult:
    """Snapshot the data directory. Never raises; the result says what happened."""
    now = now or datetime.now(timezone.utc)
    data_dir, backup_dir = Path(data_dir), Path(backup_dir)
    staging = backup_dir / f"staging-{_stamp(now)}-{uuid.uuid4().hex[:6]}{SUFFIX}"
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        members = _members(data_dir)
        if not members:
            return BackupResult("skipped", error="nothing to back up yet",
                                finished=now.isoformat(timespec="seconds"))
        with tarfile.open(staging, "w:gz") as archive:
            for path in members:
                # Every writer replaces its file atomically, so one read is one version.
                content = path.read_bytes()
                name = path.relative_to(data_dir).as_posix()
                _check_json(name, content)
                info = tarfile.TarInfo(name)
                info.size = len(content)
                info.mtime = int(path.stat().st_mtime)
                archive.addfile(info, io.BytesIO(content))
        final = backup_dir / f"{PREFIX}{_stamp(now)}{SUFFIX}"
        os.replace(staging, final)
        digest = _sha256(final)
        entry = {"file": final.name, "sha256": digest, "bytes": final.stat().st_size,
                 "files": len(members), "created": now.isoformat(timespec="seconds")}
        with (backup_dir / MANIFEST).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")
        prune(backup_dir, retention_days, now)
        return BackupResult("ok", str(final), digest, len(members),
                            finished=now.isoformat(timespec="seconds"))
    except (OSError, Invalid, tarfile.TarError) as exc:
        staging.unlink(missing_ok=True)
        return BackupResult("failed", error=str(exc), finished=now.isoformat(timespec="seconds"))


def prune(backup_dir: Path, retention_days: int, now: datetime | None = None) -> None:
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=retention_days)
    for path in backup_dir.glob(f"{PREFIX}*{SUFFIX}"):
        try:
            created = datetime.strptime(path.name[len(PREFIX):-len(SUFFIX)], "%Y%m%dT%H%M%SZ")
        except ValueError:
            continue
        if created.replace(tzinfo=timezone.utc) < cutoff:
            path.unlink(missing_ok=True)
    for path in backup_dir.glob(f"staging-*{SUFFIX}"):
        if path.stat().st_mtime < cutoff.timestamp():
            path.unlink(missing_ok=True)


def _manifest_hash(archive: Path) -> str:
    manifest = archive.parent / MANIFEST
    if not manifest.is_file():
        return ""
    recorded = ""
    for line in manifest.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("file") == archive.name:
            recorded = str(entry.get("sha256", ""))
    return recorded


def verify(archive: Path) -> dict[str, bytes]:
    """Every file in the snapshot, checked, or raise Invalid."""
    archive = Path(archive)
    if not archive.is_file():
        raise Invalid(f"snapshot not found: {archive}")
    recorded = _manifest_hash(archive)
    if recorded and recorded != _sha256(archive):
        raise Invalid("SHA-256 does not match manifest.jsonl")
    files: dict[str, bytes] = {}
    try:
        with tarfile.open(archive, "r:gz") as handle:
            for member in handle.getmembers():
                name = PurePosixPath(member.name)
                if (not member.isfile() or name.is_absolute() or ".." in name.parts
                        or ":" in member.name or "\\" in member.name):
                    raise Invalid(f"unsafe entry in snapshot: {member.name!r}")
                content = handle.extractfile(member).read()  # type: ignore[union-attr]
                _check_json(member.name, content)
                files[name.as_posix()] = content
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise Invalid(f"snapshot is unreadable: {exc}") from None
    if not files:
        raise Invalid("snapshot is empty")
    return files


def restore(archive: Path, data_dir: Path, force: bool = False) -> dict[str, Any]:
    """Replace the data directory's contents with a verified snapshot.

    Refused outright while a manager holds the directory. Left-over ``*.tmp``
    files mean a write was interrupted; ``force`` accepts them. The files that
    are replaced are kept in ``.pre-restore-<stamp>`` inside the data directory.
    """
    files = verify(archive)
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        hold_data_lock(data_dir, stack)
        interrupted = [path.name for path in data_dir.glob("*.tmp")]
        if interrupted and not force:
            raise Refused("interrupted writes present (" + ", ".join(sorted(interrupted))
                          + "); make sure the manager is stopped, then add --force")
        stamp = _stamp(datetime.now(timezone.utc))
        staging = data_dir / f".restore-{stamp}"
        kept = data_dir / f".pre-restore-{stamp}"
        staging.mkdir()
        try:
            for name, content in files.items():
                target = staging / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            current = _members(data_dir) + list(data_dir.glob("*.tmp"))
            for path in current:
                destination = kept / path.relative_to(data_dir)
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.replace(path, destination)
            for name in files:
                target = data_dir / name
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(staging / name, target)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
    return {"restored": len(files), "keptPrevious": str(kept) if kept.exists() else ""}


class Scheduler:
    """Snapshot shortly after start and then every interval, on a daemon thread."""

    def __init__(self, data_dir: Path, backup_dir: Path, interval_minutes: int,
                 retention_days: int, first_delay: float = FIRST_DELAY_SECONDS):
        self.data_dir, self.backup_dir = Path(data_dir), Path(backup_dir)
        self.interval = interval_minutes * 60.0
        self.retention_days = retention_days
        self.first_delay = first_delay
        self.last: BackupResult | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        if self.interval <= 0:
            return
        threading.Thread(target=self._run, name="icm-backup", daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        delay = self.first_delay
        while not self._stop.wait(delay):
            self.last = run_backup(self.data_dir, self.backup_dir, self.retention_days)
            if self.last.status == "failed":
                print(f"  ! Backup failed: {self.last.error}", file=sys.stderr)
            delay = self.interval


def main(argv: list[str] | None = None) -> int:
    from . import config

    settings = config.load()
    parser = argparse.ArgumentParser(prog="python -m icm.backup", description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="take a snapshot now")
    create.add_argument("--data-dir", type=Path, default=settings.data_dir)
    create.add_argument("--backup-dir", type=Path, default=settings.backup_dir)
    back = commands.add_parser("restore", help="restore a snapshot into a stopped instance")
    back.add_argument("archive", type=Path)
    back.add_argument("--data-dir", type=Path, default=settings.data_dir)
    back.add_argument("--force", action="store_true",
                      help="accept interrupted-write files; never overrides a running manager")
    arguments = parser.parse_args(argv)
    if arguments.command == "create":
        result = run_backup(arguments.data_dir, arguments.backup_dir,
                            settings.backup_retention_days)
        print(json.dumps(result.public()))
        return EXIT_REFUSED if result.status == "failed" else EXIT_OK
    try:
        outcome = restore(arguments.archive, arguments.data_dir, arguments.force)
    except Invalid as exc:
        print(f"snapshot failed verification: {exc}", file=sys.stderr)
        return EXIT_INVALID
    except Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    print("integrity: ok")
    print(f"restored {outcome['restored']} file(s) into {arguments.data_dir}")
    if outcome["keptPrevious"]:
        print(f"previous files kept in {outcome['keptPrevious']}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
