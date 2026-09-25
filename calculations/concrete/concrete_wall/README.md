# Concrete Wall Design

| | |
| --- | --- |
| Module ID | `concrete-wall` |
| Package | `ic_concrete_wall` |
| Distribution | `innocalc-concrete-wall` |
| Entry point | `ic_concrete_wall.headless` |
| Filing folder | `15 - CONCRETE WALL` |
| Category | `Concrete` |
| Standard | AS 3600:2018 incl. Amendments 1 and 2; AS/NZS 1170.0:2002 for combinations |
| Version | `v0.0.1` |
| Status | `planned`, not registered in `suite.toml` |
| Maintainer | Responsible engineer (unassigned) |

> **Not approved for design.** This module transcribes the retained Structural Toolkit
> workbook `Concrete_Wall_511.xls` (CONCRETE WALLS V5.11). It reproduces 115 saved
> workbook values to `1e-9`. That shows the transcription is faithful. It does not show
> the engineering is correct. See [TECHNICAL-README.md](TECHNICAL-README.md) for the
> technical review and the open concerns.

## Scope

This module designs a planar reinforced concrete wall per metre run to AS 3600:2018
Section 11. It forms the axial actions, finds the effective height, selects the design
method, and then checks the wall:

| Utilisation key | Check | Reference |
| --- | --- | --- |
| `designMethod` | The simplified or slab method applies: wall braced, not in part tension, no out-of-plane moment requiring column design | Cl 11.1, Cl 11.2.1, Cl 11.3 |
| `axial` | `N* / phiNu`, with `phiNu = phi (tw - 1.2 e - 2 ea) 0.6 f'c`, capped at `3 tw` for one layer, or `(0.03 f'c - sigma.in) tw` when designed as a slab | Cl 11.5.3, Cl 11.1(b)(i) |
| `slenderness` | `Hwe/tw` against 20 (one layer), 30 (two layers) or 50 (slab) | Cl 11.5.2(c), Cl 11.1(b) |
| `singleLayer` | One layer only: `tw <= 200`, `Hwe/tw <= 20`, `Hw <= 20 m`, `sigma.max <= 3 MPa`, not a ductile wall | Cl 11.5.2(a), Cl 11.7.3, Cl 14.6.7 |
| `verticalSteel`, `horizontalSteel` | Minimum reinforcement ratios | Cl 11.7.1 |
| `verticalSpacing`, `horizontalSpacing`, `barGap` | `s <= min(350, 2.5 tw)` and a clear gap of at least `3 db` | Cl 11.7.3 |
| `inPlaneShear` | `V* / phiVu`, `Vu = min(Vuc + Vus, Vu.max)` | Cl 11.6 |
| `ductileWall` | Limited ductile wall only: `pwv <= 16/fsy` and Class N | Cl 14.6.7 |

Three optional check groups are available:

| Group | Utilisation key | Reference | Source |
| --- | --- | --- | --- |
| `fire` | `fireResistance`, required FRL against the Table 5.7.1/5.7.2 FRL | Cl 5.7 | Workbook tables, with the Tedds required-FRL comparison |
| `crackControl` | `crackControl`, the Cl 11.7.2 ratio for the selected degree of control | Cl 11.7.2 | Tedds AS 3600-2018 wall calculation |
| `durability` | `cover`, the cover against the Table 4.10.3.2/3 minimum for the exposure class | Section 4 | Tedds AS 3600-2018 wall calculation |

### Excluded

The module identifies, but does not design, walls in part tension (Section 7 or 10),
walls with out-of-plane moments that must be designed as columns (use the concrete column
module), unbraced walls, and the Section 9 out-of-plane design of walls treated as slabs.
It does not design restraint of vertical bars, anchorage, lapping, or the portions of a
wall between large openings. The workbook's hidden `ACI` and `Thermal` sheets are not
transcribed: the `ACI` sheet states "Not updated to AS 3600-2018 yet, also not checked".

### Validity limits

* `20 <= f'c <= 120` MPa. Values outside this range raise `ValueError`.
* Bars are 10 to 32 mm (`Settings!I11:I17`). `fsy` is 400 or 500 MPa.
* One central layer must fit in `tw`; two layers need `cover + db.v + db.h < tw / 2`.
* `Mo*`, `Mi*` and `V*` are magnitudes and must not be negative. `Neu` may be negative.

## Units and conventions

Axial actions and capacities are in kN/m, out-of-plane moments in kNm/m, the in-plane
moment in kNm and the in-plane shear in kN over the whole wall length. Lengths are in mm
and stresses in MPa. Actions are unfactored except the ultimate earthquake axial action
`Neu`. The cover is to the outer bars; the vertical bars are taken as the outer layer.

## Differences from the source workbook

| Workbook behaviour | This module | Why |
| --- | --- | --- |
| One layer with `sigma.max > 3 MPa`: `phiNu = 3 tw` whatever `Nus` and `Hwe/tw` (`Design!E65`) | `phiNu = min(3 tw, phi Nus)` within the slenderness limit, else 0 | The 3 MPa limit is not a capacity; slender walls were overstated |
| Axial check ignores the in-plane bending stress (`Design!I9`) | Demand `N* + sigma.in tw` in wall mode | The most compressed metre governs |
| `pwv.min` threshold `MIN(2, 3*fc)` (`Design!H41`) | `min(2, 0.03 f'c)` | `3*fc` is a typo; Tedds uses the same corrected rule |
| Reinforcement, single-layer and applicability errors printed as text, capacity still "OK" | Utilisations counted in `worstUtil` | A failed rule must not report OK |
| Braced condition not asked | `braced` input | Cl 11.5 applies to braced walls only |
| Horizontal gap check uses the vertical bar size (`Design!G55`) | Uses `db.h` | Transcription defect |
| FRL reported but never compared | Optional `fire` group with a required FRL | Tedds checks the required FRL |
| `k` always typed in, with a hint | `kMode` calculated or user, warning if different | Avoids a stale `k` |
| `ACI`, `Thermal`, `As Column` sheets; mesh naming | Not transcribed | Hidden, superseded, notes only, or presentation |

## Commands

Run these from the suite root:

```powershell
$Python = Join-Path $PWD '.venv\Scripts\python.exe'
$env:PYTHONPATH = "$PWD;$PWD\calculations\concrete\concrete_wall\src"
& $Python -m unittest discover -s calculations/concrete/concrete_wall/tests -v
& $Python -c "from ic_concrete_wall import headless; from packages.innocalc_sdk import check_contract; print(check_contract(headless)); print(headless.validate()['ok'])"
& $Python -m ic_concrete_wall.dev calculations/concrete/concrete_wall/examples/worked-example.json --html artifacts/concrete-wall/worked-example.html
```

## Evidence

| Artefact | Location |
| --- | --- |
| Technical review | `TECHNICAL-README.md` |
| Retained baseline | `src/ic_concrete_wall/data/workbook-baseline.json` |
| Source provenance | `reference/README.md` |
| Worked example | `examples/worked-example.json` |
| Tests | `tests/test_engine.py`, `tests/test_release_gate.py` |

## Outstanding release gates

1. Confirm the open interpretation points against the printed AS 3600:2018 Amdt 2 and
   AS/NZS 1170.0 (TECHNICAL-README C3, C7, C8, C9, C13 and C14).
2. Obtain an independent engineering review and record it in `reference/README.md`.
3. Add a worked example from a source other than Structural Toolkit, for example
   Foster, Kilpatrick and Warner, *Reinforced Concrete Basics* 2E (cited by `Info!B19`).
4. Name a maintainer, register the module in `suite.toml` and complete manager
   integration and PDF acceptance.
