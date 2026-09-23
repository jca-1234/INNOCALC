"""Version register for the Concrete Design Parameters module.

The newest entry is first.  Bump ``VERSION`` and add an entry here for every
change that reaches a user.
"""

VERSION = "0.1.0.dev0"

VERSION_HISTORY = [
    {
        "version": "0.1.0.dev0",
        "date": "2026-09-10",
        "author": "Automated transcription; engineering review outstanding",
        "summary": "First transcription of the retained FORMULA V5.02 workbook.",
        "changes": [
            "Rectangular stress block parameters to Eq 8.1.3(1), Eq 8.1.3(2), Eq 10.6.2.2, "
            "Eq 10.6.2.5(1) and Eq 10.6.2.5(2), with the AS 3600:2009 alpha2 shown alongside.",
            "Mean in-situ compressive strength from AS 3600 Table 3.1.2, from the workbook's own "
            "curve fit and from AS 2327:2017 Table 3.6.2.3.",
            "Modulus of elasticity to Cl 3.1.2 and characteristic flexural tensile strength to "
            "Cl 3.1.1.3.",
            "Strength gain with age from the workbook's normal and high early cement table.",
            "Optional deemed-to-comply minimum flexural reinforcement to Cl 8.1.6.1 and Cl 9.1.1.",
            "Optional minimum cracking moment 1.2 Z f'ct.f.",
        ],
    },
]
