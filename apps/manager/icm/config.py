"""Deployment settings for InnoCalc Manager, read once from ``ICM_*`` variables.

The same code runs on a designer's PC (loopback, desktop helpers available) and
as a tenant behind the shared reverse proxy (``ICM_HOST=0.0.0.0``), where the
desktop helpers are withdrawn and every supplied path is confined to the
projects root.  Invalid settings stop the service at start with a clear reason.
"""

from __future__ import annotations

import ipaddress
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from . import SUITE_ROOT
from packages.innocalc_sdk.manifest import load_manifest

APP_DIR = Path(__file__).resolve().parents[1]
AUTH_MODES = ("dev", "proxy")
TABS = ("library", "calculation", "package", "qa")
ROLES = ("user", "admin")
DEFAULT_USER_HEADER = "X-Ms-Client-Principal-Name"
# PDF export has not passed its gate on Windows or in a container (ROADMAP.md, critical).
PDF_GATED_TAB_ACCESS = "package=admin,qa=admin"

log = logging.getLogger("icm")


class ConfigurationError(RuntimeError):
    """A setting that would leave the service unsafe or unusable."""


def _flag(env: Mapping[str, str], name: str, default: bool = False) -> bool:
    value = str(env.get(name, "")).strip().lower()
    if not value:
        return default
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} must be true or false, not {value!r}")


def _integer(env: Mapping[str, str], name: str, default: int, minimum: int = 0) -> int:
    value = str(env.get(name, "")).strip()
    try:
        number = int(value) if value else default
    except ValueError:
        raise ConfigurationError(f"{name} must be a whole number, not {value!r}") from None
    if number < minimum:
        raise ConfigurationError(f"{name} must be at least {minimum}")
    return number


def _items(value: Any) -> tuple[str, ...]:
    return tuple(item.strip() for item in str(value or "").split(",") if item.strip())


def parse_networks(value: Any, name: str = "ICM_TRUSTED_PROXIES") -> tuple[Any, ...]:
    networks = []
    for item in _items(value):
        try:
            networks.append(ipaddress.ip_network(item, strict=False))
        except ValueError:
            raise ConfigurationError(f"{name}: {item!r} is not an IP address or CIDR") from None
    return tuple(networks)


def parse_access(value: Any, name: str, known: tuple[str, ...] | set[str]) -> dict[str, str]:
    """``'package=admin,qa=admin'`` -> ``{'package': 'admin', 'qa': 'admin'}``."""
    access: dict[str, str] = {}
    for item in _items(value):
        key, separator, role = item.partition("=")
        key, role = key.strip(), role.strip().lower()
        if not separator or not key or not role:
            raise ConfigurationError(f"{name}: expected name=role, got {item!r}")
        if key not in known:
            raise ConfigurationError(f"{name}: unknown name {key!r}; expected one of "
                                     f"{', '.join(sorted(known))}")
        if role not in ROLES:
            raise ConfigurationError(f"{name}: unknown role {role!r}; expected one of "
                                     f"{', '.join(ROLES)}")
        access[key] = role
    return access


def _is_loopback(host: str) -> bool:
    if host.casefold() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    root: str
    data_dir: Path
    backup_dir: Path
    backup_interval_minutes: int
    backup_retention_days: int
    auth_mode: str
    user_header: str
    admins: frozenset[str]
    trusted_proxies: tuple[Any, ...]
    allowed_hosts: tuple[str, ...]
    https: bool
    read_only: bool
    tab_access: Mapping[str, str]
    module_access: Mapping[str, str]
    # Roots older records were written under, e.g. J:\Active Projects on the PCs.
    legacy_roots: tuple[str, ...] = ()
    # How people see the projects root in Explorer and Outlook, e.g. \\fileserver\Projects.
    share_path: str = ""
    # The server marks the projects root as its own; PCs then stop writing to it.
    owns_projects: bool = False

    @property
    def desktop(self) -> bool:
        """Folder pickers, Explorer and opening the browser only make sense on the user's PC."""
        return _is_loopback(self.host)

    def trusts(self, address: str) -> bool:
        try:
            peer = ipaddress.ip_address(str(address).split("%", 1)[0])
        except ValueError:
            return False
        if isinstance(peer, ipaddress.IPv6Address) and peer.ipv4_mapped:
            peer = peer.ipv4_mapped
        return any(peer in network for network in self.trusted_proxies)

    def host_allowed(self, host_header: str) -> bool:
        if not self.allowed_hosts:
            return True
        host = str(host_header or "").strip().lower()
        if host.startswith("["):
            host = host[1:].split("]", 1)[0]
        elif host.count(":") == 1:
            host = host.split(":", 1)[0]
        for allowed in self.allowed_hosts:
            if allowed == host or (allowed.startswith("*.") and host.endswith(allowed[1:])):
                return True
        return False

    def role_of(self, user: Mapping[str, Any]) -> str:
        email = str(user.get("email", "")).casefold()
        return "admin" if user.get("admin") or email in self.admins else "user"

    def permitted(self, access: Mapping[str, str], key: str, user: Mapping[str, Any] | None) -> bool:
        required = access.get(key, "user")
        if required == "user":
            return True
        return bool(user) and ROLES.index(self.role_of(user)) >= ROLES.index(required)

    def tabs_for(self, user: Mapping[str, Any]) -> list[str]:
        return [tab for tab in TABS if self.permitted(self.tab_access, tab, user)]

    def configuration(self) -> dict[str, Any]:
        """Non-secret settings, reported by the health check."""
        return {"authMode": self.auth_mode, "readOnly": self.read_only, "https": self.https,
                "desktop": self.desktop, "allowedHosts": list(self.allowed_hosts),
                "trustedProxies": [str(network) for network in self.trusted_proxies],
                "backupIntervalMinutes": self.backup_interval_minutes}


def load(env: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env
    auth_mode = str(env.get("ICM_AUTH_MODE", "dev")).strip().lower() or "dev"
    if auth_mode not in AUTH_MODES:
        raise ConfigurationError(f"ICM_AUTH_MODE must be one of {', '.join(AUTH_MODES)}")
    trusted = parse_networks(env.get("ICM_TRUSTED_PROXIES", "127.0.0.1"))
    if auth_mode == "proxy":
        if not trusted:
            raise ConfigurationError("ICM_AUTH_MODE=proxy needs ICM_TRUSTED_PROXIES")
        if _flag(env, "ICM_SSO_ENABLED"):
            raise ConfigurationError("ICM_AUTH_MODE=proxy takes identity from the proxy; "
                                     "ICM_SSO_ENABLED must stay 0")
    module_ids = {str(item["id"]) for item in load_manifest(SUITE_ROOT)["modules"]}
    data_dir = Path(env.get("ICM_DATA_DIR") or APP_DIR / "data").resolve()
    backup_dir = Path(env.get("ICM_BACKUP_DIR") or data_dir.parent / "backups").resolve()
    if backup_dir == data_dir or data_dir in backup_dir.parents:
        raise ConfigurationError("ICM_BACKUP_DIR must be outside ICM_DATA_DIR")
    header = str(env.get("ICM_SSO_USER_HEADER", DEFAULT_USER_HEADER)).strip()
    settings = Settings(
        host=str(env.get("ICM_HOST", "127.0.0.1")).strip() or "127.0.0.1",
        port=_integer(env, "ICM_PORT", 8125, minimum=1),
        root=str(env.get("ICM_ROOT", r"J:\Active Projects")),
        data_dir=data_dir,
        backup_dir=backup_dir,
        backup_interval_minutes=_integer(env, "ICM_BACKUP_INTERVAL_MINUTES", 60),
        backup_retention_days=_integer(env, "ICM_BACKUP_RETENTION_DAYS", 14, minimum=1),
        auth_mode=auth_mode,
        user_header=header or DEFAULT_USER_HEADER,
        admins=frozenset(item.casefold() for item in _items(env.get("ICM_ADMINS"))),
        trusted_proxies=trusted,
        allowed_hosts=tuple(item.lower() for item in _items(env.get("ICM_ALLOWED_HOSTS"))),
        https=_flag(env, "ICM_HTTPS"),
        read_only=_flag(env, "ICM_READ_ONLY"),
        tab_access=parse_access(env.get("ICM_TAB_ACCESS") or PDF_GATED_TAB_ACCESS,
                                "ICM_TAB_ACCESS", TABS),
        module_access=parse_access(env.get("ICM_MODULE_ACCESS"), "ICM_MODULE_ACCESS",
                                   module_ids),
        legacy_roots=_items(env.get("ICM_LEGACY_ROOTS", r"J:\Active Projects")),
        share_path=str(env.get("ICM_SHARE_PATH", "")).strip(),
        owns_projects=_flag(env, "ICM_OWNS_PROJECTS"))
    if settings.owns_projects and (settings.desktop or settings.read_only):
        raise ConfigurationError("ICM_OWNS_PROJECTS is for the production server only, not a "
                                 "PC or a read-only preview")
    if auth_mode == "dev" and not settings.desktop:
        log.warning("ICM_AUTH_MODE=dev on %s: anyone who can reach the service may sign in as "
                    "any Innovis address. Trusted networks only.", settings.host)
    return settings


def ensure_directories(settings: Settings) -> None:
    """Create the data and backup folders, or refuse with the reason.

    A folder that already exists is left alone whoever owns it; it only has to
    be writable by this process.
    """
    for label, folder in (("ICM_DATA_DIR", settings.data_dir),
                          ("ICM_BACKUP_DIR", settings.backup_dir)):
        try:
            folder.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryFile(dir=folder):
                pass
        except OSError as exc:
            raise ConfigurationError(f"{label} {folder} is not writable by this process: "
                                     f"{exc.strerror or exc}") from None
