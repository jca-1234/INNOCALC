"""Standalone development harness for the Concrete Column Design module.

Lets the calculation be worked through with no InnoCalc Manager, no server and
no browser, and prints enough internal detail to compare against a reference
calculation while the module is being refined.

    python -m ccd.dev                          defaults, summary only
    python -m ccd.dev inputs.json              your own input document
    python -m ccd.dev inputs.json --trace      every internal value
    python -m ccd.dev --html out.html          write the calculation sheet
    python -m ccd.dev --validate               self check plus retained baseline
    python -m ccd.dev --validate cases.json    compare against worked examples

Use ``python -m ccd.validation`` for the full validation tool and its report.
"""

from __future__ import annotations

from packages.innocalc_sdk.dev import main as run

from . import headless
from . import validation


def main(argv: list[str] | None = None) -> int:
    return run(headless, argv, validation=validation.run_all)


if __name__ == "__main__":
    raise SystemExit(main())
