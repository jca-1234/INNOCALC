from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tooling.clean import clean


class CleanupTests(unittest.TestCase):
    def test_dry_run_and_apply_preserve_source_and_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "pyproject.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
            generated = ["build/lib/copy.py", "src/example.egg-info/PKG-INFO", "src/__pycache__/cache.pyc"]
            protected = ["src/engine.py", "reference/build/original.txt", ".venv/__pycache__/cache.pyc",
                         ".git/objects/keep", "artifacts/baseline.json", "data/projects.json"]
            for relative in generated + protected:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("keep", encoding="utf-8")
            expected = ["build", "src/__pycache__", "src/example.egg-info"]
            self.assertEqual(clean(root), expected)
            self.assertTrue(all((root / path).exists() for path in generated + protected))
            self.assertEqual(clean(root, apply=True), expected)
            self.assertTrue(all((root / path).exists() for path in protected))
            self.assertFalse(any((root / path).exists() for path in generated))
            self.assertEqual(clean(root, apply=True), [])