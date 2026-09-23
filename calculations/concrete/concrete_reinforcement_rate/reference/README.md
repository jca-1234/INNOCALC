# Reference Evidence

## Source

| Item | Value |
| --- | --- |
| Document | `Concrete_Rate_500.xls`, Structural Toolkit module **REINFORCEMENT RATE V5.00** |
| Description | Reinforcement rate (`Settings!C5`) |
| Standard cited | AS 3600:2018 incl. Amendments 1 and 2 |
| Workbook revision | 5.00c, "Incorporated AS 3600 - 2018 Amndt 2" |
| Static review | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_Rate_500.md` |
| Complete extract | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_Rate_500.audit.json` |
| VBA extract | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_Rate_500.vba.txt` |
| Extracted | 11 September 2026 |
| Permitted use | Internal transcription evidence for the InnoCalc `concrete-reinforcement-rate` module. |

The originals are held in the workbook review workspace and are not copied here.

## This workbook performs no design check

It has no pass or fail cell, no utilisation ratio and no capacity comparison. The
only error string is the `"Error"` a schedule row returns when its type letter is
not `B`, `L` or `T`. Agreement with it establishes quantity arithmetic only.

## Extraction procedure

All 123 `Rate` sheet formulas were read from the review export's formula
register with their cached values. The 21 schedule rows share one formula
template, quoted once and applied to every row index.

## Coverage and the gap in the evidence

The workbook was saved with an **empty schedule**. `Rate!C17` and `Rate!C18`
therefore both cache zero, and the only genuine published values are the member
geometry chain:

| Cell | Quantity | Cached |
| --- | --- | --- |
| `Rate!G11` | cross sectional area | 0.15 m2 |
| `Rate!G12` | concrete volume | 0.15 m3 |
| `Rate!G14` | hook length | 150 mm |
| `Rate!G15` | transverse ligatures | 6 |
| `Rate!G16` | one ligature length | 2.32 m |
| `Rate!G17` | transverse set length | 2.46 m |

The schedule row rules (`F`, `G`, `H` and `I` columns) are transcribed from the
formulas but have **no cached values to compare against**. The baseline cases
covering them are marked `derived`: their inputs were chosen during transcription,
not taken from the workbook. Closing this gap is the first outstanding item.

## Not transcribed

* `Module1.bas` contains `onewayslab`, `twowayslab` and `band`, which set the
  member inputs and copy a schedule from Settings ranges `B8:E11`, `B14:E17` and
  `B20:E26`. Those ranges were **not captured** in the review export, so the
  templates cannot be reproduced without inventing their contents.
* `Rate` rows 48 to 54 are a superseded schedule template. They hard code the
  steel density as 7850 rather than using the `den` input, and their comment
  formula references an undefined name `B` where `rb` was intended. They are dead
  and are not transcribed.
* The comment string at `Rate!H24` contains a nested `IF` whose inner false branch
  can never be reached, because the outer condition already guarantees the inner
  one. Only the reachable behaviour is implemented.

## Outstanding

1. Recalculate the source workbook with a populated schedule, or hand-check the
   row rules, so the schedule arithmetic gains real evidence.
2. Decide whether the template macros are required; if so, re-extract the Settings
   template ranges.
3. Independent review of the transcription, recorded here with reviewer, date and
   version.
