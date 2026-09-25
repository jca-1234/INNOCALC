# Examples

## `worked-example.json`

This is the input document stored in Structural Toolkit `Concrete_Punching_506.xls`, sheet
`Design`, transcribed field for field. A 90 x 90 mm internal column supports a 100 mm slab
with `do = 67` mm and `f'c = 20` MPa. It carries `V* = 50` kN and `Mv* = 1` kNm, with N12
closed fitments at 100 mm in a 157 mm wide torsion strip.

Two inputs have no workbook cell: `nIntegrity = 21` bottom bars through the column (the
workbook asks for 20.2 N12) and `simplifiedMethod = N`.

| Quantity | Value |
| --- | --- |
| `u`, `a`, `betah` | 628 mm, 157 mm, 1.0 |
| `phiVuo`, Eq 9.3.3(1) | 44.78 kN |
| `phiVu`, Eq 9.3.4(1), no fitments | 38.97 kN |
| `phiVu.min`, Eq 9.3.4(2) | 42.83 kN |
| `phiVu`, Eq 9.3.4(4) = `phiVu.max`, Eq 9.3.4(5) | 102.54 kN |
| `M.min*`, Cl 6.10.4.5 | 2.39 kNm (not applied; warning) |
| Integrity `As.min` | 2 286 mm2 (20.2 N12) against 21 N12 = 2 375 mm2 |
| Outcome | **OK**: governing punching 0.488 on Eq 9.3.4(4); fitment spacing 100 / 100 = 1.00 and fitment width 157 / 157 = 1.00 are at their limits; integrity 0.962 |

The workbook prints No Good for the no-fitment and minimum-fitment rows (1.12, 1.28 and
1.17) beside OK (0.49) for the fitments provided, without saying which governs. It also
computes `M.min* = 2.39 kNm > Mv* = 1 kNm` without using it. See TECHNICAL-README C1 and C2.
