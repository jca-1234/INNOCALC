# Concrete Corbel Design

| | |
| --- | --- |
| Module ID | `concrete-corbel` |
| Package | `ic_concrete_corbel` |
| Distribution | `innocalc-concrete-corbel` |
| Entry point | `ic_concrete_corbel.headless` |
| Filing folder | `03 - CONCRETE CORBEL` |
| Category | `Concrete` |
| Standard | AS 3600:2018 incl. Amendments 1 and 2; AS/NZS 1170.0:2002 for combinations |
| Version | `v0.0.1` |
| Status | `planned`, `enabled = false` |
| Maintainer | Responsible engineer (unassigned) |

> **Not approved for design.** This is a transcription of the retained Structural
> Toolkit workbook `Concrete_Corbel_506.xls` (CORBEL V5.06). It reproduces that
> workbook to within `1e-9`, which establishes transcription fidelity, not
> engineering correctness. Independent review is outstanding. See
> [Outstanding release gates](#outstanding-release-gates).

## Scope

Strength design of a reinforced concrete corbel or nib cast on a wall or column,
loaded by a vertical action `V*` at an eccentricity `av` together with a
horizontal action `N*`.

### Checks included

| Utilisation key | Check | Reference |
| --- | --- | --- |
| `bearing` | Bearing stress at the corbel node, `B* / phiB` | Cl 7.4.2 |
| `shearFriction` | Shear friction on the vertical face, `V* / phiVu` | Cl 8.4.3 |
| `tensileTie` | Horizontal tensile tie, `Ft* / phiFt` | Cl 7.3.2 |
| `minimumSteel` | Minimum flexural reinforcement, `Ast.min / As` | Eq 8.1.6.1(2) |
| `depthLimit` | Minimum overall depth, `1.7 av / D` | Corbel proportioning |
| `wallThickness` | Strut width across the support, `w / th` | Geometry limit |

The Cl 7.2.3 compression strut is **solved, not checked**. The strut width `dc`
is chosen so the strut is exactly fully utilised (`Cf* = phiCa - 0.01 kN`),
because its only purpose is to fix the strut depth `x` and hence the tie lever
arm `d - x/2`. Reporting it as a utilisation would pin `worstUtil` at 1.0 for
every corbel, which is why the source workbook also excludes it from its
governing ratio. The solved state, iteration count and residual are in
`result["strut"]`.

### Checks deliberately excluded

Anchorage and development of the tie and cross bars, bearing plate or bearing pad
design, the bending induced in the supporting wall or column, torsion, fatigue,
fire, durability, crack control and all serviceability.

### Validity limits

* `20 <= f'c <= 120` MPa (Cl 1.1.2). Outside this range the module raises `ValueError`.
* `D >= df`, `D > cover + db/2`, and every dimension strictly positive.
* Bar sizes N12, N16, N20, N24, N28; `fsy` 400 or 500 MPa.
* Actions are entered as non-negative service magnitudes.
* `D >= 1.7 av` and `w <= th` are reported as utilisations, so a corbel outside
  those proportions returns `FAIL` rather than being rejected.

## Units and conventions

Working units are **N, mm, MPa**. The form accepts actions in **kN**; they are
converted once, in `engine.compute`, and the result document stores newtons.
`report.py` converts back for display with `calcpad.force`.

`V*` acts downwards on the bearing, `N*` acts outwards as tension on the tie.
`gpt` is negative because it is a permanent clamping action across the shear
plane; it reduces `tau_u`.

Entering `b = 1000` designs the corbel per metre run and switches the printed
units to `kN/m` and `mm2/m`, reproducing the source workbook's behaviour.

## Differences from the source workbook

| Workbook behaviour | This module | Why |
| --- | --- | --- |
| `dc` solved by the `Corbel_Solve` VBA macro calling `Range("error").GoalSeek` | Bounded bisection in `engine.solve_strut` on the identical residual | Deterministic, no host application, and convergence is reported |
| The saved example is unconverged (`Design!L17 = -7.903 kN`) | Always solved to `abs(residual) < 1e-3` N or reported as unattainable | A stale iterate must not be presented as a capacity |
| `Design!D40` encodes bar count, centres or area by magnitude thresholds (`<75`, `<=600`, `>600`) | Explicit `reoMode` selector plus `reoValue` | The suite form cannot express a magnitude-encoded mode safely |
| `Settings!P67` `limittu` switch for the AS 3600:2009 `tau_u` limit | Limit always applied; switch not offered | Both workbook formulas are already identical in V5.06 after Amendment 2 reinstated the limit, so the switch is dead |
| `phi` and `beta.n` are editable cells | Engine constants with clause references | They are code-prescribed, not design inputs |

## Commands

From the suite root:

```powershell
$Python = Join-Path $PWD '.venv\Scripts\python.exe'
& $Python -m tooling dev concrete-corbel --schema
& $Python -m tooling dev concrete-corbel --trace
& $Python -m tooling dev concrete-corbel calculations/concrete/concrete_corbel/examples/worked-example.json --html artifacts/concrete-corbel/worked-example.html
& $Python -m tooling check concrete-corbel --validate
& $Python -m unittest discover -s calculations/concrete/concrete_corbel/tests -v
```

The test discovery above needs `calculations/concrete/concrete_corbel/src` and the
suite root on `PYTHONPATH`, or an editable install of this distribution.

## Evidence

| Artefact | Location |
| --- | --- |
| Retained baseline comparison set | `src/ic_concrete_corbel/data/workbook-baseline.json` |
| Source provenance and extraction record | `reference/README.md` |
| Reviewed input document | `examples/worked-example.json` |
| Engineering and interface tests | `tests/test_engine.py`, with `tests/test_release_gate.py` |

`validate()` runs a 36-case internal consistency sweep plus the retained
baseline, comparing 48 published values. It returns `ok = true` when the
transcription agrees; that is **not** engineering approval, and `validate()`
carries an explicit `approval` field saying so.

## Outstanding release gates

1. Independent engineering review of the transcription against AS 3600:2018
   Sections 7 and 8.4.3, recorded in `reference/README.md` with reviewer, date and
   version.
2. A worked example from a source independent of Structural Toolkit.
3. Confirmation of the fixed `beta.n = 0.80` CCT node assumption, and a decision
   on whether CCC and CTT nodes are needed.
4. Assignment of a responsible maintainer, replacing the placeholder in
   `module.toml`.
5. Manager integration testing: form, conditional panels, save, reopen, revision,
   package export.
6. PDF acceptance. No PDF has been produced or inspected for this module.

Only after all of these may `status` become `available` and the `suite.toml`
entry `enabled = true`.