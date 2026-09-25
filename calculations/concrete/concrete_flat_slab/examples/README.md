# Examples

## `worked-example.json`

This is the input document stored in Structural Toolkit `Concrete_FlatSlab_504.xls`, sheet
`Analysis`, transcribed field for field. The slab has 6 000 mm x 6 000 mm spans, is 250 mm
thick with drop panels, `f'c = 32 MPa`, 400 mm square columns, edge beams (type C) and
overhangs of 250 mm and 200 mm. It carries 6.25 kPa dead load and 5 kPa live load, with
`Ast = 1000 mm2/m` of 400 MPa steel for the interior span deflection check.

| Quantity | Value |
| --- | --- |
| `Fd` | 15.0 kPa (1.2G + 1.5Q) |
| `Mo`, interior strip, end / interior span | 361.4 / 354.7 kNm |
| Column strip, peak negative / positive | -63.2 / 30.1 kNm/m |
| Edge column strip, peak negative | -80.8 kNm/m |
| `M*v`, first / typical interior column | 45.0 / 42.6 kNm |
| `Ast.min` | 633 mm2/m against `Ast = 1000` (0.63) |
| `d.min` / `d.min.inc` with `Lef = 5850 mm` | 170.1 / 184.2 mm against `ds = 201` mm |
| Workbook basis, `Lo = 5720 mm` | 166.3 / 180.1 mm |
| Outcome | **OK**, governed by incremental deflection (0.916) |

The workbook reports "Slab thickness OK with drop" for this example; the module agrees,
with `d.min` 2.2 % higher because it uses `Lef` (TECHNICAL-README C4).
