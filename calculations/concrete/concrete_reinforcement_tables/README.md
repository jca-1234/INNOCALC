# Reinforcement Tables

| | |
| --- | --- |
| Module ID | `concrete-reinforcement-tables` |
| Package | `ic_concrete_reinforcement_tables` |
| Entry point | `ic_concrete_reinforcement_tables.headless` |
| Filing folder | `10 - REINFORCEMENT TABLES` |
| Category | `Concrete` |
| Version | `v0.0.1` |
| Status | `planned`, `enabled = false` |
| Source workbook | `Concrete_Reinforcement_500.xls` (Structural Toolkit REINFORCEMENT V5.00) |

> **This module performs no design check.** It is a reference lookup: bar areas
> and fabric properties. It returns `util = {}` and `worstUtil = 0.0`.

## What it reports

| Table | Content |
| --- | --- |
| Selected reinforcement | Area of one bar, area of `n` bars, and area per metre at the entered centres, exact and rounded |
| Area for a number of bars | 1 to 30 bars, for 12 to 40 mm |
| Area per metre for bar centres | 60 to 1000 mm centres, for 12 to 40 mm |
| Fabric properties | 6 rectangular, 9 square and 3 trench mesh designations |

Areas are `pi db^2 / 4`, and per metre `x 1000 / centres`. Table values are
rounded **down**, as the source workbook does, so a tabulated area is always at
or below the exact value. Both are printed.

## What is excluded

* **The prestressing tendon table is not transcribed.** The review export captured
  the `Tendons` sheet column headings only, not the wire, strand and bar property
  values for AS 1310, AS 1311 and AS 1313.
* No steel grade, ductility class, mass per metre, development length or
  detailing rule.

## Provenance warning on the fabric table

The fabric wire diameters and pitches come from the workbook, which cites the
OneSteel *onemesh 500* publication. They have **not** been checked against a
current manufacturer's catalogue, and mesh products change. The calculation sheet
says so. Confirm against a current source before specifying.

The source records **one wire** for `L8TM`, which is unusual for a trench mesh
product. It is transcribed as recorded and flagged.

## Differences from the source workbook

| Workbook behaviour | This module | Why |
| --- | --- | --- |
| `Number` sheet tabulates 12 to 32 mm with a seventh user-selectable column repeating 32 mm; `Centres` uses 40 mm for its seventh | Both tables cover 12, 16, 20, 24, 28, 32 and 40 mm | A superset of the source; no value is lost |
| `Centres` column B spacing list not fully captured in the export | This module's own list of 21 practical spacings from 60 to 1000 mm | Only the first and last rows have published values |
| No user inputs at all; the tables are printed | A bar size, count, centres and mesh are selected and reported alongside the tables | Makes the module useful inside the manager |

## Commands

```powershell
Set-Location C:\CODING\INNOCALC
$Python = Join-Path $PWD '.venv\Scripts\python.exe'
& $Python -m tooling check concrete-reinforcement-tables --validate
& $Python -m tooling dev concrete-reinforcement-tables calculations/concrete/concrete_reinforcement_tables/examples/worked-example.json --html artifacts/concrete-reinforcement-tables/worked-example.html
$env:PYTHONPATH = "C:\CODING\INNOCALC\calculations\concrete\concrete_reinforcement_tables\src;C:\CODING\INNOCALC"
& $Python -m unittest discover -s calculations\concrete\concrete_reinforcement_tables\tests -v
```

## Evidence

`validate()` runs a 188-case sweep across bar sizes, counts, spacings, rounding
options and every fabric designation, and replays the retained workbook tables,
comparing **35 published values**: both published rows of the bar count table,
both published rows of the centres table, and all 14 published fabric areas.
`tests/test_engine.py` adds 36 further tests.

## Outstanding release gates

1. **Check the fabric properties against a current manufacturer's catalogue.**
2. Re-extract the `Tendons` sheet if the prestressing table is required.
3. Confirm the `L8TM` single-wire record.
4. Re-extract the `Centres` sheet column B if the source spacing list must be
   reproduced exactly.
5. A named responsible maintainer.
6. Manager integration testing and PDF acceptance. No PDF has been inspected.
