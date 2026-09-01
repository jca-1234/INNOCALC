# InnoCalc Manager

Calculation management for Innovis projects. It is the landing page for a project's
calculations: pick a project, see everything calculated on it, start a new calculation in any
module, collate finalised calculations into a single verified PDF package, and run the QA
verification process.

```
start.bat                 →  http://127.0.0.1:8125/
```

The service binds to localhost only and uses the Python standard library plus the optional
`pypdf` package.

| Setting | Default | Purpose |
|---------|---------|---------|
| `ICM_ROOT` | `J:\Active Projects` | Projects root used for project discovery. |
| `ICM_PORT` | `8125` | Listening port. |
| `ICM_DATA_DIR` | `./data` | People directory, project registry and folder index. |
| `ICM_SSO_ENABLED` | `0` | Office 365 sign-on. **Leave at 0.** |
| `ICM_SSO_TENANT`, `ICM_SSO_CLIENT_ID` | – | Entra ID application, needed only when SSO is enabled. |

---

## The separation

The front end holds no engineering knowledge whatsoever. It asks each module for a schema and
builds the input form from it, then displays the HTML the module returns. Adding a design
module therefore requires **one line** in `icm/registry.py` and no front-end work at all.

```
InnoCalcManager           head application: projects, library, packages, QA
  icm/registry.py         loads the design modules through the headless contract
calcpad/                  shared presentation, notation, PDF export, trace
SteelMemberDesign/smd     headless calculation module
ConcreteColumnDesign/ccd  headless calculation module
CalculationPad/cpd        headless calculation module
```

The contract is specified in [`docs/MODULE-SPECIFICATION.md`](../docs/MODULE-SPECIFICATION.md).

---

## What it does

### Projects
* Durable per-person project list with **Active** and **Archived** groups, most recently opened
  first, and a stable project id that does not depend on path spelling or case.
* **Add or create** a project from any folder; optionally create the Innovis folder skeleton
  (`09-Doc_WRK\01-CAL\10-IN_TOOL` and `06-QA\03-Verification`).
* **Find** by project number resolves from a durable index, then from the expected 100-block
  folder. It never blocks: if neither answers, a background scan starts with a hard deadline
  and the interface says so. This is what the previous tool got wrong — a miss triggered a
  synchronous walk of the whole network drive on the request thread.
* Archive, restore and remove-from-my-list. Removing never touches the folder.
* Project team: designers and verifiers, used for QA package access.

### Calculation library
* Every calculation from every module in one index, stored **inside the project folder**
  (`…\10-IN_TOOL\innocalc-library.json`), so it survives loss of the app's own data.
* Navigate by package and member type in the tree, or filter by package, level, module and
  calculation type and search across every field.
* Full revision history: saving supersedes the previous revision and moves it to
  `superseded\`, exactly as the standalone steel tool did.
* Inputs are stored with the record, so reopening a calculation is instant.
* **Import existing** adopts calculations filed by the standalone tools.
* **Link** sends one calculation's published values into another module.

### Leaving a calculation
Navigating away, switching project, opening another calculation or closing the tab with
unsaved changes prompts **Save / Discard / Stay**. `Ctrl+S` saves.

### Package export
Filter by package, level, member type and calculation type; order by up to three of those
keys; select what goes in; then build one PDF containing:

* a **Calculation Index** sheet listing every calculation with package, level, type, status,
  utilisation, governing check, revision and start sheet number, each linked to its sheet;
* every calculation sheet, each carrying a **Contents** link back to the index;
* any PDF drawings or Bluebeam markups inserted by Calculation Pad cells;
* an optional combined drawing review set appended.

The body is printed as one document by headless Chromium, so the links are real PDF links.

### Verification and QA
**New verification package** files everything to

```
06-QA\03-Verification\YYMMDD - TITLE - REVIEWER\
    Calculations.pdf
    Verification Form.html / .pdf
    Comment Register.html / .csv
    Comment Register - FINAL.html      (written on endorsement)
    package.json
```

* The **verification form** is the Innovis form: documents to be verified, verification
  method, designer's statement, verification comments, action and endorsement.
* The **comment register** tracks verifier comment → designer response → agreed outcome →
  status (`Open`, `Noted`, `Deferred`, `Closed`) with a change history.
* **Import verifier markups** reads PDF annotations from the returned marked-up PDF, which is
  how Bluebeam Revu comments come back.
* Only the **nominated verifier** may endorse. Endorsement is refused while comments are
  neither closed nor deferred, writes the final register and links it from the form.
* **Deferred** comments are carried into the next verification package for that project.
* **Status across projects** reports packages, endorsements, open and deferred comments for
  every project in your list — the basis for the future business-wide QA review.

### Sign-in
There are no passwords anywhere in this release. You identify yourself with your Innovis
email address; the directory keeps your display name and initials so calculations stay
attributable.

Office 365 single sign-on is fully written in `icm/auth.py` — configuration, PKCE, the
authorise URL and the redirect handler — and is **deliberately inactive**. To demonstrate it:

```
set ICM_SSO_ENABLED=1
set ICM_SSO_TENANT=<tenant id>
set ICM_SSO_CLIENT_ID=<application id>
```

with `http://127.0.0.1:8125/auth/sso/callback` registered as a redirect URI. Nothing else in
the application changes.

---

## API

All JSON, localhost only, `token` carried in the body or query string.

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/api/ping` | Version, projects root, loaded modules, PDF tooling, sign-in mode. |
| GET | `/api/auth/config` | Sign-in mode and the people directory. |
| POST | `/api/auth/signin` `/api/auth/signout` | Session. |
| GET | `/api/modules` | Loaded modules and any that failed to load. |
| GET | `/api/module/schema?module=` | Input schema and defaults. |
| GET | `/api/projects` | Your projects plus discovery status. |
| POST | `/api/projects/create` `open` `find` `refresh` `archive` `forget` `rename` `people` `adopt` | Project lifecycle. |
| GET | `/api/library?project=…` | Calculation library, filtered. |
| GET | `/api/calculation?project=&id=` | One calculation with its inputs. |
| POST | `/api/calculate` | Compute and render without saving. |
| POST | `/api/calculation/save` `update` `delete` `exchange` | Library operations. |
| POST | `/api/module/action` `/api/module/validate` | Module actions and self-validation. |
| POST | `/api/package/preview` `/api/package/build` | Collation. |
| GET | `/api/qa?project=` `/api/qa/status` | Verification record. |
| POST | `/api/qa/create` `update` `comment/add` `comment/update` `markups` `endorse` `export` | Verification workflow. |
| GET | `/api/file?path=` | Stream a generated file. Restricted to registered project folders. |
| GET | `/api/browse` `/api/files` `/api/pick` | Filesystem helpers. |

---

## Requirements

* Windows, Python 3.11 or later.
* Microsoft Edge or Google Chrome, for PDF export.
* `pypdf` (`pip install pypdf`) to combine drawing sets and PDF inserts. Without it the
  calculation body still exports; attachments are skipped.
