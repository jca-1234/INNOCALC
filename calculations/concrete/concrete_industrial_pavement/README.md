# Concrete Industrial Pavement Design

| | |
| --- | --- |
| Module ID | `concrete-industrial-pavement` |
| Package | `ic_concrete_industrial_pavement` |
| Distribution | `innocalc-concrete-industrial-pavement` |
| Entry point | `ic_concrete_industrial_pavement.headless` |
| Filing folder | `16 - INDUSTRIAL PAVEMENT` |
| Category | `Concrete` |
| Standard | As cited by the workbook: AS 3600:2018 incl. Amendments 1 and 2; C&CA Technical Report TR550 (J.W.E. Chandler, 1982); CCAA T48 *Industrial Floors and Pavements* (1999 and 2009); C&CA *Concrete Industrial Floor and Pavement Design* (1985); Austroads *Guide to Pavement Technology Part 2* (2010) |
| Version | `v0.0.1` |
| Status | `planned`, `enabled = false` |
| Maintainer | Responsible engineer (unassigned) |

> **Not approved for design.** This module transcribes the retained Structural Toolkit
> workbook `Pavements_Industrial_507.xls` (INDUSTRIAL FLOOR SLABS V5.07). It reproduces 415
> cached workbook values to `1e-9`. That shows the transcription is faithful. It does not show
> the engineering is correct. See [TECHNICAL-README.md](TECHNICAL-README.md) for the technical
> review and the open concerns.

## Scope

This module checks an unreinforced concrete industrial floor or pavement on grade. It uses the
Chandler (C&CA TR550) elastic method with the CCAA T48 material and repetition factors, and
AS 3600 for bearing and punching under a rack post. It reports:

| Utilisation key | Check | Reference |
| --- | --- | --- |
| `rackBearing` | Rack post bearing, `(1.5 RPL / Fa) / (phi 0.9 f'c)` | AS 3600 Cl 12.6 |
| `rackPunching` | Rack post punching shear, `V* / phiVuo`, internal, edge or corner perimeter | AS 3600 Cl 9.3.3 |
| `rackFlexure` | Rack post stress with adjacent posts plus the aisle UDL stress, `sigma_rt / f'ct.f` | Chandler; T48 Cl 3.3.6 |
| `wheelFlexure` | Forklift wheel stress, single or dual axle, `sigma_wf / f'ct.f` | Chandler; T48 Table 1.17 |
| `uniformVariable` | Uniform load, variable storage layout, `q / W` | C&CA Cl 5.6.3 |
| `uniformAisle` | Uniform load patterned at the actual aisle, `sigma_uf / f'ct.f` | Hetenyi |
| `uniformCritical` | Uniform load patterned at the critical aisle `2a`, `sigma_uf / f'ct.f` | Hetenyi |
| `abrasionGrade` | Minimum grade for abrasion and exposure, `25 / f'c` | T48 Tables 1.6 and 1.7 |

Two optional check groups are provided:

| Group | Utilisation key | Source |
| --- | --- | --- |
| `custom` | `customFlexure`: a point load at G with up to 11 user-placed adjacent loads, plus the aisle UDL | Workbook Custom tab |
| `location` | `positionApplicability`: the chosen internal or edge position must be at least `a + l` clear of edges or joints | Generic ground-floor rule, adopted from Tedds (see TECHNICAL-README §2.1) |

The module also reports the subgrade CBR and K conversions, the T48 nominal and bound
sub-base values, and the shrinkage reinforcement (AS 3600 unrestrained, T48 0.14 %, T48
Appendix F and Austroads subgrade drag) with a Grade 500 mesh selection. These are
requirements only; no provided reinforcement is checked.

### Excluded

Joint design (dowels, aggregate interlock, sawn joint spacing), curling and warping,
settlement, fatigue by Miner's rule and fibre reinforced concrete are not covered. The
workbook's hidden `Settings` switches for ARC Slabex steel fibre concrete and the ARC
adjacent-load tables are not transcribed, nor are its drawing macros.

### Validity limits

* `20 <= f'c <= 120` MPa; the C&CA flexural strength needs `25 <= f'c <= 50` MPa.
  Values outside these ranges raise `ValueError`.
* `0 <= mu < 0.5`; material and repetition factors are in `(0, 1]`.
* Wheels per axle are 2 or 4; four wheels need a wheel pair spacing greater than zero.
* Bound sub-base thickness is 0, 100, 125 or 150 mm. `fsy` is 500 or 400 MPa.
* Aisle widths outside 1500 to 4500 mm are clamped to the Chandler Fig 3 range, with a warning.

## Units and conventions

Lengths are in mm, stresses in MPa, K in kPa/mm and area loads in kPa. Rack and pallet
masses are in kg (converted at 10 N/kg, as in the workbook), post and custom loads in kN,
and axle loads in tonnes. The point under consideration is G for racks and custom loads and
B for wheels. X and Y are the two plan directions: T is tangential, R radial and C the
critical of both.

## Differences from the source workbook

| Workbook behaviour | This module | Why |
| --- | --- | --- |
| VBA `Moment` extrapolates the 450 and 570 mm curves for `570 < l < 675` mm | Interpolates between the 570 and 675 mm curves | The extrapolation is up to about 8 % low (TECHNICAL-README C1) |
| VBA `Moment` returns 0 for `l < 450` mm | Uses the 450 mm curve, with a warning | Zero aisle stress is unconservative (C2) |
| Design summary reports only `q / W`; the Hetenyi checks print OK or No Good on the Uniform tab only | Both Hetenyi checks count towards `worstUtil` | A printed check must govern (C3) |
| Wheels and Uniform tabs print "Accept" up to 1.025 | Pass only at `<= 1.0` | No basis for the tolerance band (C3) |
| Dual axle point G uses `Wcts - WheelPairCentres/2` for every wheel arrangement (`Wheels!C46`) | Uses `Wcts - WheelPairCentres` for 4 wheels, `Wcts` for 2 | Consistent with points C and H (C4) |
| `f'c < 25` MPa prints "Unsuitable" or "Error" but the sheets still report OK | `abrasionGrade` utilisation | A failed requirement must not report OK (C10) |
| "Error" text for C&CA outside 25 to 50 MPa, wheel count and negative custom distances | `ValueError` | Inputs outside the method |
| Invalid stresses print "No Good (99.00)" | Utilisation is `inf` (unattainable) | Suite convention |
| Adjacent custom loads default to the G load by cell formula | `customLoads` = `SAME` or `LIST` | The form cannot hold an overridable formula |
| Load position chosen with a warning only | Optional `location` check | Adopted from the generic Tedds rule |
| ARC Slabex, ARC tables, drawing macros | Not transcribed | Hidden Settings options and presentation |

## Commands

Run these from the suite root:

```powershell
$Python = Join-Path $PWD '.venv\Scripts\python.exe'
& $Python -m tooling check concrete-industrial-pavement --validate
& $Python -m tooling dev concrete-industrial-pavement calculations/concrete/concrete_industrial_pavement/examples/worked-example.json --html artifacts/concrete-industrial-pavement/worked-example.html
$env:PYTHONPATH = "$PWD;$PWD\calculations\concrete\concrete_industrial_pavement\src"
& $Python -m unittest discover -s calculations/concrete/concrete_industrial_pavement/tests -v
```

## Evidence

| Artefact | Location |
| --- | --- |
| Technical review | `TECHNICAL-README.md` |
| Retained baseline | `src/ic_concrete_industrial_pavement/data/workbook-baseline.json` |
| Source provenance | `reference/README.md` |
| Worked example | `examples/worked-example.json` |
| Tests | `tests/test_engine.py`, `tests/test_release_gate.py` |

## Outstanding release gates

1. Verify the Chandler stress formulae constants and the digitised Fig 2 and Fig 3 curve fits
   against TR550, and the flexural strength and factor tables against T48 (TECHNICAL-README
   C5 to C7).
2. Obtain an independent engineering review and record it in `reference/README.md`.
3. Add a worked example from a source other than Structural Toolkit, for example a T48 or
   TR550 design example.
4. Name a maintainer.
5. Complete manager integration and PDF acceptance.
