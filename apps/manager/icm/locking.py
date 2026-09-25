"""Exclusive, non-blocking locks that Windows PCs and the Linux host both honour on the share.

Both platforms lock byte 0 of the lock file: ``msvcrt.locking`` on Windows and a POSIX record
lock (``fcntl.lockf``) on Linux, which the CIFS client forwards to the file server as an SMB
byte-range lock (unless the share is mounted with ``nobrl``). ``flock`` is not used because
older CIFS clients keep it local to the host.

    python -m icm.locking hold  <lock file> [--seconds N]   hold it, for the C1 sign-off tests
    python -m icm.locking probe <lock file>                 exit 0 free, 3 held elsewhere
"""

from __future__ import annotations

import argparse
import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path

BUSY = "Another process is updating this project. Please retry."
EXIT_FREE, EXIT_BUSY = 0, 3

# POSIX record locks belong to the process, so a second holder in this process must be refused
# here; opening and closing a second descriptor would otherwise release the first holder's lock.
_HELD: set[str] = set()
_GUARD = threading.Lock()


def _acquire(handle) -> None:
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.lockf(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB, 1, 0)


def _release(handle) -> None:
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.lockf(handle.fileno(), fcntl.LOCK_UN, 1, 0)


@contextmanager
def project_lock(path: Path):
    key = os.path.normcase(os.path.abspath(path))
    with _GUARD:
        if key in _HELD:
            raise ValueError(BUSY)
        _HELD.add(key)
    try:
        with Path(path).open("a+b") as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            try:
                _acquire(handle)
            except OSError as exc:
                raise ValueError(BUSY) from exc
            try:
                yield
            finally:
                handle.seek(0)
                _release(handle)
    finally:
        with _GUARD:
            _HELD.discard(key)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m icm.locking",
                                     description="Check that project locks exclude each other.")
    commands = parser.add_subparsers(dest="command", required=True)
    hold = commands.add_parser("hold", help="take the lock and keep it")
    hold.add_argument("path", type=Path)
    hold.add_argument("--seconds", type=float, default=120.0)
    probe = commands.add_parser("probe", help="try the lock once and release it")
    probe.add_argument("path", type=Path)
    arguments = parser.parse_args(argv)
    try:
        with project_lock(arguments.path):
            if arguments.command == "probe":
                print(f"free: {arguments.path}")
                return EXIT_FREE
            print(f"holding {arguments.path} for {arguments.seconds:g} s", flush=True)
            time.sleep(arguments.seconds)
            print("released")
            return EXIT_FREE
    except ValueError:
        print(f"busy: {arguments.path} is locked by another process")
        return EXIT_BUSY


if __name__ == "__main__":
    raise SystemExit(main())