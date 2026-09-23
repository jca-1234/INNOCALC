# Expansion Infrastructure Rollout

## Implemented

- Strict Steel numeric conversion and failing summaries for unattainable checks.
- Manifest registration with duplicate ID, entry, path and filing-folder checks.
- Shared SDK contract checks, dev runner, root CLI and disabled module scaffold.
- Suite-owned environment, pinned runtime/build dependencies and explicit setup.
- Calculation Pad src-layout pilot and legacy CLI compatibility entry.
- OS file locking around library and QA mutations; stale direct writes rejected.
- Index corruption rejected and previous index retained as a `.json.bak` backup.
- Content-addressed revision snapshots and frozen PDF attachments with integrity checks.
- Export uses saved revision content rather than current engine calculations.
- HTML adoption uses embedded module metadata or known legacy input markers; unknown
  documents are skipped, never assumed to be Steel.
- Shared regression tests, local validation launcher and shared CI workflow.

## Compatibility and Operations

Existing module IDs, project filing folders, calculation IDs and revision paths are
unchanged. No existing project was migrated. New source organisation is independent
of project filing. Back up the complete calculation branch including `.revisions`.

Snapshot sheets retain the identity printed when saved. Subsequent QA endorsement
is recorded in the library and verification records, not retroactively printed into
old saved sheets. Review and save a new revision to change the sheet itself.

Old revisions without snapshots export their existing PDF without recomputation.
If the PDF is absent, explicitly review and save a new revision. Adoption of a legacy
input marker restores its module and inputs but marks its summary UNVERIFIED.
Unknown HTML remains untouched; it requires a reviewed importer or PDF import.

The OS lock is nonblocking: another writer receives a retry error. Windows byte
locks must be honoured by the project file share. Validate this on the real network
share before multi-user rollout. The lock serialises index mutations but is not a
distributed database. File moves plus an index update are not a crash-atomic database
transaction; use complete project backups and recovery metadata after interruption.

## Still Deliberate Follow-up Work

- Consolidate the three old Git histories after reviewing and committing local work;
  do not publish a release manifest from dirty working trees.
- Further separate Steel and Concrete internals only after their own reference and
  asset-parity checks; their repository folders have already been relocated intact.
- Split legacy standalone applications and their assets from module resources where
  their consumers are known. Do not bulk-delete reference material or runtime data.
- Exercise concurrent sessions on the actual project share and complete independent
  engineering review before operational release.

These are release gates, not work silently claimed complete by the scaffold.

## Verification on 10 September 2026

All 25 initial implementation regression tests passed. Both the shared suite and Calculation Pad
wheels built with the expected code, templates and resources; `pip check` passed.
The GitHub Actions workflow was added but has not been executed remotely.

The module self-checks passed 143 Steel, 60 Concrete and 16 Calculation Pad cases.
The pilot matched its pre-move serialised numerical results and fixed-date HTML
hash exactly. Isolated HTTP compute/save/reopen passed for all three modules.
Separate-process lock contention and snapshot integrity/recovery were regression-tested.

The browser PDF smoke check did not pass: installed Chromium returned without
producing the saved-sheet PDF. PDF rendering, final page counts and printed link
checks remain an operational release gate. Do not treat HTTP-only success as PDF
verification. Full third-party engineering reference validation was not rerun.

## Folder Cleanup

The manager now lives at `apps/manager`; all three calculation repositories are
under discipline folders in `calculations/`; shared presentation is under
`packages/calcpad`. Each original Git history and local code change was retained.
All three modules matched pre-relocation numerical and fixed-date HTML baselines
exactly. The suite passed 26 tests after relocation, including the new cleanup test.

Removed: 13 generated build/metadata/cache directories, two redundant module-local
environments (about 181 MiB), the empty Precast Bracing placeholder and an accidental
empty `$null` file. The duplicate environments contained no package/version absent
from the retained root environment. All launchers now use that root environment.

Retained and refiled: the old scratch folder under root `artifacts/legacy-scratch`,
the verification form under `docs/reference`, and the old Steel ZIP/validation
reports and Concrete scratch dump under their repositories' `artifacts/legacy`.
Reference originals, working legacy applications, project indexes and user data
were not deleted. No engineering equations were changed during this cleanup.