"""Standalone development harness for the Calculation Pad module.

    python -m cpd.dev                        the starter pad
    python -m cpd.dev pad.json               your own pad document
    python -m cpd.dev pad.json --trace       every resolved variable
    python -m cpd.dev pad.json --html out.html
    python -m cpd.dev pad.json --notebook out.ipynb
    python -m cpd.dev --validate             evaluator correctness and safety
"""

from __future__ import annotations

from packages.innocalc_sdk.dev import main as run

from . import headless, notebook


def main(argv: list[str] | None = None) -> int:
    return run(headless, argv, notebook_export=notebook.notebook_text)


if __name__ == "__main__":
    raise SystemExit(main())
