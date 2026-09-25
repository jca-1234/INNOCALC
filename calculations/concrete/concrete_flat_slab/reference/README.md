# Reference Evidence

## Source

| Item | Value |
| --- | --- |
| Document | `Concrete_FlatSlab_504.xls`, Structural Toolkit module **FLAT SLABS V5.04** |
| Description | Simplified method for reinforced two-way slab systems having multiple spans (AS3600-2018 Section 6.10) |
| Standards cited | AS/NZS 1170.0:2002 (Amdt 1 to 5), AS/NZS 1170.1:2002 (Amdt 1 and 2), AS 3600:2018 incl. Amdt 1 and 2; Warner, Rangan, Hall and Faulkes, *Concrete Structures* (1999); Warner, Rangan and Hall, *Reinforced Concrete* 3rd ed. (1996); Foster, Kilpatrick and Warner, *Reinforced Concrete Basics* 2nd ed. (2010) |
| Source SHA-256 | `bb5bb57c0f093c70e4432a2009a8e7d9656f0e19d2e5b702990a447e3f33e47a` |
| Decoded XLS SHA-256 | `e4ee8b4ce612a631ddfffaae4c2582f73828b806c914e212e598522b076d9635` |
| Static review | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_FlatSlab_504.md` |
| VBA extract | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_FlatSlab_504.vba.txt` |
| Complete extract | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_FlatSlab_504.audit.json` |
| Cell listing used | `artifacts/workbook-extracts/Concrete_FlatSlab_504.cells.txt` (hashes above are from its header) |
| Extracted | 24 September 2026 |

The originals are held in the workbook review workspace and are not copied here.

## Extraction procedure

The expected values were read programmatically from the cached values in the cell listing,
cell by cell, and written with their addresses to `data/workbook-baseline.json` (`cells`
map). They come from sheet `Analysis` (rows 8 to 193) and the named cells `Settings!O19`,
`O46`, `O64`, `P67`, `P68` and `P73`. Excel was not re-run. The VBA contains only drawing
macros (`ChangeFlatCols`, `ChangeEdges`), mesh naming (`MeshName`), a `Reset` routine and the
`FindSp*` GoalSeek routines of the `Prelim` sheet; none affects the `Analysis` results.

## Saved-state notes

* The saved state is consistent: the summary strings `Analysis!B7:B9` and the flags
  `Settings!P67`, `P68`, `P76` and `O46` agree with the cached numbers, so the baseline is not
  split.
* `Settings!O42` holds `#VALUE!` from the `ChangeFlatCols` drawing macro. This is
  presentation only.
* `Analysis!H19` stores `y` and `M53` stores `n`; Excel compares text case-insensitively.
* The `Settings!B11:C84` name/value list is the author's default table, not live input.
* The `Prelim` sheet is marked "Removed 2018 standard" and was not used.

## Outstanding

There is no worked example independent of Structural Toolkit, and Tedds has no AS flat slab
calculation. Agreement with this baseline shows transcription fidelity only.
