"""Project locks: byte-range locks that exclude other holders in this and other processes."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/manager"))

from icm import locking  # noqa: E402


def probe(path: Path) -> int:
    return subprocess.run([sys.executable, "-B", "-m", "icm.locking", "probe", str(path)],
                          cwd=ROOT / "apps/manager", capture_output=True, text=True,
                          timeout=30).returncode


class LockingTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / ".innocalc-library.lock"

    def tearDown(self):
        self.folder.cleanup()

    def test_other_process_is_refused_while_held_and_free_after(self):
        with locking.project_lock(self.path):
            self.assertEqual(probe(self.path), locking.EXIT_BUSY)
        self.assertEqual(probe(self.path), locking.EXIT_FREE)

    def test_second_holder_in_this_process_is_refused_without_releasing_the_first(self):
        with locking.project_lock(self.path):
            with self.assertRaisesRegex(ValueError, "Please retry"):
                with locking.project_lock(self.path):
                    pass
            # A refused attempt must not have dropped the lock held above.
            self.assertEqual(probe(self.path), locking.EXIT_BUSY)

    def test_lock_is_reusable_after_release(self):
        for _ in range(2):
            with locking.project_lock(self.path):
                pass
        self.assertEqual(locking.main(["probe", str(self.path)]), locking.EXIT_FREE)


if __name__ == "__main__":
    unittest.main()
