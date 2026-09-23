"""Standalone development harness for the Steel Member Design module.

Lets the calculation be worked through with no InnoCalc Manager, no server and
no browser, and prints enough internal detail to compare against a reference
calculation while the module is being refined.

    python -m smd.dev                          defaults, summary only
    python -m smd.dev inputs.json              your own input document
    python -m smd.dev inputs.json --trace      every internal value
    python -m smd.dev --html out.html          write the calculation sheet
    python -m smd.dev --pdf  out.pdf           write the sheet as PDF
    python -m smd.dev --validate               self-consistency over the catalogue
    python -m smd.dev --validate cases.json    compare against worked examples
"""

from __future__ import annotations

from packages.innocalc_sdk.dev import main as run

from . import headless


def main(argv: list[str] | None = None) -> int:
    return run(headless, argv)


if __name__ == "__main__":
    raise SystemExit(main())
