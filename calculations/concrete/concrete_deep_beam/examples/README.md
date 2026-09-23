# Examples

## `worked-example.json`

The input document stored in Structural Toolkit `Concrete_DeepBeam_502.xls`
(DEEP BEAMS V5.02), sheet `Design`: a 3000 mm cantilever deep beam, 4000 mm deep,
300 mm thick, `f'c = 100 MPa`, N16 tie bars, 10 mm mesh, WRHF crack control class.

```powershell
python -m tooling dev concrete-deep-beam calculations/concrete/concrete_deep_beam/examples/worked-example.json --html artifacts/concrete-deep-beam/worked-example.html
```

### Expected outcome

| Quantity | Value |
| --- | --- |
| `L/D` | 0.75 against a cantilever limit of 1.0 |
| `z` | 2700 mm |
| `fsy.d` | 365 MPa (serviceability governs) |
| `Ast+` | 2029.4 mm2, 10.09 N16 |
| `Ast-` | 1014.7 mm2, 5.05 N16 |
| `phiVu.max` | 6000 kN (span form governs) |
| `phiRe` / `phiRi` | 16 000 kN / 26 400 kN |
| Mesh / bar centres | 104.7 mm / 130.9 mm |
| `V* / phiVu.max` | 0.15 |
| `c / (L/5)` | **1.50 FAIL** |

### The example fails a rule the workbook reports as OK

`Design!D23` reads `mm Error - c > L/5` because `c = 900 mm` exceeds
`L/5 = 600 mm`, yet the workbook's summary ratio `Settings!O21` looks only at
`V*/phiVu` and prints `OK (0.15)`.

This module includes the support width limit in `util`, so the same inputs return
**FAIL** governed by that rule at 1.50. The diagonal compression ratio still
reproduces the workbook's 0.15 exactly.

Because the span type is a cantilever, the external support check is reported as
`not applicable to a cantilever`, matching `Design!I11`.
