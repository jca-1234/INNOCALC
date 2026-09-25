# Concrete Beam and Slab Design

| | |
| --- | --- |
| Module ID | `concrete-member` |
| Package | `ic_concrete_member` |
| Distribution | `innocalc-concrete-member` |
| Entry point | `ic_concrete_member.headless` |
| Filing folder | `17 - CONCRETE MEMBER` |
| Category | `Concrete` |
| Standard | AS 3600:2018 incl. Amendments 1 and 2; AS/NZS 1170.0:2002 for combinations |
| Version | `v0.0.1` |
| Status | `planned`, `enabled = false` |
| Maintainer | Responsible engineer (unassigned) |

> **Not approved for design.** This module transcribes the retained Structural Toolkit
> workbook `Concrete_Member_513.xls` (CONCRETE MEMBER V5.13). It reproduces 483 saved
> workbook values to `1e-9`. That shows the transcription is faithful. It does not show
> the engineering is correct. See [TECHNICAL-README.md](TECHNICAL-README.md) for the
> technical review and the open concerns.

## Scope

The module checks one section of a reinforced concrete beam (rectangular, T or L) or a
one-way slab strip (per metre) for strength and serviceability to AS 3600 Sections 8 and 9.
Bending and shear actions are entered separately, as in the workbook's manual mode.

| Utilisation key | Check | Reference |
| --- | --- | --- |
| `flexure` | Stress-block bending strength with tension and compression steel, `|M*| / phiMuo` | Cl 8.1 / Cl 9.1 |
| `ductility` | `kuo <= 0.36`, or `Asc >= 0.01 b kuo do` when exceeded | Cl 8.1.5 |
| `minimumSteel` | Minimum strength steel, deemed-to-comply or `(Muo)min = 1.2 Z f'ct.f` | Cl 8.1.6.1 / Cl 9.1.1 |
| `barSpacing` | Tension bar centres `<= 300` mm (beams) or `min(2D, 300)` (slabs) | Cl 8.6.1 / Cl 9.5.1 |
| `crackStress`, `crackStressYield` | `sigma.scr` against Tables 8.6.2.2 / 9.5.2.1 and `sigma.scr1 <= 0.8 fsy` | Cl 8.6.2.2 / Cl 9.5.2.1 |
| `shear` | `V*` against `ks phiVuc` or `phiVu` (general or simplified kv, theta.v) | Cl 8.2 |
| `shearDetailing` | Fitment spacing, transverse spacing, minimum area, `D >= 750` mm rule | Cl 8.2.1.6, Cl 8.3.2 |
| `torsion`, `torsionReinforcement` | `T* / phiTus`; minimum torsion fitments and spacing | Cl 8.2.5.5, Cl 8.2.5.6, Cl 8.3.3 |
| `webCrushing` | Combined shear and torsion stress against `phiVu.max / (bv dv)` | Cl 8.2.3.3 |
| `longitudinalTension`, `longitudinalCompression` | Additional longitudinal force from shear and torsion | Cl 8.2.8 |
| `shearMethod` | Simplified-method limits (only when selected) | Cl 8.2.4.3 |
| `deflectionTotal`, `deflectionIncremental`, `liveLoadLimit` | Deemed-to-comply span-to-depth and its `q <= g` condition | Cl 8.5.4 / Cl 9.4.4.1 |

Optional check groups:

| Group | Utilisation keys | Reference |
| --- | --- | --- |
| `crackWidth` | `crackWidth`, calculated crack width against `w'max` | Cl 8.6.2.3 |
| `calcDeflection` | `deflectionDead`, `deflectionLive`, `deflectionIncrementalCalc`, `deflectionTotalCalc` from gross analysis deflections, `Ief` at three positions, `Iav` and `kcs` | Cl 8.5.3 |
| `slenderness` | `slenderness`, lateral restraint spacing against `L1` | Cl 8.9 |
| `secondary` | `secondarySteel`, slab shrinkage and temperature steel | Cl 9.5.3 |

Shrinkage (Cl 3.1.7) and creep (Cl 3.1.8) are always calculated because the crack control,
`sigma.cs` and crack width depend on them.

### Excluded

The analysis-linked sheets (`Analysis`, `Results`), the `Layers` custom bar layouts and
pure strain-compatibility routine, the `SlabShear` quick check (see concern C1), `SlabPrelim`,
exposure classification (Table 4.10.3.2), the Cl 9.7 moment-resisting width, prestress, the
AS 5100.5 shear variants other than the `Act` definition, fire, curtailment and anchorage.
TECHNICAL-README §6 lists every deferred workbook feature.

### Validity limits

* `20 <= f'c <= 120` MPa; `f'c > 100` MPa requires a manual creep coefficient.
* Density 1800 to 2800 kg/m3. `fsy` and `fsy.f` are 250, 400 or 500 MPa.
* Bars 6 to 40 mm; fitments 0 (none), 6, 8, 10, 12 or 16 mm; at most 30 bars per face.
* Flanged beams need `Bf > W` and `0 < Tf < D`. The steel centroids must lie inside the section.
* `w'max` is 0.2, 0.3 or 0.4 mm; fitment angle 45 to 90 degrees.

## Units and conventions

Forces are in kN, moments in kNm and lengths in mm; slab values are per metre width.
`M*` is positive when the bottom face is in tension. The shear axial force `N*` is positive
in compression (workbook `Shear!E25`); the crack-width `N*` is negative in tension
(`Detailed!E144`). Bars in each face are given as a number, centres or an area.

## Differences from the source workbook

| Workbook behaviour | This module | Why |
| --- | --- | --- |
| Many failures appear only as text (`Top bar cts N.G.`, `Error - Live load exceeds the dead load`, D >= 750 mm fitments, simplified-method limits) | Each counts towards `worstUtil` | A calculation outside its method or detailing rules must not report OK |
| `ku > 0.36` is a warning | `ductility` utilisation with the Tedds AS3600-2018 compression-steel alternative | Cl 8.1.5 is mandatory |
| Simplified `kv = min(kvo, 0.15)` without minimum fitments (`Shear!E85`) | `min(kvo, 0.10)` | Conservative; matches `SlabShear!E32` and the column module (D1, C2) |
| Wider fitment spacing whenever "Increase limit = Y" | Only where `V* <= phiVu.min` | Cl 8.3.2.2 condition (D2) |
| Negative-moment crack width limits `hc.ef` by `kd` (`Detailed!J129`) | Limits it by `D - kd` | Workbook defect (D3, C3) |
| Calculated deflection uses `bef` for `Icr` whenever `k < Tf` (a ratio against a length, `Defl!D53`) | Uses `kd < Tf` | Workbook defect (D4, C7) |
| Compression `phi = 0.6` in the longitudinal-force check (`Settings!K315`) | 0.65 | AS 3600:2018 Table 2.2.2 (D6) |
| `k5 = 9999` for `f'c > 100` MPa | Manual creep coefficient required | Cl 3.1.8.3 range (D9) |
| `CalcAst2009` returns 0 when the moment is unattainable | Returns infinity | Avoids a false pass on minimum steel (D7) |
| `Asv > Asv.max` counted as a shear failure | Warning only | Excess fitments are ineffective, not unsafe (D10) |

TECHNICAL-README §5 gives the complete list (D1 to D18).

## Commands

The module is not yet in `suite.toml`, so `python -m tooling check concrete-member` does not
find it. Run these from the suite root instead:

```powershell
$Python = Join-Path $PWD '.venv\Scripts\python.exe'
$env:PYTHONPATH = "$PWD;$PWD\calculations\concrete\concrete_member\src"
& $Python -m unittest discover -s calculations/concrete/concrete_member/tests -v
& $Python -c "from ic_concrete_member import headless; from packages.innocalc_sdk import check_contract; print(check_contract(headless))"
& $Python -m ic_concrete_member.dev --validate
& $Python -m ic_concrete_member.dev calculations/concrete/concrete_member/examples/worked-example.json --html artifacts/concrete-member/worked-example.html
```

## Evidence

| Artefact | Location |
| --- | --- |
| Technical review | `TECHNICAL-README.md` |
| Retained baseline | `src/ic_concrete_member/data/workbook-baseline.json` |
| Source provenance | `reference/README.md` |
| Worked example | `examples/worked-example.json`, rendered to `artifacts/concrete-member/worked-example.html` |
| Tests | `tests/test_engine.py`, `tests/test_release_gate.py` |

## Outstanding release gates

1. Confirm the simplified-method `kv` cap (C2) and the crack-width coefficients (C4)
   against the printed AS 3600:2018 Amdt 2.
2. Obtain an independent engineering review and record it in `reference/README.md`.
3. Add a worked example from a source other than Structural Toolkit (for example Warner,
   Foster and Kilpatrick, *Reinforced Concrete Basics*).
4. Name a maintainer, register the module in `suite.toml` and complete manager and PDF acceptance.
