# Concrete Design Parameters

| | |
| --- | --- |
| Module ID | `concrete-parameters` |
| Package | `ic_concrete_parameters` |
| Entry point | `ic_concrete_parameters.headless` |
| Filing folder | `05 - CONCRETE PARAMETERS` |
| Category | `Concrete` |
| Standard | AS 3600:2018 incl. Amendments 1 and 2; AS 2327:2017 |
| Version | `0.1.0.dev0` |
| Status | `planned`, `enabled = false` |
| Source workbook | `Concrete_Formula_502.xls` (Structural Toolkit FORMULA V5.02) |

> **Not approved for design.** Transcription of a retained Structural Toolkit
> reference sheet. Independent engineering review is outstanding.

## This module performs no design check

The source workbook is a printed reference sheet: one live input (`f'c`) and a
set of tabulated material parameters. It contains no capacity comparison and no
ratio cell, so this module returns `util = {}` and `worstUtil = 0.0`. The summary
headline says so explicitly and must never be read as structural adequacy.

## What it reports

| Group | Quantities | Reference |
| --- | --- | --- |
| Stress block | `alpha1` (0.72 to 0.85), `alpha2` (>= 0.67), `gamma` (>= 0.67), `epsilon.c` | Eq 10.6.2.2, Eq 8.1.3(1), Eq 8.1.3(2), Eq 10.6.2.5(1), Eq 10.6.2.5(2), Cl 10.6.1(d) |
| Tensile strength | `f'ct.f = 0.6 sqrt(f'c)`, `f'ct = 0.36 sqrt(f'c)` | Cl 3.1.1.3 |
| Mean in-situ strength | `fcmi` from Table 3.1.2, from the workbook curve fit, and from AS 2327 | Table 3.1.2, AS 2327:2017 Table 3.6.2.3 |
| Stiffness | `Ec` with its plus or minus 20 per cent range | Cl 3.1.2 |
| Strength gain | `f'c` at 1, 3, 7, 28, 90 and 365 days for normal and high early cement | Workbook table, **no clause** |
| Optional | Deemed-to-comply `Ast.min` and `alpha.b` | Cl 8.1.6.1, Cl 9.1.1 |
| Optional | Minimum cracking moment `1.2 Z f'ct.f` | Cl 8.1.6.1 |

### Provenance warnings carried on the sheet

* The **strength gain table carries no AS 3600 clause reference.** It is the
  workbook's own table and its provenance has not been established. It must not
  be used for a specification or acceptance decision without an authoritative
  source. This is stated on the printed sheet.
* The **`fcmi` curve fit is the workbook's own approximation** to Table 3.1.2, not
  a code equation.
* The **AS 2327 `fcmi`** expression is for composite work and is not
  interchangeable with the AS 3600 value.

## Deliberate reconciliation

The workbook prints `alpha2` and `gamma` for beams (Eq 8.1.3) without their lower
bounds but states the `>= 0.67` bound for the identical column equations
(Eq 10.6.2.5). This module applies the bound in both places. At `f'c = 120 MPa`
both factors are exactly `0.67` and `alpha1` is governed by its `0.72` floor.

Selecting `Table 3.1.2` as the `fcmi` source at a grade that is not tabulated
raises `ValueError` listing the tabulated grades, rather than interpolating.

## Commands

```powershell
Set-Location C:\CODING\INNOCALC
$Python = Join-Path $PWD '.venv\Scripts\python.exe'
& $Python -m tooling check concrete-parameters --validate
& $Python -m tooling dev concrete-parameters calculations/concrete/concrete_parameters/examples/worked-example.json --html artifacts/concrete-parameters/worked-example.html
$env:PYTHONPATH = "C:\CODING\INNOCALC\calculations\concrete\concrete_parameters\src;C:\CODING\INNOCALC"
& $Python -m unittest discover -s calculations\concrete\concrete_parameters\tests -v
```

## Evidence

`validate()` runs a 162-case sweep across every grade, `fcmi` source and age, and
replays the retained workbook tables, comparing **46 published values**.
`tests/test_engine.py` adds 34 further tests.

One check goes beyond the workbook: `Ec` is compared with the AS 3600
Table 3.1.2 published values of 30 100 MPa (N32) and 32 800 MPa (N40) and agrees
within 2 per cent.

## Outstanding release gates

1. Independent engineering review of the transcription.
2. **Provenance of the strength gain table must be established or the table
   removed.**
3. A named responsible maintainer.
4. Manager integration testing and PDF acceptance. No PDF has been inspected.
