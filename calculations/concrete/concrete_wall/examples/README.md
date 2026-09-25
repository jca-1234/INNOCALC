# Examples

## `worked-example.json`

This is the input document stored in Structural Toolkit `Concrete_Wall_511.xls`, sheets
`Design` and `Shear`, transcribed field for field. The wall is 200 mm thick, 3000 mm high
and 5000 mm long, with `f'c = 50 MPa`. It is restrained against rotation and supported
on four sides, with the stored `k = 0.74`. It has one central layer of N12-200 each way
and 64 mm cover. It carries `Ndl = 600 kN/m` at `e = 25 mm` and an in-plane shear of
40 kN (`H = 6000 mm`). The fire group is on, with the workbook's fire settings and a
required FRL of 240 min. `braced`, `kMode` and `frlRequired` have no workbook cell.

| Quantity | Value |
| --- | --- |
| `N*` | 810 kN/m (1.35 G) |
| `Hwe`, `Hwe/tw` | 2220 mm, 11.1 |
| `phiNu` | 600 kN/m (`3 tw`, one layer) |
| `phiVu` | 2407 kN |
| FRL | 240 min (adequacy deemed equal to insulation) |
| Outcome | **FAIL**: `N* / phiNu = 1.35`; single-layer stress `4.05 / 3 = 1.35` |

The workbook also reports "No Good (1.35)" for the axial check (`Design!I9`) and prints
"Error - Max. stress > 3MPa" (`Design!D39`). The single-layer error now counts towards
the governing utilisation.

The rendered sheet is `artifacts/concrete-wall/worked-example.html`.
