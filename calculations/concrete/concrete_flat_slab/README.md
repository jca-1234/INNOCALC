# Concrete Flat Slab Design

| | |
| --- | --- |
| Module ID | `concrete-flat-slab` |
| Package | `ic_concrete_flat_slab` |
| Distribution | `innocalc-concrete-flat-slab` |
| Entry point | `ic_concrete_flat_slab.headless` |
| Filing folder | `14 - CONCRETE FLAT SLAB` |
| Category | `Concrete` |
| Standard | AS 3600:2018 incl. Amendments 1 and 2; AS/NZS 1170.0:2002 for combinations |
| Version | `v0.0.1` |
| Status | `planned`, `enabled = false` |
| Maintainer | Responsible engineer (unassigned) |

> **Not approved for design.** This module transcribes the retained Structural Toolkit
> workbook `Concrete_FlatSlab_504.xls` (FLAT SLABS V5.04). It reproduces 224 saved
> workbook values to `1e-9`. That shows the transcription is faithful. It does not show
> the engineering is correct. See [TECHNICAL-README.md](TECHNICAL-README.md) for the
> technical review and the open concerns.

## Scope

This module designs a reinforced two-way flat slab or flat plate with multiple spans, with
or without drop panels, by the simplified method of AS 3600 Cl 6.10.4. For the interior and
edge design strips in both directions it reports the total static moment `Mo`, the
Table 6.10.4.3 moments at the six critical sections of an end span and an interior span,
and their split into column strip and middle strip moments (Table 6.9.5.3), per strip and
per metre. It also reports the Cl 6.10.4.5 moment transferred to interior columns, for use in
the `concrete-punching-shear` module.

| Utilisation key | Check | Reference |
| --- | --- | --- |
| `spanRatio` | `(Ly/Lx) / 2` | Cl 6.10.4.1(c) |
| `liveLoadRatio` | `wll / (2 g)`, live load not exceeding twice the dead load | Cl 6.10.4.1(g) |
| `ductilityClass` | Class L flexural reinforcement not permitted (`inf` when Class L) | Cl 6.10.4.1(i) |
| `minimumSteel` | `Ast.min / Ast`, with `Ast.min = 0.24 (D/d)^2 f'ct.f/fsy b d` | Cl 9.1.1(a) |
| `liveLoadDeflection` | `wll / g`, applicability of the deemed-to-comply rule | Cl 9.4.4.1 |
| `deflectionTotal` | `d.min / ds`, total deflection | Cl 9.4.4.1 |
| `deflectionIncremental` | `d.min.inc / ds`, incremental deflection | Cl 9.4.4.1 |

Optional check groups:

| Group | Utilisation keys | Reference |
| --- | --- | --- |
| `customSupports` | none; replaces the workbook's support-length table with eight entered sums `a_sup1 + a_sup2` | Cl 6.10.4.2 |
| `customDistribution` | `distributionRange`, the entered column strip shares against the Table 6.9.5.3 ranges | Table 6.9.5.3 |
| `flexure` | `flexure`, `ductility`, `flexuralMinimum` and `barSpacing`, taken at the governing strip among column strip, middle strip and edge column strip, top and bottom | Cl 8.1, Table 2.2.2, Cl 9.1.1, Cl 9.4.1 |
| `shrinkage` | `shrinkage`, or folded into `flexuralMinimum` when flexure is on | Cl 9.4.3 |

The `flexure` and `shrinkage` groups follow the Tedds AS 3600-2018 slab calculation.

### Excluded

The module does not check punching shear (use `concrete-punching-shear`), beam shear, crack
width, edge beams, torsion, detailing, fire or vibration. It does not check the Cl 6.10.4.1
grid, offset, successive-span and end-span conditions, which it lists as assumptions. The
workbook's `Prelim` sheet (WRH Chapter 16 preliminary thickness) is excluded, because
V5.04 marks it "Removed 2018 standard".

### Validity limits

* `20 <= f'c <= 120` MPa. Values outside this range raise `ValueError`.
* Bar sizes are 10, 12, 16, 20 or 24 mm. `fsy` is 500 or 400 MPa. Live load type is N or S.
* Exterior edge condition is S, I, C or F; span type for deflection is I or E.
* Column dimensions must be smaller than the spans; `ds > 0`; `dc < ds`.
* Custom strip shares must lie between 0 and 1.

## Units and conventions

Loads are in kPa, lengths in mm, strip moments in kNm and moments per metre in kNm/m.
Negative moments are hogging. Spans are equal in each direction. `My*` spans the longer
direction `Ly` over a design strip of width `Lx`; `Mx*` spans `Lx` over width `Ly`. If `Ly`
is entered shorter than `Lx`, the two directions are swapped together with their overhangs,
column dimensions and custom support lengths. The exterior edge codes follow the workbook:
S = unrestrained (simple), I = integral columns, C = columns and edge beam,
F = fully restrained (walls).

## Differences from the source workbook

| Workbook behaviour | This module | Why |
| --- | --- | --- |
| `Analysis!D164` computes `Ast.min` but never compares it with `Ast` | `minimumSteel` utilisation | Cl 9.1.1 is a mandatory strength requirement |
| `Analysis!D10`, `D26` and `E162` print applicability errors and notes, and `B9` still reports "OK" | `spanRatio`, `liveLoadRatio` and `ductilityClass` count towards the verdict | A calculation outside its method must not report OK |
| No `q <= g` check for the deemed-to-comply method | `liveLoadDeflection` utilisation | Cl 9.4.4.1, as Tedds checks |
| `Lo = L - 0.7 (a_sup1 + a_sup2)` without the lower limit (`Analysis!D38:H39`, `D97:H98`) | `Lo >= 0.65 L`, except the wall-supported edge strip, whose `Lo = 0` is intended | Cl 6.10.4.2 |
| `d.min` uses the largest `Lo` (`Analysis!C189:G190`) | `d.min` uses `Lef = min(Ln + D, L)` of the longer span; the workbook values are reported for comparison | Lef is the effective span; revision 5.03 intended "deflections changed to use Lef" |
| `Analysis!D26` warns "dead load less than self weight" when `wdl <> 25 th` | Warns only when `wdl < 25 th` | Matches the message |
| "Error - Shorter span > Longer span" text | Directions swapped with their properties, with a warning | Directions are symmetrical |
| No reinforcement class input on `Analysis` | `reo` input, default N (named cell `Settings!O64`) | Needed for Cl 6.10.4.1(i) |
| `k3` values 0.95 and 1.05 are editable cells (`Analysis!C185`, `G185`) | Fixed constants | Cl 9.4.4.1 values |
| Custom `a_sup` table of 16 cells, custom distribution unrestricted | Eight active sums; custom shares checked against Table 6.9.5.3 | Only eight are used for a given drop setting |
| No moment transfer output | Cl 6.10.4.5 `M*v` at first and typical interior columns | Required input to punching shear design |
| No capacity or shrinkage checks | Optional `flexure` and `shrinkage` groups | Adopted from Tedds (TECHNICAL-README section 2.1) |
| `ChangeFlatCols`, `meshname` and GoalSeek `FindSp*` macros; `Prelim` sheet | SVG plan and moment diagram; mesh naming and `Prelim` omitted | Presentation only, or removed from the 2018 workbook |

## Commands

Run these from the suite root:

```powershell
$Python = Join-Path $PWD '.venv\Scripts\python.exe'
$env:PYTHONPATH = "$PWD;$PWD\calculations\concrete\concrete_flat_slab\src"
& $Python -B -m unittest discover -s calculations/concrete/concrete_flat_slab/tests -v
& $Python -c "from ic_concrete_flat_slab import headless; from packages.innocalc_sdk import check_contract; print(check_contract(headless)); print(headless.validate()['ok'])"
& $Python -m ic_concrete_flat_slab.dev --validate
```

After registration in `suite.toml`, `python -m tooling check concrete-flat-slab --validate`
and `python -m tooling dev concrete-flat-slab calculations/concrete/concrete_flat_slab/examples/worked-example.json --html artifacts/concrete-flat-slab/worked-example.html`
also apply.

## Evidence

| Artefact | Location |
| --- | --- |
| Technical review | `TECHNICAL-README.md` |
| Retained baseline | `src/ic_concrete_flat_slab/data/workbook-baseline.json` |
| Source provenance | `reference/README.md` |
| Worked example | `examples/worked-example.json`; rendered to `artifacts/concrete-flat-slab/worked-example.html` |
| Tests | `tests/test_engine.py`, `tests/test_release_gate.py` |

## Outstanding release gates

1. Confirm the Table 6.10.4.3 coefficients, the Table 6.9.5.3 ranges, the `a_sup`
   definition and the clause numbers against the printed AS 3600:2018 Amdt 2
   (TECHNICAL-README C5, C10, C15). Tedds has no AS flat slab table to compare with.
2. Obtain an independent engineering review and record it in `reference/README.md`.
3. Add a worked example from a source other than Structural Toolkit.
4. Name a maintainer, register the module in `suite.toml`, and complete manager integration
   and PDF acceptance.
