# Preparing a Calculation Package for InnoCalc

**Audience:** an engineer, developer or GPT-style coding assistant creating a new calculation module.

**Applies to:** the InnoCalc workspace at `C:\CODING\INNOCALC`, with the folder layout and manager implementation checked on 10 September 2026.

**Objective:** produce an independently testable Python calculation module that InnoCalc Manager can discover, display, calculate, save, reopen, link and include in calculation packages without adding engineering logic to the manager.

This is a complete implementation brief, not permission to invent engineering rules. An AI can implement supplied requirements; a responsible engineer must establish the design basis, resolve missing information and approve engineering use. A module that imports successfully is not necessarily correct or verified.

## Contents

1. [Terminology and ownership](#1-terminology-and-ownership)
2. [Instructions to the implementing AI](#2-instructions-to-the-implementing-ai)
3. [Engineering information required before coding](#3-engineering-information-required-before-coding)
4. [Workspace, environment and dependencies](#4-workspace-environment-and-dependencies)
5. [Create the module structure](#5-create-the-module-structure)
6. [Registration, identifiers and versions](#6-registration-identifiers-and-versions)
7. [Required Python interface](#7-required-python-interface)
8. [Inputs, identity and form schemas](#8-inputs-identity-and-form-schemas)
9. [Engineering engine and result document](#9-engineering-engine-and-result-document)
10. [Calculation sheets and rendering](#10-calculation-sheets-and-rendering)
11. [Saving, reopening and package export](#11-saving-reopening-and-package-export)
12. [Actions and exchange between modules](#12-actions-and-exchange-between-modules)
13. [Advanced editors and attachments](#13-advanced-editors-and-attachments)
14. [Complete teaching implementation](#14-complete-teaching-implementation)
15. [Automated testing and validation](#15-automated-testing-and-validation)
16. [Third-party reference validation](#16-third-party-reference-validation)
17. [Manager integration and PDF acceptance](#17-manager-integration-and-pdf-acceptance)
18. [Release, compatibility and maintenance](#18-release-compatibility-and-maintenance)
19. [Troubleshooting](#19-troubleshooting)
20. [Final acceptance checklist](#20-final-acceptance-checklist)
21. [AI handover prompt and completion report](#21-ai-handover-prompt-and-completion-report)

## 1. Terminology and Ownership

The word **package** has several meanings in this system. Do not confuse them.

| Term | Meaning |
| --- | --- |
| Calculation module | A reusable engineering tool, such as Steel Member Design. It supplies the Python interface described here. |
| Python package | The importable code inside a module, such as `ic_timber_member`. |
| Python distribution | The installable project described by the module's `pyproject.toml`, such as `innocalc-timber-member`. |
| Calculation | One input document and its computed result for a particular member or task. |
| Revision | An explicitly saved state of a calculation, including its provenance and rendered output. |
| Project calculation package | A group of calculations issued together, such as `P01`. This is the manager-owned `inputs["package"]`, not a Python package. |
| Source folder | Where development code lives under `calculations/`. |
| Filing folder | The permanent module-specific folder name used inside a project's calculation branch. It is not the source folder. |

### Responsibility boundaries

| Component | Owns | Must not own |
| --- | --- | --- |
| Module engine | Input validation, units, design equations, case selection, intermediate values, capacities, utilisation and engineering limits | HTTP, authentication, project indexing, file saving, browser operation or HTML |
| Module adapter | The public interface, descriptor, input schema, defaults, summary, identity and optional actions/exchange | A second project store or a custom server |
| Module report | Formatting engine results into shared calculation-sheet blocks | Recalculating capacities or inventing values absent from the result |
| Shared `calcpad` package | Notation, sheet layout, headers, pagination, common styles, trace and PDF-print support | Module-specific engineering decisions |
| Manager | Projects, users, forms, persistence, revisions, snapshots, PDF packages, verification records and linking | Knowledge of a specific design equation or material factor |
| Responsible engineer | Scope, standard interpretation, acceptance criteria, reference evidence and approval | Delegating approval to an unreviewed AI output |

The normal live calculation path is:

```text
suite.toml -> import module -> descriptor()
                                  |
                           schema() + defaults()
                                  |
                           manager builds form
                                  |
                           input JSON document
                                  |
                              compute()
                           /      |       \
                   summarise() identity() render()
                           \      |       /
                         manager displays result
```

Saving is a separate explicit operation. It computes the supplied inputs again, renders a standalone sheet, and files a revision snapshot. Exporting an existing saved revision uses its snapshot, not a new engine run.

### Authoritative references

This guide consolidates the current implementation. The suite contract is [../docs/MODULE-SPECIFICATION.md](../docs/MODULE-SPECIFICATION.md); the commissioning brief and detailed reference-validation procedure are [../docs/NEW-MODULE-BRIEF.md](../docs/NEW-MODULE-BRIEF.md). General development operations are in [../docs/DEVELOPMENT.md](../docs/DEVELOPMENT.md).

If a requested feature is incompatible with the implemented contract, identify the discrepancy and ask for an explicit contract change. Do not silently modify the manager to make a new module appear compatible. Recheck the implementation if these documents or the platform have changed since this guide was written.

## 2. Instructions to the Implementing AI

Follow these rules throughout development:

1. Read this guide and the completed engineering brief before writing equations.
2. Inspect the actual workspace. Preserve existing files, uncommitted changes, reference documents and Git histories.
3. Use the existing scaffold, shared reporting package and development runner. Do not copy a legacy application wholesale.
4. Make new modules under `calculations/<discipline>/<module_name>/`. Do not create another top-level application or virtual environment.
5. Do not modify manager Python, JavaScript, authentication, project records, QA code or PDF machinery for an ordinary module addition. Registration belongs in the suite manifest.
6. Never invent a design clause, resistance factor, catalogue property, material value or acceptance tolerance. Record unresolved items and keep the module disabled.
7. Keep calculations deterministic and free of external side effects. Never install packages during import, schema retrieval, calculation or rendering.
8. Do not silently replace malformed or missing required engineering input with a default. Defaults belong to new-document creation, not exception handling.
9. Produce workings that an engineer can audit without reading the source code.
10. Run tests and report actual outputs. Distinguish software compatibility, numerical validation, reference agreement and engineering approval.
11. Keep the module `planned` and disabled until all applicable release gates and independent review are complete.
12. Do not commit, publish, merge repositories, rename permanent IDs or migrate saved project documents unless specifically authorised.

Use Australian English, descriptive names, `from __future__ import annotations` and type annotations on public functions. Keep code focused. A small explicit function is preferable to an unneeded framework.

## 3. Engineering Information Required Before Coding

The framework cannot supply the design basis. Complete the following brief for every real module. Empty cells are unresolved requirements, not permission to guess.

### 3.1 Identity and scope

| Required item | Fill in |
| --- | --- |
| Module name and short name | |
| Stable module ID, in lowercase kebab-case | |
| Discipline/category, chosen from the manifest | |
| Permanent project filing-folder name | |
| Python package and source-folder names | |
| Responsible engineer / maintainer | |
| Governing standard, edition and amendments | |
| Calculation type and member-type suggestions | |
| Intended users and design task | |
| Checks included | |
| Checks deliberately excluded | |
| Valid materials, geometries, actions and boundary conditions | |
| Conditions requiring rejection or an unattainable result | |
| Required independent reviewer and approval evidence | |

### 3.2 Input schedule

Define **every** engineering input, including fields that are only relevant to optional checks.

| Group | Field ID | Label | Type | Input unit | Default | Valid range / enum | Required when | Source / explanation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| | | | | | | | | |

Also define:

- Whether actions are already factored, nominal, serviceability or characteristic values.
- Load combinations, mutually exclusive cases and the source of combination factors.
- Axis definitions, sign conventions, compression/tension conventions and moment orientation.
- Geometry definitions, effective lengths, restraint assumptions and tolerances.
- Which checks are optional and which are mandatory regardless of user input.
- Catalogue properties and their published source, units and revision.
- Whether a default is a meaningful blank state, a representative example or a prescribed value.

### 3.3 Calculation schedule

| Check/result ID | Clause/reference | Equation | Inputs and intermediate values | Limits/branches | Capacity/demand units | Utilisation definition |
| --- | --- | --- | --- | --- | --- | --- |
| | | | | | | |

For iterative procedures, state starting assumptions, convergence criterion, maximum iterations and the outcome if convergence fails. For interpolation, state the table source, interpolation rule and behaviour outside the table. For combined actions, identify the complete interaction equation and its applicability conditions.

### 3.4 Evidence and output schedule

| Required item | Fill in |
| --- | --- |
| Report section order | |
| Required diagrams, tables and intermediate values | |
| Governing utilisation and summary wording | |
| Reference documents and exact pages/cases | |
| Expected numerical values, units and tolerances | |
| Boundary and invalid-input cases | |
| Approved legacy baseline, if any | |
| Required actions or optimisations | |
| Exchange groups produced/consumed | |
| Attachments or specialist editor needs | |
| Definition of complete acceptance | |

Stop for clarification when a missing assumption can materially alter the answer. State the question precisely, for example: "Are the supplied moments already second-order design actions, or must this module amplify them?"

## 4. Workspace, Environment and Dependencies

### 4.1 Current source layout

```text
INNOCALC/
  InnoCalc.bat                         main application launcher
  setup.bat                           explicit environment setup
  validate.bat                        full local validation entry point
  suite.toml                          module registration and categories
  pyproject.toml                      shared suite distribution
  requirements.lock                   pinned runtime dependencies
  requirements-dev.lock               pinned build dependencies
  .venv/                              one suite-owned environment
  apps/manager/                       management app and local runtime data
  packages/calcpad/                   shared presentation; import as calcpad
  packages/innocalc_sdk/               contract checks and shared dev runner
  tooling/                            module generator and root CLI
  calculations/
    steel/member/                     existing independent repository
    concrete/column/                  existing independent repository
    general/calculation_pad/          existing independent repository
    <discipline>/<new_module>/        new modules owned by the root repository
  tests/                              shared tests
  docs/                               specifications and guidance
  artifacts/                          generated output and retained baselines
```

The existing three module repositories have their own Git histories and are excluded from the root repository. New scaffolded module folders normally belong to the root repository. Do not remove nested `.git` directories or assume cloning only the root obtains the three existing modules.

### 4.2 Interpreter and commands

Python 3.11 or later is required by the current packages. The verified development environment uses Python 3.12. Windows desktop operation and a local Microsoft Edge or Google Chrome installation are needed for the current manager/PDF workflow.

The examples below are **PowerShell commands run from the suite root**:

```powershell
Set-Location C:\CODING\INNOCALC
$Python = Join-Path $PWD '.venv\Scripts\python.exe'
& $Python --version
& $Python -m tooling list
```

If setup has not been completed, run the existing [../setup.bat](../setup.bat) explicitly, then repeat those checks. Setup may access the network to install dependencies. Do not run it automatically from a calculation or a test that is supposed to be side-effect-free.

On non-Windows development systems, use the appropriate environment interpreter path, typically `.venv/bin/python`, for engine and contract tests. Do not assume the current native pickers, launchers or PDF-browser discovery are portable.

### 4.3 Dependency policy

- Prefer the Python standard library for new engineering code unless a justified external dependency is approved.
- Declare module dependencies in its distribution metadata; coordinate new runtime dependencies with the suite lock files.
- Use the installed `calcpad` and `packages.innocalc_sdk` APIs. Do not duplicate them inside the new module.
- Install or update dependencies through explicit setup/development commands, never through `pip` subprocesses inside module functions.
- Do not silently fall back to different engineering behaviour when a required dependency is missing.
- Put bundled data inside the Python package and access it with `importlib.resources`. Declare package data so it survives wheel installation.
- Never rely on the current working directory or on `Path(__file__).parents[2]` locating the suite. New packages should work after installation.

## 5. Create the Module Structure

### 5.1 Use the generator

The following is an **illustrative command**, not an instruction to implement timber design without an engineering brief:

```powershell
& $Python -m tooling new timber-member --name "Timber Member Design" --category Timber --standard "AS 1720.1:2010" --filing-folder "TIMBER MEMBER" --owner "Responsible engineer"
```

Replace the standard with the actual approved edition and amendments. The generator currently derives:

| Item | Example |
| --- | --- |
| Module ID | `timber-member` |
| Source folder | `calculations/timber/timber_member/` |
| Importable package | `ic_timber_member` |
| Adapter entry point | `ic_timber_member.headless` |
| Distribution name | `innocalc-timber-member` |

Category names are normalised into lowercase source-folder names with underscores. The category label in the manifest remains its original exact spelling. IDs must be lowercase kebab-case; do not pass spaces or filesystem paths as IDs.

The generator refuses duplicate IDs, duplicate filing folders and an existing destination. It appends an `enabled = false` entry to [../suite.toml](../suite.toml). It does not produce a finished engineering calculation.

### 5.2 Files and responsibilities

```text
calculations/timber/timber_member/
  pyproject.toml
  README.md
  src/ic_timber_member/
    __init__.py
    version.py
    module.toml
    headless.py
    engine.py
    report.py
    validation.py                     add for real validation implementation
    dev.py
    data/                             optional immutable published data
  tests/
    test_release_gate.py
    test_engine.py                    add engineering and edge-case tests
    test_exchange.py                  only if exchange is implemented
  examples/
    README.md
    worked-example.json               add reviewed fixtures
  reference/
    README.md
```

| File | Required responsibility |
| --- | --- |
| `pyproject.toml` | Build metadata, Python requirement, dependencies, source package discovery and bundled resources. |
| `module.toml` | The module's descriptor metadata, excluding values deliberately supplied from one code/version source. |
| `version.py` | The engine/module version exposed by `descriptor()`. |
| `headless.py` | The seven public functions and optional extension hooks. Keep it an adapter rather than a second engine. |
| `engine.py` | Pure engineering functions and complete numerical results. It must not import the report. |
| `report.py` | Shared `calcpad` blocks built from inputs for identity and from results for engineering workings. |
| `validation.py` | Reproducible sweeps and worked-example comparison. Return structured outcomes. |
| `dev.py` | Thin call to the shared development runner. Do not copy a complete CLI implementation. |
| `tests/` | Executable software and engineering release gates. |
| `examples/` | Reviewed input documents, expected values and provenance. |
| `reference/` | Original evidence and source metadata, not disposable generated reports. |
| `README.md` | Scope, exclusions, standard, units, limits, commands, evidence and current approval status. |

The scaffold's engine intentionally raises an error and its release tests intentionally fail. Replace the placeholder by implementing the agreed engineering and tests; do not remove the tests or make `validate()` unconditionally return `True`.

### 5.3 Packaging and resources

The generated distribution depends on the installed `innocalc-suite`. Use its existing pinned build backend. An illustrative package-data configuration is:

```toml
[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
"ic_timber_member" = ["module.toml", "data/*.json"]
```

Only declare files the package actually uses. Test the built wheel, not just imports from a source directory. A successful editable install can conceal missing wheel resources.

Do not put source references, proprietary documents or large generated reports into a wheel unless there is an explicit approved requirement and permission to distribute them.

## 6. Registration, Identifiers and Versions

### 6.1 Suite registration

A new module needs one manifest record, initially disabled:

```toml
[[modules]]
id = "timber-member"
path = "calculations/timber/timber_member/src"
entry = "ic_timber_member.headless"
category = "Timber"
filing_folder = "TIMBER MEMBER"
enabled = false
```

The top-level manifest currently uses `schema_version = 1` and `contract_version = 1`. Do not change these to make a single module load.

Available categories at the time of writing are:

```text
Load Calculations, Timber, Insitu Concrete, Precast Concrete, Temporary Works,
Steel, Glass, Fibres, Composite, Foundations, Retaining wall, Analysis, General
```

Read the current [../suite.toml](../suite.toml) instead of assuming this list never changes. Use an existing exact category or obtain approval to add one.

### 6.2 Descriptor metadata

`descriptor()` must return a fresh dictionary containing at least:

| Key | Meaning / rule |
| --- | --- |
| `id` | Unique stable module ID. Must match the suite manifest. Never repurpose it for a different calculation. |
| `name` | Full readable module name. |
| `short` | Short readable name. |
| `standard` | Approved standard, edition and amendments; use an honest non-design label for a teaching example. |
| `folder` | Permanent filing folder. Must equal manifest `filing_folder`. This is not `path`. |
| `status` | `planned` during development; `available` only when approved for the intended release. |
| `version` | Current engine/module version. |
| `defaultSubject` | Default subject printed on a new sheet. |
| `calcType` | Stable readable calculation-type label for grouping and sorting. |
| `description` | Concise explanation of the actual scope, without claiming unsupported checks. |
| `capabilities` | Features actually implemented. Descriptive metadata does not create a missing function. |
| `entry` | Importable adapter entry point, matching the suite manifest. |
| `category` | Same category as the manifest; avoid conflicting declarations. |
| `maintainer` | Responsible maintainer from the brief. |
| `contractVersion` | `1` for the current module contract. |
| `inputSchemaVersion` | Version of the saved input-document structure, initially `1`. |

The last four are part of the current scaffold convention and should be retained even where legacy modules omit them. Versions are `vMajor.Patch.Minor`, starting at `v0.0.1` (see `packages/innocalc_sdk/versioning.py`): **Major** when saved calculations or results may change, **Patch** for a correction or addition that leaves saved calculations valid, **Minor** for presentation or wording only. The engine `VERSION` carries the `v` (`v0.0.1`); `pyproject.toml` carries the PEP 440 spelling of the same numbers (`0.0.1`). The contract check rejects any other descriptor version format.

### 6.3 What the loader actually checks

The manifest validator checks supported manifest versions, duplicate IDs/entries/paths/filing names, category membership, valid import syntax, source paths within the suite and explicit boolean `enabled` values. The registry imports enabled modules and verifies the seven callable functions, identity/filing consistency, duplicate loaded identities and `status == "available"`.

An enabled module that fails to import is reported in `moduleProblems`. Invalid top-level manifest data can prevent startup before individual modules are loaded. Merely adding a folder is not registration. Merely installing a distribution is not registration. Restart the manager after changing registration or module code.

The loader does **not** execute the full engineering validation suite as a release gate. Neither a successful import nor `status = "available"` proves engineering approval.

## 7. Required Python Interface

All required functions live in the adapter named by the manifest, normally `<package>.headless`.

| Function | Exact call shape | Required result |
| --- | --- | --- |
| `descriptor()` | No arguments | Metadata dictionary described above. |
| `schema()` | No arguments | Descriptor fields plus `identity`, `groups` and any supported optional schema fields. |
| `defaults()` | No arguments | New, complete valid input dictionary, including every form-field key. |
| `compute(inputs)` | One dictionary | Result dictionary containing `util`, `worstUtil`, `checks` and all engineering workings. |
| `render(inputs, result, *, standalone=False, appendix=None, anchor_prefix="", contents_href="")` | Two positional arguments and these keyword arguments | HTML string generated through `calcpad`. |
| `summarise(result)` | Result dictionary | `worstUtil`, `criticalCheck`, `status`, `headline`. |
| `identity(inputs)` | Input dictionary | `memberType`, `memberNumber`, `package`, `level`, `calcType`, `title`. |

Implement `validate(cases=None)` for **every new production module**. It is optional to the historical runtime interface but required by the new-module release workflow and the root `check --validate` command.

General rules:

- Return ordinary Python dictionaries, lists, strings, booleans and numbers; no ORM entities, custom classes, generators, NumPy arrays, sets or `Path` objects in the public documents.
- Return fresh nested mutable structures. Editing one defaults document must not change another or mutate global schema data.
- Do not mutate `inputs` in `compute`, `render`, `identity` or exchange handling. Copy before transforming.
- Raise `ValueError` with a useful field/check message for invalid engineering inputs or an unsupported option. Do not expose accidental `KeyError`/`ZeroDivisionError` as the normal input-validation interface.
- Do not catch every exception and return `OK`, zero utilisation or an empty calculation. Unexpected programming faults must remain visible to tests and developers.
- The manager uses concurrent request threads, not one isolated process per module. Do not keep a "current calculation" in a global variable.
- A compute operation may be called repeatedly on the same inputs: live preview, explicit save, validation, optimisation and linking. It must not depend on call order.

## 8. Inputs, Identity and Form Schemas

### 8.1 Manager-owned keys

| Input key | Purpose |
| --- | --- |
| `client`, `project`, `projectno` | Project identity and sheet header. |
| `designer`, `checker` | Author/verifier identity. The manager and QA workflow own these values. |
| `date` | Sheet date. A fixed explicit date is required for reproducible rendered-baseline tests. |
| `subject` | Sheet subject. |
| `memberType`, `memberNumber` | Member/task identity. |
| `package` | Project issue/grouping package, such as `P01`. |
| `level` | Level/zone used for sorting. |
| `checks` | Dictionary of optional/mandatory check activation booleans. |
| `linkedFrom` | Provenance records appended when exchange values are applied. |

The manager also uses metadata such as `description`; do not reuse it for an engineering quantity. Accept and preserve unrelated manager keys rather than rejecting the whole input document for having extra properties.

Numeric member numbers contain at most four digits and are zero-padded by the library. Alphanumeric numbers begin with a letter and may include letters, digits, dots, underscores and hyphens. Do not use a module to invent a second numbering or filing system.

`identity()` should describe the current member plainly, for example `Column 0007 - 450 x 600`. It must not write files, normalise project paths or change project ownership.

### 8.2 Schema shape

Use `groups` for regular panels and `optional` for checkbox-controlled check panels:

```json
{
  "identity": {
    "typeLabel": "Member type",
    "numberLabel": "Member number",
    "typeOptions": ["Beam", "Column"]
  },
  "groups": [
    {
      "id": "geometry",
      "title": "Geometry",
      "fields": [
        {"id": "length_mm", "label": "Length", "type": "number", "unit": "mm", "default": 4000},
        {"id": "sectionKind", "label": "Section", "type": "select", "default": "rectangular",
         "options": [{"value": "rectangular", "label": "Rectangular"}, {"value": "circular", "label": "Circular"}]},
        {"id": "width_mm", "label": "Width", "type": "number", "unit": "mm", "default": 200,
         "showWhen": {"sectionKind": ["rectangular"]}},
        {"id": "diameter_mm", "label": "Diameter", "type": "number", "unit": "mm", "default": 250,
         "showWhen": {"sectionKind": ["circular"]}}
      ]
    }
  ],
  "optional": [
    {"id": "serviceability", "label": "Serviceability", "fields": [
      {"id": "deflectionLimit_mm", "label": "Deflection limit", "type": "number", "unit": "mm", "default": 20}
    ]}
  ],
  "alwaysOn": {"strength": true},
  "actions": []
}
```

This fragment demonstrates structure only. It is not a complete descriptor or a design basis. A real `schema()` merges the descriptor with this structure, and real `defaults()` supplies all field keys plus identity and checks.

### 8.3 Supported field types

| Type | Input value | Schema requirements |
| --- | --- | --- |
| `number` | Number, or validated numeric input accepted by the adapter | `id`, `label`, `default`; include `unit` where appropriate. |
| `text` | String | Use for text, not an unvalidated encoded calculation. |
| `textarea` | String | Multi-line text; escape it when printing as HTML. |
| `checkbox` | Boolean | A normal input field; distinct from an optional check-group toggle. |
| `select` | Prefer string enum values | Supply `options` as strings or `{value, label}` objects. |
| `catalogue` | Prefer a string identifier | Supply `catalogue`, optional `optionsBy`, and corresponding schema-level catalogue data. |

Other field properties:

- `width = "full"` requests a full-width field; otherwise the standard form generally uses half-width fields.
- `help` becomes the field tooltip. It does not create a validation rule.
- `showWhen` maps other field IDs to arrays of allowed **string** values. Multiple entries are all required to match.
- `catalogues` may contain a list of identifiers or a mapping from a selector value to identifier lists. String catalogue values are the safest match for the current selector implementation.
- Keep catalogue JSON reasonably small, typically below a few hundred kilobytes. Publish selection data, not an entire external document corpus.

### 8.4 Important current frontend limitations

These are implementation facts, not features to invent in a new schema:

- The current numeric form reader turns a blank numeric control into `0`. Do not rely on blank-versus-zero being preserved. Where omission has distinct engineering meaning, use an explicit mode/select/checkbox, then validate the appropriate fields.
- Hidden fields and disabled optional-group fields may still be present in submitted inputs. Presence does not mean that a check is enabled or a geometry branch is active.
- The current `showWhen` code examines a control's string `.value`. Do not assume it evaluates an arbitrary expression, performs numeric comparisons, or reliably represents a checkbox's checked state. Prefer select-based mode conditions.
- Properties such as `min`, `max`, nested objects, repeatable tables or a custom input type are not a general supported schema language. Enforce numeric limits in Python; propose an explicit platform change for unsupported UI requirements.
- Treat optional `presets` metadata as a feature to verify in the current frontend. Do not claim a preset button exists merely because a key was added to `schema()`.
- Field IDs must be unique across regular and optional groups. A group ID is not a replacement for a field ID.

### 8.5 Defaults and check activation

`defaults()` creates a new valid document, not a partially specified object that only works after the browser fills it in. Every field from all form groups must exist, even if its group starts disabled. Initialise `checks` consistently with optional groups and `alwaysOn`.

Derive mandatory checks in the engine as well as in schema metadata. A direct API caller can submit `{"checks": {"strength": false}}`; the engine must not let this disable a check that the engineering basis declares mandatory.

Keys not displayed as fields are allowed for manager identity, structured editors, provenance and documented module state. Explain each such key. Do not delete required manager keys to satisfy an overly literal "no orphan defaults" interpretation.

## 9. Engineering Engine and Result Document

### 9.1 Units and numeric policy

Use the suite's working engineering units consistently: force in N, length in mm, stress in MPa (`N/mm2`) and moment in N.mm, unless a clearly documented specialist calculation requires another coherent system. These are engineering working units, not all SI base units.

If the form accepts kN or kNm, convert once at the input boundary and retain the converted values in the result. Format back to display units at the output boundary. For example, `calcpad.force` converts N to kN and `calcpad.moment` converts N.mm to kNm; passing an already converted kN value into `force` gives the wrong answer.

Validate types, finiteness, physical ranges, enum membership and cross-field consistency before calculating. Reject booleans as numbers where they would otherwise be accepted by `float(True)`. Reject unknown material grades instead of silently choosing a default.

### 9.2 Error versus failed design

| Situation | Required behaviour |
| --- | --- |
| Missing required engineering field | `ValueError` identifying the field. |
| Nonnumeric, NaN or infinite supplied load/dimension | `ValueError`; never replace with zero. |
| Negative/zero geometry outside the brief's valid range | `ValueError`. |
| Unknown code option or unsupported material | `ValueError` with supported choices or an actionable description. |
| Valid input but demand exceeds capacity | Return the result, utilisation greater than `1.0`, summary `FAIL`, and full workings. |
| Valid input but the capacity is unattainable | Return `math.inf` for the affected utilisation, explain why, and summary `FAIL`. |
| Zero demand and zero capacity | Define the outcome in the brief. A common intentional convention is `0.0`; do not obtain it accidentally from a general divide-by-zero fallback. |
| Iteration fails to converge | Do not return the last trial as a verified capacity. Use the brief's explicit rejection/unattainable outcome and include convergence diagnostics. |
| Programming exception | Fix it and add a regression test; do not hide it behind an `OK` result. |

Zero or negative **loads** require a documented sign convention, not a blanket positive-value validator copied from dimension validation.

### 9.3 Result structure

A suggested result document is:

```text
module, version                     provenance
inputs                              normalised engineering input values
assumptions, limitations             explicit design basis
geometry, material, loads            derived state and governing actions
checks                              effective check activation
capacities                          capacities with units in names or documentation
factors                             reductions/amplifications and source references
cases                               case-specific results where applicable
governing                           selected case, axis, location and reason
util                                {check_name: numeric utilisation}
worstUtil                           maximum finite utilisation, or 0.0 if none
unattainable                        affected checks and reasons, if any
workings                            values/expression/reference records if useful
attachments                         optional PDF attachment descriptors
```

Only `util`, `worstUtil` and `checks` are universally required result keys. Organise the other fields for the actual domain; do not add empty abstractions merely to match this suggestion.

Every engineering value printed, used for optimisation or published through exchange must be reproducible from the result. Include the intermediate values needed to distinguish a wrong input mapping, factor, capacity or interaction equation. For multiple load cases, report the selected case and why it governs; do not combine unrelated peaks from different cases unless the design basis explicitly requires it.

### 9.4 Utilisation and summary semantics

- Each utilisation has a limit of `1.0` and a stable descriptive key, such as `bendingX` or `compression`.
- `worstUtil` is the largest **finite** value in `util`; use `0.0` when there are no finite values.
- An infinite utilisation must still force `FAIL`, even when `worstUtil` is `0.0` or less than one.
- Do not generate NaN as a design result. It indicates an invalid numerical path, not a satisfied check.
- Mandatory non-ratio rules must affect the overall status. Do not report `OK` when a reinforcement/geometry/detailing rule fails just because force ratios are low.
- `criticalCheck` must identify the true governing or unattainable check in readable terms.
- `headline` should say something useful outside the sheet, such as `82.4% - Bending about major axis` or `Capacity unattainable - compression buckling`.
- For a non-design analysis module with no checks, `util = {}` and `worstUtil = 0.0` may be appropriate. The headline must describe completion, not imply structural adequacy.

The HTTP layer replaces nonfinite floating-point values with JSON `null`. The revision snapshot encoder preserves them with tagged JSON values. Therefore the human-readable summary and report must identify unattainable checks explicitly; browser `null` is not a zero utilisation. Do not depend on custom object serialisation or `default=str` silently preserving the meaning of an engineering value.

### 9.5 Determinism and performance

The same inputs, approved data and engine version must produce the same result. Do not read the clock, random values, a live website or an unversioned network spreadsheet inside `compute()`.

Immutable published tables may be bundled as resources. A read-only cache of those resources must not change calculations based on earlier calls. Never mutate a cached catalogue record when applying a grade or choosing a section.

Bound iterations, search space and user-controlled input size. Do not assume request threads enforce a CPU deadline. No unbounded recursion, uncontrolled expression execution or subprocess/network work belongs in the ordinary calculation path.

## 10. Calculation Sheets and Rendering

### 10.1 Shared reporting APIs

Use the installed package, not its source-folder name:

```python
import calcpad
```

| API | Purpose |
| --- | --- |
| `row(label, equation, value, reference="")` | One workings row. Labels/values may contain HTML; escape untrusted text. |
| `table(title, rows)` | Standard calculation table of workings rows. |
| `grid(title, headers, rows, note="")` | Schedules, case tables and other column layouts. |
| `prose(title, body_html, weight=12)` | Narrative block with a pagination weight. |
| `badge(ratio)` | Shared utilisation indicator. |
| `number(value)` | Number formatting without an assumed force/moment conversion. |
| `force(value_N)` | Force display conversion/formatting in kN. |
| `moment(value_Nmm)` | Moment display conversion/formatting in kNm. |
| `render(inputs, blocks, ...)` | Shared pages, identity headers, embedded input JSON and optional standalone wrapper. |
| `calcpad.trace.as_text(result)` | Dotted-path internal-value inspection. |
| `calcpad.trace.report(inputs, result, title=...)` | Trace as printable calculation sheets. |

The report function builds blocks and delegates layout. Do not emit another `<html>` wrapper, logo system, header/footer, page-number scheme or `@page` stylesheet.

### 10.2 Required rendering behaviour

- Accept both `standalone=False` for in-app content and `standalone=True` for filed HTML.
- Accept and forward `appendix`, `anchor_prefix` and `contents_href` unchanged to the shared renderer.
- Use the standard `class="calc-page"` page structure created by `calcpad`; the contract checker and package parser depend on it.
- Use a unique embedded input `data_id`, conventionally `<module-id>-inputs`.
- Show engineering input values from the normalised result; use the incoming input document for manager-owned identity fields.
- Print assumptions, applicability limits, effective checks, formula, substitution/intermediate values, units, capacity, demand, utilisation and governing case as required by the brief.
- Carry real clause references on engineering capacity and factor rows. Do not manufacture clauses for a teaching model or uncited rule.
- Escape user/catalogue/source text with `html.escape` or `calcpad.esc` before inserting it into raw HTML strings.
- Keep any diagram assets self-contained in filed HTML, such as an appropriate embedded image. Do not link a saved report to a temporary file, local development server or network image.
- Do not perform engineering arithmetic in `report.py`. Formatting and unit-display conversion are acceptable; choosing an engineering factor or recomputing a capacity is not.

### 10.3 Pagination and styles

Shared pagination packs whole blocks; it does not make an arbitrarily large single table fit on a page. Split long case/schedule tables into sensible blocks. Set an appropriate `weight` for prose whose height cannot be inferred and visually verify long reports.

Use the shared theme by default. The legacy `module_dir` stylesheet mechanism can select a module-local stylesheet for standalone rendering, whereas live and collated views use shared styles. Do not rely on custom local CSS being preserved in every workflow. Any unavoidable style extension needs live, standalone and snapshot-package testing.

Both the formal render signature and its anchor parameters remain required even though the current saved-revision package path uses stored HTML instead of calling the current module's renderer. Development checks and other consumers still call this interface directly.

## 11. Saving, Reopening and Package Export

### 11.1 Persistence belongs to the manager

The current project filing branch is:

```text
<project>/09-Doc_WRK/01-CAL/10-IN_TOOL/
  innocalc-library.json
  <descriptor.folder>/<project package>/
    <member>-<number>-<timestamp>-<initials>.html
    <member>-<number>-<timestamp>-<initials>.pdf
    superseded/
  .revisions/
    <snapshot hash>.json
    assets/<attachment hash>.pdf
```

Do not construct these paths in the module. Do not write the library index, assign revision numbers, move superseded files, set verifier endorsements or submit PDF jobs yourself.

### 11.2 What is saved

On save, the manager combines its project metadata with supplied inputs, computes again, obtains the summary and identity, and asks for standalone report HTML. The library stores a content-addressed snapshot including inputs, result, descriptor, summary and rendered HTML. PDF attachments are copied into immutable snapshot assets and verified by hashes.

Rendering must therefore be self-contained and deterministic enough to audit. A mutable catalogue or external attachment must not silently change the content of an already saved revision.

Reopening the editor retrieves saved inputs. A live recalculation may use the **current** engine; this is distinct from exporting an existing saved revision. Do not claim that editing an old input document automatically runs its historical engine binary.

### 11.3 What is exported

The current package builder uses the saved snapshot, including its saved summary, and adds package navigation anchors. It does not call the latest engine to regenerate an old revision. Existing revisions without snapshots require their filed PDF; where that is absent, the user must review and explicitly save a new revision.

The printed identity in an old snapshot remains what was saved. Later QA endorsement is recorded in the library/verification records and is not automatically rewritten into old printed sheets.

Back up the whole calculation branch, including `.revisions`. If an integrity check fails, do not bypass it or recompute a replacement under the old revision number.

## 12. Actions and Exchange Between Modules

### 12.1 Optional module actions

Declare only implemented actions:

```json
{"actions": [{"id": "optimise-weight", "label": "Find lightest satisfactory section"}]}
```

Implement `run_action(action_id, inputs) -> dict`. Supported response members include:

| Member | Meaning |
| --- | --- |
| `inputs` | Replacement input document. Return a complete document preserving identity and unrelated fields, not just a patch. |
| `message` | Human-readable outcome. |
| `file` | Download descriptor with `name`, text `content`, and MIME `type`. |

Actions must be deterministic/idempotent for the same source document, must not write project files, and must have bounded searches. An optimisation must check all applicable requirements for every candidate. Finite `worstUtil <= 1` alone is insufficient if another utilisation is infinite or a non-ratio rule fails. Report when no candidate works; do not quietly return the last candidate as a solution.

### 12.2 Exchange contract

Implement only the hooks needed by the brief:

- `exchange(inputs, result) -> dict`: publishes values derived from the supplied result.
- `accepts() -> list[str]`: lists supported envelope groups, such as `axial` or `moments`.
- `apply_exchange(inputs, payload) -> dict`: returns a copied input document with supported values applied and provenance appended.

An illustrative envelope is:

```json
{
  "schema": "innocalc.exchange/1",
  "source": {
    "module": "source-module",
    "version": "0.1.0",
    "memberType": "Beam",
    "memberNumber": "0001",
    "package": "P01",
    "level": "L01",
    "title": "Beam 0001"
  },
  "axial": {"compression_kN": 120.0, "tension_kN": 0.0},
  "moments": {"Mx_kNm": 30.0, "My_kNm": 5.0},
  "geometry": {"length_mm": 4000.0},
  "material": {"grade": "specified grade", "fy_MPa": 300.0},
  "utilisation": {"worstUtil": 0.75, "criticalCheck": "Bending", "status": "OK"}
}
```

Rules:

1. Never import another calculation module to read its internal data structures.
2. Validate the envelope schema and any values actually consumed. Ignore unknown keys and tolerate missing groups by preserving target values.
3. Agree exact group names, field names, axes, units and signs between producer and consumer. Unit-bearing names do not replace semantic agreement.
4. Preserve established consumer keys for compatibility. Legacy exchange examples contain some shorthand fields; do not rename them unilaterally or assume a new unit-suffixed key is automatically consumed.
5. Convert units exactly once. Never overwrite manager identity with source identity.
6. Append the source descriptor to a copied `linkedFrom` list and show relevant provenance in the report.
7. Links are snapshots of transferred values, not a dependency graph. They do not update when the upstream calculation changes.

**Current implementation caveat:** the manager's Link operation recomputes the source from its stored inputs using the currently loaded source engine before calling `exchange()`. It does not currently transfer directly from the historical revision snapshot. Test and disclose version-sensitive linking behaviour; do not claim historical-result transfer without an explicit platform change.

## 13. Advanced Editors and Attachments

### 13.1 Keep ordinary modules ordinary

Most calculations need schema fields, optional groups and shared report blocks only. Do not introduce a custom frontend because the engineering calculation is complex. If the current field types cannot represent a required input, identify the missing capability and obtain a platform decision before implementation.

The Calculation Pad has a specialist cell editor. `editor = "cells"`, cell types and editable-report attributes refer to that specific implementation, not a universal spreadsheet/table editor that any module can assume exists.

For interactive report editing, the registry checks whether the `render` signature **explicitly** declares `interactive`. A catch-all `**kwargs` alone is not the same declaration. Keep interactive controls out of standalone/printed output and follow existing supported `data-pad-*` bindings if adopting that editor.

### 13.2 PDF attachments

When explicitly required, `result["attachments"]` is a list of descriptors such as:

```json
{"attachments": [{"path": "C:/approved/drawing.pdf", "pages": "1,3-5", "title": "Connection detail", "exists": true}]}
```

Use the file-picker/attachment capabilities already supported by the manager. Do not add arbitrary filesystem browsing to an engine. Existence of an external file is an I/O concern; keep it outside pure engineering arithmetic and explicitly document any adapter-level exception for an attachment module.

The manager freezes attachment bytes on save. Never supply `snapshotPath` or snapshot hashes yourself. Missing attachments must not be presented as successfully saved. Validate page selections rather than relying on permissive parsing to silently select nothing.

The current collation code inserts a calculation's attachment list after that calculation's rendered body. Do not promise arbitrary in-body attachment placement from this list alone; inspect and test the actual package assembly if exact insertion positions matter.

## 14. Complete Teaching Implementation

This example is deliberately small and fully specified so its code and interface can be tested. It calculates a **direct stress ratio against a user-supplied allowable stress**:

```text
area_mm2 = width_mm * depth_mm
force_N = force_kN * 1000
stress_MPa = force_N / area_mm2
capacity_N = allowable_MPa * area_mm2
utilisation = force_N / capacity_N
```

**It is not a structural design module or a substitute for a material standard.** It omits buckling, bending, shear, detailing, resistance factors, load combinations and every other real design requirement. Do not enable it for project design. Arithmetic compatibility tests may pass while its engineering-release validation intentionally fails.

### 14.1 Generate the teaching package

Run this only in a development workspace where the ID is not already registered:

```powershell
& $Python -m tooling new interface-example --name "Interface Example" --category General --standard "Educational direct-stress model; not a design standard" --filing-folder "EXAMPLE - NOT FOR DESIGN" --owner "Responsible engineer"
```

This creates `calculations/general/interface_example/`, package `ic_interface_example`, version `v0.0.1`, and a disabled manifest entry. Retain the generated `pyproject.toml`, `module.toml`, `version.py`, `__init__.py` and `dev.py`. In particular, retain `status = "planned"` in module metadata and `enabled = false` in the suite manifest.

Replace the following generated files with these **complete teaching implementations**. File markers are included so the examples can be extracted and tested mechanically.

### 14.2 Engine

<!-- example-file: src/ic_interface_example/engine.py -->
```python
from __future__ import annotations

import math
from typing import Any

from .version import VERSION


def require_number(inputs: dict[str, Any], key: str, *, positive: bool) -> float:
    if key not in inputs or isinstance(inputs[key], bool):
        raise ValueError(f"{key} must be supplied as a finite number")
    try:
        value = float(inputs[key])
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{key} must be supplied as a finite number") from exc
    if not math.isfinite(value):
        raise ValueError(f"{key} must be finite")
    if value < 0 or (positive and value == 0):
        requirement = "greater than zero" if positive else "zero or greater"
        raise ValueError(f"{key} must be {requirement}")
    return value


def compute(inputs: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(inputs, dict):
        raise ValueError("An input dictionary is required")
    width = require_number(inputs, "width_mm", positive=True)
    depth = require_number(inputs, "depth_mm", positive=True)
    force_kN = require_number(inputs, "force_kN", positive=False)
    allowable = require_number(inputs, "allowable_MPa", positive=False)
    area = width * depth
    force = force_kN * 1000.0
    if not math.isfinite(area) or area <= 0 or not math.isfinite(force):
        raise ValueError("Dimensions or force exceed the supported numerical range")
    capacity = allowable * area
    stress = force / area
    if not math.isfinite(capacity) or not math.isfinite(stress):
        raise ValueError("Stress or capacity exceeds the supported numerical range")
    ratio = force / capacity if capacity > 0 else (math.inf if force > 0 else 0.0)
    if capacity > 0 and not math.isfinite(ratio):
        raise ValueError("Utilisation exceeds the supported numerical range")
    return {
        "module": "interface-example",
        "version": VERSION,
        "inputs": {"width_mm": width, "depth_mm": depth,
                   "force_kN": force_kN, "allowable_MPa": allowable},
        "geometry": {"area_mm2": area},
        "loads": {"force_N": force},
        "stress_MPa": stress,
        "capacity_N": capacity,
        "checks": {"directStress": True},
        "util": {"directStress": ratio},
        "worstUtil": ratio if math.isfinite(ratio) else 0.0,
        "unattainable": ["Zero allowable stress with nonzero force"] if math.isinf(ratio) else [],
        "limitations": ["Teaching model only; not approved for structural design"],
    }
```

### 14.3 Adapter, metadata, schema and summary

<!-- example-file: src/ic_interface_example/headless.py -->
```python
from __future__ import annotations

import math
import tomllib
from copy import deepcopy
from importlib.resources import files
from typing import Any

from . import engine, report
from .version import VERSION

DESCRIPTOR = {
    **tomllib.loads(files(__package__).joinpath("module.toml").read_text(encoding="utf-8")),
    "version": VERSION,
}


def descriptor() -> dict[str, Any]:
    return deepcopy(DESCRIPTOR)


def schema() -> dict[str, Any]:
    return {
        **descriptor(),
        "identity": {"typeLabel": "Member type", "numberLabel": "Member number",
                     "typeOptions": ["Example"]},
        "groups": [
            {"id": "geometry", "title": "Geometry", "fields": [
                {"id": "width_mm", "label": "Width", "type": "number", "unit": "mm", "default": 100.0},
                {"id": "depth_mm", "label": "Depth", "type": "number", "unit": "mm", "default": 200.0},
            ]},
            {"id": "actions", "title": "Direct stress model", "fields": [
                {"id": "force_kN", "label": "Force magnitude", "type": "number", "unit": "kN", "default": 100.0},
                {"id": "allowable_MPa", "label": "Supplied allowable stress", "type": "number", "unit": "MPa", "default": 10.0},
            ]},
        ],
        "optional": [],
        "alwaysOn": {"directStress": True},
        "actions": [],
    }


def defaults() -> dict[str, Any]:
    values = {
        "memberType": "Example", "memberNumber": "0001", "package": "Unallocated",
        "level": "", "subject": DESCRIPTOR["defaultSubject"],
        "checks": {"directStress": True},
    }
    for group in schema()["groups"]:
        for field in group["fields"]:
            values[field["id"]] = field["default"]
    return values


def compute(inputs: dict[str, Any]) -> dict[str, Any]:
    return engine.compute(inputs)


def render(inputs: dict[str, Any], result: dict[str, Any], *, standalone: bool = False,
           appendix: list[str] | None = None, anchor_prefix: str = "",
           contents_href: str = "") -> str:
    return report.render(inputs, result, standalone=standalone, appendix=appendix,
                         anchor_prefix=anchor_prefix, contents_href=contents_href)


def summarise(result: dict[str, Any]) -> dict[str, Any]:
    ratio = result["util"]["directStress"]
    if not math.isfinite(ratio):
        return {"worstUtil": result["worstUtil"], "criticalCheck": "Direct stress",
                "status": "FAIL", "headline": "Teaching model: direct-stress capacity unattainable"}
    return {"worstUtil": result["worstUtil"], "criticalCheck": "Direct stress",
            "status": "OK" if ratio <= 1.0 else "FAIL",
            "headline": f"Teaching model: {ratio * 100:.1f}% - Direct stress"}


def identity(inputs: dict[str, Any]) -> dict[str, Any]:
    member_type = str(inputs.get("memberType") or "Example")
    number = str(inputs.get("memberNumber") or "")
    return {"memberType": member_type, "memberNumber": number,
            "package": str(inputs.get("package") or "Unallocated"),
            "level": str(inputs.get("level") or ""), "calcType": DESCRIPTOR["calcType"],
            "title": f"{member_type} {number} - teaching example".strip()}


def validate(cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    from .validation import validate as run_validation
    return run_validation(cases)
```

### 14.4 Report

<!-- example-file: src/ic_interface_example/report.py -->
```python
from __future__ import annotations

from html import escape
from typing import Any

import calcpad


def render(inputs: dict[str, Any], result: dict[str, Any], *, standalone: bool = False,
           appendix: list[str] | None = None, anchor_prefix: str = "",
           contents_href: str = "") -> str:
    values = result["inputs"]
    reference = "Illustrative definition; not a design clause"
    rows = [
        calcpad.row("Width", "b", f"{calcpad.number(values['width_mm'])} mm", reference),
        calcpad.row("Depth", "d", f"{calcpad.number(values['depth_mm'])} mm", reference),
        calcpad.row("Area", "A = b d", f"{calcpad.number(result['geometry']['area_mm2'])} mm2", reference),
        calcpad.row("Force magnitude", "F", f"{calcpad.force(result['loads']['force_N'])} kN", reference),
        calcpad.row("Supplied allowable stress", "f_allow", f"{calcpad.number(values['allowable_MPa'])} MPa", reference),
        calcpad.row("Direct stress", "sigma = F / A", f"{calcpad.number(result['stress_MPa'])} MPa", reference),
        calcpad.row("Allowable force", "F_allow = f_allow A", f"{calcpad.force(result['capacity_N'])} kN", reference),
        calcpad.row("Utilisation", "F / F_allow", calcpad.badge(result['util']['directStress']), reference),
    ]
    limitations = "".join(f"<p>{escape(item)}</p>" for item in result["limitations"])
    blocks = [calcpad.prose("Limitations", limitations, weight=4),
              calcpad.table("Direct stress model", rows)]
    if result["unattainable"]:
        reasons = "".join(f"<p>{escape(item)}</p>" for item in result["unattainable"])
        blocks.append(calcpad.prose("Unattainable condition", reasons, weight=4))
    return calcpad.render(inputs, blocks, standalone=standalone, appendix=appendix,
                          anchor_prefix=anchor_prefix, contents_href=contents_href,
                          default_subject="Interface Example", data_id="interface-example-inputs")
```

### 14.5 Validation

The arithmetic fixture is exact: `100 kN / (100 mm * 200 mm) = 5 MPa`, capacity `200000 N`, utilisation `0.5`.

This validation deliberately withholds **engineering approval**, even if all arithmetic fixtures pass. For a real module, replace the teaching validation with the complete approved self-consistency and worked-example validation specified in Sections 15 and 16. Do not make a real release pass by deleting an approval warning while leaving the teaching engine in place.

<!-- example-file: src/ic_interface_example/validation.py -->
```python
from __future__ import annotations

import math
from typing import Any

from .engine import compute
from .version import VERSION


def validate(cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    baseline = {
        "name": "Exact direct-stress arithmetic",
        "inputs": {"width_mm": 100.0, "depth_mm": 200.0,
                   "force_kN": 100.0, "allowable_MPa": 10.0},
        "expect": {"geometry.area_mm2": 20000.0, "stress_MPa": 5.0,
                   "capacity_N": 200000.0, "util.directStress": 0.5},
    }
    supplied = [baseline] if cases is None else cases
    outcomes = []
    for case in supplied:
        problems = []
        try:
            result = compute(case["inputs"])
            expected_values = case.get("expect") or {}
            if not expected_values:
                problems.append("A validation case must contain expected values")
            for path, expected in expected_values.items():
                actual: Any = result
                for segment in path.split("."):
                    actual = actual[segment]
                if not math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-12):
                    problems.append(f"{path}: {actual} != {expected}")
        except (ValueError, KeyError, TypeError) as exc:
            problems.append(str(exc))
        outcomes.append({"name": case.get("name", "Unnamed"), "ok": not problems,
                         "failures": problems})
    return {"ok": False, "mode": "worked-examples", "module": "interface-example",
            "version": VERSION, "tested": len(outcomes), "cases": outcomes,
            "failures": ["Teaching example has no approved engineering design basis"]}
```

### 14.6 Teaching tests

Add the following test file. Run it on its own to verify the illustrative implementation. The scaffold's production release-gate test must still fail because `validate()["ok"]` is intentionally false.

<!-- example-file: tests/test_teaching_example.py -->
```python
from __future__ import annotations

import math
import unittest
from copy import deepcopy

from ic_interface_example import headless
from packages.innocalc_sdk import check_contract


class TeachingExampleTests(unittest.TestCase):
    def test_interface_contract(self):
        outcome = check_contract(headless)
        self.assertTrue(outcome["ok"], outcome["failures"])

    def test_exact_arithmetic_and_unchanged_inputs(self):
        inputs = headless.defaults()
        before = deepcopy(inputs)
        result = headless.compute(inputs)
        self.assertEqual(inputs, before)
        self.assertEqual(result["geometry"]["area_mm2"], 20000.0)
        self.assertEqual(result["stress_MPa"], 5.0)
        self.assertEqual(result["capacity_N"], 200000.0)
        self.assertEqual(result["util"]["directStress"], 0.5)

    def test_invalid_or_missing_input(self):
        for value in (None, True, "bad", float("nan"), float("inf"), -1, 0):
            with self.subTest(value=value):
                inputs = headless.defaults()
                inputs["width_mm"] = value
                with self.assertRaises(ValueError):
                    headless.compute(inputs)
        inputs = headless.defaults()
        del inputs["force_kN"]
        with self.assertRaises(ValueError):
            headless.compute(inputs)

    def test_limit_and_failed_design(self):
        inputs = headless.defaults()
        inputs["force_kN"] = 200.0
        self.assertEqual(headless.summarise(headless.compute(inputs))["status"], "OK")
        inputs["force_kN"] = 201.0
        self.assertEqual(headless.summarise(headless.compute(inputs))["status"], "FAIL")

    def test_unattainable_capacity(self):
        inputs = headless.defaults()
        inputs["allowable_MPa"] = 0.0
        result = headless.compute(inputs)
        self.assertEqual(result["util"]["directStress"], math.inf)
        self.assertEqual(result["worstUtil"], 0.0)
        self.assertEqual(headless.summarise(result)["status"], "FAIL")
        inputs["force_kN"] = 0.0
        self.assertEqual(headless.compute(inputs)["util"]["directStress"], 0.0)

    def test_mandatory_check_and_fresh_defaults(self):
        first, second = headless.defaults(), headless.defaults()
        first["checks"]["directStress"] = False
        self.assertTrue(second["checks"]["directStress"])
        self.assertTrue(headless.compute(first)["checks"]["directStress"])

    def test_report_navigation_and_appendix(self):
        inputs = headless.defaults()
        inputs["date"] = "01/01/2026"
        result = headless.compute(inputs)
        for standalone in (False, True):
            document = headless.render(inputs, result, standalone=standalone,
                                       appendix=["<p>Appendix fixture</p>"],
                                       anchor_prefix="example-test", contents_href="#contents-test")
            self.assertIn('class="calc-page"', document)
            self.assertIn("example-test", document)
            self.assertIn("#contents-test", document)
            self.assertIn("Appendix fixture", document)
            self.assertIn("not approved for structural design", document)

    def test_arithmetic_passes_but_release_remains_blocked(self):
        validation = headless.validate()
        self.assertTrue(all(case["ok"] for case in validation["cases"]))
        self.assertFalse(validation["ok"])
        self.assertEqual(headless.descriptor()["status"], "planned")


if __name__ == "__main__":
    unittest.main()
```

### 14.7 Run the example

```powershell
& $Python -m pip install --no-build-isolation --no-deps -e calculations/general/interface_example
& $Python -m tooling dev interface-example --schema
& $Python -m tooling dev interface-example --trace
& $Python -m tooling dev interface-example --html artifacts/interface-example/sheet.html
& $Python -m tooling check interface-example
& $Python -m unittest discover -s calculations/general/interface_example/tests -p test_teaching_example.py -v
& $Python -m tooling check interface-example --validate
```

Expected outcomes: the schema, compute, trace, HTML, basic contract and teaching tests succeed. The final `--validate` command exits unsuccessfully because there is no approved engineering design basis. The module remains unavailable in the production chooser. This is intentional, not a reason to remove a test or change the manifest to enabled.

## 15. Automated Testing and Validation

### 15.1 Minimum test matrix for a real module

| Test class | Required coverage |
| --- | --- |
| Contract | Seven functions, render signature, descriptor, identity and result shapes. |
| Defaults/schema | Every form field has a valid default; IDs are unique; nested defaults are independent. |
| Arithmetic | Independently established values for each major intermediate factor, capacity and interaction. |
| Limits | At, just below and just above applicable boundaries and utilisation `1.0`. |
| Input rejection | Missing required values, malformed strings, booleans as numbers, NaN/infinity, invalid enum values and impossible combinations. |
| Check activation | Each optional group on/off, mandatory checks forced on, inactive geometry fields ignored appropriately. |
| Units and signs | Equivalent cases expressed through approved input conversions; axis and tension/compression conventions. |
| Numerical failure | Zero capacity, unattainable checks, convergence failure and extreme supported values. |
| State isolation | Inputs unchanged, repeated computations equal, interleaved cases and concurrent calls do not leak state. |
| Reporting | Both standalone modes, references, complete workings, escaping, long text, pagination and no recomputation. |
| Exchange/actions | Missing groups, unknown fields, unit conversion, preserved identity, provenance and no-solution optimisations. |
| Persistence | Save/reopen input meaning, snapshot integrity, old-input compatibility and no implicit rewrite of historical revisions. |
| Packaging | Editable install, built wheel imports and bundled resources. |
| Workflow | Manager form, calculate, save, reopen, PDF, package export and required attachments. |

Tests must include nonzero and failing designs. A sweep of zero-load defaults cannot establish design correctness.

### 15.2 `validate(cases=None)` for a real module

With no supplied cases, run the module's documented self-consistency/retained validation set. With supplied cases, run their expected-value comparisons. Return a structured dictionary such as:

```json
{
  "ok": true,
  "mode": "worked-examples",
  "module": "real-module-id",
  "version": "0.1.0",
  "tested": 2,
  "failures": [],
  "cases": [
    {"name": "Case 1", "ok": true, "checks": []},
    {"name": "Case 2", "ok": true, "checks": []}
  ]
}
```

Populate the comparison detail; empty `checks` in this envelope only illustrates shape. Return `ok = false` if a required case fails, the required reference set is missing, or no expected values were actually compared. Count tested cases accurately. Never treat an empty list and `all([])` as evidence of coverage.

Use the existing case convention:

```json
{
  "cases": [
    {
      "name": "Independently checked example",
      "inputs": {"width_mm": 100.0, "depth_mm": 200.0, "force_kN": 100.0, "allowable_MPa": 10.0},
      "tolerance": 0.001,
      "tolerances": {"stress_MPa": 0.0001},
      "expect": {"geometry.area_mm2": 20000.0, "stress_MPa": 5.0, "util.directStress": 0.5}
    }
  ]
}
```

These numbers belong only to the teaching arithmetic. Supply the real module's own values and independently agreed tolerances. Define how per-path tolerances override global tolerance, how zero expected values use an absolute tolerance, and how nonfinite expected results are represented. Do not apply a universal percentage to dimensional zero values.

The shared runner accepts either a case list or a JSON wrapper with `cases`. It passes cases to the module; it does not implement the module's numerical comparison logic for you.

### 15.3 What the SDK does and does not prove

The current [../packages/innocalc_sdk/contracts.py](../packages/innocalc_sdk/contracts.py) checks callable functions, selected descriptor keys, field/default coverage, default-input mutation, repeatability on defaults, required result keys, finite maximum utilisation, summary fields, a failing-result status condition, identity fields, the render signature and output/navigation markers.

It does **not** establish complete type/schema validity, all invalid-input behaviours, standards compliance, clause coverage, every branch, concurrency safety, report numerical provenance, browser layout, actual PDF correctness or engineering approval. Write the missing tests.

`tooling check <id>` can inspect an explicitly named disabled module. `tooling check --all` checks enabled modules, so a disabled draft can otherwise be absent from an all-modules run. Always name the new module while developing it.

### 15.4 Development and release commands

Adapt these to the generated path and package:

```powershell
& $Python -m pip install --no-build-isolation --no-deps -e calculations/timber/timber_member
& $Python -m tooling dev timber-member --schema
& $Python -m tooling dev timber-member --trace
& $Python -m tooling dev timber-member examples-input.json --html artifacts/timber/sheet.html
& $Python -m tooling dev timber-member --trace-html artifacts/timber/trace.html
& $Python -m tooling dev timber-member --validate
& $Python -m tooling dev timber-member --validate worked-cases.json
& $Python -m tooling check timber-member --validate
& $Python -m unittest discover -s calculations/timber/timber_member/tests -v
& $Python -m unittest discover -s tests -v
& $Python -m pip check
```

Paths such as `examples-input.json` and `worked-cases.json` above are placeholders for existing reviewed files. Do not fabricate a successful command run when a fixture has not been supplied.

The shared CLI starts from defaults and merges an input JSON file. That convenience can mask missing fields during development. Input-rejection tests must call `compute()` directly with the deliberately incomplete document.

After installation, `python -m ic_timber_member.dev ...` is the standalone equivalent. Validation output formats may differ in existing specialist modules; preserve their extra reference-validation tools rather than replacing them with a weaker default-only check.

## 16. Third-party Reference Validation

Use the full Part D procedure in [../docs/NEW-MODULE-BRIEF.md](../docs/NEW-MODULE-BRIEF.md) when the brief provides a reference corpus. The essential requirements are repeated here so an AI cannot omit them.

### 16.1 Inventory and classify

List every reference document and calculation sheet. Record producing software/version, sheet type, date/revision, catalogue designation, load cases and the module scope it can test. Read at least one complete example of each distinct sheet type.

Distinguish actions/factors the reference **actually used** from merely entered values. Eccentricities, amplifications, effective lengths and derived actions often differ from manual-entry fields. Identify the governing ratio in the reference summary, not just the first utilisation printed.

State exclusions with reasons and counts. Ask for a scope decision where references mix unsupported products, load derivation, analysis-only sheets and member design. Do not silently drop difficult cases.

### 16.2 Extract reproducibly

Write a bounded extraction script, not a handwritten table of selected answers. Prefer structured inputs/exports or appropriate PDF/workbook parsers. Preserve originals unchanged.

For each case retain source path, page/sheet, producing version, input mapping, published values and units, printed precision, case identity, source governing utilisation and exclusions. Split multi-case sheets into separate cases so values from one case are never compared with another.

If regex is necessary, bound search windows and distinguish qualified symbols from substrings of longer equations. Test extraction against visually inspected examples.

### 16.3 Compare the correct quantities

Compare each published value with its corresponding result path in the same units and with the agreed tolerance. Account for the reference's printed rounding: half of the last printed digit can explain a small difference. Report the comparison rule explicitly rather than hiding deviations by increasing tolerance.

Compare governing utilisation and intermediate values, not only the headline. Missing published values should be identified as untested, not filled with invented values. Save machine-readable results and a readable parameter-level report.

### 16.4 Diagnose without tuning

Classify discrepancies as a module defect, extraction defect, permitted reference conservatism, out-of-scope bespoke rule, or catalogue-data gap. Verify one representative discrepancy arithmetically before changing the engine.

Any engineering change needs a defensible source and applicability explanation. Do not back-calculate catalogue properties to make a reference match; do not reproduce a proprietary/bespoke rule as if it were a standard clause. Rerun both the reference comparison and the module regression suite after a correction.

### 16.5 Compile evidence and report residuals

Where required, produce a linked validation PDF with an index, per-case comparison record, original reference and corresponding module calculation. Verify final page counts and link destinations after PDF insertion. Reuse shared export support instead of implementing another PDF system.

Report total reference sheets, validated cases, exclusions, agreement counts, defects corrected, residual differences, conservatism direction and the generated evidence paths. Independent review must decide whether residuals are acceptable; the AI must not declare them accepted on its own.

## 17. Manager Integration and PDF Acceptance

### 17.1 Runtime call map

This table explains integration; the module does not implement these HTTP routes.

| Manager route / operation | Module interface used |
| --- | --- |
| `GET /api/modules` | Loaded descriptors and callable support metadata. |
| `GET /api/module/schema?module=<id>` | `schema()` and `defaults()`. |
| `POST /api/calculate` | `compute`, `summarise`, `identity`, `render`; inputs are supplied in a dictionary. |
| `POST /api/module/action` | `run_action(action_id, inputs)`. |
| `POST /api/module/validate` | `validate(cases)`. |
| `POST /api/calculation/save` | Recompute, summarise, identify, standalone render, then manager-owned save/snapshot/PDF job. |
| `GET /api/calculation` | Returns saved library inputs/metadata; a subsequent editor calculation may use current code. |
| `POST /api/calculation/exchange` | Current source compute/exchange followed by target `apply_exchange`. |
| Package build | Uses saved snapshots or legacy filed PDFs; not a fresh module calculation. |

Authenticated/project operations require the manager's session token and project identifiers in addition to module-specific arguments. Use the existing UI or smoke tooling; do not hardcode, log or commit session tokens.

### 17.2 Integration acceptance sequence

1. Pass direct module tests and reference checks while the module is disabled.
2. For UI integration testing before production approval, use an isolated development copy/manifest with test-only `available` metadata. Do not enable an unapproved draft in the live project environment.
3. Restart the test manager. Check `/api/ping` and `/api/modules` for load problems and the correct ID/version/category.
4. Open a disposable project and create a calculation. Check every field, default, unit, selector, conditional panel and optional group.
5. Test nonzero valid, invalid, failing and unattainable cases. Confirm the summary and report agree and the error messages identify the problem.
6. Save, wait for the PDF job result, reopen and verify the engineering inputs and identity are preserved.
7. Save a changed revision and confirm superseded revisions remain available under the same calculation identity.
8. Test required actions and links, including provenance and unit conversion.
9. Export a package containing the new module and another existing module. Verify saved summaries match printed content.
10. Inspect the PDF and attachments, not just the HTTP success response.

Use isolated smoke storage:

```powershell
& $Python -m tooling.smoke --no-pdf
& $Python -m tooling.smoke
```

The first checks HTTP compute/save/reopen and explicitly records `pdfChecked = false`. It is **not** a PDF acceptance test. The second needs a working browser installation and tests real saved-sheet/package printing. Both discover enabled modules; they do not replace interactive testing of all non-default input branches.

### 17.3 PDF checklist

- PDF files actually exist, have nontrivial size and open without errors.
- All expected pages, tables, clauses, symbols, units, assumptions and diagrams are present.
- Long headings, text and tables do not clip or overlap at supported page sizes.
- The contents index and back-links land on the correct final pages.
- Attached pages are the intended frozen documents, in the intended order.
- Reported page counts match the final merged PDF.
- No interactive inputs, development hints or missing remote assets appear in the print.
- Failure to print is reported as failure, not as a completed verified package.

At the last recorded platform verification, Chromium returned without producing PDFs. See [../docs/IMPLEMENTATION-STATUS.md](../docs/IMPLEMENTATION-STATUS.md) for the current evidence and remaining gate. A new module must not inherit a claim of PDF verification from passing arithmetic or HTTP tests. Resolve or explicitly report any environment blocker.

## 18. Release, Compatibility and Maintenance

### 18.1 Release procedure

1. Complete the approved scope and all required tests/reference evidence.
2. Obtain independent engineering review and record reviewer, date, version and scope of approval.
3. Verify package metadata, engine version, standard edition and input schema version.
4. Set the approved module's metadata to `status = "available"` and its manifest record to `enabled = true`.
5. Restart Manager and run the combined module, suite and integration gates on the intended deployment.
6. Retain source revisions, dependency locks, reference evidence and actual test output. Release provenance requires reviewed, committed source states; do not commit automatically without authorisation.

```powershell
& $Python -m tooling check --all --validate
& $Python -m unittest discover -s tests -v
& $Python -m tooling release-check --output artifacts/suite-release.json
```

`release-check` refuses dirty repositories and records repository commits plus the suite manifest. It does not run every module's tests, approve engineering, fetch repositories or publish software. The shared CI workflow does not obtain the private legacy module repositories automatically; run the full suite in a workspace containing the required modules.

### 18.2 Saved-input compatibility

Permanent module IDs and filing folders must not be renamed to clean up source layout. Field IDs, enum values, units and exchange meanings are also compatibility surfaces once inputs have been saved.

Do not change a field from mm to m under the same key or reinterpret an old load convention silently. Add a reviewed normalisation/migration strategy, explicit version handling and old-input fixtures. The current manager records version metadata but has no generic automatic `migrate_inputs` hook that a module can assume will be called.

Legacy inputs may not carry an input schema version. Document how they are identified and supported. Do not overwrite old snapshots as part of normalisation. A source-code update and a saved engineering revision are separate events.

### 18.3 Maintenance and generated files

Put generated traces, sheets, comparison reports and temporary extracts under `artifacts/`. Keep source evidence, hand-reviewed fixtures and expected values in version-controlled module locations.

```powershell
& $Python -m tooling clean
& $Python -m tooling clean --apply
```

The first is a dry run. Cleanup excludes references, Git history, environments, assets, data and artifacts; it removes known source build/cache metadata. Never broaden it to delete reference folders or project data just because they are large.

## 19. Troubleshooting

| Symptom | Check / corrective action |
| --- | --- |
| Module absent from New calculation | Check manifest `enabled`, descriptor `status`, then restart and inspect `moduleProblems`. A disabled module is intentionally absent. |
| Startup fails before module import | Validate manifest TOML, version fields, duplicate IDs/paths/filing folders and category spelling. |
| `ModuleNotFoundError: calcpad` | Use the suite environment and explicit setup; do not create another private copy of the reporting package. |
| Module works only from its own folder | Check installation, `src` discovery, resource packaging and working-directory assumptions. |
| Catalogue selection resets on reopen | Ensure saved identifiers exist in the current catalogue and selector keys agree with `optionsBy`; use string IDs. |
| Hidden input still affects results | Guard by the active engineering mode/check, not by field presence or UI visibility. |
| Empty numeric input unexpectedly becomes zero | This is the current form reader behaviour; validate ranges and model missingness with an explicit mode where necessary. |
| All default checks pass but real cases fail | Add nonzero, boundary and branch-specific fixtures; default-only contract checks are insufficient. |
| Infinite utilisation reports `OK` | Do not determine status only from finite `worstUtil`. Check all utilisations and mandatory non-ratio failures. |
| Saved package differs from current preview | Preview can use current code; export uses the saved revision. Review and explicitly save a new revision if intended. |
| A link differs from the historical printed source | Current linking recomputes source inputs with the loaded engine; verify engine version and disclose this limitation. |
| Custom styling disappears in package export | Use shared styles; standalone module-local CSS is not a universal styling contract. |
| PDF missing after a successful save | Saving HTML/index and printing PDF are separate stages. Inspect the PDF-job result and browser environment. |
| Release tests fail on the generated module | Expected until the engine, evidence and validation are implemented. Do not disable tests. |
| `check --all` does not test a draft | Name the disabled module explicitly with `check <id>`. |
| `release-check` refuses to proceed | Review and commit all required repository changes through the authorised workflow; do not bypass the dirty-state check. |

## 20. Final Acceptance Checklist

### Engineering

- [ ] Scope, exclusions, standard edition/amendments and validity limits are explicit.
- [ ] Every factor, table and catalogue property has a permitted identifiable source.
- [ ] Load basis, combinations, signs, axes and units are documented and tested.
- [ ] All required checks and interactions are implemented; mandatory checks cannot be disabled.
- [ ] Valid failed designs and unattainable conditions are reported correctly.
- [ ] Invalid input is rejected explicitly without silent substitution.
- [ ] Intermediate workings, governing cases and limitations are available in the result and report.
- [ ] Reference differences and exclusions are explained, not tuned away.
- [ ] Independent engineering review is recorded for the released version.

### Software interface

- [ ] Correct folder, import package, distribution and manifest entry.
- [ ] Permanent module ID and filing folder are final and unique.
- [ ] Seven required functions plus real `validate(cases=None)` are implemented.
- [ ] Descriptor and manifest agree; schema and defaults are complete and fresh.
- [ ] Engine works without the manager or report and does not mutate inputs/global state.
- [ ] Outputs use supported serialisable values; nonfinite semantics are explicit.
- [ ] Dependencies and resources install into the shared environment and built wheel correctly.
- [ ] No new server, project store, copied renderer or runtime installer was introduced.
- [ ] Every declared action or exchange capability actually works and is tested.

### Reporting and persistence

- [ ] Shared `calcpad` output in live and standalone modes.
- [ ] Anchors, contents links and appendices forwarded correctly.
- [ ] Printed values come from the result; units and clauses are correct.
- [ ] Untrusted strings escaped; assets self-contained; no custom page furniture.
- [ ] Save/reopen, revisions and required attachments tested in a disposable project.
- [ ] Snapshot export verified, including consistency with the saved summary.
- [ ] Real PDFs, pagination, links and final package contents inspected.
- [ ] No historical project identity, revision or snapshot was rewritten implicitly.

### Delivery

- [ ] Module README includes commands, scope, limitations and evidence.
- [ ] Module and shared tests pass; missing/unrun checks are explicitly listed.
- [ ] Every reference case is validated or has a recorded exclusion.
- [ ] Generated outputs are separated from source and original reference evidence.
- [ ] Approval precedes production `available`/`enabled` status.
- [ ] Completion report states actual versions, commands, counts, outputs and remaining blockers.

## 21. AI Handover Prompt and Completion Report

### 21.1 Prompt to start a real module

Copy this section together with the completed engineering brief and source evidence into the implementing AI's task. The placeholders are mandatory information to fill in, not facts supplied by this guide.

```text
Implement a new InnoCalc headless calculation module in the current workspace.

Read calculations/readme_CalculationPreparation.md and the current authoritative
module specification before coding. Use the existing generator and SDK. Do not
modify manager application code or duplicate its server, UI, persistence or PDF
systems. Preserve existing work and repository histories.

Module name: [fill in]
Stable module ID: [fill in]
Category: [fill in]
Permanent filing folder: [fill in]
Responsible engineer/maintainer: [fill in]
Standard, edition and amendments: [fill in]
Scope and exclusions: [attach completed schedule]
Input fields, units, defaults and validity limits: [attach schedule]
Equations, clauses, cases, factors and interaction rules: [attach design basis]
Report sections and required workings: [attach schedule]
Reference documents and expected results: [attach evidence]
Acceptance tolerances: [fill in with justification]
Actions/exchange/attachments: [state requirements or none]
Independent reviewer and release approval process: [fill in]

Ask for clarification before inventing any material engineering assumption.
Keep the module planned and disabled until approved. Implement the seven required
functions, real validation, module tests, examples and a module README. Run the
module tests, shared contracts and relevant integration checks. Do not claim PDF
or engineering verification from default-only or HTTP-only success.

Return a completion report with files changed, interface identity, engineering
scope, commands actually executed, test/reference counts, generated evidence,
known limitations and exact outstanding release gates. Do not commit or publish
without explicit authorisation.
```

### 21.2 Required completion report

The implementing AI should deliver:

1. Module ID, version, standard, source path, package name and current enabled/status values.
2. Implemented checks and explicit exclusions, including unresolved engineering questions.
3. Added/changed files and any approved shared-platform changes.
4. Commands actually run, their exit results, case counts and comparison outcomes.
5. Reference inventory, extraction method, tolerances, defects corrected and residual differences.
6. Locations of test fixtures, traces, generated reports and PDFs; state whether PDFs were actually opened/inspected.
7. Save/reopen, exchange, revision and package-export verification results.
8. Missing dependencies, environmental blockers or tests not run.
9. Reviewer/approval status and the exact next action needed before production enablement.

Do not end with "ready for engineering use" unless the agreed engineering review and all applicable gates have actually been completed.

### 21.3 Current implementation references

Use these as patterns, not as code to copy wholesale:

| Reference | Purpose |
| --- | --- |
| [../tooling/scaffold.py](../tooling/scaffold.py) | Actual generator naming, duplicate checks and disabled registration. |
| [../tooling/__main__.py](../tooling/__main__.py) | Root CLI commands and selection behaviour. |
| [../packages/innocalc_sdk/manifest.py](../packages/innocalc_sdk/manifest.py) | Manifest validation. |
| [../packages/innocalc_sdk/contracts.py](../packages/innocalc_sdk/contracts.py) | Exact basic contract checks. |
| [../packages/innocalc_sdk/dev.py](../packages/innocalc_sdk/dev.py) | Shared standalone development harness. |
| [../apps/manager/icm/registry.py](../apps/manager/icm/registry.py) | Module loading and runtime calls. |
| [../apps/manager/app.js](../apps/manager/app.js) | Supported schema controls and actual form value handling. |
| [../apps/manager/server.py](../apps/manager/server.py) | HTTP/module call boundaries and current linking behaviour. |
| [../apps/manager/icm/snapshots.py](../apps/manager/icm/snapshots.py) | Snapshot encoding, frozen attachments and saved-sheet parsing. |
| [../apps/manager/icm/collate.py](../apps/manager/icm/collate.py) | Saved-revision package assembly. |
| [../packages/calcpad/sheet.py](../packages/calcpad/sheet.py) | Shared report primitives, pagination and standalone HTML. |
| [steel/member/smd/headless.py](steel/member/smd/headless.py) | Catalogue fields, optional groups, actions and exchange. |
| [concrete/column/ccd/headless.py](concrete/column/ccd/headless.py) | Conditional fields, mandatory checks and validation adapter. |
| [general/calculation_pad/src/cpd/headless.py](general/calculation_pad/src/cpd/headless.py) | Specialist editor and attachments; not a template for ordinary engineering forms. |

**Definition of success:** the module is independently understandable, reproducible, testable, auditable and compatible with the manager, and its engineering scope has been reviewed. Folder structure and successful imports are necessary, but they are not the whole acceptance criterion.