# InnoCalc

Calculation management, shared calculation sheets and independently testable
engineering modules. Python 3.11 or later; Windows is required for the desktop
launcher. Microsoft Edge or Google Chrome is required for PDF export.

## Setup

Run `setup.bat` explicitly to create the suite-owned `.venv`, install the pinned
dependencies and check the modules. Then run `InnoCalc.bat`. Starting the manager
or opening a calculation does not install dependencies.

This workspace currently contains four Git repositories. The root repository
does not contain the Steel, Concrete or Calculation Pad repositories. Keep their
histories and uncommitted changes; see `docs/DEVELOPMENT.md` before cloning or moving
them. New calculations belong to this repository under `calculations/`.

## Folder Layout

```
apps/manager/                         manager application and local data
calculations/steel/member/             Steel repository, including legacy app
calculations/concrete/column/          Concrete repository, including legacy app
calculations/general/calculation_pad/  Calculation Pad repository
packages/calcpad/                      shared presentation (import calcpad)
packages/innocalc_sdk/                 shared module contracts and dev runner
tooling/                              scaffolding, validation and cleanup commands
tests/                                shared regression tests
docs/                                 specifications, guides and reference form
artifacts/                            retained scratch work and generated output
.venv/                                the single suite environment
```

## Developer Commands

From the suite root, using `.venv/Scripts/python.exe` on Windows:

```
python -m tooling list
python -m tooling check --all
python -m tooling check --all --validate
python -m tooling dev steel-member --trace
python -m tooling dev concrete-column --html artifacts/column.html
python -m tooling dev calculation-pad --notebook artifacts/pad.ipynb
python -m unittest discover -s tests -v
python -m tooling clean
python -m tooling clean --apply
```

`validate.bat` runs the full local regression and module self-validation gates.
See `docs/DEVELOPMENT.md` for scaffolding, source ownership and release checks.
`clean` is a dry run unless `--apply` is supplied. It only removes build metadata
and bytecode caches; environments, reference evidence, project data and artifacts
are excluded. Module-local virtual environments are no longer needed.

## Saved Revisions

New revisions have hashed snapshots of inputs, results, engine metadata, rendered
sheets and PDF attachments. Package export does not recompute them. Older revisions
use their filed PDF; if none exists, review and explicitly save a new revision.
The complete project calculation folder, including `.revisions`, must be backed up.

The JSON index is protected by an OS file lock and stale-write detection. Busy
projects return an actionable retry error. Corrupt indexes must be restored, not
silently replaced. See `docs/IMPLEMENTATION-STATUS.md` for rollout limitations.