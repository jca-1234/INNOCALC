# Examples

## `worked-example.json`

This is the input state saved in Structural Toolkit `Concrete_Member_513.xls` (sheets
`Design`, `Detailed`, `Shear`, `Defl`, `Creep&Shrink` and `BeamDefl`), transcribed field for
field. The member is a 9 m simply supported rectangular beam, 600 deep x 500 wide, with
`f'c = 32` MPa and 30 mm cover. It has 4 N16 bottom bars and N12 fitments at 150 mm centres
(2 legs). The top bars are N12 at 300 mm nominal centres, which gives one bar across the
500 mm width (`Design!B8` reports `N12-500 cts top`).

The bending action is `M* = -30` kNm, with `Ms* = -19.5` and `Ms1* = -22.5` kNm. The shear
sheet uses its own actions: `V* = 9` kN, `M* = 23` kNm and `T* = 0`. The crack width,
calculated deflection and slenderness groups are enabled.

| Quantity | Value |
| --- | --- |
| `kuo`, `phi Muo` (negative) | 0.009, 26.43 kNm with `Ast = 113` mm2 |
| `Ast.min` (Cl 8.1.6.1, deemed, `alpha.b = 0.20`) | 442.7 mm2 |
| `phi Vuc`, `ks phi Vuc` (general method, `theta.v = 30.2 deg`) | 333.7, 178.0 kN |
| Fitment requirement | None required, Cl 8.2.1.6(a) |
| Deemed deflection `d.min` / `d.min.inc` (`BeamDefl`) | 717.6 / 866.8 mm, against `d = 550` mm |
| Calculated crack width (Cl 8.6.2.3) | 0.698 mm against 0.3 mm (the workbook gives 0.385 mm; departure D3) |
| Outcome | **FAIL**, `worstUtil = 3.914` (minimum strength steel) |

| Utilisation | Value | Utilisation | Value |
| --- | --- | --- | --- |
| `flexure` | 1.135 | `webCrushing` | 0.008 |
| `ductility` | 0.025 | `longitudinalTension` | 0.171 |
| `minimumSteel` | 3.914 | `deflectionTotal` | 1.305 |
| `barSpacing` | 1.667 | `deflectionIncremental` | 1.576 |
| `crackStress` | 1.305 | `liveLoadLimit` | 2.667 |
| `crackStressYield` | 0.923 | `crackWidth` | 2.326 |
| `shear` | 0.051 | `deflectionTotalCalc` | 0.306 |
| `shearDetailing` | 0.000 | `deflectionIncrementalCalc` | 0.460 |
| `torsion` | 0.000 | `slenderness` | 0.300 |

The workbook reports the flexural failure (`Design!I9`, `No Good (1.14)`). The minimum
steel (`Design!B11`, `Ast.min = 443mm² > Ast = 113mm²`), the bar spacing (`Design!I8`,
`Top bar cts N.G.`), the crack stress (`Design!B10`, `fscr = 320MPa > Fscr = 245MPa`) and the
live-load limit appear only as text, with no pass/fail status. The saved state also selects tested drying shrinkage with a blank
`eps.csd.b*`, so only autogenous shrinkage is included; the module reproduces this and
warns. See `reference/README.md` for the other saved-state notes.
