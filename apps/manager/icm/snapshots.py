from __future__ import annotations

import hashlib
import html
import json
import math
from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


def _encode(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return {"$innocalcFloat": "nan" if math.isnan(value) else "inf" if value > 0 else "-inf"}
    if isinstance(value, dict):
        return {key: _encode(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_encode(item) for item in value]
    return value


def _decode(value: dict) -> Any:
    if set(value) == {"$innocalcFloat"} and value["$innocalcFloat"] in ("nan", "inf", "-inf"):
        return float(value["$innocalcFloat"])
    return value


def snapshot_json(value: dict) -> str:
    return json.dumps(_encode(value), ensure_ascii=True, allow_nan=False, default=str)


class SavedSheet(HTMLParser):
    def __init__(self, anchor: str):
        super().__init__(convert_charrefs=False)
        self.anchor = anchor
        self.output: list[str] = []
        self.in_body = False
        self.skip_script = False
        self.pages = 0

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self.in_body = True
            return
        if not self.in_body:
            return
        if tag == "script":
            self.skip_script = True
        if self.skip_script:
            return
        if "calc-page" in dict(attrs).get("class", "").split():
            self.pages += 1
            identifier = self.anchor if self.pages == 1 else f"{self.anchor}-p{self.pages}"
            attrs = [(key, value) for key, value in attrs if key != "id"] + [("id", identifier)]
            attributes = "".join(f' {key}="{html.escape(value or "", quote=True)}"' for key, value in attrs)
            self.output.append(f'<{tag}{attributes}><a class="contents-link" href="#innocalc-contents">Contents</a>')
        else:
            self.output.append(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        if self.in_body and not self.skip_script:
            self.output.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if tag == "body":
            self.in_body = False
        elif tag == "script":
            self.skip_script = False
        elif self.in_body and not self.skip_script:
            self.output.append(f"</{tag}>")

    def handle_data(self, data):
        if self.in_body and not self.skip_script:
            self.output.append(data)

    def handle_entityref(self, name):
        self.handle_data(f"&{name};")

    def handle_charref(self, name):
        self.handle_data(f"&#{name};")


def package_body(document: str, anchor: str) -> tuple[str, int]:
    parser = SavedSheet(anchor)
    parser.feed(document)
    if not parser.pages:
        raise ValueError("The saved revision contains no calculation pages; re-save it before export")
    return "".join(parser.output), parser.pages


def freeze_attachments(root: Path, result: dict[str, Any]) -> dict[str, Any]:
    frozen = deepcopy(result)
    for attachment in frozen.get("attachments") or []:
        source = Path(attachment.get("path", ""))
        if not source.is_file():
            raise ValueError(f"Cannot save a revision with a missing attachment: {source}")
        content = source.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        target = root / ".revisions" / "assets" / f"{digest}.pdf"
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            with target.open("xb") as handle:
                handle.write(content)
        elif target.read_bytes() != content:
            raise ValueError("Saved attachment integrity check failed")
        attachment.update({"snapshotPath": str(target.relative_to(root)),
                           "sha256": digest, "exists": True})
    return frozen


def attachment_path(root: Path, attachment: dict[str, Any]) -> Path:
    if not attachment.get("snapshotPath"):
        raise ValueError("This revision has an unfrozen attachment; review and re-save it")
    path = (root / attachment["snapshotPath"]).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Saved attachment is outside the calculation library")
    if hashlib.sha256(path.read_bytes()).hexdigest() != attachment.get("sha256"):
        raise ValueError("Saved attachment integrity check failed")
    return path


def save_snapshot(root: Path, snapshot: dict[str, Any]) -> tuple[str, str]:
    content = snapshot_json(snapshot).encode("utf-8")
    digest = hashlib.sha256(content).hexdigest()
    path = root / ".revisions" / f"{digest}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("xb") as handle:
            handle.write(content)
    elif path.read_bytes() != content:
        raise ValueError("The saved revision snapshot is damaged")
    return str(path.relative_to(root)), digest


def load_snapshot(root: Path, revision: dict[str, Any]) -> dict[str, Any]:
    path = (root / revision["snapshotPath"]).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Revision snapshot is outside the calculation library")
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != revision.get("snapshotSha256"):
        raise ValueError("Revision snapshot integrity check failed; restore the original snapshot")
    return json.loads(content, object_hook=_decode)


class EmbeddedInputs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.documents: dict[str, Any] = {}
        self.identifier = ""
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "script" and attributes.get("type") == "application/json":
            self.identifier = attributes.get("id", "")
            self.parts = []

    def handle_data(self, data):
        if self.identifier:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.identifier:
            try:
                self.documents[self.identifier] = json.loads("".join(self.parts), object_hook=_decode)
            except ValueError:
                pass
            self.identifier = ""


def recovery_data(document: str) -> dict[str, Any] | None:
    parser = EmbeddedInputs()
    parser.feed(document)
    metadata = parser.documents.get("innocalc-record")
    if isinstance(metadata, dict) and metadata.get("module") and isinstance(metadata.get("inputs"), dict):
        return metadata
    legacy = {"smd-inputs": ("steel-member", "01 - STEEL MEMBER", "Steel member"),
              "ccd-inputs": ("concrete-column", "02 - CONCRETE COLUMN", "Concrete column"),
              "cpd-inputs": ("calculation-pad", "90 - CALCULATION PAD", "Calculation pad")}
    found = [(identifier, values) for identifier, values in legacy.items()
             if isinstance(parser.documents.get(identifier), dict)]
    if len(found) != 1:
        return None
    identifier, (module_id, folder, calc_type) = found[0]
    return {"module": module_id, "moduleFolder": folder, "calcType": calc_type,
            "inputs": parser.documents[identifier], "summary": {"status": "UNVERIFIED"}}