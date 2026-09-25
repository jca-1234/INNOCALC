# Concrete Stair Design

| | |
| --- | --- |
| Module ID | `concrete-stair` |
| Package | `ic_concrete_stair` |
| Entry point | `ic_concrete_stair.headless` |
| Filing folder | `07 - CONCRETE STAIR` |
| Category | `Concrete` |
| Standard | AS 3600:2018 incl. Amendments 1 and 2; AS/NZS 1170.0:2002 |
| Version | `v0.0.1` |
| Status | `planned`, `enabled = false` |
| Source workbook | `Concrete_Stair_506.xls` (Structural Toolkit CONCRETE STAIRS V5.06) |

> **Not approved for design.** Transcription of a retained Structural Toolkit
> workbook. Agreement with it establishes transcription fidelity, not engineering
> correctness. Independent review is outstanding.

## Scope

A reinforced concrete stair flight spanning horizontally, designed **per metre
width**.

| Utilisation key | Check | Reference |
| --- | --- | --- |
| `bending` | `M* / phiMuo` | Cl 9.1 |
| `minimumSteel` | `Ast.min / Ast` | Cl 9.1.1, Eq 8.1.6.1(2) |
| `ductility` | `kuo / 0.36` | Cl 8.1.5 |
| `deflection` | `th.min / ath` for the total deflection limit | Cl 9.4.4, Table 2.3.2 |
| `deflectionIncremental` | `th.min.inc / ath` for the incremental limit | Cl 9.4.4, Table 2.3.2 |

The stepped profile drives the self weight through the average thickness
`ath = th + going/ang x riser/2` and the vertical average thickness factor
`f = ang/going`. The v5.06 inclined deflection modifier is applied to the minimum
depth, on either a local `(1/cos^2 theta)^(1/4)` or a global `(1/cos theta)^(1/4)`
basis.

### Excluded

Shear, torsion, landings, supports and the connection to the supporting
structure; transverse and distribution reinforcement; crack control, vibration,
fire, durability and any calculated deflection. Only the deemed-to-comply
thickness rule is applied.

A landed flight must be modelled as separate spans; the module assumes the flight
spans the full horizontal span `L`.

## Units and conventions

Working units are **N and mm on a one metre wide strip**. A load in kPa is
numerically a line load in N/mm on that strip, so moments come out in N.mm per
metre and areas in mm2 per metre. Concrete density is in kg/m3 because that is
the unit AS 3600 Cl 3.1.2 uses.

The design moment is `w* L^2 / 8` for every span type. The span type only selects
the Table 2.3.2 deflection constant `k4` (1.4 simple, 2.1 interior, 1.75 end).

## Differences from the source workbook

| Workbook behaviour | This module | Why |
| --- | --- | --- |
| `Design!D34` encodes bar count, centres or area by magnitude (`<75`, `75..600`, `>600`) | Explicit `reoMode` selector plus `reoValue` | The suite form cannot express a magnitude-encoded mode safely |
| Summary ratio is `MAX(astmin/Ast, Mstar/fMuo, thmin/ath)` | Adds `ductility` and `deflectionIncremental` | The workbook computes both but leaves them out of its ratio; a failed rule must affect the status |
| `Design!C60` label tests `fc <= 40` while `Design!D60` tests `fcmi <= 40` | The formula's `fcmi` test is used | The label and the formula disagree in the source; the formula governs |
| `meshname` VBA lookup naming a standard mesh from a pair of steel areas | Not transcribed | Display only; it affects no capacity |
| Text comparisons such as `loadtype="floor"` | Selector values folded to upper case | Reproduces Excel's case-insensitive text comparison |

## Commands

```powershell
Set-Location C:\CODING\INNOCALC
$Python = Join-Path $PWD '.venv\Scripts\python.exe'
& $Python -m tooling check concrete-stair --validate
& $Python -m tooling dev concrete-stair calculations/concrete/concrete_stair/examples/worked-example.json --html artifacts/concrete-stair/worked-example.html
$env:PYTHONPATH = "C:\CODING\INNOCALC\calculations\concrete\concrete_stair\src;C:\CODING\INNOCALC"
& $Python -m unittest discover -s calculations\concrete\concrete_stair\tests -v
```

## Evidence

`validate()` runs a 108-case sweep across three span types, four grades, three
geometries and three load levels, and replays the retained workbook example,
comparing **38 published values** including the full serviceability chain
(`Ec`, `n`, `ku`, `NA`, `kcs`, `Fd.ef`) and both minimum thicknesses.
`tests/test_engine.py` adds 43 further tests.

The retained example is a **failed design**: the workbook itself prints
`No Good (1.11)` for bending, and it also exercises the compression-steel-in-tension
branch, which the module reproduces exactly.

## Outstanding release gates

1. Independent engineering review against AS 3600:2018 Sections 8, 9 and 2.3.
2. Confirmation that the ductility limit and the incremental deflection limit
   should contribute to the governing ratio, which the workbook omitted.
3. A decision on whether the mesh naming lookup is needed.
4. A worked example from a source independent of Structural Toolkit.
5. A named responsible maintainer.
6. Manager integration testing and PDF acceptance. No PDF has been inspected.
