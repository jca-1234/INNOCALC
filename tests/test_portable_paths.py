"""Nothing the manager stores may carry a Windows drive letter or backslash."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/manager"))

from icm import mail
from icm.library import Library
from icm.paths import locate, portable, relative
from icm.projects import Discovery, ProjectRegistry

ACTOR = {"email": "pat.user@innovis.com.au", "displayName": "Pat User", "initials": "PU"}


class PathTests(unittest.TestCase):
    def test_windows_paths_are_understood_on_any_host(self):
        self.assertEqual(relative(r"J:\Active Projects\J3601 to J3700\J3657 - A - B",
                                  r"j:\active projects"), "J3601 to J3700/J3657 - A - B")
        self.assertIsNone(relative(r"K:\Other\J3657", r"J:\Active Projects"))
        self.assertEqual(relative("/mnt/projects/J3601 to J3700/J3657", "/mnt/projects"),
                         "J3601 to J3700/J3657")
        self.assertIsNone(relative(r"J:\Active Projects\J3657", "/mnt/projects"))

    def test_stored_relative_paths_use_forward_slashes(self):
        self.assertEqual(portable(r"01 - STEEL MEMBER\P01\Beam.html", "/anything"),
                         "01 - STEEL MEMBER/P01/Beam.html")
        self.assertEqual(locate(r"a\b/c.html", Path("/base")), Path("/base/a/b/c.html"))


class RegistryTests(unittest.TestCase):
    def test_projects_are_stored_by_location_and_legacy_records_adopted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "projects"
            folder = root / "J9001 to J9100" / "J9001 - ACME - Warehouse"
            data = Path(temporary) / "projects.json"
            data.write_text(json.dumps({"schema": 1, "members": {}, "projects": {"old": {
                "id": "old", "folderPath": r"J:\Active Projects\J9001 to J9100\J9001 - ACME - Warehouse",
                "folderName": "J9001 - ACME - Warehouse", "designers": [], "verifiers": []}}}),
                encoding="utf-8")
            registry = ProjectRegistry(data, str(root), (r"J:\Active Projects",))
            self.assertEqual(Path(registry.get("old")["folderPath"]), folder)
            added = registry.register(str(root / "J9002 to J9100" / "J9002 - B - C"), ACTOR)
            registry.write()
            stored = data.read_text(encoding="utf-8")
            self.assertNotIn("\\\\", stored)
            self.assertNotIn("J:", stored)
            self.assertEqual(json.loads(stored)["projects"][added["id"]]["location"],
                             "J9002 to J9100/J9002 - B - C")
            reopened = ProjectRegistry(data, str(root))
            self.assertEqual(Path(reopened.get(added["id"])["folderPath"]),
                             root / "J9002 to J9100" / "J9002 - B - C")

    def test_discovery_index_is_root_relative(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "projects"
            (root / "J9001 to J9100" / "J9001 - ACME - Warehouse").mkdir(parents=True)
            index = Path(temporary) / "index.json"
            discovery = Discovery(index, str(root))
            discovery.remember(str(root / "J9001 to J9100" / "J9001 - ACME - Warehouse"))
            stored = json.loads(index.read_bytes())
            self.assertEqual(stored["projects"]["J9001"], ["J9001 to J9100/J9001 - ACME - Warehouse"])
            self.assertNotIn("root", stored)
            self.assertEqual(Discovery(index, str(root)).cached("J9001"),
                             [str(root / "J9001 to J9100" / "J9001 - ACME - Warehouse")])


class LibraryTests(unittest.TestCase):
    def test_legacy_backslash_and_absolute_paths_are_rewritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            library = Library(temporary)
            saved = library.save(module_id="example", module_folder="Example", inputs={},
                                 identity={"memberType": "Beam", "memberNumber": "1",
                                           "package": "P01"},
                                 summary={"worstUtil": 0.5, "status": "OK"},
                                 html_text="<p>x</p>", initials="TEST")
            record = library.data["calculations"][0]
            revision = record["revisions"][0]
            self.assertNotIn("\\", revision["relativePath"])
            revision["relativePath"] = revision["relativePath"].replace("/", "\\")
            library.data["issues"].append({"pdfPath": str(Path(temporary) / "packages" / "x.pdf"),
                                           "folder": str(Path(temporary) / "packages")})
            library.write()
            reopened = Library(temporary)
            reopened.write()
            text = reopened.path.read_text(encoding="utf-8")
            self.assertNotIn("\\\\", text)
            self.assertNotIn(temporary.replace("\\", "\\\\"), text)
            self.assertEqual(reopened.data["issues"][0]["pdfPath"], "packages/x.pdf")
            self.assertEqual(reopened.pdf_of(reopened.data["calculations"][0]), None)
            self.assertEqual(reopened.file_of(reopened.data["calculations"][0]["revisions"][0]),
                             Path(saved["htmlPath"]).resolve())
            self.assertEqual(Path(reopened.index()["issues"][0]["pdfPath"]),
                             Path(temporary).resolve() / "packages" / "x.pdf")
            self.assertFalse(reopened.rewrite_portable())

    def test_rewrite_persists_without_a_save(self):
        with tempfile.TemporaryDirectory() as temporary:
            library = Library(temporary)
            library.data["issues"].append({"folder": str(Path(temporary) / "packages")})
            library.write()
            self.assertTrue(Library(temporary).rewrite_portable())
            self.assertEqual(json.loads(library.path.read_bytes())["issues"][0]["folder"],
                             "packages")


class MergeTests(unittest.TestCase):
    def test_two_pcs_become_one_list(self):
        from icm import merge

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "projects"
            first, second, server = base / "pc1", base / "pc2", base / "server"
            for folder, email, name, opened in ((first, "pat.user@innovis.com.au", "Pat", "2026-09-01"),
                                                (second, "sam.other@innovis.com.au", "Sam", "2026-09-05")):
                folder.mkdir()
                (folder / "projects.json").write_text(json.dumps({"schema": 1, "projects": {
                    f"id-{name}": {"id": f"id-{name}", "code": "J9001",
                                   "folderPath": r"J:\Active Projects\J9001 to J9100\J9001 - A - B",
                                   "designers": [email], "verifiers": []}},
                    "members": {email: {f"id-{name}": {"lastOpened": opened}}}}), encoding="utf-8")
                (folder / "people.json").write_text(json.dumps({email: {
                    "displayName": name, "initials": "PS", "lastSeen": opened}}), encoding="utf-8")
            combined = merge.merge([first, second], server, str(root), (r"J:\Active Projects",))
            self.assertEqual(combined["report"]["combined"], {"projects": 1, "people": 2})
            project = next(iter(combined["projects"]["projects"].values()))
            self.assertEqual(project["designers"], ["pat.user@innovis.com.au", "sam.other@innovis.com.au"])
            self.assertEqual({key for entries in combined["projects"]["members"].values()
                              for key in entries}, {project["id"]})
            self.assertIn("PS", combined["report"]["initialsShared"])
            merge.apply(combined, server, str(root), (), base / "backups")
            stored = (server / "projects.json").read_text(encoding="utf-8")
            self.assertNotIn("J:", stored)
            self.assertIn('"location": "J9001 to J9100/J9001 - A - B"', stored)


class MailTests(unittest.TestCase):
    def tearDown(self):
        mail.set_share("", "")

    def test_links_use_the_share_people_see(self):
        mail.set_share("/mnt/projects", r"\\fileserver\Projects")
        self.assertEqual(mail.user_path("/mnt/projects/J9001 - A/06-QA"),
                         r"\\fileserver\Projects\J9001 - A\06-QA")
        self.assertTrue(mail._link("/mnt/projects/J9001 - A").startswith("file://fileserver/Projects/"))


if __name__ == "__main__":
    unittest.main()
