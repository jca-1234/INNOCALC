# Reinforcement Rate

| | |
| --- | --- |
| Module ID | `concrete-reinforcement-rate` |
| Package | `ic_concrete_reinforcement_rate` |
| Entry point | `ic_concrete_reinforcement_rate.headless` |
| Filing folder | `08 - REINFORCEMENT RATE` |
| Category | `Concrete` |
| Version | `v0.0.1` |
| Status | `planned`, `enabled = false` |
| Source workbook | `Concrete_Rate_500.xls` (Structural Toolkit REINFORCEMENT RATE V5.00) |

> **This module performs no design check.** It reports the weight of
> reinforcement per cubic metre of concrete, returns `util = {}` and
> `worstUtil = 0.0`, and its summary headline says so. Never read it as
> structural adequacy.

## What it reports

| Quantity | Expression | Reference |
| --- | --- | --- |
| Cross sectional area | `rb rd / 10^6` | Rate!G11 |
| Concrete volume | `A L / 1000` | Rate!G12 |
| Hook length | tabulated by ligature diameter, 8 to 20 mm | Rate!G14 |
| Number of transverse ligatures | `roundup[(rb - 2 cover - 12) / min(600, rd)] - 1` | Cl 8.3.2.2 |
| One ligature length | `2(rb - 2c - 10) + 2(rd - 2c - 10) + 2 hook` | Rate!G16 |
| Transverse set length | `ties x (rd - cover - 10 + 2 hook)` | Rate!G17 |
| Row weight | `rho pi (db/1000)^2 / 4 x total length` | Rate!I24 |
| Rate | total weight / concrete volume | Rate!C18 |

### Exclusions that matter

**Laps and ligature cogs are excluded**, as they are in the source workbook, so
the rate is not a complete estimating quantity. Wastage, chairs, spacers, tie
wire, couplers, starter bars and any bar leaving the member are also excluded.
This is printed on the sheet.

## The schedule is entered as validated text

The source workbook provides 21 schedule rows. The suite form has **no
repeatable table control**, so the schedule is a `textarea` with one row per
line:

```
# type, number or centres, bar size, length (mm), description
B, 200, 12, 1000, Bottom bars main direction
L, 300, 10, 6000, Ligatures
T, 400, 12, 6000, Transverse ligature sets
```

* `B` bar, `L` ligature, `T` transverse ligature set. Case-insensitive.
* A number of **100 or more is read as centres in millimetres**; a smaller number
  is read as a **count**. This is the workbook's own rule, and the interpretation
  actually applied is printed against every row on the calculation sheet so it can
  be audited.
* Blank lines and lines beginning with `#` are ignored. Descriptions may contain
  commas. Malformed lines raise `ValueError` naming the line number.
* Maximum 21 rows, matching the source.

**A repeatable table field type is the missing platform capability here.** If one
is added, this input should move to it.

## Differences from the source workbook

| Workbook behaviour | This module | Why |
| --- | --- | --- |
| 21 fixed schedule rows on the sheet | One validated text block | No repeatable table control exists |
| `onewayslab`, `twowayslab` and `band` VBA template macros | Not provided | They copy Settings ranges whose contents were not captured in the review export |
| Rows 48 to 54, a superseded template with density hard coded to 7850 and a reference to an undefined name | Not transcribed | Dead code |
| A nested `IF` in the comment string that can never be reached | The reachable behaviour only | The inner branch is unreachable in the source |

## Commands

```powershell
Set-Location C:\CODING\INNOCALC
$Python = Join-Path $PWD '.venv\Scripts\python.exe'
& $Python -m tooling check concrete-reinforcement-rate --validate
& $Python -m tooling dev concrete-reinforcement-rate calculations/concrete/concrete_reinforcement_rate/examples/worked-example.json --html artifacts/concrete-reinforcement-rate/worked-example.html
$env:PYTHONPATH = "C:\CODING\INNOCALC\calculations\concrete\concrete_reinforcement_rate\src;C:\CODING\INNOCALC"
& $Python -m unittest discover -s calculations\concrete\concrete_reinforcement_rate\tests -v
```

## Evidence

`validate()` runs a 24-case sweep across three members, two densities and four
schedules, and replays the retained baseline, comparing **23 values**.
`tests/test_engine.py` adds 36 further tests.

**The published evidence is limited.** The workbook was saved with an *empty*
schedule, so `Rate!C17` and `Rate!C18` both cache zero. Only the member geometry
chain (`G11`, `G12`, `G14`, `G15`, `G16`, `G17`) has genuine cached evidence. The
schedule row arithmetic is asserted by cases marked `derived` in the baseline:
their inputs were chosen here, not taken from the workbook.

## Outstanding release gates

1. **Schedule row arithmetic needs independent evidence.** Recalculate the source
   workbook with a populated schedule, or hand-check the row rules.
2. A decision on whether the three template macros are needed; if so, the Settings
   template ranges must be re-extracted.
3. Independent engineering review of the transcription.
4. A named responsible maintainer.
5. Manager integration testing and PDF acceptance. No PDF has been inspected.
