# Reference Evidence

## Source

| Item | Value |
| --- | --- |
| Document | `Concrete_Reinforcement_500.xls`, Structural Toolkit module **REINFORCEMENT V5.00** |
| Description | Reinforcement areas and development (`Settings!C5`) |
| Fabric source cited | OneSteel Ltd, "onemesh 500" |
| Tendon source cited | AS 1310, AS 1311, AS 1313 |
| Workbook revision | 5.0, "Version 5 release" |
| Static review | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_Reinforcement_500.md` |
| Complete extract | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_Reinforcement_500.audit.json` |
| Extracted | 11 September 2026 |
| Permitted use | Internal transcription evidence for the InnoCalc `concrete-reinforcement-tables` module. |

The originals are held in the workbook review workspace and are not copied here.

## This workbook performs no design check

It has no user input, no design standard declared on its Info sheet, no error or
warning cell, no comparison and no utilisation. It is a printed library of areas.
Agreement with it establishes area arithmetic only.

## Extraction procedure

The `Number` and `Centres` sheets share one formula template per cell block,
quoted once in the review export and applied to every row and column. The
`Fabric` sheet has one formula per wire direction per designation. All were read
with their cached values.

## Coverage and gaps

* The `Centres` sheet **column B spacing list was not fully captured**. Only the
  first row (60 mm) and last row (1000 mm) have published values. This module
  uses its own list of 21 practical spacings between those two, and asserts only
  the two published rows.
* The `Tendons` sheet captured **column headings only** — `Type`, `Dia (mm)`,
  `At (mm2)`, `Breaking (kN)`, `fp (MPa)` — and not the property values. The
  prestressing table is therefore not transcribed. Its single formula,
  `Tendons!E17 = 1140`, is an isolated constant of unclear purpose.
* The `Number` sheet's seventh column duplicates 32 mm as a user-selectable
  column; the `Centres` sheet's seventh column is 40 mm. This module tabulates
  12 to 40 mm on both, a superset.

## Items requiring confirmation

1. **The fabric properties have not been checked against a current manufacturer's
   catalogue.** They derive from a OneSteel publication cited by a workbook whose
   last fabric revision was 2010. Mesh products change.
2. The source records **one wire** for `L8TM` trench mesh, which is unusual.
   Transcribed as recorded and flagged on the sheet.
3. The `Settings` sheet carries eight validation ranges (`__fc`, `__bar`, `__yn`,
   `__fsy`, `__k2`, `__bundle`, `__wires`, `__round`) that no formula in the
   workbook uses. They are vestigial and are not transcribed.

## Outstanding

An independent check of the fabric and, if required, tendon data against current
published sources, recorded here with reviewer, date and version.
