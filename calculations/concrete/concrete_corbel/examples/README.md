# Examples

## `worked-example.json`

The input document stored in Structural Toolkit `Concrete_Corbel_506.xls`
(CORBEL V5.06), sheet `Design`, transcribed field for field. It is a 600 mm long
corbel, 300 mm overall depth, `f'c = 32 MPa`, six N12 top bars, a roughened
casting interface, carrying 60 kN dead and 60 kN live vertical action at 105 mm
eccentricity.

Render it from the suite root:

```powershell
python -m tooling dev concrete-corbel calculations/concrete/concrete_corbel/examples/worked-example.json --html artifacts/concrete-corbel/worked-example.html
```

### Expected outcome

| Quantity | Value |
| --- | --- |
| `V*` | 162.0 kN |
| `Nd*` | 32.4 kN |
| `phiB` | 14.976 MPa |
| `tau_u` | 3.3466 MPa |
| `phiVu` | 421.68 kN |
| `phiFt` | 288.40 kN |
| Governing utilisation | 0.601, bearing at the corbel node |

### Deliberate difference from the stored workbook values

The workbook was saved unconverged: `Design!L17` (the GoalSeek residual) holds
`-7.903 kN`, so the stored strut width `dc = 18.795 mm` is not the solution for
the stored inputs. This module solves the same residual and obtains
`dc = 17.967 mm`, which changes `x`, `Cf*`, `w` and `Ft*`. Reproduction of the
workbook's own strut chain **at its stored `dc`** is checked separately, in
`tests/test_engine.py` and in the retained baseline strut case.