"""Draft emails for issued calculation and verification packages.

Outlook opens an ``.eml`` file carrying the ``X-Unsent: 1`` header as a new
unsent message, so a draft can be raised without any mail library, MAPI
automation or add-in.  The file is written beside the package it announces, so
the draft is part of the project record even if it is never sent.
"""

from __future__ import annotations

import html
import os
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from .library import safe_name


def _link(path: str | Path) -> str:
    """A file:// link Outlook renders as a clickable network path."""
    return Path(path).absolute().as_uri()


def compose(*, to: str, subject: str, intro: str, project: dict[str, Any],
            links: list[tuple[str, str]], sender: str = "",
            closing: str = "") -> EmailMessage:
    message = EmailMessage()
    message["X-Unsent"] = "1"
    message["To"] = to
    message["Subject"] = subject
    if sender:
        message["From"] = sender
    heading = " - ".join(str(project.get(key, "")) for key in ("code", "projectName")
                         if project.get(key))
    rows = "".join(
        f'<li><a href="{html.escape(_link(target))}">{html.escape(label)}</a></li>'
        for label, target in links if target)
    body = (f"<p>{html.escape(intro)}</p>"
            f"<p><b>{html.escape(heading)}</b></p>"
            f"<ul>{rows}</ul>"
            f"<p>{html.escape(closing)}</p>")
    plain = "\n".join([intro, heading, *[f"{label}: {target}" for label, target in links],
                       closing])
    message.set_content(plain)
    message.add_alternative(f"<html><body>{body}</body></html>", subtype="html")
    return message


def write_draft(folder: str | Path, name: str, message: EmailMessage) -> Path:
    path = Path(folder) / f"{safe_name(name)}.eml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(message))
    return path


def open_draft(path: str | Path) -> bool:
    """Hand the draft to the default mail client. Never fatal."""
    if os.name != "nt":
        return False
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
        return True
    except OSError:
        return False


def draft_for_package(*, folder: str | Path, name: str, to: str, subject: str,
                      intro: str, project: dict[str, Any], links: list[tuple[str, str]],
                      sender: str = "", closing: str = "",
                      open_now: bool = True) -> dict[str, Any]:
    message = compose(to=to, subject=subject, intro=intro, project=project,
                      links=links, sender=sender, closing=closing)
    path = write_draft(folder, name, message)
    return {"path": str(path), "opened": open_now and open_draft(path), "to": to}
