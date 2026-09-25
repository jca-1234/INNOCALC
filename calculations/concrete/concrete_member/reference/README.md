# Reference Evidence

## Source

| Item | Value |
| --- | --- |
| Document | `Concrete_Member_513.xls`, Structural Toolkit module **CONCRETE MEMBER V5.13** |
| Description | Design of beams and slabs for strength and serviceability (AS3600-2018 Sections 8 and 9) |
| Standards cited | AS 3600:2018 incl. Amdt 1 and 2; AS/NZS 1170.0:2002; AS 5100.5:2017 (the `Act` definition option only); Warner, Rangan, Hall and Faulkes, *Concrete Structures* (1999) |
| Source SHA-256 (`C:/CODING/STK/Concrete_Member_513.xlse`) | `a247d2cfecc0792b75f14a07244900d9766a6d881c234ee981d3c4246a7ac015` |
| Decoded XLS SHA-256 (`Concrete_Member_513.xls`) | `1482aa3be6362a83cee6118f317623c8795319b14e353c27dee266026cf644de` |
| VBA extract SHA-256 (`Concrete_Member_513.vba.txt`) | `0f7bb9480721f7347f9f1213c1aa90f81f68042d02a608e15ae032f73641fe0e` |
| Cell listing SHA-256 (`artifacts/workbook-extracts/Concrete_Member_513.cells.txt`) | `577929e9582384e8de529f55b286c61eee2bc486b6201e55dbf4cb7a75118e06` |
| Static review | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_Member_513.md` |
| Complete extract | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_Member_513.audit.json` |
| Extracted | 24 September 2026 |
| Permitted use | Internal transcription evidence for the InnoCalc `concrete-member` module |

The originals are held in the workbook review workspace and are not copied here. The workbook
has 16 worksheets, 2894 formulas, 1413 defined names and 29 readable VBA modules.

## Independent benchmark

| Item | Value |
| --- | --- |
| Document | Tekla Tedds *RC member design (AS3600)*, AS 3600-2018 Amdt 1 and 2 |
| Location | `C:/CODING/Tedds/_TEDDS_MDs/calculations/AU/RC member design-AS3600-si-enau.md` |
| Also reviewed | `system-sets/Developer/RC beam deflection-AS3600.md` (AustRC library, AS 3600-2001 era; not used), `calculations/General/RC beam torsion design-x-x-x.md` (no AS 3600 content) |

TECHNICAL-README §2.1 records the comparison. No Tedds values enter the baseline.

## Extraction procedure

1. The expected values are the cached values in the cell listing. Excel was not re-run.
   They cover `Design!C13:N70`, `Detailed!C7:M170`, `Shear!C18:I249`, `Defl!C13:U81`,
   `Creep&Shrink!D11:H86`, `BeamDefl!D14:E55` and `Settings!O22:AF495`.
2. The saved inputs were read from the same cells and mapped to the module schema
   (`computeCases[0].inputs` in `data/workbook-baseline.json`). Text inputs keep the saved
   case (`s`, `n`, `c`) to test case folding.
3. These VBA routines were transcribed from the extract: `centroid`, `CalcAst2009`,
   `CalcIuncrkna`, `CalcIuncrkk`, `CalcIcrkna`, `CalcIcrkk` and `CalcTable`.
4. 492 cell mappings were compared at relative tolerance `1e-9`. Of these, 483 have
   numeric cached values; all 483 agree. The rest are text or blank.
5. The deliberate departures (`Design!G68`, `Detailed!J129`, `J130`, `J131`, `J138`, `J139`,
   `J141`, `J160`, `J161`, `J164`, `Settings!X464` and `BeamDefl!E30`) are listed in the
   baseline with both the workbook value and the module value. They are not compared.

## Saved-state notes

* The saved member fails. `M* = -30` kNm is resisted by one N12 top bar at 300 mm centres in a
  500 mm wide beam. The deemed-to-comply live load (20 kN/m) exceeds the dead load (7.5 kN/m).
* `Creep&Shrink!E12` selects tested drying shrinkage, but `E13` is blank. So `eps.csd.b* = 0`
  and `eps.cs = 90 x 10^-6`, which is autogenous shrinkage only. This is reproduced and the
  module warns.
* The `Shear` sheet uses its own actions (`V* = 9` kN, `M* = +23` kNm). These are independent of
  the bending `M* = -30` kNm, and the module keeps the two action sets separate.
* The actions are entered manually (`atypev = "M"`, so `Settings!K321` reads `Manual`). The
  `Analysis` and `Results` sheets are therefore inactive and were not used. `Layers`,
  `SlabShear` and `SlabPrelim` were not used either.
* The Preview and drawing macros write to hidden cells. These are presentation only and were
  not compared.

## Outstanding

There is no worked example independent of Structural Toolkit. Agreement with this baseline
shows transcription fidelity only. No independent engineering review has been recorded.
