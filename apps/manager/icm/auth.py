"""Identity for InnoCalc Manager.

Two mutually exclusive modes:

``development`` (the mode this release ships in)
    No passwords exist anywhere in the product.  A user picks their name from
    the people list, or creates a new username from their full name; the
    directory records their display name and initials so calculations remain
    attributable.  This is intended for use on the internal network only.

``sso`` (scaffolded, deliberately inactive)
    Office 365 / Microsoft Entra ID authorisation-code flow with PKCE.  Every
    piece is present - configuration, state and verifier generation, the
    authorise URL, and the redirect handler - but :data:`SSO_ENABLED` is False,
    so :func:`start_sso` and :func:`complete_sso` refuse to run.  Set
    ``ICM_SSO_ENABLED=1`` with a tenant and client id to demonstrate it; nothing
    else in the application needs to change.

There is no password storage, no password hashing and no password reset in this
module by design.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

INNOVIS_EMAIL = re.compile(r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@innovis\.com\.au$", re.I)
SESSION_HOURS = 12

# --- Office 365 single sign-on: configured but NOT activated -----------------
SSO_ENABLED = os.environ.get("ICM_SSO_ENABLED", "0") == "1"
SSO_CONFIG: dict[str, Any] = {
    "provider": "microsoft",
    "authority": "https://login.microsoftonline.com",
    "tenantId": os.environ.get("ICM_SSO_TENANT", ""),
    "clientId": os.environ.get("ICM_SSO_CLIENT_ID", ""),
    "redirectPath": "/auth/sso/callback",
    "scopes": ["openid", "profile", "email", "User.Read"],
    "responseType": "code",
    "codeChallengeMethod": "S256",
    "domainHint": "innovis.com.au",
    # Deliberately absent: no client secret is held by this desktop application;
    # the authorisation-code + PKCE flow does not need one.
}
_PENDING: dict[str, dict[str, Any]] = {}


def sso_status() -> dict[str, Any]:
    """What the browser is told about sign-in, without leaking configuration."""
    configured = bool(SSO_CONFIG["tenantId"] and SSO_CONFIG["clientId"])
    return {"enabled": SSO_ENABLED, "configured": configured,
            "provider": SSO_CONFIG["provider"],
            "mode": "sso" if SSO_ENABLED else "development",
            "note": ("Office 365 single sign-on is configured but not activated. "
                     "Passwords are not used anywhere in this release.")}


def normalise_email(value: Any) -> str:
    email = str(value or "").strip().lower()
    if not INNOVIS_EMAIL.fullmatch(email):
        raise ValueError("Use your Innovis email address, name@innovis.com.au")
    return email


def initials_for(full_name: str, email: str = "") -> str:
    words = re.findall(r"[A-Za-z]+", full_name)
    if len(words) >= 2:
        return "".join(word[0] for word in words[:4]).upper()
    source = words[0] if words else email.split("@", 1)[0]
    parts = re.findall(r"[A-Za-z]+", source.replace(".", " "))
    if len(parts) >= 2:
        return "".join(part[0] for part in parts[:4]).upper()
    return (source[:3] or "XX").upper()


def display_name_for(email: str) -> str:
    local = email.split("@", 1)[0]
    return " ".join(part.capitalize() for part in re.split(r"[._-]+", local) if part)


def username_for(full_name: Any) -> str:
    """Directory key for a new user, following the Innovis first.last address convention.

    Office 365 sign-on will later confirm or correct it; the key is never shown.
    """
    words = re.findall(r"[A-Za-z]+", str(full_name or ""))
    if len(words) < 2:
        raise ValueError("Enter your first name and surname")
    return normalise_email(".".join(word.lower() for word in words) + "@innovis.com.au")


class Directory:
    """People who use the tool. No credentials are stored."""

    def __init__(self, path: Path):
        self.path = Path(path)
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        self.data: dict[str, dict[str, Any]] = data if isinstance(data, dict) else {}

    def write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.data, indent=2, ensure_ascii=True), encoding="utf-8")
        temporary.replace(self.path)

    def upsert(self, email: str, full_name: str = "", initials: str = "") -> dict[str, Any]:
        email = normalise_email(email)
        entry = self.data.get(email, {})
        name = " ".join(str(full_name).split()) or entry.get("displayName") or display_name_for(email)
        chosen = re.sub(r"[^A-Za-z]", "", str(initials)).upper()[:4]
        entry.update({"displayName": name,
                      "initials": chosen or entry.get("initials") or initials_for(name, email),
                      "admin": bool(entry.get("admin")),
                      "lastSeen": time.strftime("%Y-%m-%dT%H:%M:%S")})
        self.data[email] = entry
        self.write()
        return self.public(email)

    def public(self, email: str) -> dict[str, Any]:
        entry = self.data.get(email, {})
        return {"email": email, "name": email, "displayName": entry.get("displayName", email),
                "initials": entry.get("initials", "XX"), "admin": bool(entry.get("admin"))}

    def everyone(self) -> list[dict[str, Any]]:
        return [self.public(email) for email in sorted(self.data)]


class Sessions:
    """In-memory bearer tokens; they do not survive a server restart."""

    def __init__(self):
        self._tokens: dict[str, dict[str, Any]] = {}

    def issue(self, user: dict[str, Any]) -> str:
        self._purge()
        token = secrets.token_urlsafe(32)
        self._tokens[token] = {"user": user, "expires": time.time() + SESSION_HOURS * 3600}
        return token

    def actor(self, token: Any) -> dict[str, Any]:
        self._purge()
        entry = self._tokens.get(str(token or ""))
        if not entry:
            raise PermissionError("Your session has ended; please sign in again")
        return entry["user"]

    def revoke(self, token: Any) -> None:
        self._tokens.pop(str(token or ""), None)

    def _purge(self) -> None:
        now = time.time()
        for token in [key for key, value in self._tokens.items() if value["expires"] < now]:
            self._tokens.pop(token, None)


# ---------------------------------------------------------------------------
#  Office 365 flow - fully written, intentionally gated off
# ---------------------------------------------------------------------------
def _pkce() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def start_sso(origin: str) -> dict[str, Any]:
    """Authorisation URL for the Microsoft sign-in page."""
    if not SSO_ENABLED:
        raise PermissionError("Office 365 single sign-on is not activated in this release")
    if not (SSO_CONFIG["tenantId"] and SSO_CONFIG["clientId"]):
        raise ValueError("Set ICM_SSO_TENANT and ICM_SSO_CLIENT_ID before enabling sign-on")
    verifier, challenge = _pkce()
    state = secrets.token_urlsafe(24)
    _PENDING[state] = {"verifier": verifier, "expires": time.time() + 600}
    query = urlencode({
        "client_id": SSO_CONFIG["clientId"],
        "response_type": SSO_CONFIG["responseType"],
        "redirect_uri": origin.rstrip("/") + SSO_CONFIG["redirectPath"],
        "response_mode": "query",
        "scope": " ".join(SSO_CONFIG["scopes"]),
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": SSO_CONFIG["codeChallengeMethod"],
        "domain_hint": SSO_CONFIG["domainHint"],
    })
    authority = f"{SSO_CONFIG['authority']}/{SSO_CONFIG['tenantId']}/oauth2/v2.0/authorize"
    return {"url": f"{authority}?{query}", "state": state}


def complete_sso(code: str, state: str, origin: str) -> dict[str, Any]:
    """Exchange the authorisation code for the signed-in user's profile."""
    if not SSO_ENABLED:
        raise PermissionError("Office 365 single sign-on is not activated in this release")
    pending = _PENDING.pop(str(state), None)
    if not pending or pending["expires"] < time.time():
        raise PermissionError("The sign-in attempt expired; please try again")
    import urllib.request  # imported here so the disabled path pulls in nothing

    payload = urlencode({
        "client_id": SSO_CONFIG["clientId"],
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": origin.rstrip("/") + SSO_CONFIG["redirectPath"],
        "code_verifier": pending["verifier"],
        "scope": " ".join(SSO_CONFIG["scopes"]),
    }).encode()
    endpoint = f"{SSO_CONFIG['authority']}/{SSO_CONFIG['tenantId']}/oauth2/v2.0/token"
    request = urllib.request.Request(endpoint, data=payload, method="POST",
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310 - fixed https host
        tokens = json.loads(response.read().decode("utf-8"))
    claims = _id_token_claims(tokens.get("id_token", ""))
    email = claims.get("preferred_username") or claims.get("email") or ""
    return {"email": normalise_email(email), "displayName": claims.get("name", ""),
            "tenant": claims.get("tid", "")}


def _id_token_claims(id_token: str) -> dict[str, Any]:
    """Read the claim set from an id token.

    The token arrives directly from the Microsoft token endpoint over TLS in the
    authorisation-code flow, so the transport authenticates it; signature
    validation would be required if a token were ever accepted from the browser.
    """
    try:
        payload = id_token.split(".")[1]
        padded = payload + "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
    except (IndexError, ValueError, UnicodeDecodeError):
        return {}
