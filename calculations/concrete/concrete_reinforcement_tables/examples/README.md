# Examples

## `worked-example.json`

The reference tables with N16 selected at 4 bars and 200 mm centres, and the
RL1218 fabric designation.

```powershell
python -m tooling dev concrete-reinforcement-tables calculations/concrete/concrete_reinforcement_tables/examples/worked-example.json --html artifacts/concrete-reinforcement-tables/worked-example.html
```

### Expected outcome

| Quantity | Value |
| --- | --- |
| Area of one N16 | 201.062 mm2 |
| 4 x N16 | 804.248 mm2, tabulated 800 mm2 |
| N16 at 200 centres | 1005.310 mm2/m, tabulated 1000 mm2/m |
| RL1218 longitudinal | 1112.202 mm2/m |
| RL1218 cross | 226.823 mm2/m |

### Published corners of the tables

The source workbook's cached values are reproduced exactly:

| Table | Row | Values |
| --- | --- | --- |
| Number of bars | 1 bar | 110, 200, 310, 450, 610, 800 |
| Number of bars | 30 bars | 3390, 6030, 9420, 13570, 18470, 24120 |
| Bar centres | 60 mm | 1880 (12), 3350 (16), 20940 (40) |
| Bar centres | 1000 mm | 110 (12), 200 (16), 1250 (40) |

There is **no utilisation**. The summary reads
`N16: 4 bars = 804 mm2, at 200 centres = 1005 mm2/m; no design check performed`.
