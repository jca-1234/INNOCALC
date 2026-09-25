"""Version register for the Concrete Punching Shear module.

The newest entry is first.  Bump ``VERSION`` and add an entry here for every
change that reaches a user.
"""

VERSION = "v0.0.1"

VERSION_HISTORY = [
    {
        "version": "v0.0.1",
        "date": "2026-09-24",
        "author": "Automated transcription; engineering review outstanding",
        "summary": "First transcription of the retained PUNCHING SHEAR V5.06 workbook.",
        "changes": [
            "Critical shear perimeter at dom/2 for rectangular and circular columns at "
            "internal, edge and corner positions, with the ineffective portion deducted.",
            "Spandrel-averaged mean depth dom solved by bisection in place of the workbook "
            "GoalSeek macro RecalcDom.",
            "Cl 9.3.3 strength without moment transfer, with and without a shear head.",
            "Cl 9.3.4 strength with moment transfer for cases (a) to (d), with the "
            "Cl 9.3.5 minimum fitment area and the Cl 9.3.6 spacing limit.",
            "Governing strength selected from the reinforcement provided, correcting the "
            "workbook's unranked set of OK / No Good results.",
            "Cl 6.10.4.5 minimum transferred moment applied when the slab is designed by the "
            "simplified method, and integrity reinforcement compared with the bars provided.",
            "Optional mean effective depth from the two reinforcement layers, following Tedds.",
        ],
    },
]
