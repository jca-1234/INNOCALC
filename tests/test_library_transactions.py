from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/manager"))

from icm.library import Library
from icm.locking import project_lock
from icm.qa import QAStore


def save_example(library, number):
    return library.save(module_id="example", module_folder="Example", inputs={},
                        identity={"memberType": "Beam", "memberNumber": number, "package": "P01"},
                        summary={"worstUtil": 0.5, "status": "OK"},
                        html_text="<p>Example</p>", initials="TEST")


class LibraryTransactions(unittest.TestCase):
    def test_qa_update_preserves_concurrent_calculation(self):
        with tempfile.TemporaryDirectory() as temporary:
            first = Library(temporary)
            first.data["qaPackages"] = [{"id": "qa", "comments": []}]
            first.write()
            stale = Library(temporary)
            save_example(first, "1")
            store = QAStore(stale, {})
            with patch.object(store, "_write_documents"):
                store.add_comment("qa", {"comment": "Review"}, {"initials": "TEST"})
            persisted = Library(temporary).data
            self.assertEqual(len(persisted["calculations"]), 1)
            self.assertEqual(len(persisted["qaPackages"][0]["comments"]), 1)

    def test_stale_instances_preserve_both_saves(self):
        with tempfile.TemporaryDirectory() as temporary:
            first, second = Library(temporary), Library(temporary)
            save_example(first, "1")
            save_example(second, "2")
            records = Library(temporary).data["calculations"]
            self.assertEqual({record["memberNumber"] for record in records}, {"0001", "0002"})

    def test_direct_stale_write_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            first, second = Library(temporary), Library(temporary)
            first.add_package("First")
            second.data["qaPackages"].append({"id": "second"})
            with self.assertRaisesRegex(ValueError, "Refresh"):
                second.write()
            self.assertIn("First", Library(temporary).data["packages"])

    def test_lock_contention_is_retryable(self):
        with tempfile.TemporaryDirectory() as temporary:
            library = Library(temporary)
            with project_lock(library.root / ".innocalc-library.lock"):
                with self.assertRaisesRegex(ValueError, "retry"):
                    library.add_package("Blocked")

    def test_corrupt_index_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            library = Library(temporary)
            library.path.write_text("{broken", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "damaged"):
                Library(temporary)
            self.assertEqual(library.path.read_text(encoding="utf-8"), "{broken")

    def test_failed_transaction_does_not_write_index(self):
        with tempfile.TemporaryDirectory() as temporary:
            library = Library(temporary)
            library.add_package("Before")
            with self.assertRaises(RuntimeError):
                with library.transaction():
                    library.add_package("After")
                    raise RuntimeError("Abort")
            self.assertNotIn("After", json.loads(library.path.read_bytes())["packages"])

    def test_show_superseded_lists_earlier_revisions(self):
        with tempfile.TemporaryDirectory() as temporary:
            library = Library(temporary)
            save_example(library, "1")
            save_example(library, "1")
            hidden = library.index()["calculations"]
            self.assertEqual(len(hidden), 1)
            self.assertEqual(hidden[0]["history"], [])
            shown = library.index(show_superseded=True)["calculations"]
            self.assertEqual([item["rev"] for item in shown[0]["history"]], [1])
            self.assertTrue(shown[0]["history"][0]["superseded"])
            self.assertTrue(Path(shown[0]["history"][0]["htmlPath"]).is_file())
            self.assertFalse(shown[0]["superseded"])


if __name__ == "__main__":
    unittest.main()