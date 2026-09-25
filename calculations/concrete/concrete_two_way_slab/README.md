# Concrete Two-Way Slab Design

| | |
| --- | --- |
| Module ID | `concrete-two-way-slab` |
| Package | `ic_concrete_two_way_slab` |
| Distribution | `innocalc-concrete-two-way-slab` |
| Entry point | `ic_concrete_two_way_slab.headless` |
| Filing folder | `11 - CONCRETE TWO-WAY SLAB` |
| Category | `Concrete` |
| Standard | AS 3600:2018 incl. Amendments 1 and 2; AS/NZS 1170.0:2002 for combinations |
| Version | `v0.0.1` |
| Status | `planned`, `enabled = false` |
| Maintainer | Responsible engineer (unassigned) |

> **Not approved for design.** This module transcribes the retained Structural Toolkit
> workbook `Concrete_TwoWaySlab_502.xls` (TWO-WAY SLABS V5.02). It reproduces 51 saved
> workbook values to `1e-9`. That shows the transcription is faithful. It does not show
> the engineering is correct. See [TECHNICAL-README.md](TECHNICAL-README.md) for the
> technical review and the open concerns.

## Scope

This module analyses a rectangular reinforced concrete slab panel supported on all four
sides by walls or beams, using the simplified method of AS 3600 Cl 6.10.3. It reports:

| Utilisation key | Check | Reference |
| --- | --- | --- |
| `deflectionTotal` | Deemed-to-comply minimum effective depth, total deflection, `d.min / ds` | Cl 9.4.4.2 |
| `deflectionIncremental` | Same check for incremental deflection, `d.min.inc / ds` | Cl 9.4.4.2 |
| `minimumSteel` | Minimum strength reinforcement, `Ast.min / Ast` | Cl 9.1.1(b) |
| `liveLoadLimit` | Applicability of the deemed-to-comply method, `wll / wdl` | Cl 9.4.4.2 |

It also reports the positive and negative design moments per metre width from
Table 6.10.3.2(A), Table 6.10.3.2(B) or the closed-form coefficients.

Two optional check groups follow the Tedds AS 3600-2018 slab calculation:

| Group | Utilisation keys | Reference |
| --- | --- | --- |
| `flexure` | `flexure`, `ductility`, `flexuralMinimum` and `barSpacing`, each taken at the governing location among midspan and every continuous or discontinuous edge | Cl 8.1, Table 2.2.2, Cl 9.1.1, Cl 9.4.1 |
| `shrinkage` | `shrinkage`, or folded into `flexuralMinimum` when flexure is on | Cl 9.4.3 |

### Excluded

The module does not check shear or punching shear, crack width, torsional corner
reinforcement (Cl 9.1.3.3), fire, vibration, or the adjacent-span limits of the simplified
methods. The workbook's `Prelim` sheet is also excluded, because
V5.02 hides it with the note "Removed 2018 code".

### Validity limits

* `20 <= f'c <= 120` MPa. Values outside this range raise `ValueError`.
* The panel must have 0, 1 or 2 continuous long edges and 0, 1 or 2 continuous short edges.
* Bar sizes are 8, 10, 12, 16 or 20 mm. `fsy` is 500 or 400 MPa.
* `ds > 0`, and `dc < ds`.
* If Ly/Lx is greater than 2, the module applies the tables' "> 2" column and issues a warning.

## Units and conventions

Loads are in kPa and moments are in kNm per metre width. Lengths are in mm. If you enter
the spans in either order, the module sorts them so that `Ly >= Lx`. `Mx*` spans the short
direction, and `My*` spans the long direction. On the drawing, any discontinuous edges are
placed first on the top long edge and the left short edge, as in the workbook.

## Differences from the source workbook

| Workbook behaviour | This module | Why |
| --- | --- | --- |
| `Analysis!F25` tests `wll > wdl + wsdl` | Tests `wll > wdl` | `wdl` already includes `wsdl`, so the workbook counts `wsdl` twice |
| `Ast.min` is displayed but never compared with `Ast` | Reported as the `minimumSteel` utilisation | Cl 9.1.1 is a mandatory strength requirement |
| An applicability "Error" is printed but the sheet still shows OK | `liveLoadLimit` counts towards `worstUtil` | A calculation outside its method must not report OK |
| `ChangeEdges` and `meshname` macros redraw hatching and name a mesh | SVG plan drawn from the result; mesh naming omitted | Presentation only |
| `Prelim` sheet | Not transcribed | Hidden in V5.02, "Removed 2018 code" |
| No capacity or shrinkage checks | Optional `flexure` and `shrinkage` groups | Adopted from the Tedds AS 3600-2018 slab calculation (see TECHNICAL-README §2.1) |

## Commands

Run these from the suite root:

```powershell
$Python = Join-Path $PWD '.venv\Scripts\python.exe'
& $Python -m tooling check concrete-two-way-slab --validate
& $Python -m tooling dev concrete-two-way-slab calculations/concrete/concrete_two_way_slab/examples/worked-example.json --html artifacts/concrete-two-way-slab/worked-example.html
$env:PYTHONPATH = "$PWD;$PWD\calculations\concrete\concrete_two_way_slab\src"
& $Python -m unittest discover -s calculations/concrete/concrete_two_way_slab/tests -v
```

## Evidence

| Artefact | Location |
| --- | --- |
| Technical review | `TECHNICAL-README.md` |
| Retained baseline | `src/ic_concrete_two_way_slab/data/workbook-baseline.json` |
| Source provenance | `reference/README.md` |
| Worked example | `examples/worked-example.json` |
| Tests | `tests/test_engine.py`, `tests/test_release_gate.py` |

## Outstanding release gates

1. Confirm the coefficient tables against the printed AS 3600:2018 Amdt 2. They already
   agree with Tedds' independent tables (TECHNICAL-README C1).
2. Obtain an independent engineering review and record it in `reference/README.md`.
3. Add a worked example from a source other than Structural Toolkit.
4. Name a maintainer.
5. Complete manager integration and PDF acceptance.
