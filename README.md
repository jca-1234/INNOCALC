# InnoCalc

Calculation management, shared calculation sheets and independently testable
engineering modules. Python 3.11 or later; Windows is required for the desktop
launcher. Microsoft Edge or Google Chrome is required for PDF export.

## Setup

Run `setup.bat` explicitly to create the suite-owned `.venv`, install the pinned
dependencies and check the modules. Then run `InnoCalc.bat`. Starting the manager
or opening a calculation does not install dependencies.

Steel, Concrete Column and Calculation Pad are Git submodules. Clone with
`git clone --recurse-submodules` (or run `git submodule update --init --recursive`;
`setup.bat` does this when they are missing). See `docs/DEVELOPMENT.md` before
committing inside them. New calculations belong to this repository under `calculations/`.

## Guides

* [README-ENDUSER.md](README-ENDUSER.md) - using InnoCalc, step by step.
* [README-USER-CALCDEVELOPMENT.md](README-USER-CALCDEVELOPMENT.md) - developing and validating
  calculation modules.
* `docs/training/InnoCalc - Calculation Pad Training.pptx` - Calculation Pad training deck
  (rebuilt by `docs/training/build_calcpad_training.py`).
* [ROADMAP.md](ROADMAP.md) - known gaps and planned improvements.
* [docs/DOCKER-DEPLOYMENT.md](docs/DOCKER-DEPLOYMENT.md) - server deployment and its critical steps.

Versions are `vMajor.Patch.Minor` and restarted at `v0.0.1` for the software and every module.

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

## Server Deployment

The manager is prepared to run as a tenant of the shared internal application
host (production plus a read-only preview, behind the reverse proxy, LAN and VPN
only). Settings are listed in `.env.example`; behaviour is described in
`apps/manager/README.md` under *Running on the application host*. What remains
before containerisation is in `docs/DEPLOYMENT-GAP-ASSESSMENT.md`.

## Saved Revisions

New revisions have hashed snapshots of inputs, results, engine metadata, rendered
sheets and PDF attachments. Package export does not recompute them. Older revisions
use their filed PDF; if none exists, review and explicitly save a new revision.
The complete project calculation folder, including `.revisions`, must be backed up.

The JSON index is protected by an OS file lock and stale-write detection. Busy
projects return an actionable retry error. Corrupt indexes must be restored, not
silently replaced. See `docs/IMPLEMENTATION-STATUS.md` for rollout limitations.