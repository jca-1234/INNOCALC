# Examples

## `worked-example.json`

This is the input document stored in Structural Toolkit `Concrete_NonFlexural_504.xls`,
sheet `Design` (the `example73` macro followed by `FindAngle`), transcribed field for field.
It models a 3 500 mm x 3 660 mm transfer panel, 600 mm thick, with `f'c = 50 MPa`. The strut
carries `C* = 5 424 kN` and the tie `T* = 5 131 kN`, with `a = 3 500` and `z = 3 100` mm
entered manually. The bursting bars are N19.87 at 208 mm vertically and N15.95 at 225 mm
horizontally, 2 layers each; the tie is 16 N32 per layer in 2 layers. The optional nodal face
check is off, as in the workbook.

| Quantity | Value |
| --- | --- |
| `theta` | 41.53 deg (= `atan(3100/3500)`) |
| `dc.max` / `phiC` | 572 mm / 5 424 kN (1.00 by construction) |
| `Lrg` against `Lr` | 530 mm against 600 mm (0.883) |
| `Tb*` / `phiTb` | 1 085 / 3 393 kN (0.320) |
| `Tb.s` / `Tbs` | 1 695 / 1 964 kN (0.863) |
| `Tb.cr` / `Tbsc` | 4 387 / 3 393 kN (**1.293**) |
| `T*` / `phiT` | 5 131 / 10 938 kN (0.469) |
| Outcome | **FAIL**: governed by the bursting reinforcement at cracking, 1.293 |

The workbook shows the same failure (`Design!I13`, "No Good (1.29)"). The required bar
centres are 181 mm vertically and 159 mm horizontally; see TECHNICAL-README concern C4.
With `checks.nodeFaces = true` the face utilisations are 0.675 (strut), 0.427 (bearing)
and 0.853 (tie, `u = dc cos(theta) = 428 mm`).
