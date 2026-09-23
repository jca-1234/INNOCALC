# New Calculation Module — Requirements Brief

**A prompt input, not documentation.** Fill in Part B, paste the whole file into an AI
assistant working in this repository, and it has everything it needs to generate a calculation
module that InnoCalc Manager can host.

Part A is fixed — it is the contract and never changes between modules.
Part B is the only part you edit.
Part C is the acceptance test the generated module must pass before it is accepted.
Part D is the fixed procedure for validating the module against third-party calculations.
Part E is where to look for working examples.

The authoritative contract is [`docs/MODULE-SPECIFICATION.md`](MODULE-SPECIFICATION.md); read it
alongside this brief. Where the two disagree, the specification wins.

---

# Part A — Fixed requirements

## A1. Role and objective

> You are writing a new headless calculation module for the InnoCalc suite
> (`c:\CODING\INNOCALC`). The module is a pure Python function library. InnoCalc Manager
> discovers it through one `suite.toml` entry, builds its input form from the schema it publishes,
> calls `compute()` and displays the HTML `render()` returns. **No front-end or back-end change
> to the manager is permitted** beyond that one manifest entry.

## A2. Non-negotiable architecture

| Rule | Consequence |
|------|-------------|
| The front end holds no engineering knowledge. | Every label, unit, option list, default and conditional visibility rule comes from `schema()`. Never assume the manager knows anything about the discipline. |
| A module is a pure function. | `compute(inputs) -> result`. No HTTP, no file writes, no global state, no browser, no clock-dependent behaviour. Same inputs, same result, always. |
| Presentation is shared, not copied. | All output goes through `calcpad`. The module never emits `<html>`, `@page` rules, headers, footers or page numbers. |
| The module is independently workable. | It must compute, render, trace and validate with no manager running. |
| Modules never import one another. | Data crosses module boundaries only through the `innocalc.exchange/1` envelope. |
| Identity is manager-owned. | `client`, `project`, `projectno`, `designer`, `checker`, `date`, `subject`, `memberType`, `memberNumber`, `package`, `level`, `checks`, `linkedFrom` are read, never repurposed. |

## A3. Files to produce

```
calculations/<discipline>/<id>/
  pyproject.toml     installable module package
  src/<pkg>/
    __init__.py       no fixed directory-depth bootstrap
    module.toml       identity, standard, maintainer and planned/available status
    version.py        VERSION = "V0.01"
    headless.py       the contract: the seven required functions and DESCRIPTOR
    engine.py         the calculation. Pure functions, SI internally, no presentation.
    report.py         calcpad blocks only. No arithmetic beyond formatting.
    validation.py     self-consistency sweep and worked-example comparison
    dev.py            thin wrapper around the shared SDK runner (see A6)
  tests/              contract and engineering release gates
  examples/           reviewed inputs and expected outputs
  reference/          unchanged source evidence and provenance
suite.toml            one added entry, initially enabled = false
```

Generate this structure with `python -m tooling new`; see `docs/DEVELOPMENT.md`.
The generated engineering placeholder and release tests must fail until implemented.
Generated reports and scratch extracts belong under the suite `artifacts/` folder.

`engine.py` must be usable and testable without `report.py`, and `report.py` must not
recompute anything. If a number appears on the sheet it was produced by the engine and is
present in the result document.

## A4. Required functions in `headless.py`

| Function | Signature | Must return |
|----------|-----------|-------------|
| `descriptor()` | `() -> dict` | `id`, `name`, `short`, `standard`, `folder`, `status`, `version`, `defaultSubject`, `calcType`, `description`, `capabilities`, `entry`. `id` and `folder` are permanent. |
| `schema()` | `() -> dict` | `descriptor()` plus `identity`, `groups`, and optionally `optional`, `alwaysOn`, `catalogues`, `actions`, `presets`, `editor`. |
| `defaults()` | `() -> dict` | A complete, valid, blank input document. **Every** schema field id must be a key. |
| `compute(inputs)` | `(dict) -> dict` | The result document. `ValueError` for bad input — never a bare exception. |
| `render(inputs, result, *, standalone=False, appendix=None, anchor_prefix="", contents_href="")` | `-> str` | Calculation-pad HTML via `calcpad.render`. `anchor_prefix` and `contents_href` pass straight through. |
| `summarise(result)` | `(dict) -> dict` | `worstUtil`, `criticalCheck`, `status`, `headline`. The headline must read plainly to a project manager. |
| `identity(inputs)` | `(dict) -> dict` | `memberType`, `memberNumber`, `package`, `level`, `calcType`, `title`. |

Optional, implement only if Part B asks for them: `exchange`, `accepts`, `apply_exchange`,
`run_action`, `validate`.

## A5. The result document

Reserved keys: `util` `{name: float}`, `worstUtil` `float`, `checks` `{id: bool}`, and
optionally `attachments`.

* `1.0` is the limit for every utilisation.
* An unattainable condition is reported as `math.inf` in `util`, **never** as an exception.
* `worstUtil` equals the largest finite value in `util`.
* Everything the sheet prints, and everything `exchange()` publishes, lives in the result.
* Keep every intermediate value in the result so `calcpad.trace` can expose it — the trace is
  how the module gets checked against a reference calculation during refinement.

## A6. Independent development harness

```
python -m <pkg>.dev                        compute the defaults, print the summary
python -m <pkg>.dev inputs.json --trace    print every internal value
python -m <pkg>.dev --html out.html        write the calculation sheet
python -m <pkg>.dev --validate             run validation
python -m <pkg>.dev --schema               print the schema
```

## A7. Presentation rules

* Build blocks with `calcpad.row`, `table`, `grid`, `prose`, `badge`, and format with
  `calcpad.number / force / moment`.
* Every `row` carries a **clause reference** to the standard. A capacity line without a clause
  reference is not acceptable in a verified calculation.
* Expressions are written plainly (`phi alpha_s Msx`, `M*x / phiMbx`, `L^2`) and are typeset by
  `calcpad.notation`. Do not hand-write HTML entities or markup.
* Show the workings, not just the answer: the reader must be able to follow the calculation
  from input to utilisation without the source code.
* Page packing is automatic. Declare `weight` on prose blocks whose depth cannot be inferred.

## A8. Prohibited

Writing outside the module tree; global state between calls; importing another calculation
module; emitting page furniture; executing user-supplied code without an AST allow-list;
blocking without a timeout; silently substituting a default for a missing or nonsensical input.

## A9. Style

Australian English. Match the surrounding code: `from __future__ import annotations`, type
hints on public functions, no decorative comments, no docstrings restating the obvious. SI
units internally (N, mm, MPa); convert only at the presentation boundary. Standard library
only unless Part B states otherwise.

---

# Part B — The module brief *(edit this)*

## B1. Identity

| Field | Value |
|-------|-------|
| Module name | *e.g. Timber Member Design* |
| Short name | *e.g. Timber Member* |
| Package / folder | *e.g. `TimberMemberDesign/` and package `tmd`* |
| `descriptor()["id"]` | *kebab-case, permanent, e.g. `timber-member`* |
| `descriptor()["folder"]` | *filing sub-folder, e.g. `03 - TIMBER MEMBER`* |
| `calcType` label | *e.g. Timber member* |
| Design standard(s) | *including amendment, e.g. AS 1720.1:2010 Amdt 1* |
| Member types offered | *e.g. Beam, Joist, Bearer, Post, Stud* |

## B2. Scope

* **In scope:** *the checks the module performs, listed as they will appear on the sheet.*
* **Explicitly out of scope:** *what it must not attempt. State this — it stops invented work.*
* **Limits of validity:** *ranges outside which the module must raise `ValueError` or report
  `math.inf`.*

## B3. Inputs

For each input group, list: field id, label, unit, type, default, and any `showWhen` condition.

| Group | Field id | Label | Unit | Type | Default | Notes / visibility |
|-------|----------|-------|------|------|---------|--------------------|
| | | | | | | |

* **Optional check groups** (tick box + panel, land in `inputs["checks"][id]`): *…*
* **Always-on checks** (`alwaysOn`): *…*
* **Catalogues** (fixed data sent with the schema — section tables, product ranges): *source
  and how it is keyed.*
* **Presets** (one-click common configurations): *…*

## B4. The calculation

For each check, state: the clause, the equation, every factor and how it is obtained, the
capacity, and the utilisation name that appears in `util`.

| `util` key | Check name | Clause | Capacity expression | Notes |
|------------|------------|--------|---------------------|-------|
| | | | | |

Also state:

* **Load combinations** and where they come from.
* **Interaction / combined-action equations.**
* **Iterative or search procedures**, with the convergence criterion and the iteration cap.
* **Any table, chart or curve fit** being reproduced, and its source.
* **Sign conventions and axis definitions.**

## B5. Sheet layout

The order of sections on the calculation sheet, and what appears in each. Note any grid tables
(schedules, capacity tables) and any narrative blocks (assumptions, references, limitations).

## B6. Actions and exchange

* **Actions** (buttons beside the inputs, `run_action`): id, label, behaviour. Must be
  idempotent and must not write to the project folder.
* **Exchange produced** (`exchange()`): which groups of `innocalc.exchange/1` are populated and
  from what. Units go in the key name.
* **Exchange consumed** (`accepts()` / `apply_exchange()`): which groups, and which input fields
  each maps to.

## B7. Validation evidence

* **Self-consistency sweep:** the input ranges to sweep.
* **Worked examples:** the reference calculations to reproduce, as
  `{"name", "inputs", "tolerance", "tolerances", "expect"}` with dotted result paths. Attach or
  reference the source documents.
* **Known-good baseline:** any legacy spreadsheet or tool the module must agree with, and the
  agreed tolerance.

### Reference validation

Fill this in only where a body of third-party calculations exists for the same member type.
It drives the procedure in **Part D**, which is fixed and must not be restated here.

| Field | Value |
|-------|-------|
| Reference folder | *path holding the reference documents, e.g. `<ModuleFolder>/reference`* |
| Producing tool and version | *e.g. a legacy in-house tool, a supplier's design suite* |
| Acceptance band | *e.g. 1 % on every published value and on the governing utilisation* |
| Sheet types expected | *and which of them are member design checks this module reproduces* |
| Known bespoke rules in the reference | *rules outside the standard — record as out of scope, never implement* |
| Data the module's catalogue may lack | *properties the reference prints that this module has no published source for* |

## B8. Anything else

Reference documents, worked examples, legacy code to port, drawings, and any behaviour the
engineer wants that is not implied by the standard.

---

# Part C — Acceptance criteria

The generated module is accepted only when all of the following hold.

- [ ] Suite and module packages install; `import calcpad` works standalone without fixed path-depth assumptions.
- [ ] `headless.py` implements the seven required functions with the exact signatures in A4.
- [ ] Every `schema()` field id exists in `defaults()`, and no key in `defaults()` is orphaned.
- [ ] `compute(defaults())` succeeds and returns `util`, `worstUtil` and `checks`.
- [ ] Every value printed on the sheet exists in the result document.
- [ ] Every capacity row on the sheet carries a clause reference.
- [ ] Bad input raises `ValueError` with a message an engineer can act on; unattainable
      conditions return `math.inf`, not an exception.
- [ ] `render()` produces sheets only through `calcpad`, and passes `anchor_prefix` and
      `contents_href` through unchanged.
- [ ] `summarise()` returns a headline a project manager can read without the sheet.
- [ ] `python -m <pkg>.dev`, `--trace`, `--html`, `--schema` and `--validate` all work with no
      manager running.
- [ ] `validate()` self-consistency passes across the whole input range in B2.
- [ ] Every worked example in B7 reproduces within its stated tolerance.
- [ ] One entry in `suite.toml`, enabled only after independent engineering review and passing release tests.
- [ ] `python server.py` in `apps/manager` reports the module loaded with no problems, the
      form builds, a calculation computes, renders, saves and exports to PDF.
- [ ] A `README.md` in the module folder: scope, standard, checks, limits of validity,
      validation status.
- [ ] Where B7 nominates a reference folder, Part D has been carried out and its acceptance
      criteria met.

---

# Part D — Reference validation *(fixed procedure)*

Run this whenever B7 nominates a folder of third-party calculations. The objective is to
validate the module against every one of them, resolve every discrepancy above the acceptance
band in B7, and compile the result into one linked PDF package.

Work through the stages in order. **Do not start a later stage until the earlier one is
evidenced by a run you have actually executed.**

## D1. Establish the reference set

1. Read every file in the reference folder and classify it by the tool and sheet type that
   produced it. Report the count of each type before going further.
2. For each distinct sheet type, dump one full example and read it end to end. Identify:
   * the design actions the sheet **used** — not the values a user typed. Many tools derive the
     governing action from an eccentricity, a load model or an amplification and print the
     derived value on the summary line while leaving the manual entry in the body;
   * every derived factor **actually used** — effective lengths, restraint or end-condition
     codes, modification factors — again distinct from a manually entered value where the tool
     calculates its own;
   * every published capacity and interaction ratio;
   * the summary block, which carries the governing utilisation.
3. State explicitly which sheet types are design checks the module can reproduce and which are
   outside its scope — load derivation, serviceability, analysis-only, bespoke interaction
   rules, proprietary products. **Do not silently drop anything.**

Ask the user to confirm the scope before continuing if the folder mixes calculation types or
contains items the module's catalogue does not carry.

## D2. Write an extraction script

Parse the reference documents into a normalised record per sheet. **Do not hand-transcribe
values** — the comparison must be reproducible against the documents themselves.

```
file, sheetType, version, title, designation, catalogueItem, grade,
inputs      -> a module input document
published   -> {canonical name: value} for everything the sheet prints
cases       -> one or more load cases, each with its own inputs and published overrides
worst       -> the governing utilisation from the summary block
skip        -> why the sheet is not validated, empty when it is
outOfScope  -> reference checks the module deliberately does not perform
```

Rules that matter:

* **Every published value is optional.** A sheet contributes whatever it prints; absent values
  are simply not compared.
* **Bound every regex.** Patterns such as `(?:[^=]+ = )*` backtrack catastrophically on a page
  of text and will appear to hang. Locate a label, then search a short fixed window after it.
* **Anchor labels against prefixes and expressions.** A pattern for a factor will happily match
  the same characters inside a compound expression that contains it — `alpha` inside
  `phiN = phiNs*alpha = 862.6 kN` — and silently return a capacity as if it were the factor.
  Use a negative look-behind for the operator and a look-ahead that rejects the unit.
* **Disambiguate near-identical labels** with explicit patterns rather than one generic one; a
  qualified variant of a symbol is a different quantity from the plain symbol.
* **A sheet with more than one load case becomes more than one case**, each with its own
  published overrides, so a value belonging to one case is never compared against another.
* **Map the inputs so the module reproduces the reference's own derived factors.** Where the
  reference prints a factor as a product of sub-factors, choose the module inputs that
  reproduce the sub-factors the reference took as given, so that the sub-factor the module
  derives itself is the quantity actually being validated.

## D3. Write a comparison script

For each case, run the module on the extracted inputs and compare every published value that
has a module counterpart.

* Compare in the **reference's own units and printed precision**. A deviation counts only when
  it exceeds the acceptance band **and** the absolute difference exceeds the reference's
  rounding step — half of the last printed digit. Apply the same test to the governing
  utilisation: a reference printing `0.10` against a module value of `0.097` is rounding, not a
  discrepancy.
* Write a machine-readable summary and a human-readable report. Per sheet: the reference
  governing utilisation, the module's, the deviation and the governing check; then a detail
  section naming every offending parameter.
* **Tabulate the offending parameters by name.** Classes of failure are far more informative
  than individual sheets and point straight at the defect.

## D4. Diagnose and fix

Classify every class of deviation into one of these, explicitly:

| Category | Action |
|---|---|
| **Module defect** — a required clause is missing, mis-stated or applied under the wrong condition | Fix the engine. This is the point of the exercise. |
| **Extraction defect** — the wrong value was read from the sheet | Fix the script, not the engine. Verify by hand against the sheet first. |
| **Reference conservatism** — both are code-compliant, the reference uses the more conservative permitted form | Adopt the reference basis where it is defensible for a design tool, and record the clause. |
| **Reference bespoke rule** — outside the standard | Do not implement it. Record it as out of scope on the validation record and exclude it from the statistics. |
| **Catalogue data gap** — the module's data tables lack a property the check needs | Record it as a data item with the residual magnitude. **Never fabricate catalogue properties**; back-calculating a table value from the reference is not a substitute for the published source. |

Before changing the engine, verify the diagnosis arithmetically on one sheet by hand. After
changing it, re-run the module's own self-consistency validation **and** the full comparison,
and report the before/after counts.

**Do not tune the module to the reference.** Every change must be justified by a clause of the
governing standard, and the clause must be cited in the code comment and in the report.

## D5. Compile the package

Build one PDF through `calcpad`, so the output is identical in style to a calculation issued by
the manager. Reuse the manager's collation approach (`icm/collate.py`, `calcpad/export.py`)
rather than inventing a second one.

1. **Validation Index** — one row per reference calculation: number, title, sheet type,
   catalogue item, reference governing utilisation, module governing utilisation, deviation %,
   governing check or the reason it was not validated, and the page numbers of both the
   reference and the module calculation. The lead paragraph states how many were compared and
   how many agree within the band.
2. Then, for each reference calculation in index order:
   * a **validation record** sheet giving the parameter-by-parameter comparison, the status,
     and any reference checks excluded as out of scope;
   * the **reference calculation** itself;
   * the **calculation this module produces** for the same member.

Make the index links real PDF links:

* print the index, the validation records and the module calculations as **one** HTML document,
  so the browser emits genuine link annotations;
* place each validation record immediately before the point where its reference document will
  be inserted, and anchor the index's reference-page link to that record sheet;
* splice the reference PDFs in afterwards by page position, which leaves the link annotations
  pointing at the same page objects;
* compute the final page numbers **before** printing, from the rendered sheet counts and the
  reference page counts, and assert the printed page count matches.

Deduplicate repeated objects when writing the merged file; a package of this kind is otherwise
dominated by one copy of the letterhead per sheet.

## D6. Report

State, in this order:

1. the number of reference calculations, how many were validated, and the reason and count for
   each exclusion;
2. how many agree within the band on the governing utilisation;
3. a table of the defects found and fixed, each with its clause reference and the size of the
   error it was causing;
4. the residual differences that remain, each with its cause, its magnitude, and whether it is
   conservative or unconservative;
5. the path, page count and structure of the package.

Add the scripts to the module tree and a short section to the module `README.md` describing how
to re-run the validation. Add the generated package and report to `.gitignore` — they are
rebuildable artefacts.

## D7. Acceptance

- [ ] Every sheet in the folder is either validated or carries a stated reason why not.
- [ ] Every parameter deviation above the band is classified into one of the five categories.
- [ ] No engine change exists that is not justified by a cited clause.
- [ ] The module's self-consistency validation still passes.
- [ ] The package opens with a working index whose links land on the correct pages.

---

# Part E — Existing modules to copy from

| Module | Copy this from it |
|--------|-------------------|
| `calculations/steel/member/smd/headless.py` | Catalogue-backed fields, optional check groups, module actions, exchange producer. |
| `calculations/concrete/column/ccd/headless.py` | Conditional fields (`showWhen`), always-on checks, presets, layered validation (`ccd/validation.py`). |
| `calculations/general/calculation_pad/src/cpd/headless.py` | Custom editor, PDF attachments, safe expression evaluation behind an AST allow-list. |

**Read one of these end to end before writing anything.** A new module should look like it was
written by the same hand on the same day.
