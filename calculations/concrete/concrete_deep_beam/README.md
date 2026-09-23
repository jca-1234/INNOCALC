# Concrete Deep Beam Design

| | |
| --- | --- |
| Module ID | `concrete-deep-beam` |
| Package | `ic_concrete_deep_beam` |
| Entry point | `ic_concrete_deep_beam.headless` |
| Filing folder | `06 - CONCRETE DEEP BEAM` |
| Category | `Concrete` |
| Method | Superseded CEB approach after Warner, Rangan, Hall and Faulkes (WRHF) |
| Version | `0.1.0.dev0` |
| Status | `planned`, `enabled = false` |
| Source workbook | `Concrete_DeepBeam_502.xls` (Structural Toolkit DEEP BEAMS V5.02) |

> ## SUPERSEDED METHOD — INFORMATIVE ONLY
>
> The source workbook labels its own method
> `Superceded CEB Approach - Informative only` at `Info!F19` and `Design!B15`.
> AS 3600:2018 Section 12 strut-and-tie is the current method. This module must
> not be the sole basis of a deep beam design. It is transcribed so the legacy
> results remain reproducible and auditable.

## Scope

| Utilisation key | Check | Reference |
| --- | --- | --- |
| `diagonalCompression` | `V* / phiVu.max`, the lesser of the depth and span forms | WRHF Eq 24.24 |
| `externalSupport` | `R* / phiRe = 0.8 bw (c + Df) f'cd` | WRHF Eq 24.26 |
| `internalSupport` | `R* / phiRi = 1.2 bw (c + 2 Df) f'cd` | WRHF Eq 24.27 |
| `spanDepthLimit` | `(L/D) / limit`, limit 2.0 / 2.5 / 3.0 / 1.0 by span type | CEB applicability |
| `supportWidthLimit` | `c / (L/5)` | CEB detailing limit |

Also produced: the effective lever arm `z`, the effective design stress
`fsy.d = min(fsy / gamma_s, fsi)`, the positive and negative tension tie areas and
bar counts, their distribution over the outer `0.2 D` and middle `0.6 D` zones,
and the maximum web reinforcement spacing for mesh and for bars.

The external support check is skipped for a cantilever and the internal support
check for a simple span, exactly as the source workbook does (`Design!I11`,
`Design!I12`).

### Excluded

Anchorage and development of the tie, support zone detailing, torsion, web
openings, deflection, crack width calculation and fire. The reinforcement output
is a required area and a nominal bar count, not a bar schedule.

## A material difference from the source workbook

The workbook's summary ratio is `Settings!O21 = MAX(Vstar/fV)` — the diagonal
compression ratio **alone**. In the saved example it reports `OK (0.15)` while
`Design!D23` on the same sheet simultaneously reads
`mm Error - c > L/5`, because `c = 900 mm` exceeds `L/5 = 600 mm`.

This module reports the support width limit and the span-to-depth limit as
utilisations, so the same inputs return **FAIL at 1.50**, governed by the support
width. A rule that fails must affect the reported status.

## Units and conventions

Working units are **N, mm, MPa, N.mm**. Actions are entered in kN, kNm and kN/m.

`gamma_s` and `gamma_c` are CEB material safety factors entered by the user, not
AS 3600 capacity reduction factors.

The point load and uniform load fields produce only the *indicative* moment and
shear printed beside them; they do not drive the design. `Mp*`, `Mn*`, `V*` and
`R*` do.

## Differences from the source workbook

| Workbook behaviour | This module | Why |
| --- | --- | --- |
| Summary ratio counts only diagonal compression | All five ratios contribute to `worstUtil` | A failed geometry rule must not report OK |
| `Design!C17` stores lowercase `c` | Span type folded to upper case | Reproduces Excel's case-insensitive text comparison |
| Mesh diameter validated by a list that the saved value (10 mm) is not in | Any positive diameter accepted, with a warning when it is not standard | Rejecting it would reject the workbook's own example |
| `fsic` used only when `crack = "C"`, with a `0.001` floor | Same, and the floor is retained and documented | Faithful transcription of `Design!E38` |

## Commands

```powershell
Set-Location C:\CODING\INNOCALC
$Python = Join-Path $PWD '.venv\Scripts\python.exe'
& $Python -m tooling check concrete-deep-beam --validate
& $Python -m tooling dev concrete-deep-beam calculations/concrete/concrete_deep_beam/examples/worked-example.json --html artifacts/concrete-deep-beam/worked-example.html
$env:PYTHONPATH = "C:\CODING\INNOCALC\calculations\concrete\concrete_deep_beam\src;C:\CODING\INNOCALC"
& $Python -m unittest discover -s calculations\concrete\concrete_deep_beam\tests -v
```

## Evidence

`validate()` runs a 144-case sweep across all four span types, four grades, three
geometries and three load levels, and replays the retained workbook example,
comparing **29 published values**. `tests/test_engine.py` adds 39 further tests.

## Outstanding release gates

1. **A decision on whether a superseded method should be published at all.** If it
   is, the calculation sheet and the module description must keep saying so.
2. Independent engineering review of the transcription against WRHF and against
   AS 3600:2018 Section 12.
3. Confirmation that the summary should include the geometry limits, which the
   workbook omitted.
4. A named responsible maintainer.
5. Manager integration testing and PDF acceptance. No PDF has been inspected.
