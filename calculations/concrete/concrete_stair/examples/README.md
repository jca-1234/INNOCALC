# Examples

## `worked-example.json`

The input document stored in Structural Toolkit `Concrete_Stair_506.xls`
(CONCRETE STAIRS V5.06), sheet `Design`: a 5000 mm interior span, 150 mm throat,
190 x 250 steps, `f'c = 100 MPa`, N10 at 100 centres, 4 kPa floor live load.

```powershell
python -m tooling dev concrete-stair calculations/concrete/concrete_stair/examples/worked-example.json --html artifacts/concrete-stair/worked-example.html
```

### Expected outcome

| Quantity | Value |
| --- | --- |
| `ath` | 225.64 mm |
| `f` | 1.256025 |
| `w*` | 14.502 kPa |
| `M*` | 45.319 kNm/m |
| `Ast` | 785.4 mm2/m, `Ast.min` 432 mm2/m |
| `kuo` / `phi` | 0.06233 / 0.85 |
| `phiMuo` | 40.788 kNm/m |
| `Ec` | 42 327 MPa |
| `ku` / `NA` | 0.21703 / 27.13 mm |
| `th.min` | 170.16 mm against `ath` 225.64 mm |
| `M* / phiMuo` | **1.11 FAIL** |

### The example is a failed design and exercises a warning branch

`Settings!O29` caches `1.11108960735` and `Design!I9` reads `No Good (1.11)`:
bending governs.

`Design!E52` simultaneously displays
`Warning - Compression steel in tension, Asc ignored for kcs`. The compression
steel, 100 mm2/m at `dc = 40 mm`, sits inside the cracked tension zone
(`NA - db/2 = 22.1 mm < 40 mm`), so `kcs` becomes `2.0` rather than the
unfiltered `Settings!O24` value of `1.84721125463`. The module reproduces this.

Note that the workbook's `Settings` reset block holds different values from the
`Design` sheet (for example `f'c` 32 against 100). The cached `Design` values are
the ones used here.
