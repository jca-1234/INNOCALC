# Concrete Punching Shear Design

| | |
| --- | --- |
| Module ID | `concrete-punching-shear` |
| Package | `ic_concrete_punching_shear` |
| Distribution | `innocalc-concrete-punching-shear` |
| Entry point | `ic_concrete_punching_shear.headless` |
| Filing folder | `13 - CONCRETE PUNCHING SHEAR` |
| Category | `Concrete` |
| Standard | AS 3600:2018 incl. Amendments 1 and 2 |
| Version | `v0.0.1` |
| Status | `planned`, `enabled = false` |
| Maintainer | Responsible engineer (unassigned) |

> **Not approved for design.** This module transcribes the retained Structural Toolkit
> workbook `Concrete_Punching_506.xls` (PUNCHING SHEAR V5.06). It reproduces 81 saved
> workbook values to `1e-9` and all 120 results of the workbook author's GoalSeek test
> harness. That shows the transcription is faithful. It does not show the engineering is
> correct. See [TECHNICAL-README.md](TECHNICAL-README.md) for the technical review and the
> open concerns.

## Scope

This module checks the punching shear strength of a reinforced or prestressed concrete slab
at a rectangular or circular column, at an internal, edge or corner position, to AS 3600
Section 9.3. It covers an optional spandrel beam along the free edge, closed fitments in the
torsion strip or spandrel, shear heads, an ineffective portion of the perimeter for openings,
the Cl 6.10.4.5 minimum transferred moment and the column integrity reinforcement. It reports:

| Utilisation key | Check | Reference |
| --- | --- | --- |
| `punching` | `V* / phiVu` for the governing case: Eq 9.3.3(1) or (2) when `Mv* = 0`; otherwise Eq 9.3.4(1) without closed fitments, or Eq 9.3.4(4) with compliant fitments (with Eq 9.3.4(2) or (3) as the minimum and Eq 9.3.4(5) as the ceiling) | Cl 9.3.3, Cl 9.3.4 |
| `fitmentArea` | `Asw.min / Asw`, when fitments are provided | Cl 9.3.5 |
| `fitmentSpacing` | `s / min(Ds or Db, 300)`, when fitments are provided | Cl 9.3.6 |
| `fitmentWidth` | `wcl / a`, torsion strip fitments only (workbook rule `Design!H13`) | Workbook |
| `prestressDepth` | `0.8 Ds / do`, when `sigma.cp > 0` (workbook rule `Design!F16`) | Cl 1.7 |
| `integrity` | `As.min / As` with `As.min = 2 N* / (phi fsy)`, unless waived by beams | Cl 9.2.2 (as cited by the workbook) |

Every Cl 9.3.3 and Cl 9.3.4 case is also printed, with its own ratio, in a comparison grid.

One optional check group follows Tedds:

| Group | Effect | Reference |
| --- | --- | --- |
| `effectiveDepth` | `dom` is the mean of the outer and inner bar-layer depths, `((Ds - c - db1/2) + (Ds - c - db1 - db2/2)) / 2`, replacing the entered `do` | Cl 9.3.1.4; Tedds *RC slab design (AS3600)* 1.0.21 |

### Excluded

The module does not design the shear head, the flexural reinforcement or the extent and
anchorage of the fitments along the torsion strip. Only one direction of moment transfer is
checked per calculation. Columns set back from a free edge, re-entrant corners, L-shaped or
other non-rectangular loaded areas, and the load inside the critical perimeter are not
modelled. The workbook's hidden `Curved = Y` perimeter option (`Settings!AB129`) is not
transcribed.

### Validity limits

* `20 <= f'c <= 120` MPa. Values outside this range raise `ValueError`.
* `20 mm <= do < Ds`. For a rectangular column `L >= W`.
* With a spandrel, `Db > Ds`. `Lo' <= Lo`.
* `V*`, `Mv*` and `sigma.cp` are magnitudes and must not be negative.
* Fitment bars are 0 (none), 6, 8, 10, 12, 16 or 20 mm. Integrity bars are 10 to 36 mm.
  `fsy` and `fsy.f` are 250, 400 or 500 MPa. The number of integrity bars is a whole number.

## Units and conventions

`V*` and `N*` are entered in kN, `Mv*` in kNm, the Cl 6.10.4.5 loads in kPa and lengths in
mm. The engine works in N, mm and MPa. `L` is the larger column dimension, and `pmDir` says
whether `Mv*` acts along `L` or `W`, which selects `a`. At an edge, `pface` names the column
face lying on the edge; at a corner it names the face parallel with the spandrel. Text
options are compared case-insensitively, as Excel does.

## Differences from the source workbook

| Workbook behaviour | This module | Why |
| --- | --- | --- |
| `Design!I8:I12` print an OK / No Good for every case; the saved example shows three No Good and one OK | One governing case from the reinforcement provided; all cases shown in a grid | A result must say whether the slab passes (TECHNICAL-README C1) |
| `Design!F105` computes the Cl 6.10.4.5 minimum `M.min*` but never uses it | `simplifiedMethod = Y` applies `max(Mv*, M.min*)` at interior supports; otherwise a warning when `M.min* > Mv*` | C2 |
| `Design!F92` computes `As.min` but never compares it | `integrity` utilisation against `nIntegrity` bars | C3 |
| Applicability errors (`Design!H13`, `F16`, `H27`) are printed but do not affect OK | `fitmentWidth`, `prestressDepth`, `fitmentArea`, `fitmentSpacing` count towards `worstUtil` | C5 |
| `ctsp = 0` with a fitment size, or `y1 = 0`, still gives a non-zero `phiVu.min` (`Design!F67`) | Treated as no fitments | C6 |
| GoalSeek macro `RecalcDom` averages `dom`; stale if not re-run | Bounded bisection, flagged when no exact root exists | C7 |
| Non-compliant fitments zero the fitment strength and print No Good | Ignored for strength (Eq 9.3.4(1) used) and failed on `fitmentArea` / `fitmentSpacing` | C5 |
| `L < W`, `Ds >= Db`, `Lo' > Lo`, `f'c` outside 20 to 120 MPa print an error | `ValueError` | Invalid input |
| Fitment label prints `N` for 250 MPa bars (`Design!I28`) | Prints `R` | Label only |
| `Curved` setting and curved perimeter branch | Not transcribed | Hidden setting fixed at `N` |
| `dom` entered directly | Optional `effectiveDepth` group | Adopted from Tedds (TECHNICAL-README §2.1) |

## Commands

Run these from the suite root:

```powershell
$Python = Join-Path $PWD '.venv\Scripts\python.exe'
$env:PYTHONPATH = "$PWD;$PWD\calculations\concrete\concrete_punching_shear\src"
& $Python -m unittest discover -s calculations/concrete/concrete_punching_shear/tests -v
& $Python -m ic_concrete_punching_shear.dev --validate
& $Python -m ic_concrete_punching_shear.dev calculations/concrete/concrete_punching_shear/examples/worked-example.json --html artifacts/concrete-punching-shear/worked-example.html
```

Once the module is registered in `suite.toml`, `python -m tooling check concrete-punching-shear --validate`
also applies.

## Evidence

| Artefact | Location |
| --- | --- |
| Technical review | `TECHNICAL-README.md` |
| Retained baseline and GoalSeek harness | `src/ic_concrete_punching_shear/data/workbook-baseline.json` |
| Source provenance | `reference/README.md` |
| Worked example | `examples/worked-example.json` |
| Tests | `tests/test_engine.py`, `tests/test_release_gate.py` |

## Outstanding release gates

1. Confirm against the printed AS 3600:2018 Amdt 2 the integrity reinforcement clause and
   its `phi = 0.7`, the Cl 6.10.4.5 load factors, and the Cl 9.3.6 spacing limit
   (TECHNICAL-README C4, C9 and C12).
2. Decide the treatment of `a` for circular columns at edges and corners (C8).
3. Obtain an independent engineering review and record it in `reference/README.md`.
4. Add a worked example from a source other than Structural Toolkit.
5. Name a maintainer, register the module in `suite.toml`, and complete manager
   integration and PDF acceptance.
