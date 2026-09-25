# Reference Evidence

## Source

| Item | Value |
| --- | --- |
| Document | `Pavements_Industrial_507.xls`, Structural Toolkit module **INDUSTRIAL FLOOR SLABS V5.07** (revision 5.07a) |
| Description | "Industrial Pavement design using Chandlers methods" (`Settings!C5`); "Design of concrete industrial pavements" |
| References cited (`Info!B10:B29`) | 1. AS 3600 - 2018: Concrete Structures (Incl. Amendment 1 & 2). 2. Technical Report 550 (TR550), J.W.E. Chandler, June 1982. 3. Industrial Floors and Pavements (T48), Cement and Concrete Association of Australia, May 1999. 4. Industrial Floors and Pavements (T48), Cement Concrete & Aggregates Australia, October 2009. 5. Concrete Industrial Floor and Pavement Design (C&CA), Cement and Concrete Association of Australia, July 1985. 6. Smorgan ARC Slabex Steel Fibre Reinforced Concrete, Pavement and Floor Design Technical Manual, November 1998. 7. Guide to Pavement Technology, Part 2: Pavement Structural Design, Austroads, Sydney 2010 |
| Source SHA-256 | `1a8011d5be81191ebe76aef616184e73a67b66926223d23fb9232c71a7b3b9a0` |
| Decoded XLS SHA-256 | `ac22fc1fb4b264bec207f58afc128dd631318d88f53527386899f99ddfcadfe2` |
| Static review | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Pavements_Industrial_507.md` |
| VBA extract | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Pavements_Industrial_507.vba.txt` (`Module1`) |
| Complete extract | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Pavements_Industrial_507.audit.json` |
| Cell listing used | `artifacts/workbook-extracts/Pavements_Industrial_507.cells.txt` (header hashes match the table above) |
| Extracted | 24 September 2026 |

The originals are held in the workbook review workspace and are not copied here.

## Extraction procedure

The expected values in `src/ic_concrete_industrial_pavement/data/workbook-baseline.json` were
read programmatically from the cached values in the cell listing. Each expected path records
its source cell under `cells`. Excel was not re-run. Three summary utilisations have no
dedicated cell and are recomputed from the cited cached stress and strength cells. The VBA
routines `StressRatio`, `MSR`, `CBR`, `Trans`, `Radial`, `TransEdge`, `RadialEdge`, `Moment`
and `ShrinkageSteel` were transcribed from the VBA extract, and their cached results
(`Settings!AO71:AR110`, `Racking!F61`, `Custom!F59`, `Design!E53`, `Design!E56`,
`Design!E104`) are compared as well.

| Evidence set | Values |
| --- | --- |
| Saved example, all tabs incl. Custom | 250 |
| Chandler chart functions `Settings!AN71:AR110` | 160 |
| VBA scalar functions | 5 |
| **Total** | **415**, relative tolerance `1e-9`, all agree |

## Saved-state notes

* The saved state is consistent. Live inputs are on `Design` (for example
  `Design!E23` fmethod = A). `Settings!C11:C123` is the macro store of saved settings and
  differs (fmethod T, cjlen 24 000, CustomA 2863.43); it is not live and was not used.
* `Settings!N35` holds `#VALUE!` from the missing `showaxle` drawing function (presentation).
* `Design!M60` stores `y`; Excel compares text case-insensitively.
* The Custom tab is calculated but is not in the workbook print list (`Settings!O12`).
* Digitised chart data retained in the workbook (`Graphs 1`, `Graphs 2`, `Graphs 3`) have no
  source scans. See TECHNICAL-README concern C6.

## Tedds material consulted

* `C:/CODING/Tedds/_TEDDS_MDs/calculations/General/Concrete industrial ground floors-x-x-x.md`
  and `system-sets/Developer/Concrete industrial ground floor slab design-TR34.md` (UK TR34;
  code-independent theory only).
* `C:/CODING/Tedds/_TEDDS_MDs/calculations/GB/Concrete industrial ground floors-TR34-si-engb.md`
  (radius of relative stiffness, `lambda`, Meyerhof equations, load location rule).
* `C:/CODING/Tedds/_TEDDS_MDs/calculations/AU/AU RC slab design.md` (AS 3600-2018 Cl 9.3.3
  punching and Cl 9.4.3 shrinkage citations).
* `calculations/AU/AuRoad.md`, `AusFound.md`, `AUPad.md`: not relevant.

## Outstanding

There is no worked example independent of Structural Toolkit, and no independent
engineering review. Agreement with this baseline shows transcription fidelity only.
