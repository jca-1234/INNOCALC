# Reinforcement Development and Laps

| | |
| --- | --- |
| Module ID | `concrete-development` |
| Package | `ic_concrete_development` |
| Entry point | `ic_concrete_development.headless` |
| Filing folder | `09 - REINFORCEMENT DEVELOPMENT` |
| Category | `Concrete` |
| Standard | AS 3600:2018 incl. Amendments 1 and 2, Section 13 |
| Version | `v0.0.1` |
| Status | `planned`, `enabled = false` |
| Source workbook | `Concrete_Development_506.xls` (Structural Toolkit REINFORCEMENT DEVELOPMENT V5.06) |

> **Not approved for design.** Transcription of a retained Structural Toolkit
> workbook. Independent engineering review is outstanding.

## This module produces lengths, not a design check

It returns `util = {}` and `worstUtil = 0.0`. It does, however, reproduce the
workbook's two **lapped splice validity errors**, and those force a `FAIL`
summary:

* a tension bar stress below `fsy` invalidates the Cl 13.2.2 tension lap
  (`Development!G69`);
* a compression bar stress below `fsy` invalidates the Cl 13.2.4 compression lap
  (`Development!G122`).

## What it calculates

| Result | Expression | Reference |
| --- | --- | --- |
| `Lsy.tb` | `max[0.5 k1 k3 fsy db / (k2 sqrt(f'c)), 0.058 fsy k1 db] x me ml ms x mb` | Eq 13.1.2.2 |
| `Lsy.t` | reduced for `sigma.st`, minimum `12 db` | Cl 13.1.2.4 |
| `Lsy.tp` | `max(1.5 Lsy.t, 300)` | Cl 13.1.3 |
| `Lsy.t.lap` | wide: `max(k7 Lsy.t(1)/corr, 29 k1 db)`; narrow: also `1.5 sb + Lsy.t(1)` | Cl 13.2.2 |
| `Lsy.cb` | `max[0.22 fsy/sqrt(f'c) db, 0.0435 fsy db, 200] x mb` | Eq 13.1.5.2 |
| `Lsy.cp` | `2 Lsy.c` | Cl 13.1.6 |
| `Lsy.c.lap` | `mb rn rh max[max(Lsy.c(1), 300), 40 db]` | Cl 13.2.4 |
| Hooks and cogs | optional, from the Cl 17.2.3.3 internal diameter | Cl 13.1.2.7 |

Factors reported: `k1`, `k2`, `k3`, `cd`, `mb`, `me`, `ml`, `ms`, `k7`, `sb`,
`rn`, `rh`. `ms` is fixed at 1.0, as the source workbook has done since its
v5.04.

Tension development caps `f'c` at 65 MPa (Cl 13.1.2.2). Compression development
offers that cap as an option, off by default, matching the workbook.

## Two chains, deliberately

The **single bar** results carry full precision through the whole chain and are
rounded only for printing. The **bar size table** rounds up at every step, exactly
as the workbook does, so a table value can exceed the single bar value. For the
retained example the single bar plain tension length is `522 mm` while the 12 mm
table row reads `530 mm`. Both are reproduced and the difference is stated on the
sheet.

The tension lap correction inside the table uses the **unlimited** `f'c`, while
the single bar correction follows from the tension limited `f'c`. Above 65 MPa
the two differ. This is the workbook's own behaviour.

## The LapCorrection factor

Cl 13.2.2 is implemented with the workbook's own VBA function:

```
LapCorrection = max(0.058 / 0.5 x k2 sqrt(f'c) / k3, 1)
```

Its purpose, per a note on the workbook sheet, is to remove the Eq 13.1.2.2 lower
limit before `k7` is applied. **That derivation is a workbook note, not a clause,
and the reviewer must confirm it.**

## Differences from the source workbook

| Workbook behaviour | This module | Why |
| --- | --- | --- |
| Separate bar diameter, galvanising and rebending inputs for the hook block and the cog block | One set of bend inputs | The two formula sets are identical; duplicating the inputs adds no engineering |
| `Settings!R57` aggregates the lap error as `OR(stress < fsy, stressc > fsy)` | Follows the on-sheet tests, both `< fsy` | The aggregate cell disagrees with the two cells that print the messages |
| Slip formed switch `sk` retained but unused | Not offered | Dead since v5.04; `ms` is fixed at 1.0 |
| Text comparisons such as `plain="n"` | Options folded to upper case | Reproduces Excel's case-insensitive text comparison |

## Commands

```powershell
Set-Location C:\CODING\INNOCALC
$Python = Join-Path $PWD '.venv\Scripts\python.exe'
& $Python -m tooling check concrete-development --validate
& $Python -m tooling dev concrete-development calculations/concrete/concrete_development/examples/worked-example.json --html artifacts/concrete-development/worked-example.html
$env:PYTHONPATH = "C:\CODING\INNOCALC\calculations\concrete\concrete_development\src;C:\CODING\INNOCALC"
& $Python -m unittest discover -s calculations\concrete\concrete_development\tests -v
```

## Evidence

`validate()` runs a 75-case sweep across five grades, five bar sizes and three
option sets, and replays the retained workbook example and its hook and cog
block, comparing **59 published values**. `tests/test_engine.py` adds 48 further
tests, including the workbook's full published compression table
(220, 270, 350, 440, 530, 610, 700, 790 mm for 10 to 36 mm bars).

## Outstanding release gates

1. Independent engineering review against AS 3600:2018 Section 13.
2. **Confirmation of the LapCorrection derivation**, which rests on a workbook
   note rather than a clause.
3. Resolution of the `Settings!R57` discrepancy in the lap error condition.
4. A worked example from a source independent of Structural Toolkit.
5. A named responsible maintainer.
6. Manager integration testing and PDF acceptance. No PDF has been inspected.
