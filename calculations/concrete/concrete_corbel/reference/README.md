# Reference Evidence

## Source

| Item | Value |
| --- | --- |
| Document | `Concrete_Corbel_506.xls`, Structural Toolkit module **CORBEL V5.06** |
| Description | Concrete corbel design (`Settings!C5`) |
| Standard cited | AS 3600:2018 incl. Amendments 1 and 2; AS/NZS 1170.0:2002; AS/NZS 1170.1:2002 |
| Workbook revision | 5.06, dated 31-Jul-2023, "Corrected the steel area for shear friction calculation" |
| Source SHA-256 | `2e85b8d74f54329ff7ed285ec912f933e467265a2922da4572aaf9778150fde6` |
| Decoded XLS SHA-256 | `b2c361b5d4c4d9c9cfe03bfecaf5650b2bb3e3b26699675809c5abf299242d3f` |
| Static review | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_Corbel_506.md` |
| Complete extract | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_Corbel_506.audit.json` |
| Extracted | 10 September 2026 |
| Permitted use | Internal transcription evidence for the InnoCalc `concrete-corbel` module. |

The originals are held in the workbook review workspace and are not copied here.

## Extraction procedure

The review export lists every worksheet formula, every defined name and every
cached value for the workbook's saved state. The expected values in
`../src/ic_concrete_corbel/data/workbook-baseline.json` were taken cell by cell
from that register (sheet `Design`, plus `Settings!O19` for the governing ratio),
not by re-running Excel. Each expected value records the cell it came from in the
`sheetCells` field of its case.

## Known defect in the saved state

`Design!A6` and `Design!K14` both read "Warning - Recalculation required" because
`Design!L17` (`error = Cf* + 0.01 - phiCa`) holds `-7.90333089991` kN instead of
zero. The stored strut width `Design!E75` (`dc = 18.7954083212` mm) is therefore
**not** the GoalSeek solution for the stored inputs.

The baseline is split accordingly:

* `computeCases` compares only quantities that do not depend on `dc`.
* `strutCases` pins `dc` at the stored value and checks the Cl 7.2.3 strut chain
  and the Cl 7.3.2 tie force, reproducing `Design!L17` as the residual. This
  proves the formula transcription without adopting the unconverged answer.

## Outstanding

No third-party worked example independent of Structural Toolkit has been supplied.
Agreement with this baseline establishes transcription fidelity only. An
independent hand calculation to AS 3600:2018 Sections 7 and 8.4.3 is required
before release, and must be recorded here with reviewer, date and version.