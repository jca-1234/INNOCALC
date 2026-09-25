"""Version register for the Concrete Two-Way Slab module.

The newest entry is first.  Bump ``VERSION`` and add an entry here for every
change that reaches a user.
"""

VERSION = "v0.0.1"

VERSION_HISTORY = [
    {
        "version": "v0.0.1",
        "date": "2026-09-24",
        "author": "Automated transcription; engineering review outstanding",
        "summary": "First transcription of the retained TWO-WAY SLABS V5.02 workbook.",
        "changes": [
            "AS/NZS 1170.0 strength combination and Table 4.1 serviceability factors.",
            "Cl 6.10.3.2 positive and negative design moments from Table 6.10.3.2(A), "
            "Table 6.10.3.2(B) or the closed-form coefficients, with the workbook's "
            "Ly/Lx interpolation.",
            "Cl 9.1.1(b) minimum strength reinforcement reported as a utilisation.",
            "Deemed-to-comply span-to-depth check for total and incremental deflection "
            "with the Table 9.4.4.2 k4 interpolation.",
            "Live load not exceeding the dead load compared against the dead load only, "
            "correcting the workbook's double count of superimposed dead load.",
        ],
    },
]
