"""What the service believes about a request that arrived through the reverse proxy.

``X-Forwarded-Proto`` and ``X-Forwarded-Host`` are honoured only when the
connecting peer is one of ``ICM_TRUSTED_PROXIES``; from anyone else they are
ignored.  The real peer address is never replaced, so the identity-header
backstop in the request handler can still tell the proxy from a LAN host.
"""

from __future__ import annotations

from typing import Any, Mapping

from .config import Settings


def _first(headers: Mapping[str, str], name: str) -> str:
    return str(headers.get(name) or "").split(",", 1)[0].strip()


def origin(settings: Settings, peer: str, headers: Mapping[str, str]) -> str:
    """Scheme and host the browser used, for redirects and absolute links."""
    scheme = "https" if settings.https else "http"
    host = str(headers.get("Host") or "").strip() or f"{settings.host}:{settings.port}"
    if settings.trusts(peer):
        proto = _first(headers, "X-Forwarded-Proto").lower()
        if proto in {"http", "https"}:
            scheme = proto
        host = _first(headers, "X-Forwarded-Host") or host
    return f"{scheme}://{host}"


def identity(settings: Settings, peer: str, headers: Mapping[str, Any]) -> str:
    """The signed-in user the proxy vouches for, or raise PermissionError."""
    value = str(headers.get(settings.user_header) or "").strip()
    if not settings.trusts(peer):
        raise PermissionError("Sign-in is only accepted through the InnoCalc proxy")
    if not value:
        raise PermissionError("No signed-in user was received from the proxy")
    return value
