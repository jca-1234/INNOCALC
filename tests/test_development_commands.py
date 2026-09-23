from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tooling.__main__ import main


class DevelopmentTests(unittest.TestCase):
    def test_shared_runner_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "sheet.html"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["dev", "calculation-pad", "--html", str(output), "--trace"]), 0)
            self.assertIn('class="calc-page"', output.read_text(encoding="utf-8"))

    def test_schema(self):
        with contextlib.redirect_stdout(io.StringIO()) as captured:
            self.assertEqual(main(["dev", "steel-member", "--schema"]), 0)
        self.assertEqual(json.loads(captured.getvalue())["id"], "steel-member")

    def test_pad_never_installs_on_open(self):
        from cpd import environment, headless
        with patch.object(environment, "_report", None), patch.object(environment, "_importable", return_value=False), patch("subprocess.run") as install:
            headless.schema()
            install.assert_not_called()
            with self.assertRaisesRegex(ValueError, "libraries are missing"):
                headless.compute(headless.defaults())