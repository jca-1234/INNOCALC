# Calculation Development

## Source Layout

```
apps/manager/                   manager application and local runtime data
packages/calcpad/               shared sheet renderer, retained import name
packages/innocalc_sdk/           manifest checks, contracts and development runner
tooling/                        CLI, templates and migration baselines
calculations/<discipline>/<id>/  new modules, owned by the suite repository
  pyproject.toml
  src/<package>/
    module.toml                 identity, standard, maintainer and release status
    headless.py                 public calculation contract
    engine.py                   engineering values and intermediate results
    report.py                   presentation, no recomputation
    dev.py                      thin shared runner entry
  tests/                        contract and engineering release gates
  examples/                     reviewed inputs and expected results
  reference/                    original evidence and provenance
tests/                         shared regression and integration tests
artifacts/                     ignored generated outputs and baselines
suite.toml                     enabled modules, source paths and discipline list
```

All calculation repositories now live under `calculations/`: Steel at
`steel/member`, Concrete at `concrete/column`, and Calculation Pad at
`general/calculation_pad`. Each retains its original Git history. Steel and Concrete
keep their working standalone apps and reference material alongside their engines;
these are not redundant copies of the manager. Calculation Pad uses `src/cpd`, with
a compatibility entry at `cpd` for its standalone development command.

All launchers use the root `.venv`. New modules do not copy a server, web frontend,
project store, PDF exporter or a virtual environment. Shared presentation lives
under `packages/calcpad`, but its public Python import remains `calcpad`.

## Create a Calculation

```
python -m tooling new timber-member --name "Timber Member Design" --category Timber --standard "AS 1720.1:2010" --filing-folder "TIMBER MEMBER" --owner "Responsible engineer"
```

Use the actual agreed standard including amendments, maintainer and permanent
filing name. Complete `NEW-MODULE-BRIEF.md` before writing equations. The generator
creates a module under `calculations/`, assigns a unique Python package, and adds
an **enabled = false** manifest entry. It refuses existing IDs, filing names and
destination folders. The release tests deliberately fail until implemented.

```
python -m tooling dev timber-member --schema
python -m tooling dev timber-member --trace
python -m tooling check timber-member --validate
python -m pip install --no-build-isolation --no-deps -e calculations/timber/timber_member
python -m unittest discover -s calculations/timber/timber_member/tests -v
```

Before release: add worked examples, invalid-input and boundary tests, independently
review the engineering, change module status to `available`, then set `enabled = true`
in `suite.toml`. Restart the manager. No manager Python or JavaScript edit is needed.
Contract checks are software checks, not engineering certification.

## Validation and Evidence

Run `validate.bat` for shared regression tests plus each enabled module's own
self-validation. Concrete's full reference/baseline workflow remains available
through `python -m ccd.dev --validate` and its specialist validation commands.
Keep reference originals and their revision/source information unchanged. Generated
HTML, PDFs, extracts and traces go into `artifacts/`; reviewed numerical fixtures
and expected results belong in the module's tests or examples.

`python -m tooling.smoke` exercises HTTP compute/save/reopen and real PDF export
with isolated test storage under `artifacts/`. It requires Chromium. Use
`python -m tooling.smoke --no-pdf` for the HTTP-only check; its report explicitly
records `pdfChecked = false` and is not evidence of PDF export success.

Before moving a module:

```
python -m tooling.baseline calculation-pad artifacts/pilot-before.json
python -m tooling.baseline calculation-pad artifacts/pilot-before.json --compare
```

This compares fully serialised numerical results, identity and summary, plus a
fixed-date HTML hash. Also run module validation and a save/reopen/PDF check.

## Repository Ownership

There are currently four independent repositories, not Git submodules. The suite
root ignores the existing module repositories. Do not remove their `.git` folders
or flatten their uncommitted work. To reproduce this development workspace, obtain
the suite plus all three module repositories at the paths named by `suite.toml`.

New modules use the root repository. Consolidation of the old repository histories
is a separate Git operation after the local changes have been reviewed and committed.
No Git history was rewritten by the layout pilot.

The legacy repositories were moved intact, not merged into the root repository.
The root `.gitignore` explicitly excludes those three paths. New calculation
folders remain part of the root repository. Source-folder names are not project
filing names: the latter are unchanged in `suite.toml`.

```
python -m tooling release-check --output artifacts/suite-release.json
```

This refuses dirty repositories and records each repository commit plus the module
manifest. It does not commit, fetch or publish. A release must retain these exact
source revisions, the dependency locks, test results and reference evidence.
The output is release provenance, not an automated multi-repository checkout tool.

## Dependency Policy

`requirements.lock` pins runtime dependencies including transitive dependencies.
`requirements-dev.lock` adds pinned build tools. Update them deliberately and rerun
module validation. Editable installations use the pinned local build tools with
`--no-build-isolation`. Calculation code and schema retrieval may check dependencies,
but must not install them. Optional notebook-only packages are not required to run
the manager; install them explicitly in the notebook environment when needed.

The shared GitHub Actions workflow runs storage, snapshot and scaffold tests on
Windows and Linux. Full module integration runs locally with all four repositories;
the root checkout alone does not contain those private module sources.

## Housekeeping

```
python -m tooling clean
python -m tooling clean --apply
```

The first command lists generated directories; the second deletes only that class
of files. It prunes environments, Git histories, references, assets, project data
and artifacts from traversal. Build directories are removed only beside a Python
project manifest; arbitrary folders named `build` in source are not removed.

Build metadata is regenerated by setup/build commands. The installed editable
package metadata remains in `.venv`; deleting source `.egg-info` does not remove
the environment. Keep validation baselines and reviewed outputs under `artifacts/`.
The old scratch script/report are retained at `artifacts/legacy-scratch/`; the
original verification form is at `docs/reference/Verification form.docx`.