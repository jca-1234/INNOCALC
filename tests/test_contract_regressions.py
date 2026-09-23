from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT, ROOT / "apps/manager", ROOT / "calculations/steel/member"):
    sys.path.insert(0, str(folder))

from icm.registry import REQUIRED, Registry
from smd import headless
from smd.engine import _ratio


class SteelContractTests(unittest.TestCase):
    def test_invalid_moment_is_rejected(self):
        for value in ("not-a-number", None, math.nan, math.inf):
            with self.subTest(value=value):
                inputs = headless.defaults()
                inputs["Mx"] = value
                with self.assertRaisesRegex(ValueError, "Mx"):
                    headless.compute(inputs)

    def test_unattainable_capacity_fails(self):
        self.assertEqual(_ratio(100.0, 0.0), math.inf)
        self.assertEqual(_ratio(0.0, 0.0), 0.0)
        summary = headless.summarise({"util": {"bendingX": math.inf}})
        self.assertEqual(summary["status"], "FAIL")
        self.assertEqual(summary["criticalCheck"], "Bending x")

    def test_defaults_still_compute(self):
        self.assertEqual(headless.summarise(headless.compute(headless.defaults()))["status"], "OK")


class RegistryTests(unittest.TestCase):
    def test_duplicate_id_is_reported_without_overwrite(self):
        functions = {name: lambda *args, **kwargs: {} for name in REQUIRED}
        functions["descriptor"] = lambda: {
            "id": "duplicate", "name": "Example", "folder": "Example"}
        sources = [{"folder": "calculations/general/calculation_pad", "entry": "first.headless"},
                   {"folder": "calculations/concrete/column", "entry": "second.headless"}]
        with patch("icm.registry.importlib.import_module", return_value=SimpleNamespace(**functions)):
            registry = Registry(sources=sources, root=ROOT)
        self.assertEqual(registry.get("duplicate").entry, "first.headless")
        self.assertEqual(len(registry.problems), 1)
        self.assertIn("duplicate", registry.problems[0]["error"].lower())


if __name__ == "__main__":
    unittest.main()