"""Version register for the Concrete Stair Design module.

The newest entry is first.  Bump ``VERSION`` and add an entry here for every
change that reaches a user.
"""

VERSION = "0.1.0.dev0"

VERSION_HISTORY = [
    {
        "version": "0.1.0.dev0",
        "date": "2026-09-11",
        "author": "Automated transcription; engineering review outstanding",
        "summary": "First transcription of the retained CONCRETE STAIRS V5.06 workbook.",
        "changes": [
            "Stepped profile geometry: hypotenuse of the riser and going, the average thickness "
            "and the vertical average thickness factor f.",
            "Self weight from the average thickness and the AS/NZS 1170.0 strength combinations.",
            "Section 9 bending capacity per metre width with Eq 8.1.3(1) and Eq 8.1.3(2) stress "
            "block factors and the Table 2.2.2(b) capacity reduction factor.",
            "Minimum reinforcement to Eq 8.1.6.1(2) and the Cl 8.1.5 ductility limit on kuo.",
            "Cl 9.4.4 deemed-to-comply minimum thickness including the v5.06 inclined deflection "
            "modifier, for both the total and the incremental deflection limits.",
            "Cracked neutral axis, modular ratio and the Cl 8.5.3.2 kcs factor, including the "
            "workbook's rule that compression steel in tension is ignored.",
        ],
    },
]
