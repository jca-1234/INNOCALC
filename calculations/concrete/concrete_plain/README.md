# Plain Concrete Design

| | |
| --- | --- |
| Module ID | `concrete-plain` |
| Package | `ic_concrete_plain` |
| Entry point | `ic_concrete_plain.headless` |
| Filing folder | `04 - CONCRETE PLAIN` |
| Category | `Concrete` |
| Standard | AS 3600:2018 incl. Amendments 1 and 2, Section 20 |
| Version | `v0.0.1` |
| Status | `planned`, `enabled = false` |
| Maintainer | Responsible engineer (unassigned) |

> **Not approved for design.** Transcription of the retained Structural Toolkit
> workbook `Concrete_Plain_502.xls` (PLAIN CONCRETE V5.02). Agreement with that
> workbook establishes transcription fidelity, not engineering correctness.

## Scope

Section 20 strength design of a plain (unreinforced) concrete pad footing and of
an unreinforced pedestal.

| Utilisation key | Check | Reference |
| --- | --- | --- |
| `bending` | `M* / phiMuo`, `phiMuo = phi f'ct.f b D^2 / 6` | Cl 20.4.2 |
| `oneWayShear` | `V* / phiVu`, `phiVu = phi 0.15 b D f'c^(1/3)` | Eq 20.4.3(1) |
| `punchingShear` | `V* / phiVum` with the moment reduction | Cl 20.4.3(b), Eq 20.4.3(2) |
| `pedestalCompression` | `sigma.tc / (phi 0.4 f'c)` | Cl 20.3 |
| `pedestalTension` | `abs(sigma.tt) / (phi 0.45 sqrt(f'c))` | Cl 20.3 |
| `minimumDepth` | `200 / Dt` | Cl 20.4.1 |

`phi = 0.6` throughout (Table 2.2.2(g)) and the design depth is `D = Dt - 50`.

### Excluded

Bearing pressure, sliding, overturning, settlement and every other geotechnical
check; serviceability, shrinkage, temperature, durability, fire and fatigue. The
pedestal height is not an input, so only the Cl 20.1(a) maximum permitted height
`3 min(Lpx, Wpy)` is reported.

### An assumption you must confirm

The source workbook prints the bending and one-way shear **capacities** with no
on-sheet comparison; only the two pedestal stress checks have printed ratios. This
module compares those capacities against the same `M*` and `V*` that the workbook
uses for the Eq 20.4.3(2) punching interaction. Confirm those are the right
demands for all three footing checks before relying on the result. This is listed
as an outstanding review item.

## Units and conventions

Working units are **N, mm, MPa, N.mm**. The form takes forces in kN and moments
in kNm, converted once in `engine.compute`.

`P*` is positive in compression. `Mx*` and `My*` may be either sign; the Cl 20.3
stress equations use their magnitudes, as the workbook does. `M*` and `V*` for the
footing must be non-negative magnitudes.

## Differences from the source workbook

| Workbook behaviour | This module | Why |
| --- | --- | --- |
| `Design!E38` blank/zero manual perimeter means "use the calculated one" | Explicit `uMode` selector plus `um` | Blank and zero are not distinguishable in the suite form |
| `Design!E48` stores lowercase `w`, matched case-insensitively by Excel | Selector values folded to upper case | Reproduces Excel text comparison exactly |
| `Settings!P31` `cast` against-soil switch | Not offered | Retired at v5.02; AS 3600:2018 makes the 50 mm allowance mandatory |
| Capacities printed without ratios | Utilisations formed, and the assumption disclosed | The manager needs a governing utilisation |
| `Dt < 200` shown as an on-sheet error message | Reported as the `minimumDepth` utilisation | Keeps the numbers visible while still forcing `FAIL` |

## Commands

```powershell
Set-Location C:\CODING\INNOCALC
$Python = Join-Path $PWD '.venv\Scripts\python.exe'
& $Python -m tooling check concrete-plain --validate
& $Python -m tooling dev concrete-plain calculations/concrete/concrete_plain/examples/worked-example.json --html artifacts/concrete-plain/worked-example.html
$env:PYTHONPATH = "C:\CODING\INNOCALC\calculations\concrete\concrete_plain\src;C:\CODING\INNOCALC"
& $Python -m unittest discover -s calculations\concrete\concrete_plain\tests -v
```

## Evidence

`validate()` runs a 36-case internal consistency sweep and replays the retained
workbook example, comparing **32 published values**. `tests/test_engine.py`
contains 38 further tests; with the release gate the suite is 40 tests.

The retained example is a **failed design** — the workbook itself prints
`No Good (1.04)` for pedestal tension — and the module reproduces both printed
ratios, `0.06` and `1.04`.

## Outstanding release gates

1. Independent engineering review against AS 3600:2018 Section 20.
2. A decision on the bending / one-way shear demand assumption described above.
3. A worked example from a source independent of Structural Toolkit.
4. A named responsible maintainer.
5. Manager integration testing and PDF acceptance. No PDF has been inspected.
