# InnoCalc Manager

Calculation management for Innovis projects. It is the landing page for a project's
calculations: pick a project, see everything calculated on it, start a new calculation in any
module, collate finalised calculations into a single verified PDF package, and run the QA
verification process.

```
start.bat                 →  http://127.0.0.1:8125/
```

By default the service binds to localhost and uses the Python standard library plus the
optional `pypdf` package. It is also prepared to run as a tenant of the shared internal
application host; see [Running on the application host](#running-on-the-application-host).

| Setting | Default | Purpose |
|---------|---------|---------|
| `ICM_ROOT` | `J:\Active Projects` | Projects root used for project discovery. |
| `ICM_HOST` | `127.0.0.1` | Listening address. Anything but loopback is server mode. |
| `ICM_PORT` | `8125` | Listening port. |
| `ICM_DATA_DIR` | `./data` | People directory, project registry and folder index. |
| `ICM_BACKUP_DIR` | `../backups` beside the data folder | Snapshots of the data folder. |
| `ICM_SSO_ENABLED` | `0` | In-app Office 365 sign-on. **Leave at 0.** |
| `ICM_SSO_TENANT`, `ICM_SSO_CLIENT_ID` | – | Entra ID application, needed only when SSO is enabled. |

The deployment settings (`ICM_AUTH_MODE`, `ICM_TRUSTED_PROXIES`, `ICM_ALLOWED_HOSTS`,
`ICM_HTTPS`, `ICM_READ_ONLY`, `ICM_TAB_ACCESS`, `ICM_MODULE_ACCESS`, `ICM_ADMINS`, backup
interval and retention, `INNOCALC_BROWSER`) are described in
[`../../.env.example`](../../.env.example). An invalid value stops the service at start with
the reason.

---

## The separation

The front end holds no engineering knowledge whatsoever. It asks each module for a schema and
builds the input form from it, then displays the HTML the module returns. Adding a design
module therefore requires **one manifest entry** in `../../suite.toml` and no front-end work at all.

```
apps/manager           head application: projects, library, packages, QA
  icm/registry.py         loads the design modules through the headless contract
packages/calcpad/         shared presentation, notation, PDF export, trace
calculations/steel/member/smd     headless calculation module
calculations/concrete/column/ccd  headless calculation module
calculations/general/calculation_pad/src/cpd    headless calculation module (src-layout pilot)
```

The contract is specified in [`docs/MODULE-SPECIFICATION.md`](../../docs/MODULE-SPECIFICATION.md).
To commission a new module, fill in [`docs/NEW-MODULE-BRIEF.md`](../../docs/NEW-MODULE-BRIEF.md) and
hand it to an AI assistant working in this repository. The only manager-side change is one
entry in `suite.toml` naming the source path, entry point, permanent filing name and
discipline. Use `python -m tooling new` from the suite root; see `../../docs/DEVELOPMENT.md`.

---

## What it does

### Projects
* Durable per-person project list with **Active** and **Archived** groups, most recently opened
  first, and a stable project id that does not depend on path spelling or case.
* **Add or create**: type the project number and the folder, client reference and project name
  are read from the drive. The project folder and the Innovis skeleton
  (`09-Doc_WRK\01-CAL\10-IN_TOOL` and `06-QA\03-Verification`) are always created if missing.
  A folder chosen below the project's own level reverts to `…\JXXXX - CLIENT - PROJECT NAME`.
* **Find** by project number or by any part of the client or project name. It resolves from a
  durable index, then from the expected 100-block folder. It never blocks: if neither answers, a
  background scan starts with a hard deadline and the interface says so. This is what the
  previous tool got wrong — a miss triggered a synchronous walk of the whole network drive on
  the request thread.
* Archive, restore and remove-from-my-list. Removing never touches the folder.
* **Relink** re-addresses a project whose folder has been moved, renamed or broken.
* Project team: designers and verifiers, used for QA package access.

### Calculation Index
* Every calculation from every module in one index, stored **inside the project folder**
  (`…\10-IN_TOOL\innocalc-library.json`), so it survives loss of the app's own data.
* Navigate by package and member type in the tree, or filter by package, level, module and
  calculation type with multi-select dropdowns, sort on any column, and search across every
  field including the free-text **description** you can type against each calculation.
* Package, level and description are edited directly in the table; changing the package moves
  the files.
* A **PDF symbol** opens the calculation's PDF and a **folder symbol** opens its folder in
  Explorer. Superseded revisions are shown in grey when **Show superseded** is ticked.
* Full revision history: saving supersedes the previous revision and moves it to
  `superseded\`, exactly as the standalone steel tool did.
* Inputs are stored with the record, so reopening a calculation is instant.
* **Import PDF calculation** indexes a calculation prepared in other software; it takes its
  place in the index, in packages and in verification.
* **Adopt existing** indexes calculations filed by the standalone tools.
* **Link** sends one calculation's published values into another module.

### Starting a calculation
**New calculation** — on the Calculation Index and on the calculation page — opens a discipline
navigation tree: Favourites, Load Calculations, Timber, Insitu Concrete, Precast Concrete,
Temporary Works, Steel, Glass, Fibres, Composite, Foundations, Retaining wall, Analysis and
General, with a search across module names, standards and descriptions. Star a module to keep
it in Favourites. A module declares its branch in `suite.toml`.

### Saving
Saving writes the calculation and its index entry, then returns. The sheet is printed to PDF by
headless Chromium on a background worker, because starting a browser costs a few seconds every
time. The toolbar shows **Saving…**, then **Printing PDF…**, then **Saved with PDF**, so a slow
print is never mistaken for a hung save.

### Leaving a calculation
Navigating away, switching project, opening another calculation or closing the tab with
unsaved changes prompts **Save / Discard / Stay**. `Ctrl+S` saves.

### Package export
Filter by package, level, member type and calculation type; order by up to three of those
keys; select what goes in; give the package a title, a **reason for issue** (Internal Review,
Verification, Certification, Preliminary Check, Status Print, or your own words) and the
person to issue it to; then build one PDF containing:

* a **Calculation Index** sheet listing every calculation with package, level, type, status,
  utilisation, governing check, revision and start sheet number, each linked to its sheet;
* every calculation sheet, each carrying a **Contents** link back to the index;
* calculations imported as PDF, and any PDF drawings or Bluebeam markups inserted by
  Calculation Pad cells, spliced into their proper place;
* the drawing review set appended to the rear.

The body is printed as one document by headless Chromium and the extra documents are pushed
into it, so the contents links stay real PDF links. The finished package is then:

* **watermarked** `PACKAGE PREPARED DD/MM/YYYY FOR <purpose>` in red at the bottom right of
  every sheet;
* **flattened** — form fields and inherited markups are removed permanently, so the issue
  cannot be edited, while remaining open for the verifier's own review markups;
* **recorded** in the project's issue register with its reason, date of issue, and PDF and
  folder links;
* accompanied by a standalone flattened drawing file named
  `JXXXX-STR-VER-YYYY - TITLE - DRAWINGS - INITIALS.pdf`.

The package folder opens in Explorer, and a **draft email** to the nominated reviewer is raised
with links to the package.

### Verification and QA
**New verification package** files everything to

```
06-QA\03-Verification\YYMMDD - TITLE - REVIEWER\
    Calculations.pdf                          watermarked and flattened
    JXXXX-STR-VER-YYYY - … - DRAWINGS - XX.pdf
    Verification Form.html / .pdf
    Comment Register.html / .csv
    Comment Register - FINAL.html             (written on endorsement)
    JXXXX-STR-VER-YYYY - Verification request.eml   (the draft to the verifier)
    package.json
```

* The **verification form** is the Innovis form: documents to be verified, verification
  method, designer's statement, verification comments, action and endorsement.
* Creating a package raises a **draft email** to the verifier with links to the calculations,
  the drawings and the package folder.
* The **comment register** tracks verifier comment → designer response → agreed outcome →
  status (`Open`, `Noted`, `Deferred`, `Closed`) with a change history.
* Refreshing the tab **reads any marked-up PDF the verifier has returned to the package
  folder** and imports its annotations, which is how Bluebeam Revu comments come back. The
  manual **Import verifier markups** is still there for a file kept elsewhere.
* Only the **nominated verifier** may endorse. Endorsement is refused while comments are
  neither closed nor deferred, writes the final register, links it from the form, and writes
  the verifier's initials into **Checked by** on every calculation in the package. That is the
  only way Checked by is ever set — a designer cannot type it.
* **Deferred** comments are carried into the next verification package for that project.
* **Status across projects** reports packages, endorsements, open and deferred comments for
  every project in your list — the basis for the future business-wide QA review.

### Sign-in
There are no passwords or email addresses anywhere in this release. Choose your name from the
list, or press **Create a new username** and give your full name and initials; the directory
keeps your display name and initials so calculations stay attributable. Internally a new user
is keyed `first.last@innovis.com.au`, which Office 365 sign-on confirms or corrects later.

### Feedback
The **Feedback** page lists every bug report and improvement request (`data/feedback.json`,
numbered `BUG-0001` / `IMP-0001`). Anyone signed in can raise one - the page, module, project
and version are attached automatically - and press **Me too** on someone else's. Admins set
status and priority, reply to the reporter and export the list to CSV.

### Moving to the server
`python -m icm.merge <PC data folders> --into <data> [--apply]` combines every PC's project list
and people directory; `python -m icm.merge --libraries` rewrites a PC's project files so they
hold no Windows paths. See [docs/DOCKER-DEPLOYMENT.md](../../docs/DOCKER-DEPLOYMENT.md).

Office 365 single sign-on is fully written in `icm/auth.py` — configuration, PKCE, the
authorise URL and the redirect handler — and is **deliberately inactive**. To demonstrate it:

```
set ICM_SSO_ENABLED=1
set ICM_SSO_TENANT=<tenant id>
set ICM_SSO_CLIENT_ID=<application id>
```

with `http://127.0.0.1:8125/auth/sso/callback` registered as a redirect URI. Nothing else in
the application changes.

On the application host, sign-in is not done by the manager at all: `ICM_AUTH_MODE=proxy`
takes the signed-in address from the reverse proxy (see below), and the in-app flow must stay
off.

---

## Running on the application host

The manager is prepared to run as one tenant on the shared internal application host: a
**production** instance and a **preview** instance behind a TLS-terminating reverse proxy that
later performs Entra ID sign-in for every application. The container build and deployment
scripts are the next step and are not in this repository yet; the gap assessment in
[`docs/DEPLOYMENT-GAP-ASSESSMENT.md`](../../docs/DEPLOYMENT-GAP-ASSESSMENT.md) lists what
remains.

### Network placement
The service is designed for **office LAN and VPN access only, behind the reverse proxy**. It
must never be published to the internet or reached directly: the container publishes no
ports, and

* `ICM_TRUSTED_PROXIES` names the proxy (`172.30.0.2` on the host). Only that peer may set
  `X-Forwarded-Proto` / `X-Forwarded-Host`, which the manager uses for redirects; from anyone
  else they are ignored and the real peer address is kept.
* In `ICM_AUTH_MODE=proxy` the signed-in address arrives on `ICM_SSO_USER_HEADER`
  (`X-Ms-Client-Principal-Name`). A request carrying that header from any other peer is
  refused with 401 and logged. The proxy stripping client-supplied identity headers remains
  the primary control; this is the backstop.
* `ICM_ALLOWED_HOSTS` rejects any other `Host` header with 400 - including a health probe
  that does not send the site's hostname.
* `ICM_HTTPS=true` adds `Strict-Transport-Security` (the proxy sends it too; harmless).
* With a non-loopback `ICM_HOST` the desktop helpers are withdrawn - the folder picker,
  opening Explorer and opening a browser run on the server, not the user's PC - and every path
  a browser supplies (new project, relink, PDF import, markups, drawings, folder browsing) must
  lie under `ICM_ROOT`, so the server's own files cannot be listed or copied into a project.
* `ICM_AUTH_MODE=dev` on a non-loopback address is allowed for early trials but logs a
  warning: anyone who can reach it may sign in as any Innovis address.

### Preview instances
Preview runs the next release against a copy of production's data folder:

* `ICM_READ_ONLY=true` makes every route that writes to the projects share return **409**
  *"This instance is read-only (a preview on a copy of production); save in production."*
  Calculating, browsing the index and previewing packages still work; verifier returns are
  not scanned. The toolbar shows a read-only notice and disables Save. Mount the projects
  share read-only for preview as well - the setting is the application's half of the rule.
* Preview's data folder is replaced from production's newest snapshot (below).

### Tabs and modules that are not ready for everyone
Unfinished work ships in production but stays invisible until a setting changes, rather than
living on a branch:

* `ICM_TAB_ACCESS=package=admin,qa=admin` withholds tabs (`library`, `calculation`,
  `package`, `qa`) from all but admins. **This is the default while PDF export is unproven**
  (see ROADMAP.md); set `ICM_TAB_ACCESS=package=user,qa=user` to open them. The sign-in reply lists the permitted tabs, the
  browser hides the others and never opens a hidden view, and the routes behind each tab
  return **403** to anyone else. Project lists, the module catalogue and opening one saved
  calculation are never gated.
* `ICM_MODULE_ACCESS=concrete-corbel=admin` does the same for an enabled calculation module:
  it is left out of the catalogue and its schema, calculate, save, action, validate and link
  routes return 403. The module must still be enabled in `suite.toml`.
* Admins are `ICM_ADMINS` plus anyone marked `admin` in `people.json`.

### Health
`GET /api/health` needs no sign-in. It returns **200** with `status` `ok` or `degraded`
(projects root unreachable, a module failed to load, no Chromium, or the last backup failed)
and **503** with `status: "unavailable"` when the data folder cannot be written. The reply
includes the non-secret configuration.

### Backups and restore
Calculations, revisions and QA records live in the project folders and are protected by the
projects share's own backups. The manager's data folder - people, registry, discovery index -
is snapshotted **30 seconds after every start and then every `ICM_BACKUP_INTERVAL_MINUTES`**
to `ICM_BACKUP_DIR` as `innocalc-<UTC stamp>.tar.gz`, with SHA-256 hashes in
`manifest.jsonl`. Every JSON file is checked before it is archived; snapshots older than
`ICM_BACKUP_RETENTION_DAYS` are pruned. From `apps/manager`:

```
python -m icm.backup create
python -m icm.backup restore <innocalc-….tar.gz> [--data-dir DIR] [--force]
```

Restore verifies the hash and every file, refuses any unsafe archive entry, and **refuses
outright while a manager is running against the folder** (it holds `manager.lock`; `--force`
never overrides this). `--force` only accepts left-over `*.tmp` files from an interrupted
write. The replaced files are kept in `.pre-restore-<stamp>` inside the data folder. Exit
codes: 0 restored, 1 refused, 2 snapshot failed verification. A second manager started
against a data folder that is already in use also refuses to start.

### PDF printing on Linux
Chromium is found at the usual Linux locations or at `INNOCALC_BROWSER`;
`INNOCALC_BROWSER_ARGS` adds flags such as `--no-sandbox` where the container requires them.

---

## API

All JSON, `token` carried in the body or query string (ignored in proxy sign-in mode). A
withheld tab or module returns 403 and a write on a read-only instance returns 409.

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/api/health` | Unauthenticated health: 200 ok/degraded, 503 unavailable. |
| GET | `/api/ping` | Version, projects root, loaded modules, PDF tooling, sign-in mode. |
| GET | `/api/auth/config` | Sign-in mode and the people directory. |
| POST | `/api/auth/signin` `/api/auth/signout` | Session, permitted tabs, role, read-only flag. |
| GET | `/api/modules` | Loaded modules, their discipline branches, and any that failed to load. |
| GET | `/api/module/schema?module=` | Input schema and defaults. |
| GET | `/api/projects` | Your projects plus discovery status. |
| POST | `/api/projects/create` `open` `find` `search` `relink` `refresh` `archive` `forget` `rename` `people` `adopt` | Project lifecycle. |
| GET | `/api/library?project=…` | Calculation index, filtered. Filter keys repeat for multi-select. |
| GET | `/api/calculation?project=&id=` | One calculation with its inputs, PDF and folder. |
| GET | `/api/calculation/pdf?id=` | Progress of the background PDF print for a saved calculation. |
| POST | `/api/calculate` | Compute and render without saving. |
| POST | `/api/calculation/save` `update` `delete` `exchange` `import` | Index operations. |
| POST | `/api/module/action` `/api/module/validate` | Module actions and self-validation. |
| POST | `/api/package/preview` `/api/package/build` | Collation, watermarking, flattening and the issue register. |
| GET | `/api/qa?project=` `/api/qa/status` | Verification record; reads verifier returns. |
| POST | `/api/qa/create` `update` `comment/add` `comment/update` `markups` `endorse` `export` `scan` | Verification workflow. |
| GET | `/api/file?path=` | Stream a generated file. Restricted to registered project folders. |
| GET | `/api/browse` `/api/files` `/api/pick` `/api/reveal` | Filesystem helpers; `reveal` opens Explorer. On the server, confined to the projects root; `pick` and `reveal` are unavailable. |

---

## Requirements

Run `../../setup.bat` explicitly to prepare the suite-owned virtual environment and
pinned dependencies. The launcher no longer borrows Steel's environment or installs
packages during startup. New revisions retain snapshots; package export uses the
saved sheet and attachments instead of recomputing with the current engine.

* Windows, Python 3.11 or later.
* Microsoft Edge or Google Chrome, for PDF export.
* `pypdf` (`pip install pypdf`) to combine drawing sets and PDF inserts, and to watermark and
  flatten an issued package. Without it the calculation body still exports; attachments,
  watermarking and flattening are skipped.
* Outlook, or any mail client that opens `.eml`, for the draft issue emails.
