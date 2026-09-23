from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/manager"))

from icm.library import Library


class ProcessLockTests(unittest.TestCase):
    def test_another_process_cannot_overwrite_locked_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            library = Library(temporary)
            code = ("import sys; from pathlib import Path; "
                    "sys.path.insert(0, str(Path(sys.argv[1]) / 'apps/manager')); "
                    "from icm.library import Library; Library(sys.argv[2]).add_package('Child')")
            with library.transaction():
                completed = subprocess.run([sys.executable, "-B", "-c", code, str(ROOT), temporary],
                                           capture_output=True, text=True, timeout=15)
                self.assertNotEqual(completed.returncode, 0)
                self.assertIn("Please retry", completed.stderr)
                library.add_package("Parent")
            completed = subprocess.run([sys.executable, "-B", "-c", code, str(ROOT), temporary],
                                       capture_output=True, text=True, timeout=15)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue({"Parent", "Child"}.issubset(Library(temporary).data["packages"]))