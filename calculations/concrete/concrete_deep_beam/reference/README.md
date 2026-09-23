# Reference Evidence

## Source

| Item | Value |
| --- | --- |
| Document | `Concrete_DeepBeam_502.xls`, Structural Toolkit module **DEEP BEAMS V5.02** |
| Description | Compression strut design (`Settings!C5`) |
| Method | CEB approach after Warner, Rangan, Hall and Faulkes, *Reinforced Concrete*, Longman 1998 |
| Standard cited | AS 3600:2018 incl. Amendments 1 and 2; AS/NZS 1170.0:2002; AS/NZS 1170.1:2002 |
| Workbook revision | 5.02b, "Incorporated AS 3600 - 2018 Amendment 2 (no functional change)" |
| Static review | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_DeepBeam_502.md` |
| Complete extract | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_DeepBeam_502.audit.json` |
| Extracted | 10 September 2026 |
| Permitted use | Internal transcription evidence for the InnoCalc `concrete-deep-beam` module. |

The originals are held in the workbook review workspace and are not copied here.

## The method is declared superseded by its own source

`Info!F19` and `Design!B15` both read
`Superceded CEB Approach - Informative only`, and `Settings!Q28` reads
`Superceded v5.01`. The v5.02 revision note records "added superceded warnings".

Agreement with this baseline therefore establishes **transcription fidelity of a
superseded method**. It is not evidence that the method is acceptable for current
design. A decision on whether to publish the module at all is the first
outstanding gate.

## Extraction procedure

All 60 `Design` sheet formulas and the 14 `Settings` sheet formulas were read from
the review export's formula register with their cached values, cell by cell. No
Excel recalculation was performed. The workbook has no VBA procedures, no
GoalSeek, no circular references, no external links and no broken names, so the
cached values are consistent with the stored inputs.

## State of the saved example

The example is a cantilever with `c = 900 mm` against a limit of `L/5 = 600 mm`.
`Design!D23` correctly displays `mm Error - c > L/5`, but the workbook's summary
`Settings!O21 = MAX(Vstar/fV)` does not include that rule and `Design!I7`
therefore prints `OK (0.15)`.

This is reproduced deliberately: the baseline asserts both
`util.diagonalCompression = 0.15` (the workbook's own cached ratio) and
`util.supportWidthLimit = 1.5`, and the module reports FAIL.

`Design!C17` stores lowercase `c` for the span type; Excel matches it
case-insensitively against `"C"`, which the module reproduces by folding case.

`Design!H22` stores a mesh wire diameter of 10 mm, which is not in the workbook's
own validation list (6.75, 7.6, 8.55, 9.5, 10.65, 11.9, 12 mm). The module
therefore accepts any positive diameter and warns instead of rejecting.

## Outstanding

No third-party worked example independent of Structural Toolkit has been
supplied. An independent hand calculation, and a comparison against an
AS 3600:2018 Section 12 strut-and-tie solution for the same beam, are required
before release and must be recorded here with reviewer, date and version.
