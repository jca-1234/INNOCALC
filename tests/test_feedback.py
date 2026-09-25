from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/manager"))

from icm.feedback import FeedbackStore

USER = {"email": "pat.user@innovis.com.au", "displayName": "Pat User"}
ADMIN = {"email": "sam.admin@innovis.com.au", "displayName": "Sam Admin"}


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.store = FeedbackStore(Path(self.folder.name) / "feedback.json")

    def tearDown(self):
        self.folder.cleanup()

    def test_references_are_numbered_per_kind(self):
        first = self.store.submit({"kind": "bug", "title": "A", "description": "a"}, USER)
        idea = self.store.submit({"kind": "improvement", "title": "B", "description": "b"}, USER)
        second = self.store.submit({"kind": "bug", "title": "C", "description": "c"}, USER)
        self.assertEqual([first["reference"], idea["reference"], second["reference"]],
                         ["BUG-0001", "IMP-0001", "BUG-0002"])
        self.assertEqual(len(self.store.reports(kind="bug")), 2)

    def test_incomplete_report_refused(self):
        with self.assertRaises(ValueError):
            self.store.submit({"kind": "bug", "title": "", "description": "x"}, USER)
        with self.assertRaises(ValueError):
            self.store.submit({"kind": "rant", "title": "x", "description": "x"}, USER)

    def test_vote_toggles_and_triage_is_recorded(self):
        report = self.store.submit({"kind": "bug", "title": "A", "description": "a"}, USER)
        self.assertEqual(self.store.vote(report["id"], ADMIN)["votes"], [ADMIN["email"]])
        self.assertEqual(self.store.vote(report["id"], ADMIN)["votes"], [])
        updated = self.store.update(report["id"], {"status": "done", "response": "Fixed"}, ADMIN)
        self.assertEqual(updated["status"], "done")
        self.assertEqual(updated["history"][0]["by"], "Sam Admin")
        with self.assertRaises(ValueError):
            self.store.update(report["id"], {"status": "maybe"}, ADMIN)

    def test_csv_neutralises_formulas(self):
        self.store.submit({"kind": "bug", "title": "=HYPERLINK(\"x\")", "description": "a"}, USER)
        self.assertIn("'=HYPERLINK", self.store.as_csv())


if __name__ == "__main__":
    unittest.main()
