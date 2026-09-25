# Roadmap

Known and suggested improvements to InnoCalc, grouped by area. Each item records **what** is
needed, **why**, and **where** in the code it lands. Items move to a hosted issue tracker once
the repository has one; until then this file is the backlog. End-user bug reports and
improvement requests arrive through the **Feedback** page (`apps/manager/data/feedback.json`,
exportable to CSV); triage them into this file. When an item ships, delete it here and record
it in the version register (`apps/manager/icm/version.py`).

Priority: **Critical** blocks the server go-live, **P1** blocks a business outcome, **P2**
material gap, **P3** nice to have.

---

## Critical before the server go-live

### Mount the projects drive from Linux and prove file locking across it - Critical
**What.** IT to provide a service account and SMB path; mount the projects share on the
application host (read-write into prod, read-only into preview) and pass the sign-off tests
C1.1-C1.5 in [docs/DOCKER-DEPLOYMENT.md](docs/DOCKER-DEPLOYMENT.md).
**Why.** Every calculation, revision, package and verification record is on the projects
drive. Project writes are serialised by OS locks. Since v0.0.1 both platforms take the same
exclusive byte-range lock on byte 0 (`msvcrt` on Windows, `fcntl.lockf` on Linux, forwarded by
the CIFS client to the file server), so the file server should arbitrate between PCs and the
host - but that is unproven until C1.2 passes on the real share (`python -m icm.locking
hold|probe`). The cut-over guard (`ICM_OWNS_PROJECTS=true` on prod) stops PCs writing to a
server-managed projects root either way.
**Where.** `apps/manager/icm/locking.py`, `server.py` (`claim_projects`, `server_owner`), host
`/etc/fstab`, `deploy/compose.yml` (Step 3). Remaining: IT's service account and mount, then
C1.1-C1.5.

### Prove PDF printing inside the container, and on Windows - Critical
**What.** Pass sign-off tests C2.1-C2.5 in [docs/DOCKER-DEPLOYMENT.md](docs/DOCKER-DEPLOYMENT.md):
saved-sheet PDFs, package page counts, contents links, watermark, flattening, Bluebeam return.
**Why.** On Windows an earlier full smoke run returned from Chromium without producing PDFs;
the smoke check has since passed twice on one PC (24 and 25 September 2026). The image
(`Dockerfile`: Chromium, Carlito/Liberation/DejaVu fonts, `HOME=/tmp`, `--no-sandbox
--disable-dev-shm-usage`) and an automated in-image proof (CI job `container-pdf`: full PDF
smoke as UID 1001 with a read-only root, Docker health check, Host allow-list) are in place,
but the job has not run until the repository is pushed. **Until the sign-off tests pass,
Package Export and Verification are limited to admins** - the default when `ICM_TAB_ACCESS` is
blank.
**Where.** `Dockerfile`, `.github/workflows/shared-quality.yml`, `packages/calcpad/export.py`,
`apps/manager/icm/pdf.py`, `icm/collate.py`, `apps/manager/icm/config.py`
(`PDF_GATED_TAB_ACCESS`). Remaining: C2.1 on a second PC, C2.2 green in CI, C2.3-C2.5 by hand.

---

## Deployment and platform

### Commit the module repositories and their submodule pointers - P1
**What.** Commit and push the local work in `calculations/steel/member`,
`calculations/concrete/column` and `calculations/general/calculation_pad`, then commit the
updated submodule pointers in the suite. `python -m tooling release-check` must pass.
**Why.** The modules are now pinned submodules, but each has substantial uncommitted work
(Calculation Pad's src layout among it). An image built from the pushed commits would not match
what runs on PCs today.
**Where.** `.gitmodules`, the three module repositories, `tooling/__main__.py` (release check).

### Single sign-on at the edge; retire the name picker - P1
**What.** Entra ID at the shared Caddy proxy with `ICM_AUTH_MODE=proxy`; remove the
development sign-in.
**Why.** Choosing a name from the list lets anyone act as anyone. InnoCalc records designer
initials and verifier endorsements, so identity matters. The directory keys new users as
`first.last@innovis.com.au`; SSO must confirm or correct each key, and draft emails go to that
derived address until it does.
**Where.** `apps/manager/icm/auth.py`, `server.py` (`_development_user`, `_proxy_user`),
`apps/manager/icm/merge.py` (reconcile keys).

### Server replacements for desktop-only workflows - P1
**What.** Copyable share paths instead of "open folder"; download the `.eml` draft through
`/api/file` instead of opening Outlook; typed paths with project-number lookup instead of the
folder picker.
**Why.** The picker, Explorer and Outlook launch are withdrawn in server mode but not replaced.
**Where.** `server.py` (`_pick`, `_reveal`), `icm/mail.py`, `app.js` (`pickFolder`,
`revealFolder`).

### Container and deploy artefacts - P1
**What.** `deploy/compose.yml` (prod + preview), Caddy site, env examples, deploy/refresh
scripts. The `Dockerfile` and `.dockerignore` exist (for the PDF proof, G5).
**Why.** Step 3 of the hosting plan; see G8 in
[docs/DEPLOYMENT-GAP-ASSESSMENT.md](docs/DEPLOYMENT-GAP-ASSESSMENT.md).
**Where.** New `deploy/` folder.

### File paths inside module inputs - P2
**What.** Store Calculation Pad PDF, figure and attachment paths relative to the project
folder, as the manager's own records now are.
**Why.** The manager's data is portable (v0.0.1) but a module's saved inputs can still hold
`J:\...` paths typed by the user. Frozen attachments are safe (they are copied into
`.revisions/assets`), but reopening a pad on the server shows the original paths as missing.
**Where.** `calculations/general/calculation_pad/src/cpd/headless.py`,
`apps/manager/icm/snapshots.py` (`freeze_attachments`), `icm/paths.py`.

### Retire the stale root copies - P2
**What.** Review and remove `InnoCalcManager/`, `CalculationPad/`, `SteelMemberDesign/`,
`ConcreteColumnDesign/` (22 tracked compatibility files).
**Why.** They duplicate code now under `apps/` and `calculations/` and confuse new developers.
**Where.** Repository root; check launchers and imports first.

### Release discipline - P2
**What.** Annotated `vMajor.Patch.Minor` tags matching `icm/version.py`; protect `main`; run
the CI workflow; a CI check that a module whose engine changed also bumped its `VERSION` and
added a history entry.
**Why.** Saved revisions record `moduleVersion`; it is only meaningful if every change bumps it.
**Where.** `.github/workflows/shared-quality.yml`, `packages/innocalc_sdk/versioning.py`.

---

## Calculation Index and saving

### Superseded revisions can lose their PDF - P2
**What.** When a calculation is saved twice in quick succession, the first revision's PDF is
printed in the background after it has already been moved to `superseded/`, so the superseded
row has no PDF. Print into the revision's current location, or supersede only after printing.
**Why.** Found while testing Show superseded: superseded rows show the folder and View links but
no PDF.
**Where.** `server.py` (`PDF_WORKER`), `icm/library.py` (`_supersede`).

### Open a superseded revision read-only - P3
**What.** Open the snapshot of any revision into the Calculation view, read-only, with a
"Restore as new revision" action.
**Why.** Today a superseded row offers View (its HTML) only.
**Where.** `icm/library.py`, `icm/snapshots.py` (`load_snapshot`), `app.js`.

### Downstream flags for linked calculations - P2
**What.** Record Link relationships and flag a downstream calculation when the upstream one is
re-saved with a different result.
**Why.** A beam reaction sent to a column calculation silently goes stale today.
**Where.** `server.py` (`_exchange_calculation`), `icm/library.py`.

### Index paging for large projects - P3
**What.** Server-side paging and sorting.
**Why.** Very large projects send every record on each refresh.
**Where.** `icm/library.py` (`index`), `app.js` (`renderLibrary`).

### Audit log - P2
**What.** Append-only log of saves, moves, removals, finalisation and verification actions.
**Why.** Engineering record keeping; answers "who removed this calculation from the index".
**Where.** `icm/library.py` transactions.

---

## Calculation modules and validation

### Independent engineering review of Steel and Concrete Column - P1
**What.** Third-party reference validation rerun and signed off per module version.
**Why.** A release gate in docs/IMPLEMENTATION-STATUS.md that has not been closed.
**Where.** `calculations/*/validation`, `python -m smd.dev --validate`, `python -m ccd.validation`.

### Review and enable the eight scaffolded concrete modules - P2
**What.** Corbel, deep beam, development length, parameters, plain concrete, reinforcement rate,
reinforcement tables and stair are transcribed but disabled.
**Why.** Engineering review is outstanding; each is `enabled = false` in `suite.toml`.
**Where.** `calculations/concrete/concrete_*`, `suite.toml`. Follow
[README-USER-CALCDEVELOPMENT.md](README-USER-CALCDEVELOPMENT.md).

### Validation evidence pack per version - P2
**What.** Each module release produces a filed validation report (cases, sources, tolerance,
result, engine version) that the Versions dialog links to.
**Why.** Lets a verifier see what a `moduleVersion` in a saved revision was validated against.
**Where.** `packages/innocalc_sdk/dev.py`, module `validation.py`.

### Calculation Pad templates - P2
**What.** A library of starter pads (load takedown, lintel, bolt group, design philosophy) chosen
from New calculation.
**Why.** Most pads start from the same structure; templates keep them consistent.
**Where.** `calculations/general/calculation_pad/src/cpd/headless.py` (defaults).

---

## Feedback

### Screenshot attachment and notifications - P2
**What.** Attach a screenshot to a report; notify admins of new **critical** reports.
**Why.** Most bug reports are clearer with a picture; critical reports (wrong engineering
result, lost work) need attention the same day.
**Where.** `apps/manager/icm/feedback.py`, `app.js` (`openFeedbackDialog`).

### Move feedback to the issue tracker - P3
**What.** Export or sync triaged reports to GitHub Issues once the repository has one.
**Why.** One backlog rather than a JSON file and this roadmap.
**Where.** `icm/feedback.py` (`as_csv` today).

---

## Documentation and training

### Slide decks from the user guides - P3
**What.** Build decks from [README-ENDUSER.md](README-ENDUSER.md) and
[README-USER-CALCDEVELOPMENT.md](README-USER-CALCDEVELOPMENT.md); both are written slide by
slide (Marp format) with screenshot slots under `docs/assets/screenshots`.
**Why.** Training sessions; the Calculation Pad deck already exists in `docs/training/`.
**Where.** `npx @marp-team/marp-cli README-ENDUSER.md --pptx`, `docs/training/`.

### Module training decks - P3
**What.** Steel Member and Concrete Column decks in the style of the Calculation Pad deck.
**Where.** `docs/training/build_calcpad_training.py` as the pattern.

---

## Suggested further improvements

* **Project-wide search** across every project a person can see (P3).
* **Keyboard and accessibility pass**: focus order in dialogs, labels on icon buttons (P3).
* **Admin health page** in the app showing `/api/health`, last backup and module problems (P3).
* **Load combination helpers** in Calculation Pad for AS/NZS 1170.0 (P3).
* **Offline read-only copy** of a project's issued packages for site visits (P3).
