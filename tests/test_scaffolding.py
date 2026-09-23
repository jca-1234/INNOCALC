from __future__ import annotations

import ast
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from packages.innocalc_sdk.manifest import load_manifest
from tooling.scaffold import create_module

ROOT = Path(__file__).resolve().parents[1]


class ScaffoldingTests(unittest.TestCase):
    def test_generates_disabled_module_and_refuses_duplicates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "suite.toml").write_bytes((ROOT / "suite.toml").read_bytes())
            arguments = dict(module_id="test-member", name="Test Member", category="Steel",
                             standard="Test standard", filing_folder="TEST MEMBER", owner="Test engineer")
            folder = create_module(root, **arguments)
            for source in folder.rglob("*.py"):
                ast.parse(source.read_text(encoding="utf-8"))
            module = load_manifest(root)["modules"][-1]
            self.assertFalse(module["enabled"])
            self.assertTrue((folder / "src" / "ic_test_member" / "module.toml").is_file())
            environment = {**os.environ, "PYTHONPATH": os.pathsep.join((str(folder / "src"), str(ROOT)))}
            completed = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover",
                                        "-s", str(folder / "tests"), "-v"],
                                       cwd=root, env=environment, capture_output=True, text=True, timeout=30)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("not implemented", completed.stderr)
            self.assertIn("Engineering implementation and reference evidence required", completed.stderr)
            with self.assertRaisesRegex(ValueError, "already registered"):
                create_module(root, **arguments)

    def test_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            create_module(ROOT, module_id="../../bad", name="Bad", category="Steel",
                          standard="Test", filing_folder="Bad", owner="Test")