# Reference Evidence

## Source

| Item | Value |
| --- | --- |
| Document | `Concrete_Wall_511.xls`, Structural Toolkit module **CONCRETE WALLS V5.11** (20 February 2024, "Added further functionally to effective height factor k calculations") |
| Description | Design of walls (AS3600-2018 Section 11) |
| Standards cited | AS/NZS 1170.0:2002 (Amdt 1 to 5), AS/NZS 1170.1:2002 (Amdt 1 and 2), AS 3600:2018 incl. Amdt 1 and 2; Foster, Kilpatrick and Warner, *Reinforced Concrete Basics* 2E (Pearson, 2010) |
| Source SHA-256 | `ca07fc319ae8b8550da0daa852d0d4f07b18d1b22e26fc3edcf101f8682e3b48` |
| Decoded XLS SHA-256 | `03f022f4c20e014d911ceeb8ce88147471cd2ce91be12aff144c0b9482352fa9` |
| Static review | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_Wall_511.md` |
| VBA extract | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_Wall_511.vba.txt` |
| Complete extract | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_Wall_511.audit.json` |
| Cell listing used | `artifacts/workbook-extracts/Concrete_Wall_511.cells.txt` |
| Extracted | 24 September 2026 |

The originals are held in the workbook review workspace and are not copied here.

## Extraction procedure

The expected values were taken cell by cell from the cached values in the cell listing.
They come from sheet `Design` (rows 13 to 118), sheet `Shear` (E13 to E53) and sheet
`Settings` (O48 to O78, the fire tables U35 to AA67, and X122 to X133). Excel was not
re-run. The VBA routine `CalcExposure` was transcribed from the extracted source. The
routine `MeshName` and the `RCB58` example macro are presentation or input helpers and
were not transcribed.

## Benchmark sources (Tedds)

| Calculation | Location | Use |
| --- | --- | --- |
| RC wall design (AS3600) 1.0.10, AS 3600-2018 Amdt 1 and 2 | `C:/CODING/Tedds/_TEDDS_MDs/calculations/AU/RC Wall Design (AS 3600-2001).md` and `system-sets/Developer/RC wall design-AS3600.md` | Minimum steel, crack control, cover, fire and bar restraint comparisons |
| Tilt-up wall panel design (AS3600) 1.0.10 | `C:/CODING/Tedds/_TEDDS_MDs/calculations/AU/Tilt up wall panel design-AS3600_2001-si-enau.md` and `system-sets/Developer/Tilt-up wall panel design-AS3600.md` | Slab-route limits; P-delta method (ACI 318), not adopted |
| RC Shear wall design, Basement wall design, Tilt up wall panel design (generic) | `C:/CODING/Tedds/_TEDDS_MDs/calculations/General/` | No AS 3600 content; not used |
| AS-NZS data tables | `C:/CODING/Tedds/_TEDDS_MDs/data-tables/AS-NZS/` | Only the superseded 1994 cover table relates to walls; not used |

## Saved-state notes

* `Design`, `Shear` and `Settings` agree with each other for the stored inputs. The
  saved user `k = 0.74` (`Design!D18`) rounds to the calculated `k = 0.7353`
  (`Settings!O78` is False).
* `Settings!B19:C153` ("Save Properties") stores another member (`f'c = 40`, `tw = 150`).
  The `ACI` and `Thermal` sheets hold their own example. None of these feed `Design`.
* `Design!E64` (`Nus = 0`) is excluded from the baseline; see TECHNICAL-README D1.
* The saved example FAILS: `N* = 810 > phiNu = 600 kN/m` and the single-layer stress
  4.05 MPa exceeds 3 MPa.

## Outstanding

There is no worked example independent of Structural Toolkit. Agreement with this baseline
shows transcription fidelity only. No independent engineering review has been recorded.
