"""Portable paths for everything InnoCalc writes to disk.

The manager runs on Windows PCs today and on a Linux server next, against the
same projects drive mounted in different places (``J:\\Active Projects`` versus
``/mnt/projects``).  Nothing it stores may therefore hold a drive letter or a
backslash: a path is stored relative to a known base - the projects root, a
project folder or its calculation folder - always with ``/`` separators, and is
joined back onto that base when read.

A path outside its base (a project a PC user added from outside the projects
root) cannot be made portable and is kept as it is; server mode never accepts
such a path in the first place.
"""

from __future__ import annotations

import ntpath
import posixpath
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


def _windows(text: str) -> bool:
    return bool(PureWindowsPath(text).drive) or "\\" in text


def is_absolute(value: Any) -> bool:
    text = str(value or "")
    return PureWindowsPath(text).is_absolute() or PurePosixPath(text).is_absolute()


def relative(target: Any, base: Any) -> str | None:
    """``target`` relative to ``base`` as 'a/b' ('' when equal), or None when outside it.

    Windows-style strings compare case-insensitively whatever the host, so a
    Linux server can still migrate paths written on a PC.
    """
    target, base = str(target or "").strip(), str(base or "").strip()
    if not (target and base):
        return None
    flavour = ntpath if _windows(base) or _windows(target) else posixpath
    target, base = flavour.normpath(target), flavour.normpath(base)
    try:
        common = flavour.commonpath([target, base])
    except ValueError:  # different drives, or absolute against relative
        return None
    if flavour.normcase(common) != flavour.normcase(base):
        return None
    result = flavour.relpath(target, base)
    if result == ".":
        return ""
    return PureWindowsPath(result).as_posix() if flavour is ntpath else result


def portable(path: Any, base: Any) -> str:
    """Store ``path`` relative to ``base`` with '/' separators; outside ``base`` it is kept."""
    text = str(path or "").strip()
    if not text:
        return ""
    if not is_absolute(text):
        return PureWindowsPath(text).as_posix()
    found = relative(text, base)
    if found is None:
        try:
            found = relative(Path(text).resolve(), Path(str(base)).resolve())
        except OSError:
            found = None
    return text if found is None else found


def locate(value: Any, base: Any) -> Path:
    """Join a stored value back onto ``base``; legacy absolute and backslash forms still work."""
    text = str(value or "").strip()
    if not text:
        return Path(base)
    if is_absolute(text):
        return Path(text)
    return Path(base).joinpath(*PureWindowsPath(text).parts)
