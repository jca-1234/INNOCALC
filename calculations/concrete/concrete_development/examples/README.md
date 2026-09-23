# Examples

## `worked-example.json`

The input document stored in Structural Toolkit `Concrete_Development_506.xls`
(REINFORCEMENT DEVELOPMENT V5.06), sheets `Development` and `Cogs`: a 12 mm
deformed bar, `f'c = 40 MPa`, `fsy = 500 MPa`, 50 mm cover, 200 mm clear
distance, narrow element, helical fitments, with the hook and cog block enabled
at a 20 mm bar.

```powershell
python -m tooling dev concrete-development calculations/concrete/concrete_development/examples/worked-example.json --html artifacts/concrete-development/worked-example.html
```

### Expected outcome, single bar

| Quantity | Value |
| --- | --- |
| `k1`, `k2`, `k3`, `cd` | 1.0, 1.2, 0.7, 50 mm |
| `Lsy.tb` first term / lower limit | 276.70 mm / 348 mm |
| `Lsy.t` | 348 mm |
| `Lsy.tp` | 522 mm |
| `Lsy.t.lap` | 348 mm |
| `Lsy.cb` first term / lower limit | 208.71 mm / 261 mm |
| `Lsy.c` | 261 mm |
| `Lsy.c.lap` | 384 mm, with `rh = 0.8` |
| 180 degree hook | 268.496 mm |
| 90 degree cog height at `8 db` | 321.372 mm |

### Expected outcome, bar size table

The workbook's published table values are reproduced exactly:

| Result | 12 mm | 20 mm | 32 mm |
| --- | --- | --- | --- |
| `Lsy.tb` | 350 | 580 | 1160 |
| `Lsy.cb` | 270 | 440 | 700 |

and the plain, lap and compression lap rows at 12 mm read 530, 350, 540 and
390 mm.

### The two chains differ, on purpose

The single bar plain tension length is **522 mm** while the 12 mm table row reads
**530 mm**. The table rounds up at every step; the single bar chain carries full
precision. Both are the workbook's own behaviour and both are asserted.
