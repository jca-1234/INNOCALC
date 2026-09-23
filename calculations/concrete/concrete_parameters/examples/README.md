# Examples

## `worked-example.json`

An N32 grade with both optional groups enabled: a 300 x 600 rectangular beam
section with `ds = 550 mm` and `fsy = 500 MPa`, and `Z = 18 x 10^6 mm3`.

```powershell
python -m tooling dev concrete-parameters calculations/concrete/concrete_parameters/examples/worked-example.json --html artifacts/concrete-parameters/worked-example.html
```

### Expected outcome

| Quantity | Value |
| --- | --- |
| `alpha2` | 0.802 |
| `gamma` | 0.89 |
| `alpha1` | 0.85 (bounded from 0.904) |
| `f'ct.f` | 3.394 MPa |
| `fcmi` (Table 3.1.2) | 35 MPa |
| `Ec` | approximately 29 900 MPa |
| `alpha.b` | 0.20 |

There is **no utilisation**. The summary reads
`Parameters for f'c = 32 MPa; no design check performed`.

The source workbook itself was saved with `f'c = 120 MPa`; the grade-by-grade
tables it prints are reproduced in the retained baseline rather than in this
example.
