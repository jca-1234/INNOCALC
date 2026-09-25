"""Deterministic PDF export of a calculation-pad document.

Shared by every module so a sheet printed from the steel tool, the concrete
tool, the calculation pad or InnoCalc Manager is produced identically.  An
installed Chromium browser is used because it keeps in-document anchors as real
PDF links, which is what makes a collated package's contents page work.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

BROWSER_CANDIDATES = [
    Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft/Edge/Application/msedge.exe",
    Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft/Edge/Application/msedge.exe",
    Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    Path("/usr/bin/chromium"),
    Path("/usr/bin/chromium-browser"),
    Path("/usr/bin/google-chrome"),
]
# Headless Chromium is not safe to run concurrently against one profile.
_PRINT_LOCK = threading.Lock()


def browser_path() -> Path:
    configured = os.environ.get("INNOCALC_BROWSER", "").strip()
    if configured:
        if not Path(configured).is_file():
            raise RuntimeError(f"INNOCALC_BROWSER does not exist: {configured}")
        return Path(configured)
    browser = next((path for path in BROWSER_CANDIDATES if path.is_file()), None)
    if not browser:
        raise RuntimeError("Microsoft Edge or Google Chrome is required for PDF export")
    return browser


def export_pdf(html_path: str | Path, pdf_path: str | Path, *, open_after: bool = False,
               timeout: int = 240) -> Path:
    html_path, pdf_path = Path(html_path).resolve(), Path(pdf_path).resolve()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    # A throwaway profile per run stops a second export attaching to the first
    # browser instance and hanging until the timeout.
    profile = Path(tempfile.mkdtemp(prefix="calcpad-print-"))
    command = [str(browser_path()), "--headless=new", "--disable-gpu",
               "--no-pdf-header-footer", "--disable-extensions",
               "--disable-background-networking", "--no-first-run",
               f"--user-data-dir={profile}",
               *shlex.split(os.environ.get("INNOCALC_BROWSER_ARGS", "")),
               "--run-all-compositor-stages-before-draw", "--virtual-time-budget=20000",
               f"--print-to-pdf={pdf_path}", html_path.as_uri()]
    try:
        with _PRINT_LOCK:
            completed = subprocess.run(command, capture_output=True, text=True,
                                       timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"PDF export timed out after {timeout}s") from exc
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    if completed.returncode or not pdf_path.is_file() or pdf_path.stat().st_size < 1000:
        detail = (completed.stderr or completed.stdout or "PDF file was not produced").strip()
        raise RuntimeError(f"PDF export failed: {detail[:400]}")
    if open_after and os.name == "nt":
        os.startfile(pdf_path)  # type: ignore[attr-defined]
    return pdf_path
