"""Version register for the Concrete Strut-and-Tie module.

The newest entry is first.  Bump ``VERSION`` and add an entry here for every
change that reaches a user.
"""

VERSION = "v0.0.1"

VERSION_HISTORY = [
    {
        "version": "v0.0.1",
        "date": "2026-09-24",
        "author": "Automated transcription; engineering review outstanding",
        "summary": "First transcription of the retained STRUT & TIE V5.04 workbook.",
        "changes": [
            "Fig 7.2.4(A) strut geometry with the FindAngle GoalSeek replaced by a bounded "
            "scan and bisection.",
            "Cl 7.2 strut capacity, Cl 7.2.4 bursting reinforcement for strength, "
            "serviceability and cracking, Cl 7.3 tie, Cl 7.4.2 node and Cl 12.6 bearing.",
            "Support length, strut angle, angle compatibility and vertical-load steel "
            "errors now count towards worstUtil.",
            "Development length limits f'c to 65 MPa and applies the slip-form factor.",
            "Optional nodal face stress check computed from the strut, bearing and tie forces.",
        ],
    },
]
