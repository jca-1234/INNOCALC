# Examples

## `worked-example.json`

The input document stored in Structural Toolkit `Concrete_Plain_502.xls`
(PLAIN CONCRETE V5.02), sheet `Design`.

**This example is a failed design and is retained deliberately.** The workbook
prints `No Good (1.04)` at `Design!G88`: the total pedestal tensile stress of
`-3.0625 MPa` exceeds the `2.9577 MPa` Cl 20.3 limit. The module reproduces both
printed ratios.

| Quantity | Value |
| --- | --- |
| `D` | 200 mm |
| `phiMuo` | 26.291 kNm |
| `phiVu` (one-way) | 88.784 kN |
| `phiVu` (punching) | 304.972 kN |
| `phiVum` | 177.900 kN |
| `sigma.tc` / `sigma.c.max` | 1.8125 / 28.8 MPa = 0.06 |
| `abs(sigma.tt)` / `sigma.t.max` | 3.0625 / 2.9577 MPa = **1.04 FAIL** |

The example also exercises two documented oddities of the saved workbook: `P*` is
stored as `-250 kN` (tension) although the sheet labels it positive in
compression, and `Dir` is stored as lowercase `w`, which Excel matches
case-insensitively.

```powershell
python -m tooling dev concrete-plain calculations/concrete/concrete_plain/examples/worked-example.json --html artifacts/concrete-plain/worked-example.html
```
