from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps/manager"))
os.environ["CPD_NO_AUTO_INSTALL"] = "1"

from icm.registry import Registry
from packages.innocalc_sdk import check_contract, load_manifest


class SDKTests(unittest.TestCase):
    def test_current_modules_meet_basic_contract(self):
        registry = Registry()
        self.assertFalse(registry.problems)
        self.assertEqual(len(registry.modules), len([module for module in load_manifest(ROOT)["modules"] if module["enabled"]]))
        for module in registry.modules.values():
            with self.subTest(module=module.id):
                report = check_contract(module.adapter)
                self.assertTrue(report["ok"], report["failures"])

    def test_duplicate_manifest_identity_is_rejected(self):
        source = (ROOT / "suite.toml").read_text(encoding="utf-8")
        source = source.replace('id = "concrete-column"', 'id = "steel-member"')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "suite.toml").write_text(source, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                load_manifest(root)


if __name__ == "__main__":
    unittest.main()