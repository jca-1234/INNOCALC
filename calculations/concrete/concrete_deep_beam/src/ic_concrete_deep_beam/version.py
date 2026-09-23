"""Version register for the Concrete Deep Beam Design module.

The newest entry is first.  Bump ``VERSION`` and add an entry here for every
change that reaches a user.
"""

VERSION = "0.1.0.dev0"

VERSION_HISTORY = [
    {
        "version": "0.1.0.dev0",
        "date": "2026-09-10",
        "author": "Automated transcription; engineering review outstanding",
        "summary": "First transcription of the retained DEEP BEAMS V5.02 workbook.",
        "changes": [
            "CEB span-to-depth applicability limits and effective lever arm z for simple, "
            "double, multi-span and cantilever deep beams.",
            "Serviceability stress limit fsi by crack control class and the effective design "
            "stress fsy.d = min(fsy / gamma_s, fsi).",
            "Positive and negative tension tie areas and their distribution over the 0.2 D and "
            "0.6 D zones.",
            "Diagonal compressive stress limit from the lesser of the depth and span forms.",
            "Web reinforcement mesh and bar spacing limits.",
            "External and internal support zone bearing capacity, each applied only to the span "
            "types the source workbook applies them to.",
            "The support width limit c <= L/5 reported as a utilisation.",
        ],
    },
]
