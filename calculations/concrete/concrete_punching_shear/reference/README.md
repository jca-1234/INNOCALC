# Reference Evidence

## Source

| Item | Value |
| --- | --- |
| Document | `Concrete_Punching_506.xls`, Structural Toolkit module **PUNCHING SHEAR V5.06** (8 December 2023, "Added integrity reinforcement") |
| Description | Design of slabs in punching shear (AS3600-2018 Section 9.3) |
| Standards cited | AS/NZS 1170.0:2002, AS/NZS 1170.1:2002, AS 3600:2018 incl. Amdt 1 and 2; Warner, Rangan, Hall and Faulkes, *Concrete Structures* (1999) |
| Source SHA-256 | `3c3519e391eb8a3ea1292f2a7158289d18ae75336d49e926f39b084d539ae271` |
| Decoded XLS SHA-256 | `622fda7c1227c40cb22060e41116eb919580269374c845463e2b3c07295099d7` |
| Static review | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_Punching_506.md` |
| VBA extract | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_Punching_506.vba.txt` |
| Complete extract | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_Punching_506.audit.json` |
| Cell listing used | `artifacts/workbook-extracts/Concrete_Punching_506.cells.txt` (hashes in its header match the above) |
| Extracted | 24 September 2026 |

The originals are held in the workbook review workspace and are not copied here.

## Extraction procedure

The expected values were taken cell by cell from the cached values in the cell listing:

* sheet `Design`, rows 18 to 105, and sheet `Settings`, cells O22:O40, T44:U67 and
  AB50:AB53, for the saved example;
* sheet `Settings`, cells T72:AE95, for the circular-perimeter geometry, which the workbook
  evaluates for the saved `pL` and `domc` whatever the column shape;
* sheet `Settings`, cells Z139:AB178, AI139:AK178 and AQ139:AS178, for the author's
  GoalSeek harness. `Module2.MarkSuccess` writes `CInt(bw) & "," & CInt(domc)`, which Excel
  stored as a number (for example `25177` for `bw = 25`, `domc = 177`).

Excel was not re-run. `Module1.RecalcDom` was replaced by a bisection. Workbook forces in
kN and moments in kNm are compared as N and N mm (x 1000 and x 1e6).

## Saved-state notes

* The saved state is internally consistent. Every summary string in `Design!B8:I14` agrees
  with the cached numbers.
* `Settings!T56` (`dom_gs = 304.74`) is left from an earlier GoalSeek; it is not used
  because `Settings!T44` (`dom_gs_required`) is FALSE.
* The 73 `#NUM!` cells in `Settings!V106:AR115` belong to the curved-perimeter test matrix
  and are outside their valid geometric range; they do not feed the design.
* `Design!D31` stores `l`, `I18` stores `n` and `I21` stores `y`; Excel compares text
  case-insensitively.

## Independent benchmark

Tedds library exports reviewed for §2.1 of `TECHNICAL-README.md`:
`C:/CODING/Tedds/_TEDDS_MDs/calculations/AU/AU RC slab design.md`,
`Foundations-AS3600-si-enau.md`, `AUPad.md`, `AusFound.md`, `AustRC.md`,
`RC member design-AS3600-si-enau.md` and
`C:/CODING/Tedds/_TEDDS_MDs/calculations/General/Pile cap design-x-x-x.md`.

## Outstanding

There is no worked example independent of Structural Toolkit. Agreement with this baseline
shows transcription fidelity only. Independent engineering review has not been recorded.
