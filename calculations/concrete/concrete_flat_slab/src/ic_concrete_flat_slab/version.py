"""Version register for the Concrete Flat Slab module.

The newest entry is first.  Bump ``VERSION`` and add an entry here for every
change that reaches a user.
"""

VERSION = "v0.0.1"

VERSION_HISTORY = [
    {
        "version": "v0.0.1",
        "date": "2026-09-24",
        "author": "Automated transcription; engineering review outstanding",
        "summary": "First transcription of the retained FLAT SLABS V5.04 workbook.",
        "changes": [
            "AS/NZS 1170.0 strength combination and Table 4.1 serviceability factors.",
            "Cl 6.10.4.2 total static moments for the interior and edge design strips, with "
            "the workbook's support-length table and the Lo >= 0.65 L lower limit.",
            "Table 6.10.4.3 moment coefficients and Table 6.9.5.3 column and middle strip "
            "distribution, per strip and per metre.",
            "Cl 9.1.1(a) minimum strength reinforcement reported as a utilisation.",
            "Cl 9.4.4.1 deemed-to-comply span-to-depth check using the effective span Lef, "
            "with the workbook's Lo-based values retained for comparison.",
            "Cl 6.10.4.1 applicability rules (span ratio, live load, Class N) in worstUtil.",
            "Cl 6.10.4.5 moment transferred to interior columns for punching shear.",
            "Optional flexure, shrinkage, custom support and custom distribution groups.",
        ],
    },
]
