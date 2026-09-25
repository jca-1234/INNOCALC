"""Version register for InnoCalc Manager.

Versions are ``vMajor.Patch.Minor`` (packages/innocalc_sdk/versioning.py).  The
newest entry is first; bump ``VERSION`` and add an entry for every change that
reaches a user.  Entries before v0.0.1 keep their old numbers, marked legacy.
"""

VERSION = "v0.0.1"

VERSION_HISTORY = [
    {
        "version": "v0.0.1",
        "date": "2026-09-24",
        "author": "JA",
        "summary": "Numbering restarted at v0.0.1 (vMajor.Patch.Minor) for the software and "
                   "every calculation module, and the application is now called InnoCalc.",
        "changes": [
            "Show superseded on the Calculation Index now lists every earlier revision, "
            "greyed, beneath the current one, with its PDF, folder and a View link.",
            "Projects opens as its own page instead of a pop-up window.",
            "Sign in by choosing your name from a list, or create a new username; no email "
            "address is asked for until Office 365 sign-on arrives on the server.",
            "Feedback page: report a bug or suggest an improvement, see what others have "
            "raised and add 'Me too'; admins triage, respond and export to CSV.",
            "Package Export and Verification are limited to admins until PDF export passes "
            "its check.",
            "New InnoCalc visual style, matching InnoResource.",
            "Nothing stored holds a Windows drive letter any more, ready for the server; "
            "'python -m icm.merge' combines every PC's project list and people.",
            "Steel, Concrete Column and Calculation Pad are pinned in the suite as submodules.",
        ],
    },
    {
        "version": "legacy V0.04",
        "date": "2026-09-24",
        "author": "JA",
        "summary": "Prepared to run on the shared application server behind the reverse "
                   "proxy; no change when run from your PC.",
        "changes": [
            "A preview copy is read-only: saving and every other write to the projects "
            "drive is refused, and the toolbar says so.",
            "Tabs and calculation modules that are not ready can be limited to admins by a "
            "setting rather than held back in code.",
            "On the server the folder picker and Explorer are unavailable and every folder "
            "must be under the projects root.",
            "The manager's own data is backed up automatically and can be restored with a "
            "checked command; a health page reports whether the service is usable.",
        ],
    },
    {
        "version": "legacy V0.03",
        "date": "2026-09-02",
        "author": "JA",
        "summary": "Fixed the 'Server error (200)' raised when opening or calculating a "
                   "Concrete Column Design.",
        "changes": [
            "A utilisation of infinity - a member with no demand or no capacity - is a real "
            "result, but it was written into the reply as a value no browser can read, so "
            "the whole calculation came back as 'Server error (200)'. Infinities and NaN are "
            "now sent as no value, and every reply is checked before it leaves the server.",
        ],
    },
    {
        "version": "legacy V0.02",
        "date": "2026-09-01",
        "author": "JA",
        "summary": "Head unit changes: faster saving, a navigable module tree, a working "
                   "Calculation Index, and issued packages that are watermarked, flattened "
                   "and recorded.",
        "changes": [
            "New calculation is now offered on the calculation page as well as the index.",
            "Saving returns as soon as the calculation is on the drive; the sheet is printed "
            "on a background worker and the toolbar shows Saving, Printing PDF and the "
            "result, so a slow print no longer looks like a hung save.",
            "New calculation chooser is a discipline navigation tree - Favourites, Load "
            "Calculations, Timber, Insitu Concrete, Precast Concrete, Temporary Works, "
            "Steel, Glass, Fibres, Composite, Foundations, Retaining wall, Analysis - with "
            "a search and per-person favourites. A module declares its branch in one line.",
            "'Checked by' can no longer be typed: it is written from the verifier's initials "
            "when they endorse the verification package the calculation was issued in.",
            "Projects: type the project number and the folder, client reference and project "
            "name are found for you; search by project name as well as number; a folder "
            "chosen below the project's own level reverts to the top of the project; the "
            "folder and Innovis sub-folders are always created, so the check box has gone; "
            "Remove and Archive now work; Relink re-addresses a broken folder link.",
            "Library renamed Calculation Index. Package, level and a new searchable "
            "description are edited in the table; filters are multi-select dropdowns with a "
            "sort; PDF and folder symbols open the calculation and its folder; superseded "
            "rows are greyed.",
            "Import PDF calculation indexes a calculation prepared in other software; it "
            "takes its place in the index, in packages and in verification.",
            "Package Export: one tidy input row with a longer title, Reason for issue "
            "(Internal Review, Verification, Certification, Preliminary Check, Status Print "
            "or free text) and the person to issue to. The package folder opens on export.",
            "An issued package is watermarked 'PACKAGE PREPARED DD/MM/YYYY FOR <purpose>' in "
            "red at the bottom right of every sheet and is permanently flattened, so it "
            "cannot be edited but still takes the verifier's markups.",
            "Drawings are issued twice: as a standalone flattened "
            "'JXXXX-STR-VER-YYYY - TITLE - DRAWINGS - INITIALS.pdf', and appended to the "
            "rear of the combined document.",
            "Every issue is recorded in a project issue register with its reason, date of "
            "issue and PDF and folder links.",
            "Issuing a package or a verification package raises a draft email to the "
            "reviewer with links to the package.",
            "The Verification tab reads any marked-up PDF the verifier has returned to the "
            "package folder on every refresh, so returned comments appear without an import.",
            "Imported PDF calculations, drawing sets and Bluebeam inserts are spliced into "
            "their proper place in a package, and the contents page links survive it.",
        ],
    },
    {
        "version": "legacy V0.01",
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
