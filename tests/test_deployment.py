"""Tenant-readiness of the manager: settings, access gates, proxy trust, health, backups."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tarfile
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import ExitStack
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/manager"))

from icm import backup, config, proxy  # noqa: E402

TEMP = Path(tempfile.mkdtemp(prefix="icm-deploy-"))
PROJECTS = TEMP / "projects"
BASE_ENV = {"ICM_DATA_DIR": str(TEMP / "data"), "ICM_BACKUP_DIR": str(TEMP / "backups"),
            "ICM_ROOT": str(PROJECTS), "ICM_SSO_ENABLED": "0"}
IDENTITY = config.DEFAULT_USER_HEADER
server = httpd = None
origin = ""


def settings(**overrides: str) -> config.Settings:
    return config.load({**BASE_ENV, **{f"ICM_{key.upper()}": value
                                       for key, value in overrides.items()}})


def setUpModule():
    global server, httpd, origin
    PROJECTS.mkdir(parents=True)
    with patch.dict(os.environ, BASE_ENV):
        spec = importlib.util.spec_from_file_location("icm_server_under_test",
                                                      ROOT / "apps/manager/server.py")
        server = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(server)
    server.PDF_WORKER.submit = lambda *args: None
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{httpd.server_port}"


def tearDownModule():
    httpd.shutdown()
    httpd.server_close()
    shutil.rmtree(TEMP, ignore_errors=True)


def call(path: str, payload: dict | None = None, headers: dict | None = None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    message = urllib.request.Request(origin + path, data=body, headers={
        "Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(message, timeout=120) as response:
            return response.status, json.loads(response.read()), response.headers
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read()), error.headers


def sign_in(email: str = "designer@innovis.com.au") -> tuple[str, dict]:
    status, data, _ = call("/api/auth/signin", {"email": email})
    assert status == 200, data
    return data["token"], data


def new_project(token: str, name: str) -> dict:
    status, data, _ = call("/api/projects/create", {"token": token, "path": str(PROJECTS / name)})
    assert status == 200, data
    return data["project"]


class ConfigurationTests(unittest.TestCase):
    def test_defaults_are_the_desktop_behaviour(self):
        current = settings()
        self.assertEqual(current.auth_mode, "dev")
        self.assertTrue(current.desktop)
        self.assertFalse(current.read_only)
        self.assertEqual(current.tabs_for({"email": "a@innovis.com.au"}), ["library", "calculation"])
        self.assertEqual(current.tabs_for({"email": "a@innovis.com.au", "admin": True}),
                         list(config.TABS))
        opened = settings(tab_access="package=user,qa=user")
        self.assertEqual(opened.tabs_for({"email": "a@innovis.com.au"}), list(config.TABS))

    def test_bad_tab_access_refused(self):
        for value in ("finance=admin", "package=boss", "package"):
            with self.subTest(value=value), self.assertRaises(config.ConfigurationError):
                settings(tab_access=value)

    def test_unknown_module_refused(self):
        with self.assertRaisesRegex(config.ConfigurationError, "ICM_MODULE_ACCESS"):
            settings(module_access="no-such-module=admin")

    def test_bad_trusted_proxy_refused(self):
        with self.assertRaisesRegex(config.ConfigurationError, "ICM_TRUSTED_PROXIES"):
            settings(trusted_proxies="caddy")

    def test_proxy_mode_refuses_in_app_sign_on(self):
        with self.assertRaisesRegex(config.ConfigurationError, "ICM_SSO_ENABLED"):
            settings(auth_mode="proxy", sso_enabled="1")

    def test_backups_inside_data_refused(self):
        with self.assertRaisesRegex(config.ConfigurationError, "ICM_BACKUP_DIR"):
            settings(backup_dir=str(TEMP / "data" / "backups"))

    def test_unwritable_directory_refused(self):
        blocker = TEMP / "a-file"
        blocker.write_text("x", encoding="utf-8")
        with self.assertRaisesRegex(config.ConfigurationError, "ICM_DATA_DIR"):
            config.ensure_directories(settings(data_dir=str(blocker / "data")))


class ReadOnlyTests(unittest.TestCase):
    def test_writes_refused_with_409(self):
        token, _ = sign_in()
        with patch.object(server, "SETTINGS", settings(read_only="true")):
            for route in ("/api/projects/create", "/api/calculation/save", "/api/package/build",
                          "/api/qa/create", "/api/qa/scan"):
                with self.subTest(route=route):
                    status, data, _ = call(route, {"token": token})
                    self.assertEqual(status, 409)
                    self.assertIn("read-only", data["error"])

    def test_saving_allowed_when_writable(self):
        token, _ = sign_in()
        project = new_project(token, "J9001 - TEST - WRITABLE")
        _, schema, _ = call("/api/module/schema?module=steel-member")
        status, data, _ = call("/api/calculation/save", {
            "token": token, "projectId": project["id"], "module": "steel-member",
            "inputs": {**schema["defaults"], "date": "01/01/2026"}})
        self.assertEqual(status, 200, data)
        self.assertTrue(data["calculationId"])

    def test_read_only_is_reported(self):
        with patch.object(server, "SETTINGS", settings(read_only="true")):
            _, session = sign_in()
            _, health, _ = call("/api/health")
        self.assertTrue(session["readOnly"])
        self.assertTrue(health["configuration"]["readOnly"])


class CutOverTests(unittest.TestCase):
    def test_owning_projects_is_for_the_server_only(self):
        for overrides in ({}, {"host": "0.0.0.0", "read_only": "true"}):
            with self.subTest(**overrides), self.assertRaisesRegex(config.ConfigurationError,
                                                                   "ICM_OWNS_PROJECTS"):
                settings(owns_projects="true", **overrides)

    def test_pc_stops_writing_once_the_server_claims_the_root(self):
        token, _ = sign_in()
        with self.assertLogs("icm", "WARNING"):
            owner = settings(host="0.0.0.0", owns_projects="true",
                             allowed_hosts="innocalc.apps.example")
        with patch.object(server, "SETTINGS", owner):
            server.claim_projects()
        marker = PROJECTS / server.SERVER_MARKER
        try:
            status, data, _ = call("/api/projects/create",
                                   {"token": token, "path": str(PROJECTS / "J9003 - TEST - MOVED")})
            _, session = sign_in()
            reads = call(f"/api/projects?token={token}")
        finally:
            marker.unlink()
        self.assertEqual(status, 409)
        self.assertIn("https://innocalc.apps.example/", data["error"])
        self.assertTrue(session["readOnly"])
        self.assertIn("server", session["readOnlyReason"])
        self.assertEqual(reads[0], 200)


class AccessTests(unittest.TestCase):
    def test_sign_in_by_name_without_email(self):
        status, created, _ = call("/api/auth/signin", {"newUser": True, "fullName": "Pat Newcomer",
                                                       "initials": "PN"})
        self.assertEqual(status, 200, created)
        self.assertEqual(created["user"]["displayName"], "Pat Newcomer")
        again = call("/api/auth/signin", {"newUser": True, "fullName": "pat newcomer"})
        self.assertEqual(again[0], 400)
        status, picked, _ = call("/api/auth/signin", {"userId": created["user"]["email"]})
        self.assertEqual(status, 200, picked)
        self.assertEqual(picked["user"]["initials"], "PN")
        self.assertEqual(call("/api/auth/signin", {"userId": "nobody@innovis.com.au"})[0], 400)
        self.assertEqual(call("/api/auth/signin", {"newUser": True, "fullName": "Pat"})[0], 400)

    def test_tabs_follow_role(self):
        current = settings(tab_access="package=admin,qa=admin", admins="boss@innovis.com.au")
        with patch.object(server, "SETTINGS", current):
            _, user = sign_in()
            _, admin = sign_in("boss@innovis.com.au")
        self.assertEqual(user["tabs"], ["library", "calculation"])
        self.assertEqual(admin["tabs"], list(config.TABS))

    def test_withheld_tab_is_403_for_user_and_open_to_admin(self):
        user_token, _ = sign_in()
        admin_token, _ = sign_in("boss@innovis.com.au")
        project = new_project(admin_token, "J9002 - TEST - TABS")
        current = settings(tab_access="package=admin", admins="boss@innovis.com.au")
        with patch.object(server, "SETTINGS", current):
            refused = call("/api/package/preview", {"token": user_token, "projectId": project["id"]})
            allowed = call("/api/package/preview", {"token": admin_token, "projectId": project["id"]})
        self.assertEqual(refused[0], 403)
        self.assertEqual(allowed[0], 200, allowed[1])

    def test_withheld_module_is_hidden_and_refused(self):
        user_token, _ = sign_in()
        admin_token, _ = sign_in("boss@innovis.com.au")
        current = settings(module_access="concrete-column=admin", admins="boss@innovis.com.au")
        with patch.object(server, "SETTINGS", current):
            listed = call(f"/api/modules?token={user_token}")[1]["modules"]
            admin_listed = call(f"/api/modules?token={admin_token}")[1]["modules"]
            status, _, _ = call("/api/calculate", {"token": user_token, "module": "concrete-column",
                                                   "inputs": {}})
        self.assertNotIn("concrete-column", [item["id"] for item in listed])
        self.assertIn("concrete-column", [item["id"] for item in admin_listed])
        self.assertEqual(status, 403)


class ProxyTests(unittest.TestCase):
    def test_identity_from_untrusted_peer_refused(self):
        with patch.object(server, "SETTINGS", settings(auth_mode="proxy",
                                                       trusted_proxies="10.9.9.9")):
            with self.assertLogs("icm", "WARNING"):
                status, _, _ = call("/api/projects", headers={IDENTITY: "designer@innovis.com.au"})
        self.assertEqual(status, 401)

    def test_identity_from_trusted_peer_accepted(self):
        with patch.object(server, "SETTINGS", settings(auth_mode="proxy")):
            status, data, _ = call("/api/auth/signin", {},
                                   headers={IDENTITY: "Proxy.User@innovis.com.au"})
            listed = call("/api/projects", headers={IDENTITY: "proxy.user@innovis.com.au"})
            missing = call("/api/projects")
        self.assertEqual(status, 200, data)
        self.assertEqual(data["user"]["email"], "proxy.user@innovis.com.au")
        self.assertEqual(listed[0], 200)
        self.assertEqual(missing[0], 401)

    def test_forwarded_headers_only_from_trusted_proxy(self):
        current = settings(trusted_proxies="10.0.0.2")
        headers = {"Host": "internal:8125", "X-Forwarded-Proto": "https",
                   "X-Forwarded-Host": "innocalc.apps.example"}
        self.assertEqual(proxy.origin(current, "10.0.0.2", headers),
                         "https://innocalc.apps.example")
        self.assertEqual(proxy.origin(current, "10.0.0.9", headers), "http://internal:8125")


class TransportTests(unittest.TestCase):
    def test_unlisted_host_rejected(self):
        with patch.object(server, "SETTINGS", settings(allowed_hosts="innocalc.apps.example")):
            refused = call("/api/health", headers={"Host": "evil.example"})
            allowed = call("/api/health", headers={"Host": "innocalc.apps.example"})
        self.assertEqual(refused[0], 400)
        self.assertEqual(allowed[0], 200)

    def test_hsts_only_with_https(self):
        plain = call("/api/health")[2]
        with patch.object(server, "SETTINGS", settings(https="true")):
            secure = call("/api/health")[2]
        self.assertIsNone(plain.get("Strict-Transport-Security"))
        self.assertIn("max-age", secure.get("Strict-Transport-Security"))


class HealthTests(unittest.TestCase):
    def test_health_is_200_when_data_is_usable(self):
        status, data, _ = call("/api/health")
        self.assertEqual(status, 200)
        self.assertIn(data["status"], {"ok", "degraded"})
        self.assertTrue(data["checks"]["dataDir"])

    def test_health_is_503_when_data_is_unavailable(self):
        with patch.object(server, "SETTINGS", settings(data_dir=str(TEMP / "gone" / "data"))):
            status, data, _ = call("/api/health")
        self.assertEqual(status, 503)
        self.assertEqual(data["status"], "unavailable")


class ServerModeTests(unittest.TestCase):
    def setUp(self):
        with self.assertLogs("icm", "WARNING"):
            self.server_mode = settings(host="0.0.0.0")
        self.token, _ = sign_in()

    def test_paths_are_confined_to_the_projects_root(self):
        outside = str(TEMP / "elsewhere" / "J9100 - TEST - OUTSIDE")
        with patch.object(server, "SETTINGS", self.server_mode):
            browsed = call(f"/api/browse?token={self.token}&path={urllib.request.quote(str(TEMP))}")
            places = call(f"/api/browse?token={self.token}")[1]["dirs"]
            created = call("/api/projects/create", {"token": self.token, "path": outside})
        self.assertEqual(browsed[0], 400)
        self.assertEqual([item["path"] for item in places], [str(PROJECTS)])
        self.assertEqual(created[0], 400)
        self.assertFalse(Path(outside).exists())

    def test_desktop_helpers_are_withdrawn(self):
        with patch.object(server, "SETTINGS", self.server_mode):
            picked = call(f"/api/pick?token={self.token}")
            revealed = call(f"/api/reveal?token={self.token}&path={urllib.request.quote(str(PROJECTS))}")
        self.assertFalse(picked[1]["ok"])
        self.assertEqual(revealed[0], 400)


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="icm-backup-"))
        self.data, self.backups = self.base / "data", self.base / "backups"
        self.data.mkdir()
        (self.data / "people.json").write_text('{"a@innovis.com.au": {}}', encoding="utf-8")
        (self.data / "projects.json").write_text('{"projects": {}}', encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def snapshot(self) -> Path:
        result = backup.run_backup(self.data, self.backups)
        self.assertEqual(result.status, "ok", result.error)
        return Path(result.path)

    def test_round_trip(self):
        archive = self.snapshot()
        self.assertTrue(archive.name.startswith("innocalc-"))
        self.assertIn(archive.name, (self.backups / backup.MANIFEST).read_text(encoding="utf-8"))
        (self.data / "projects.json").write_text('{"projects": {"x": {}}}', encoding="utf-8")
        (self.data / "stray.json").write_text("{}", encoding="utf-8")
        outcome = backup.restore(archive, self.data)
        self.assertEqual(outcome["restored"], 2)
        self.assertEqual((self.data / "projects.json").read_text(encoding="utf-8"),
                         '{"projects": {}}')
        self.assertFalse((self.data / "stray.json").exists())
        self.assertTrue((Path(outcome["keptPrevious"]) / "stray.json").is_file())

    def test_running_manager_is_never_overridden(self):
        archive = self.snapshot()
        with ExitStack() as stack:
            backup.hold_data_lock(self.data, stack)
            for force in (False, True):
                with self.subTest(force=force), self.assertRaises(backup.Refused):
                    backup.restore(archive, self.data, force=force)

    def test_interrupted_write_needs_force(self):
        archive = self.snapshot()
        (self.data / "projects.json.tmp").write_text("{", encoding="utf-8")
        with self.assertRaises(backup.Refused):
            backup.restore(archive, self.data)
        self.assertEqual(backup.restore(archive, self.data, force=True)["restored"], 2)
        self.assertFalse((self.data / "projects.json.tmp").exists())

    def test_tampered_snapshot_fails_verification(self):
        archive = self.snapshot()
        with archive.open("ab") as handle:
            handle.write(b"x")
        with self.assertRaisesRegex(backup.Invalid, "SHA-256"):
            backup.restore(archive, self.data)

    def test_unsafe_entry_fails_verification(self):
        self.backups.mkdir()
        archive = self.backups / "innocalc-20260101T000000Z.tar.gz"
        with tarfile.open(archive, "w:gz") as handle:
            info = tarfile.TarInfo("../escape.json")
            info.size = 2
            handle.addfile(info, io.BytesIO(b"{}"))
        with self.assertRaisesRegex(backup.Invalid, "unsafe"):
            backup.restore(archive, self.data)
        self.assertFalse((self.base / "escape.json").exists())

    def test_damaged_data_is_not_snapshotted(self):
        (self.data / "people.json").write_text("{", encoding="utf-8")
        result = backup.run_backup(self.data, self.backups)
        self.assertEqual(result.status, "failed")
        self.assertEqual(list(self.backups.glob("*.tar.gz")), [])

    def test_empty_data_is_skipped(self):
        empty = self.base / "empty"
        empty.mkdir()
        self.assertEqual(backup.run_backup(empty, self.backups).status, "skipped")
        self.assertEqual(list(self.backups.glob("*.tar.gz")), [])

    def test_command_line_exit_codes(self):
        archive = self.snapshot()
        damaged = self.backups / "innocalc-20200101T000000Z.tar.gz"
        damaged.write_bytes(b"not a snapshot")
        quiet = contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO())
        with quiet[0], quiet[1]:
            restored = backup.main(["restore", str(archive), "--data-dir", str(self.data)])
            invalid = backup.main(["restore", str(damaged), "--data-dir", str(self.data)])
            with ExitStack() as stack:
                backup.hold_data_lock(self.data, stack)
                refused = backup.main(["restore", str(archive), "--data-dir", str(self.data)])
        self.assertEqual((restored, invalid, refused),
                         (backup.EXIT_OK, backup.EXIT_INVALID, backup.EXIT_REFUSED))


if __name__ == "__main__":
    unittest.main()
