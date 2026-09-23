# Reference Evidence

## Source

| Item | Value |
| --- | --- |
| Document | `Concrete_Plain_502.xls`, Structural Toolkit module **PLAIN CONCRETE V5.02** |
| Description | Plain concrete element design (`Settings!C5`) |
| Standard cited | AS 3600:2018 incl. Amendments 1 and 2; AS/NZS 1170.0:2002; AS/NZS 1170.1:2002 |
| Workbook revision | 5.02b, "Incorporated AS 3600 - 2018 Amendment 2 (no change)" |
| Static review | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_Plain_502.md` |
| Complete extract | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_Plain_502.audit.json` |
| Extracted | 10 September 2026 |
| Permitted use | Internal transcription evidence for the InnoCalc `concrete-plain` module. |

The originals are held in the workbook review workspace and are not copied here.

## Extraction procedure

All 47 `Design` sheet formulas and their cached values were read from the review
export's formula register, cell by cell. No Excel recalculation was performed.
The expected values live in `../src/ic_concrete_plain/data/workbook-baseline.json`,
each case naming the cells it came from.

## State of the saved example

The workbook has no VBA, no GoalSeek, no external links and no broken names, so
the cached values are consistent with the stored inputs. The example is,
however, a **failed design** (`Design!G88` = `No Good (1.04)`), and two stored
inputs are worth noting:

* `Design!E55` (`P*`) is `-250 kN`, a tensile reaction, although the sheet labels
  `P*` positive in compression.
* `Design!E48` (`Dir`) is lowercase `w`, outside the `{L, W}` validation list.
  Excel's case-insensitive text comparison still resolves `a = aW`.

## Outstanding

No third-party worked example independent of Structural Toolkit has been
supplied. An independent hand calculation to AS 3600:2018 Section 20 is required
before release and must be recorded here with reviewer, date and version.

The review must also settle whether `M*` and `V*`, which the workbook supplies
only for the Eq 20.4.3(2) punching interaction, are the correct demands for the
Cl 20.4.2 bending and Eq 20.4.3(1) one-way shear checks. This module currently
assumes they are and says so on the calculation sheet.
