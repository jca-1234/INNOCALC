# Examples

## `worked-example.json`

This is the input document stored in Structural Toolkit `Concrete_TwoWaySlab_502.xls`,
sheet `Analysis`, transcribed field for field. The panel is 20 000 mm x 4 000 mm,
250 mm thick, `f'c = 120 MPa`, with all edges continuous and Class L reinforcement. It
carries 1 kPa superimposed dead load and 9 kPa live load.

| Quantity | Value |
| --- | --- |
| `Fd` | 22.2 kPa |
| `Mx*` / `My*` | 14.92 / 7.10 kNm/m |
| Negative `Mx*` / `My*` at continuous edges | 29.84 / 19.11 kNm/m |
| `d.min` / `d.min.inc` | 98.7 / 108.4 mm, against `ds = 209` mm |
| Outcome | **FAIL**: `Ast.min = 746.9 > Ast = 227 mm2/m` (3.29), and `wll > wdl` (1.24) |

The workbook shows no failure for this example. It never compares `Ast.min` with `Ast`,
and it prints the live-load error as a note. See TECHNICAL-README concerns C2 and C3.
