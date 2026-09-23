# Examples

## `worked-example.json`

The member geometry stored in Structural Toolkit `Concrete_Rate_500.xls`
(REINFORCEMENT RATE V5.00), sheet `Rate` — a 1000 x 1000 x 150 mm slab panel with
30 mm cover and 8 mm ligatures — with a **three row schedule added here**.

```powershell
python -m tooling dev concrete-reinforcement-rate calculations/concrete/concrete_reinforcement_rate/examples/worked-example.json --html artifacts/concrete-reinforcement-rate/worked-example.html
```

### Expected outcome

| Quantity | Value | Evidence |
| --- | --- | --- |
| Cross sectional area | 0.15 m2 | `Rate!G11` cached |
| Concrete volume | 0.15 m3 | `Rate!G12` cached |
| Hook length | 150 mm | `Rate!G14` cached |
| Transverse ligatures | 6 | `Rate!G15` cached |
| One ligature length | 2.32 m | `Rate!G16` cached |
| Transverse set length | 2.46 m | `Rate!G17` cached |
| Reinforcement rate | derived from the added schedule | not in the workbook |

### The workbook's own schedule is empty

The saved workbook has **no schedule rows**, so `Rate!C17` (total weight) and
`Rate!C18` (rate) both cache zero. The schedule in this example was written here
to exercise the row rules; it is not workbook evidence, and the baseline marks
the corresponding cases `derived`.

There is **no utilisation**. The summary reads
`... kg/m3 from ... kg of steel; no design check performed`.
