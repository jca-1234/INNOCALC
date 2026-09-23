"""Version register for the Concrete Corbel Design module.

The newest entry is first.  Bump ``VERSION`` and add an entry here for every
change that reaches a user.
"""

VERSION = "0.1.0.dev0"

VERSION_HISTORY = [
    {
        "version": "0.1.0.dev0",
        "date": "2026-09-10",
        "author": "Automated transcription; engineering review outstanding",
        "summary": "First transcription of the retained CORBEL V5.06 workbook.",
        "changes": [
            "AS/NZS 1170.0 strength combinations for the vertical and horizontal corbel actions.",
            "Bearing at the corbel node to Cl 7.4.2 with the Cl 7.4.2(b) CCT node coefficient.",
            "Interface shear friction to Cl 8.4.3 including the permanent clamping action gp.",
            "Compression strut to Cl 7.2.3 with the strut width solved so the strut is fully "
            "utilised, replacing the workbook's Excel GoalSeek macro with a bounded bisection.",
            "Horizontal tensile tie to Cl 7.3.2 using the solved strut depth.",
            "Minimum flexural reinforcement to Eq 8.1.6.1(2), the Dmin = 1.7 av depth limit and "
            "the strut width across the supporting wall reported as utilisations.",
        ],
    },
]