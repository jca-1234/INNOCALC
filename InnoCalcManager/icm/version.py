"""Version register for InnoCalc Manager.

The newest entry is first.  Bump ``VERSION`` and add an entry for every change
that reaches a user.
"""

VERSION = "V0.01"

VERSION_HISTORY = [
    {
        "version": "V0.01",
        "date": "2026-09-01",
        "author": "JA",
        "summary": "First release of the calculation management head application.",
        "changes": [
            "Calculation management landing page over a registry of design modules.",
            "Front end fully separated from the calculation back end: every module form is "
            "built from a schema the module publishes, so a new module needs no front-end work.",
            "Steel Member Design, Concrete Column Design and Calculation Pad hosted headlessly.",
            "Durable project registry with reliable create, open, switch, archive and restore; "
            "project discovery now runs in the background with a deadline instead of blocking.",
            "Calculation library per project with package, level, module and free-text search.",
            "Unsaved-change prompt before leaving a calculation or switching project.",
            "Passwords removed entirely; Office 365 single sign-on scaffolded but not activated.",
            "Package export: filter and order by package, member type, level and calculation "
            "type, then print one PDF with a linked contents page and a Contents link on "
            "every sheet.",
            "QA verification packages filed to 06-QA\\03-Verification\\YYMMDD - TITLE - REVIEWER "
            "with the Innovis verification form and a tracked comment register.",
            "Deferred comments carry forward to later calculation packages.",
        ],
    },
]


def current():
    return VERSION_HISTORY[0]
