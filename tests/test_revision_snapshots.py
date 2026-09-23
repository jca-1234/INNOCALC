from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/manager"))

from icm.collate import build_html
from icm.library import Library
from icm.snapshots import attachment_path, freeze_attachments, load_snapshot, save_snapshot


class RevisionTests(unittest.TestCase):
    def test_nonfinite_values_use_valid_json_and_round_trip(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, digest = save_snapshot(root, {"util": {"capacity": math.inf}})
            json.loads((root / path).read_bytes(), parse_constant=lambda value: self.fail(value))
            restored = load_snapshot(root, {"snapshotPath": path, "snapshotSha256": digest})
            self.assertEqual(restored["util"]["capacity"], math.inf)

    def test_attachments_are_frozen_and_verified(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "drawing.pdf"
            source.write_bytes(b"Original drawing")
            original = {"attachments": [{"path": str(source), "exists": True}]}
            frozen = freeze_attachments(root, original)
            source.write_bytes(b"Changed drawing")
            saved_path = attachment_path(root, frozen["attachments"][0])
            self.assertEqual(saved_path.read_bytes(), b"Original drawing")
            self.assertNotIn("snapshotPath", original["attachments"][0])
            saved_path.write_bytes(b"Tampered")
            with self.assertRaisesRegex(ValueError, "integrity"):
                attachment_path(root, frozen["attachments"][0])

    def save(self, library):
        return library.save(module_id="concrete-column", module_folder="02 - CONCRETE COLUMN",
                            inputs={"memberNumber": "1"}, identity={"memberType": "Column",
                            "memberNumber": "1", "package": "P01", "title": "Example"},
                            summary={"status": "OK", "worstUtil": 0.5}, initials="TEST",
                            descriptor={"version": "V1"}, result={"util": {"bending": 0.5}},
                            html_text='<html><body><section class="calc-page">Saved 50%</section></body></html>')

    def test_export_never_calls_current_module(self):
        with tempfile.TemporaryDirectory() as temporary:
            library = Library(temporary)
            saved = self.save(library)
            registry = Mock()
            built = build_html(library, registry, [saved["calculationId"]], {})
            registry.get.assert_not_called()
            self.assertIn("Saved 50%", built["html"])
            self.assertIn('id="calc-001"', built["html"])
            self.assertEqual(built["entries"][0]["worstUtil"], 0.5)

    def test_tampered_snapshot_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            library = Library(temporary)
            saved = self.save(library)
            (library.root / saved["revision"]["snapshotPath"]).write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "integrity"):
                build_html(library, Mock(), [saved["calculationId"]], {})

    def test_adoption_restores_identity_and_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            library = Library(temporary)
            self.save(library)
            library.data["calculations"] = []
            library.write()
            self.assertEqual(library.adopt_existing(), 1)
            record = library.data["calculations"][0]
            self.assertEqual(record["module"], "concrete-column")
            self.assertEqual(record["inputs"]["memberNumber"], "1")
            self.assertEqual(record["worstUtil"], 0.5)
            self.assertEqual(library.adopt_existing(), 0)

    def test_unknown_html_is_not_assumed_steel(self):
        with tempfile.TemporaryDirectory() as temporary:
            library = Library(temporary)
            (library.root / "Column-0001-260910 12-00-TEST.html").write_text("<p>Unknown</p>", encoding="utf-8")
            self.assertEqual(library.adopt_existing(), 0)

    def test_legacy_without_pdf_requires_explicit_save(self):
        with tempfile.TemporaryDirectory() as temporary:
            library = Library(temporary)
            saved = self.save(library)
            record = library.calculation(saved["calculationId"])
            del record["revisions"][0]["snapshotPath"]
            with self.assertRaisesRegex(ValueError, "explicitly save"):
                build_html(library, Mock(), [record["id"]], {})


if __name__ == "__main__":
    unittest.main()