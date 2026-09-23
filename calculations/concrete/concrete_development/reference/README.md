# Reference Evidence

## Source

| Item | Value |
| --- | --- |
| Document | `Concrete_Development_506.xls`, Structural Toolkit module **REINFORCEMENT DEVELOPMENT V5.06** |
| Description | Reinforcement areas and development (`Settings!C5`) |
| Standard cited | AS 3600:2018 incl. Amendments 1 and 2, Section 13 |
| Workbook revision | 5.06a, "Removed hook and cog development length for compression" |
| Decoded XLS SHA-256 | `c8c758731c883535c0200c187ed42f52f29d4a1d9beb6699e04c38424b23f298` |
| Static review | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_Development_506.md` |
| Complete extract | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_Development_506.audit.json` |
| Extracted | 11 September 2026 |
| Permitted use | Internal transcription evidence for the InnoCalc `concrete-development` module. |

The originals are held in the workbook review workspace and are not copied here.

## This workbook performs no design check

It produces lengths. Its only on-sheet error strings concern the validity of
lapped splices at a reduced bar stress, not capacity. Agreement with it
establishes length arithmetic only.

## Extraction procedure

All 157 `Development` sheet formulas and 30 `Cogs` sheet formulas were read from
the review export's formula register with their cached values. The bar size table
shares one formula template per row, quoted once and applied to every column.

## VBA transcribed

`Module1.bas` defines one function, transcribed verbatim as
`engine.lap_correction`:

```vba
Function LapCorrection(db As Double, fc As Double, cd As Double) As Double
    k2 = (132 - db) / 100
    k3 = (1 - 0.15 * (cd - db) / db)
    If k3 < 0.7 Then k3 = 0.7
    If k3 > 1 Then k3 = 1
    lc = 0.058 / 0.5 * k2 * Sqr(fc) / k3
    If lc < 1 Then lc = 1
    LapCorrection = lc
End Function
```

A note at `Development!K85:K87` explains its purpose as taking account of
Cl 13.2.2 not requiring the Eq 13.1.2.2 lower limit. **That is a workbook note,
not a clause reference, and the reviewer must confirm the derivation.**

## Internal inconsistency found

`Settings!R57` defines the aggregate lap error as
`OR(stress < fsy, stressc > fsy)`, but the two cells that actually print the
messages, `Development!G69` and `Development!G122`, both test `< fsy`. The
`stressc > fsy` term appears to be a typographical error. This module follows the
two message cells. The reviewer must resolve which is intended.

## Precision limit in the export

The cached value at `Development!E97` (`Lsycb1`) was truncated to `208.71...` in
the review export. The baseline therefore asserts it to four decimal places only.
Every other asserted value carries full published precision.

## Not transcribed

* The `Cogs` sheet repeats identical formulas for a hook block and a cog block
  with separate inputs. The module uses one set of bend inputs; the maths is
  unchanged.
* The slip formed switch `sk` and its multiplier `ms` were retired at workbook
  v5.04 and `ms` is fixed at 1.0.

## Outstanding

An independent hand calculation to AS 3600:2018 Section 13, and a decision on the
LapCorrection derivation and the `Settings!R57` discrepancy, are required before
release and must be recorded here with reviewer, date and version.
