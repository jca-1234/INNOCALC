# Reference Evidence

## Source

| Item | Value |
| --- | --- |
| Document | `Concrete_TwoWaySlab_502.xls`, Structural Toolkit module **TWO-WAY SLABS V5.02** (revision 5.02f) |
| Description | Simplified method for reinforced two-way slabs supported on four sides (AS3600-2018 Section 6.10) |
| Standards cited | AS/NZS 1170.0:2002, AS/NZS 1170.1:2002, AS 3600:2018 incl. Amdt 1 and 2; Warner, Rangan, Hall and Faulkes, *Concrete Structures* (1999); Warner, Rangan and Hall, *Reinforced Concrete* 3rd ed. (1996) |
| Source SHA-256 | `83c09e2f54200c846ba4ed8ec6212f2977e75d48a48d86a57d029c945ff73f39` |
| Decoded XLS SHA-256 | `7e3527e5e12c868cd2684a7fb245bcb7d48e5eac544fdc64bfab175029a1d69e` |
| Static review | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_TwoWaySlab_502.md` |
| Complete extract | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_TwoWaySlab_502.audit.json` |
| Cell listing used | `artifacts/workbook-extracts/Concrete_TwoWaySlab_502.cells.txt` |
| Extracted | 24 September 2026 |

The originals are held in the workbook review workspace and are not copied here.

## Extraction procedure

The expected values were taken cell by cell from the cached values in the audit extract.
They come from sheet `Analysis` (rows 13 to 68) and sheet `Settings` (O19 to O36 and the
coefficient tables P39:Z88). Excel was not re-run. The VBA routines `Interp` and `Getk4`
were transcribed from the extracted source.

## Saved-state notes

* `Settings!O25` holds `#VALUE!` from the `ChangeEdges` drawing macro. This is presentation
  only.
* The `Prelim` sheet is hidden in V5.02 ("Removed 2018 code") and was not used.

## Outstanding

There is no worked example independent of Structural Toolkit. Agreement with this baseline
shows transcription fidelity only.
