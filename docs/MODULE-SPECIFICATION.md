# InnoCalc Module Specification

**Version 1.1 — 10 September 2026**

This document defines the contract a calculation module must satisfy to be hosted by
**InnoCalc Manager**. A module that follows it can be developed, calculated, validated and
released entirely on its own, and then dropped into the manager **without any change to the
manager's front end or back end** beyond one entry in `suite.toml`.

---

## 1. Principles

| # | Principle | What it means in practice |
|---|-----------|---------------------------|
| 1 | **The front end holds no engineering knowledge.** | The manager builds every input form from a schema the module publishes, and displays the HTML the module returns. It never knows what a `kf` or a `phiNuo` is. |
| 2 | **A module is a pure function library.** | `compute(inputs) -> result`. No HTTP, no global state, no files written, no browser. The same inputs always give the same result. |
| 3 | **Inputs and outputs are consistent across modules.** | Identity, project and revision fields are owned by the manager and are identical for every member type and analysis type (section 4). |
| 4 | **Presentation is shared, not copied.** | All output is rendered through the `calcpad` package so every sheet in a package looks the same. |
| 5 | **A module is independently workable.** | It must run and be validated with no manager present (section 9). |
| 6 | **Modules may exchange data, but never reach into each other.** | Exchange happens through one neutral envelope (section 8). |

---

## 2. Where a module lives

```
INNOCALC/
  suite.toml                      enabled modules and source locations
  packages/calcpad/               shared presentation (import calcpad)
  packages/innocalc_sdk/           shared contract checks and dev runner
  calculations/<discipline>/<id>/
    pyproject.toml
    src/<package>/
      module.toml                 module metadata
      headless.py                 the public contract
      engine.py, report.py, ...
    tests/
    examples/
    reference/
```

Use `python -m tooling new` as described in `docs/DEVELOPMENT.md`. It creates this
structure and a disabled manifest entry. Registration is data, not manager code:

```toml
[[modules]]
id = "your-module"
path = "calculations/general/your_module/src"
entry = "ic_your_module.headless"
category = "General"
filing_folder = "YOUR MODULE"
enabled = false
```

The manager adds the declared source path and imports the entry point. Duplicate
IDs, paths, entry points and filing names are rejected. Enable only after contract,
engineering and reference checks pass and the module declares `status = "available"`.
Install the suite and module packages for standalone development; new modules must
not depend on fixed directory-depth `sys.path` bootstraps. Existing module paths
remain supported during migration. Source paths may move; saved IDs and filing
names must not change.

---

## 3. The contract

### 3.1 Required functions

| Function | Signature | Returns |
|----------|-----------|---------|
| `descriptor()` | `() -> dict` | Module identity (section 3.2). |
| `schema()` | `() -> dict` | Everything needed to build the input form (section 5). |
| `defaults()` | `() -> dict` | A complete, valid, blank input document. |
| `compute(inputs)` | `(dict) -> dict` | The result document. Raise `ValueError` for bad input. |
| `render(inputs, result, *, standalone=False, appendix=None, anchor_prefix="", contents_href="")` | `-> str` | Calculation-pad HTML. |
| `summarise(result)` | `(dict) -> dict` | `{"worstUtil", "criticalCheck", "status", "headline"}`. |
| `identity(inputs)` | `(dict) -> dict` | `{"memberType", "memberNumber", "package", "level", "calcType", "title"}`. |

### 3.2 `descriptor()`

```python
{
  "id": "steel-member",            # unique, kebab-case, stable forever
  "name": "Steel Member Design",
  "short": "Steel Member",
  "standard": "AS 4100:2020",
  "folder": "01 - STEEL MEMBER",   # sub-folder used inside a project's calculation branch
  "status": "available",           # available | planned
  "version": "V0.05",
  "defaultSubject": "Steel member design",
  "calcType": "Steel member",      # the label used when sorting a package
  "description": "...",
  "capabilities": ["compute", "render", "validate", "optimise", "exchange"],
  "entry": "smd.headless",
}
```

`id` and `folder` must never change once calculations have been filed with them.

### 3.3 Optional functions

| Function | Purpose |
|----------|---------|
| `exchange(inputs, result) -> dict` | Publish values other modules may consume (section 8). |
| `accepts() -> list[str]` | Exchange groups this module can consume. |
| `apply_exchange(inputs, payload) -> dict` | Merge an exchange envelope into this module's inputs. |
| `run_action(action_id, inputs) -> dict` | Perform a module-specific button action (section 6). |
| `validate(cases=None) -> dict` | Self-validation and worked-example comparison (section 9). |

If a function is absent the manager simply does not offer that feature.

---

## 4. Manager-owned input keys

These keys are written into every input document by the manager. **A module must read them
where relevant but must never repurpose them.** They are what makes inputs and outputs
consistent regardless of member or analysis type.

| Key | Meaning |
|-----|---------|
| `client` | Client name, printed in the sheet header. |
| `project` | Project name. |
| `projectno` | Project number. |
| `designer` | Initials of the person doing the work. |
| `checker` | Initials of the verifier. |
| `date` | Sheet date; omit to use today. |
| `subject` | Sheet subject line. |
| `memberType` | Free text with suggestions, e.g. `Rafter`, `Column`. |
| `memberNumber` | Four-digit numeric (zero padded) or alphanumeric starting with a letter. |
| `package` | Calculation package the item belongs to. |
| `level` | Building level or zone, used for package sorting. |
| `checks` | `{optionalGroupId: bool}` — which optional check groups are enabled. |
| `linkedFrom` | Appended by `apply_exchange`; a list of source descriptors. |

Everything else in the input document belongs to the module and may be named freely.

### 4.1 Result document

`compute()` may return any structure, with three reserved keys:

| Key | Type | Meaning |
|-----|------|---------|
| `util` | `{name: float}` | Every utilisation the calculation produced. `1.0` is the limit. |
| `worstUtil` | `float` | The largest finite value in `util`. |
| `checks` | `{id: bool}` | Which optional groups were active. |
| `attachments` | `list[dict]` *(optional)* | PDF pages to splice into an exported package: `{"path", "pages", "title", "exists"}`. |

Values that cannot be attained must be reported as `math.inf` in `util`, not as an exception.

Any unattainable or invalid utilisation must produce a failing summary even when
`worstUtil` contains only the maximum finite value. Invalid supplied numbers must
raise `ValueError`; do not turn nonnumeric values, NaN or infinity into zero loads.

The manager snapshots every new revision's inputs, results, descriptor, summary,
HTML and PDF attachments. Export uses that snapshot without calling `compute`.
Old revisions without a snapshot require their saved PDF or an explicit reviewed
re-save. See `docs/IMPLEMENTATION-STATUS.md` for the compatibility policy.

---

## 5. The input schema

`schema()` returns `descriptor()` plus:

```python
{
  "identity": {"typeLabel": "Member type", "numberLabel": "Member number",
               "typeOptions": ["Rafter", "Column", ...]},
  "groups":   [ {"id": "...", "title": "...", "fields": [ ...field... ]} ],
  "optional": [ {"id": "compression", "label": "Compression", "fields": [ ... ]} ],
  "alwaysOn": {"biaxial": True},          # checks always enabled, not shown as a tick box
  "catalogues": {"sections": {"UB": ["310UB40.4", ...], "UC": [...]}},
  "actions":  [ {"id": "optimise-weight", "label": "Find lightest section"} ],
  "editor":   "cells",                     # optional; "cells" gives the pad editor
  "presets":  [ {"label": "450 x 700", "cX": 450, "cY": 700} ],
}
```

### 5.1 Field definition

```python
{
  "id": "Mx",                 # the input document key
  "label": "M*x",
  "type": "number",           # number | text | select | checkbox | textarea | catalogue
  "unit": "kNm",              # optional, shown beside the label
  "default": 0,
  "width": "full",            # optional; otherwise half width
  "help": "Design bending moment about the major axis",
  "options": [{"value": "300", "label": "300"}],       # select only
  "catalogue": "sections",                             # catalogue only
  "optionsBy": "secType",                              # catalogue keyed by another field
  "showWhen": {"secType": ["EA", "UA"]},               # conditional visibility
}
```

Rules:

* Every field `id` must exist in `defaults()`.
* `optional` groups are rendered as a tick box plus a panel; the tick box value lands in
  `inputs["checks"][group.id]`.
* A field in an optional group is still sent when the group is off — the module decides
  whether to use it. Guard on `checks`, not on the presence of a value.
* `catalogue` data is sent once with the schema; keep it under a few hundred kilobytes.

---

## 6. Actions

An action is a button the manager shows beside the inputs. `run_action` returns any of:

```python
{"inputs": {...},                   # replace the current input document
 "message": "460UB74.6 selected",   # shown as a toast
 "file": {"name": "pad.ipynb", "content": "...", "type": "application/x-ipynb+json"}}
```

Actions must be idempotent and must not write to the project folder.

---

## 7. Presentation

Render through `calcpad`; do not emit your own page furniture.

```python
import calcpad

def render(inputs, result, *, standalone=False, appendix=None,
           anchor_prefix="", contents_href=""):
    blocks = [
        calcpad.table("Bending", [
            calcpad.row("Section capacity", "phiMsx = phi fy Zex",
                        f"{calcpad.moment(result['phiMsx'])} kNm", "Cl 5.2.1"),
            calcpad.row("Check", "M*x / phiMbx",
                        calcpad.badge(result["util"]["bendingX"])),
        ]),
        calcpad.prose("Assumptions", "<p>...</p>", weight=8),
    ]
    return calcpad.render(inputs, blocks, default_subject="My calculation",
                          appendix=appendix, standalone=standalone,
                          module_dir=MODULE_DIR, data_id="ynm-inputs",
                          anchor_prefix=anchor_prefix, contents_href=contents_href)
```

| Helper | Use |
|--------|-----|
| `calcpad.row(label, expression, value, reference)` | One line of the audit trail. Expressions are written plainly (`phi alpha_s Msx`, `M*x / phiMbx`, `L^2`) and typeset automatically. |
| `calcpad.table(title, rows)` | The four-column calculation table. |
| `calcpad.grid(title, headers, rows, note)` | Free-form numeric tables (schedules, capacity tables). |
| `calcpad.prose(title, html, weight=n)` | Narrative. `weight` declares its depth in table-row units. |
| `calcpad.badge(ratio)` | The OK / FAIL chip. |
| `calcpad.number / force / moment` | Formatting. `force` and `moment` convert N and N·mm. |
| `calcpad.render(...)` | Pagination, header block, page numbers, machine-readable inputs. |

`anchor_prefix` and `contents_href` are passed by the manager when collating a package: they
place a bookmark on each sheet and a **Contents** link back to the index page. Pass both
straight through to `calcpad.render`.

Page packing is automatic: `calcpad` never splits a block across a page break, and honours an
`<!--weight:n-->` comment when a block's depth cannot be inferred from its row count.

### 7.1 Editing in the sheet (optional)

A module may accept a keyword argument `interactive` on `render`. The manager passes
`interactive=True` for the sheet it shows on screen and never for a printed or exported one,
so the printed calculation is always the plain sheet. A module that does not declare the
argument is called exactly as before.

Use it to put form controls into the sheet where the values print, rather than only in the
input panel. The calculation pad renders each calculation cell as a text area followed by its
result. The front end binds anything it finds in the report pane carrying these attributes:

| Attribute | Meaning |
|-----------|---------|
| `data-pad-cell="id"` | The block that holds one editable cell. |
| `data-pad-source="id"` | A text area holding that cell's source. |
| `data-pad-title="id"` | An input holding that cell's title. |
| `data-pad-add="id"` | Add a cell after `id`; empty adds at the end. |
| `data-pad-delete="id"` | Delete that cell. |

The caret is captured before each recalculation and restored afterwards, so typing is not
interrupted by the sheet redrawing.

---

## 8. Data exchange between modules

Modules do not import one another. They publish and consume one neutral envelope,
`innocalc.exchange/1`:

```python
{
  "schema": "innocalc.exchange/1",
  "source": {"module": "steel-member", "version": "V0.05",
             "memberType": "Rafter", "memberNumber": "0001",
             "package": "P01", "level": "L01", "title": "..."},
  "axial":      {"compression_kN": 180.0, "tension_kN": 0.0},
  "moments":    {"Mx_kNm": 73.1, "My_kNm": 8.0},
  "reactions":  {"support_kN": 100.0, "Vx": 100.0, "Vy": 35.0},
  "geometry":   {"length_mm": 4500.0, "depth_mm": 304.0, "width_mm": 165.0},
  "material":   {"grade": "300", "fy_MPa": 320.0},
  "variables":  {"M_max": 22.5},          # free-form, module defined
  "utilisation": {"worstUtil": 0.80, "criticalCheck": "Bending x", "status": "OK"},
}
```

Conventions:

* **Units are in the key name.** `_kN`, `_kNm`, `_mm`, `_MPa`, `_mm2`. Never send a bare number
  whose unit is implied.
* Every group is optional; consumers must tolerate a missing group.
* `apply_exchange` must not throw on unknown keys, and must append the sender to
  `inputs["linkedFrom"]` so the link is traceable on the sheet.
* A link is a **snapshot**, not a live reference. The manager records where a value came from;
  it does not recompute upstream calculations automatically.

The manager exposes this as **Link** in the calculation library:
`POST /api/calculation/exchange {sourceId, targetModule}`.

---

## 9. Independent development and validation

A module must be workable with no manager present. Provide a `dev.py`:

```
python -m ynm.dev                      compute the defaults, print the summary
python -m ynm.dev inputs.json --trace  print every internal value
python -m ynm.dev --html out.html      write the calculation sheet
python -m ynm.dev --validate           run validation
python -m ynm.dev --schema             print the schema
```

`calcpad.trace` provides the internal output needed to compare a module against a reference
calculation during refinement:

```python
from calcpad import trace
print(trace.as_text(result))                    # dotted path = value, one per line
trace.report(inputs, result, title="...")       # the same, on calculation-pad sheets
```

### 9.1 `validate()`

Two modes, both returning the same envelope:

```python
{"ok": bool, "mode": "self-consistency" | "worked-examples" | "baseline",
 "module": "...", "version": "...", "tested": int,
 "failures": [...],            # self-consistency
 "cases": [...]}               # worked examples
```

**Self-consistency** (`validate()` with no arguments) needs no reference data. It must prove,
across the module's own input range, that:

* every case computes without raising;
* every reported utilisation is finite or is declared unattainable;
* `worstUtil` equals the largest finite value in `util`;
* capacities are positive and reduction factors are bounded.

**Worked examples** (`validate(cases)`) compares against supplied references:

```json
{"cases": [
  {"name": "AISC DCT 310UB40.4",
   "inputs": {...},
   "tolerance": 0.01,
   "tolerances": {"bending.phiMbx": 0.02},
   "expect": {"bending.phiMsx": 182.1e6, "util.bendingX": 0.803}}
]}
```

Paths are dotted paths into the result document. This is the format to use when feeding a
module a range of example calculations.

---

## 10. What the manager guarantees

* `compute` and `render` are called on a worker thread; they may run for a few seconds.
* Input documents are plain JSON — no dates, sets, or custom classes survive a round trip.
* The manager writes the standalone HTML and the PDF, files the revision, supersedes the
  previous one and maintains the library index. A module never touches the project folder.
* Saved sheets carry the input document in a `<script type="application/json">` block, so a
  calculation can always be reopened from the file alone.

## 11. What a module must not do

* Write to the project folder, or anywhere outside its own tree.
* Read or write global state between calls.
* Import another calculation module.
* Emit its own `<html>`, `@page` rules or page furniture.
* Execute user-supplied code without an allow-list. (The Calculation Pad evaluates arithmetic
  behind an AST whitelist; see `cpd/evaluator.py` for the pattern to follow.)
* Block indefinitely. Give every external call a timeout.

---

## 12. Checklist for a new module

- [ ] The suite and module install as Python packages; standalone imports do not depend on directory depth.
- [ ] `ynm/headless.py` implements the seven required functions.
- [ ] `descriptor()["id"]` and `["folder"]` are final.
- [ ] Every `schema()` field id exists in `defaults()`.
- [ ] `compute(defaults())` succeeds and returns `util` and `worstUtil`.
- [ ] `render()` produces sheets through `calcpad` and passes `anchor_prefix` / `contents_href` through.
- [ ] `summarise()` returns a headline a project manager can read.
- [ ] `validate()` self-consistency passes across the module's input range.
- [ ] `ynm/dev.py` runs the calculation, the trace and the validation with no manager.
- [ ] `exchange()` / `apply_exchange()` implemented if the module produces or consumes actions.
- [ ] One validated entry in `suite.toml`; no manager source-code change.
- [ ] `python server.py` in `apps/manager` reports the module with no problems.

---

## 13. Reference implementations

| Module | Shows |
|--------|-------|
| `calculations/steel/member/smd/headless.py` | Catalogue-backed fields, optional check groups, module actions, exchange producer. |
| `calculations/concrete/column/ccd/headless.py` | Conditional fields, always-on checks, a three-level validation tool (`ccd/validation.py`). |
| `calculations/general/calculation_pad/src/cpd/headless.py` | A custom `cells` editor, PDF and blank-sheet attachments, notebook export, safe expression evaluation. |
