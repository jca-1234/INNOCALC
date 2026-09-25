# Examples

## `worked-example.json`

This is the input document stored in Structural Toolkit `Pavements_Industrial_507.xls`,
sheets `Design`, `Custom`, `Uniform` and `Reinft`, transcribed field for field, with the
optional Custom tab enabled. The slab is 150 mm thick, `f'c = 32 MPa`, on a subgrade of
`K = 40 kPa/mm`, at an internal position. It carries a standard Dexian rack with three
1000 kg pallet levels and a ground pallet, a 3.5 t single-axle forklift and a 10 kPa floor
load.

| Quantity | Value |
| --- | --- |
| `f'ct.f` (AS 3600 method) / `l` | 3.394 MPa / 681.7 mm |
| Rack post bearing / punching | 0.233 / 0.253 |
| Rack post total stress | 4.106 MPa against 3.394 MPa: **1.21 FAIL** |
| Wheel factored stress | 2.367 MPa: 0.697 |
| Uniform load `q / W`; Hetenyi actual / critical aisle | 0.181; 0.187 / 0.190 |
| Custom point load stress | 4.741 MPa: **1.40 FAIL** |
| Abrasion grade | 0.781 (medium or heavy pneumatic-tyred traffic) |
| Shrinkage reinforcement (AS 3600 method) | 262.5 mm2/m, SL92 top |
| Outcome | **FAIL**, governed by the custom load (1.40) and the rack post stress (1.21) |

The workbook reports the same failures: `Racking!I69` "No Good (1.21)" and `Custom!I67`
"No Good (1.40)". The Hetenyi checks now also count towards the governing utilisation, but
they pass for this example.
