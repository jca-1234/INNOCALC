# Concrete Strut-and-Tie Design

| | |
| --- | --- |
| Module ID | `concrete-strut-tie` |
| Package | `ic_concrete_strut_tie` |
| Distribution | `innocalc-concrete-strut-tie` |
| Entry point | `ic_concrete_strut_tie.headless` |
| Filing folder | `12 - CONCRETE STRUT AND TIE` |
| Category | `Concrete` |
| Standard | AS 3600:2018 incl. Amendments 1 and 2 (Section 7, Cl 12.6, Cl 13.1.2) |
| Version | `v0.0.1` |
| Status | `planned`, `enabled = false` |
| Maintainer | Responsible engineer (unassigned) |

> **Not approved for design.** This module transcribes the retained Structural Toolkit
> workbook `Concrete_NonFlexural_504.xls` (STRUT & TIE V5.04). It reproduces 149 saved
> workbook values to `1e-9`. That shows the transcription is faithful. It does not show
> the engineering is correct. See [TECHNICAL-README.md](TECHNICAL-README.md) for the
> technical review and the open concerns.

## Scope

The module checks one bottle-shaped concrete strut of a strut-and-tie model, its bursting
reinforcement, one tension tie with its development zone, the node stress limit and the
bearing under the support. The strut runs between a support node on the tie and a loaded
node, within a panel of horizontal length `Lstrut`, depth `D` and thickness `bc`. You supply
the member forces (`C*`, `Cserv`, `T*`, `Vr*`, `Vr.serv`) from your own model.

| Utilisation key | Check | Reference |
| --- | --- | --- |
| `strut` | Strut capacity, `C* / phiC`, `phiC = phi betas 0.9 f'c bc dc`. Exactly 1.0 when `dc = dc.max` | Cl 7.2.2, Cl 7.2.3 |
| `supportLength` | Support length needed by the strut, `Lrg / Lr`, `Lrg = dc.max sin(theta) + dz` | Fig 7.2.4(A) |
| `strutAngle` | Strut-to-tie angle not less than 30 degrees, `30 / theta` | Cl 7.1 (workbook citation) |
| `angleCompatibility` | Adopted `theta` equals `theta_az = atan(z / a)` within 0.001 degrees; `inf` if not | Fig 7.2.2 |
| `bottleLength` | Strut depth less than the strut length, `dc / Ls`, so that `lb > 0` | Eq 7.2.4(4) |
| `burstingStrength` | `Tb* / phiTb`, `Tb* = C* tan alpha*`, `tan alpha* >= 0.2` | Cl 7.2.4(b) |
| `burstingService` | `Tb.s / Tbs`, `Tb.s = Cserv tan alpha.s`, `tan alpha.s >= 0.5`, steel at `fsi` | Cl 7.2.4(a), Cl 12.7 |
| `burstingCracking` | `Tb.cr / Tbsc`, `Tb.cr = 0.7 bc lb f'ct` | Eq 7.2.4(1) |
| `burstingThreshold` | Replaces the three bursting keys when `Tbb* = 0.5 C* <= 0.5 Tb.cr` | Cl 7.2.4 (workbook rule) |
| `oneWayAngle` | Bars in one direction only: `40 / gamma` of the bars provided | Workbook rule `Design!C70` |
| `verticalLoadSteel` | Vertical steel for `Vr*`, `max(Asvr, Asvr.s) / Asi1` | Cl 7.2.4 |
| `tie` | `T* / phiT`, `phiT = phi fsy Ast` | Cl 7.3.2 |
| `node` | Entered nodal stress `sigma_o / (phi betan 0.9 f'c)` | Cl 7.4.2 |
| `bearing` | `B* / phiB`, `phiB = min(phi 1.8 f'c, phi 0.9 f'c sqrt(A2/A1)) A1` | Cl 12.6 |

The report also gives the Cl 13.1.2.2 development lengths of the horizontal and tie bars and
the required bursting bar spacings for strength, serviceability and cracking.

One optional check group follows the Tedds node approach:

| Group | Utilisation keys | Reference |
| --- | --- | --- |
| `nodeFaces` | `nodeStrutFace` = `C* / (bc dc)`, `nodeBearingFace` = `Cv* / (bc Lr)` and `nodeTieFace` = `T* / (bc u)`, each against `phi betan 0.9 f'c`. `u` defaults to the hydrostatic tie face `dc cos(theta)` | Cl 7.4.2 |

### Excluded

The module does not analyse the truss, find member forces or check equilibrium of the model.
It does not check other struts or ties, laps and bar detailing, node confinement, minimum wall
or web reinforcement, crack widths, fire or durability.

### Validity limits

* `20 <= f'c <= 120` MPa (Cl 1.1.2). Development lengths use `f'c <= 65` MPa (Cl 13.1.2.2).
* `C* > 0` and `Cserv <= C*`. Actions and `sigma_o` are zero or positive.
* `fsy` is 500 or 400 MPa. Bar sizes are zero or positive and less than 132 mm. Bundles are 1 to 4 bars.
* Manual `theta` lies between 0 and 90 degrees. The geometry must leave `a > 0` and `z > 0`.
* A manual `A2` must not be less than `A1`.

## Units and conventions

Forces are entered in kN and held in N. Lengths are in mm, stresses in MPa and angles in
degrees. `gamma1 = 90 - theta` is the angle between the vertical bars and the strut, and
`gamma2 = theta` the angle for the horizontal bars. Bar sets are counted over the bursting
length projections `lb.1 = lb sin(gamma1)` and `lb.2 = lb sin(gamma2)`. Modes replace the
workbook's "leave blank to use calculated" cells, because the manager form turns a blank
number into zero.

## Differences from the source workbook

| Workbook behaviour | This module | Why |
| --- | --- | --- |
| `FindAngle` runs `Range("angerror").GoalSeek` on `ang` | Closed form when `a` and `z` are both manual (`atan(z/a)`) or both calculated (`atan(D/Lstrut)`, an exact identity); otherwise a 0.05 degree scan from 90 degrees and bisection | Deterministic and bounded |
| Strut ratio `C*/phiC` prints `OK (1.00)` from `5424 / 5423.999999999999` | `strut = dc.max / dc`, exactly 1.0 when `dc = dc.max` | Algebraically equal; avoids a 1-ulp false failure |
| `Lrg > Lr`, `theta < 30`, `theta <> theta_az` and "more vertical reinf't required" are printed as errors (`E18`, `G33`, `G157`, `C70`) but the summary can still show OK | `supportLength`, `strutAngle`, `angleCompatibility` and `verticalLoadSteel` count towards `worstUtil` | A model outside its own rules must not report OK |
| `lb = MAX(0, Ls - dc)` silently becomes 0 | `bottleLength = dc / Ls`; `lb = 0` is reported as unattainable | No bottle can form |
| A bursting capacity of zero or less gives 999 or a negative ratio | `inf`, with an unattainable reason | Negative capacity is not a pass |
| `sqrt(f'c)` in `E110:F110` is not limited, although `K110` says 65 MPa | `f'c <= 65` MPa | Cl 13.1.2.2 |
| Slip-form input `sk` exists but is "< Not used" (`Settings!S83`) | `sk = Y` applies 1.3 to Lsy.t | Cl 13.1.2.2(c), as the workbook cites; confirm (TECHNICAL-README C8) |
| One-way reinforcement tests `OR(gamma1 < 40, gamma2 < 40)` | Tests the angle of the bars actually provided | The other angle is irrelevant |
| `phi` values in `E126`, `E201`, `E218` are editable | Fixed at 0.65, 0.85 and 0.6 | Table 2.2.4 and Table 2.2.2 |
| `Cserv > C*` prints an error; custom `fsi <= 0` becomes 0.001 | `ValueError` | Invalid input, not a design result |
| Manual `dz` is accepted without comment | Warning if `dz < 50% Lsy + cover` | Cl 7.3.3 intent |
| Node stress `sigma_o` must be entered (0 in the saved example) | Retained, plus the optional `nodeFaces` group | Adopted from Tedds (TECHNICAL-README §2.1) |
| "Auto Reinf't Spacing" button | Required spacings reported; bar spacing stays an input | The routine is not in the VBA extract |

## Commands

Run these from the suite root:

```powershell
$Python = Join-Path $PWD '.venv\Scripts\python.exe'
$env:PYTHONPATH = "$PWD;$PWD\calculations\concrete\concrete_strut_tie\src"
& $Python -B -m unittest discover -s calculations/concrete/concrete_strut_tie/tests -v
& $Python -m ic_concrete_strut_tie.dev --validate
& $Python -m ic_concrete_strut_tie.dev calculations/concrete/concrete_strut_tie/examples/worked-example.json --html artifacts/concrete-strut-tie/worked-example.html
```

## Evidence

| Artefact | Location |
| --- | --- |
| Technical review | `TECHNICAL-README.md` |
| Retained baseline | `src/ic_concrete_strut_tie/data/workbook-baseline.json` |
| Source provenance | `reference/README.md` |
| Worked example | `examples/worked-example.json` |
| Tests | `tests/test_engine.py`, `tests/test_release_gate.py` |

## Outstanding release gates

1. Confirm against the printed AS 3600:2018 Amdt 2 the clauses the workbook cites but this
   review could not verify: Cl 7.1 (30 degrees), Cl 7.2.4 reinforcement-required test,
   Eq 7.2.4(4), Cl 12.7 stress limits and the Cl 13.1.2.2(c) slip-form factor.
2. Obtain an independent engineering review and record it in `reference/README.md`.
3. Add a worked example from a source other than Structural Toolkit, for example
   Foster, Kilpatrick and Warner, *Reinforced Concrete Basics* (2021), which the workbook cites.
4. Name a maintainer, register the module in `suite.toml` and complete manager and PDF acceptance.
