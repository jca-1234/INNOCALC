"""Version register for the Plain Concrete Design module.

The newest entry is first.  Bump ``VERSION`` and add an entry here for every
change that reaches a user.
"""

VERSION = "0.1.0.dev0"

VERSION_HISTORY = [
    {
        "version": "0.1.0.dev0",
        "date": "2026-09-10",
        "author": "Automated transcription; engineering review outstanding",
        "summary": "First transcription of the retained PLAIN CONCRETE V5.02 workbook.",
        "changes": [
            "Section 20 footing bending capacity to Cl 20.4.2.",
            "One-way shear to Eq 20.4.3(1) and two-way punching shear to Cl 20.4.3(b) with the "
            "Eq 20.4.3(2) moment reduction and an optional manual shear perimeter.",
            "Unreinforced pedestal compressive and tensile stress checks to Cl 20.3, including "
            "the minimum eccentricity and its documented override.",
            "The Cl 20.4.1 minimum nominal depth reported as a utilisation.",
        ],
    },
]
