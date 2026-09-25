"""Version register for the Concrete Industrial Pavement module.

The newest entry is first.  Bump ``VERSION`` and add an entry here for every
change that reaches a user.
"""

VERSION = "v0.0.1"

VERSION_HISTORY = [
    {
        "version": "v0.0.1",
        "date": "2026-09-24",
        "author": "Automated transcription; engineering review outstanding",
        "summary": "First transcription of the retained INDUSTRIAL FLOOR SLABS V5.07 workbook.",
        "changes": [
            "Chandler (C&CA TR550) point-load stresses: Westergaard internal, Kelley edge and "
            "Pickett corner, with the digitised adjacent-load stress-increase curves.",
            "Rack post bearing (AS 3600 Cl 12.6) and punching shear (AS 3600 Cl 9.3.3) at "
            "internal, edge and corner positions.",
            "Forklift single and dual axle wheel stresses with the T48 load repetition factor.",
            "Uniform load checks: C&CA Cl 5.6.3 variable layout and Hetenyi patterned aisle, "
            "both now counted in the governing utilisation.",
            "Shrinkage reinforcement by AS 3600, T48 Appendix F and Austroads subgrade drag.",
            "Optional custom point-load layout (workbook Custom tab) and an optional load "
            "position applicability check adopted from the generic Tedds ground-floor approach.",
        ],
    },
]
