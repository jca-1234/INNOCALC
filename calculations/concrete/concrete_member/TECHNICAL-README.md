# Technical Review: Concrete Beam and Slab Design

| | |
| --- | --- |
| Module | `concrete-member` `v0.0.1` |
| Source | Structural Toolkit CONCRETE MEMBER V5.13, `Concrete_Member_513.xls` |
| Standard | AS 3600:2018 incl. Amendments 1 and 2; AS/NZS 1170.0:2002 |
| Reviewer | Automated transcription and review. **An independent engineer still needs to review this module.** |
| Date | 24 September 2026 |
| Overall opinion | **Sound in method; not yet suitable for release.** The strength, shear, torsion and deemed-to-comply methods are standard AS 3600:2018 methods, and the transcription is exact: 483 saved values agree to `1e-9`. Seven workbook defects have been corrected (C3, C7, C8, C10, C11, C12, C15). Several failures the workbook shows only as text now count towards the overall result. Two points still need checking against the printed Amendment 2 before release: the simplified `kv` cap (C2) and the crack-width formula (C4). The `SlabShear` sheet has a **High** defect (C1) and was not transcribed. |

## 1. What the calculation does

The module checks one cross-section. It transcribes the `Design`, `Detailed`, `Shear`, `Defl`,
`Creep&Shrink`, `BeamDefl`, `SlabDefl` and `Secondary` sheets and the VBA section routines.
It runs in eight steps.

1. **Section and reinforcement.** The section is a slab strip (1000 mm wide), a rectangle, or
   a T or L beam.
   * The effective flange is `bef = min(Bf, bw + 0.2 a)` for T-beams and `min(Bf, bw + 0.1 a)`
     for L-beams, with `a = mke Lm` (Cl 8.8.2).
   * Bars in each face can be given as a number, centres or an area. They are placed in
     layers at the stated clear spacings, and the layer centroid offset gives `ds` and `dc`.
     This follows the VBA `centroid` routine.
2. **Bending strength (Cl 8.1).** The rectangular stress block has
   `alpha2 = max(0.85 - 0.0015 f'c, 0.67)` and `gamma = max(0.97 - 0.0025 f'c, 0.67)`.
   * Compression steel is included, first assuming it yields, then with its strain
     `0.003 (kud - dc)/kud`. For T-beams the block may lie in the flange or extend into the web.
   * `phi = 1.24 - 13 kuo/12`, limited to 0.65 to 0.85, for Class N; 0.65 for Class L
     (Table 2.2.2).
   * `Mu = 0` when `ku > kub = 0.003/(0.003 + fsy/Es)`, as in the workbook.
3. **Ductility and minimum steel.**
   * `kuo <= 0.36`. Beyond that, `Asc >= 0.01 b kuo do` (Cl 8.1.5; the Tedds rule).
   * The minimum strength is `(Muo)min = 1.2 Z f'ct.f`, with `Z` taken from the uncracked
     section including the steel. The steel area needed for it comes from `CalcAst2009`.
   * The deemed-to-comply area is `alpha.b (D/d)^2 f'ct.f/fsy b d` (Cl 8.1.6.1 for beams,
     Cl 9.1.1 for slabs). There are separate T-beam expressions.
   * The basis is the deemed area (`D`), the actual area (`A`) or the lesser of the two (`M`).
4. **Crack control (Cl 8.6.1, 8.6.2, 9.5).**
   * The cracked transformed section follows the VBA routines `CalcIcrkna` and `CalcIcrkk`.
     It gives `sigma.scr` at `Ms*` and `sigma.scr1` at `Ms1*`.
   * The limits come from Table 8.6.2.2(A)/(B) or Table 9.5.2.1(A)/(B), interpolated as in
     `CalcTable`, and `0.8 fsy`.
   * Bar centres are limited to 300 mm, or `min(2D, 300)` for slabs.
   * The optional crack width (Cl 8.6.2.3) is `w = sr.max (eps.sm - eps.cm)`, where:
     * `sr.max = min(1.3 (D - kd), 3.4 c + 0.3 k1 k2 db/rho.eff)`;
     * `eps.sm - eps.cm = max([sigma.s - 0.6 fct.m/rho.eff (1 + n.e rho.eff)]/Es + eps.cs, 0.6 sigma.s/Es)`;
     * `n.e = (1 + phi.cc) Es/Ec`.
5. **Shrinkage and creep (Cl 3.1.7, 3.1.8).**
   * Shrinkage is `eps.cs = eps.cse + eps.csd`, with `k1`, `k4` and the basic drying strain
     either standard (800 x 10^-6) or tested.
   * Creep is `phi.cc = k2 k3 k4 k5 phi.cc.b`, with the basic creep coefficient from
     Table 3.1.8.2. Either value may instead be entered manually.
6. **Shear and torsion (Cl 8.2, 8.3).**
   * `dv = max(0.72 D, 0.9 d)`.
   * General method: `eps.x = min((|M*|/dv + V* - 0.5 N*)/(2 Es Ast), 0.003)`, with `N*`
     positive in compression. `M*` is at least `V* dv`, and a negative strain is recomputed
     with the concrete area `Act`. Then `kv = 0.4/(1 + 1500 eps.x) x 1300/(1000 + kdg dv)`
     (the second factor applies only when `Asv < Asv.min`) and `theta.v = 29 + 7000 eps.x`.
   * Simplified method: `kv = min(200/(1000 + 1.3 dv), 0.10)` without minimum fitments, or
     0.15 with them; `theta.v = 36 deg`.
   * `Vuc = kv bv dv sqrt(f'c)`, with `sqrt(f'c) <= 8`.
     `Vus = Asv fsy.f dv/s (sin alpha cot theta + cos alpha)`.
     `Vu.max = 0.55 [0.9 f'c bv dv (cot theta + cot alpha)/(1 + cot^2 theta)]`.
   * The fitment requirement follows Cl 8.2.1.6. It uses the workbook's separate
     no-fitment strength (`Settings!X459:X481`). Minimum area is `0.08 sqrt(f'c) bv s/fsy.f`.
     Spacing is limited to `min(0.5 D, 300)`, or `min(0.75 D, 500)` where
     `V* <= phiVu.min`. Transverse spacing is limited to `min(D, 600)`.
   * Torsion: `Tcr = 0.33 sqrt(f'c) Acp^2/uc sqrt(1 + sigma.cp/(0.33 sqrt(f'c)))`,
     `Tus = 2 Ao Asw fsy.f/s cot theta` and minimum torsion steel (Cl 8.2.5, 8.3.3).
   * Web crushing is checked on the combined shear and torsion stress.
   * The additional longitudinal tension and compression come from Cl 8.2.8 (the workbook
     cites Cl 8.2.7).
7. **Deflection.**
   * Deemed to comply (Cl 8.5.4, 9.4.4.1): `d.min = Lef/[k1/k2 (Delta/Lef) b Ec/Fd.ef]^(1/3)`
     for beams, and `Lef/[k3 k4 ((Delta/Lef) Ec/Fd.ef)^(1/3)]` for slabs, where
     `Fd.ef = (1 + kcs) g + (psi.s + kcs psi.l) q`. The method requires `q <= g`.
   * Optional calculated deflection (Cl 8.5.3), at the left end, midspan and right end:
     `Ief = min(Icr/[1 - (1 - Icr/Ig)(Mcr/Ms*)^2], Ief.max)`, with
     `Mcr = (f'ct.f - sigma.cs) Z` and `kcs = max(2 - 1.2 Asc/Ast, 0.8)`. The gross elastic
     deflections from the analysis are scaled by `Ig/Iav`.
8. **Detailing.** The optional groups check lateral restraint spacing for slenderness
   (Cl 8.9.2/8.9.3) and slab shrinkage and temperature steel (Cl 9.5.3).

## 2. Validation undertaken

| Check | Method | Outcome |
| --- | --- | --- |
| Transcription fidelity | Replayed the saved workbook state against 483 cached numeric values, from 492 cell mappings across seven sheets (`data/workbook-baseline.json`), at relative tolerance `1e-9` | **All 483 agree.** The 12 departure cells are recorded with both values |
| Bending | Hand calculations: a singly reinforced rectangle, a doubly reinforced section with yielding compression steel, a T-beam with the stress block in the web, effective flange width, bar layers and centroid (`tests/test_engine.py`) | Agree to `1e-9` |
| Minimum steel and ductility | Hand calculation of the deemed-to-comply area; the Tedds compression-steel rule for `kuo > 0.36` | Agree |
| Shear and torsion | Hand calculation of the general method with fitments (`eps.x`, `kv`, `theta.v`, `Vuc`, `Vus`, `Vu.max`, `phiVu`), the simplified cap, rejection of wider spacing, `Tus`, and compression `phi` | Agree |
| Serviceability | Hand calculations of the cracked-section `sigma.scr`, the deemed-to-comply beam and slab `d.min`, the live-load limit and the crack-width tension depth | Agree |
| Robustness | 72-case sweep (4 section types x 2 moment signs x 3 strengths x 3 shear levels) plus the saved example (`validation.self_check`). Checks for NaN or negative utilisations, `worstUtil` consistency, `phi` within 0.65 to 0.85, `phiVu <= phiVu.max`, no `OK` status for a failing member, repeatability and no input mutation. A further 17 variants were rendered, with no NaN or double-escaped text | Pass |
| Invalid input | 23 rejected inputs, case folding of text options, `f'c > 100` MPa without manual creep, an unattainable moment at a deflection position | `ValueError` as intended |
| Contract | `packages.innocalc_sdk.check_contract` and `headless.validate()` | `ok` |
| Tests | `tests/test_engine.py` and `tests/test_release_gate.py` | 31 pass |

### 2.1 Comparison with Tedds

The independent benchmark is Tekla Tedds *RC member design (AS3600)*, which implements
AS 3600-2018 Amdt 1 and 2 (`C:/CODING/Tedds/_TEDDS_MDs/calculations/AU/RC member design-AS3600-si-enau.md`).
Two other Tedds files were reviewed and not used. The AustRC *RC beam deflection* set uses the
superseded AS 3600-2001 Branson form `Icr + (Ig - Icr)(Mcr/Ms)^3`. The general
*RC beam torsion design* has no AS 3600 content.

| Aspect | Workbook | Tedds | Adopted here |
| --- | --- | --- | --- |
| Stress block, `phi` for bending, `kub` | 2018 `alpha2`, `gamma`, `1.24 - 13 kuo/12` | Same | Workbook form, which agrees with Tedds |
| Ductility, `kuo > 0.36` | Warning only | Requires `Asc >= 0.01 b kuo do` | **Adopted** as the `ductility` utilisation |
| Minimum strength | `(Muo)min = 1.2 Z f'ct.f`, deemed `alpha.b` areas | Same `(Muo)min`; designs for `max(M*, 0.8 (Muo)min)` against `phi Muo` | Workbook form. The Tedds `0.8` factor matches `phi = 0.8` only and is slightly unconservative when `phi = 0.85`. **Not adopted** |
| General `kv`, `theta.v`, `kdg` | `kdg = 2.0` for `f'c > 65` MPa or lightweight concrete, else `max(32/(16 + dg), 0.8)` | Same (lightweight taken as density `<= 2100 kg/m3`) | Workbook form, which agrees with Tedds. The `concrete-column` module uses `kdg = 1.0` for `f'c > 65`. That module was not modified (see C21) |
| Simplified `kv` without minimum fitments | `min(kvo, 0.15)` (`Shear!E85`, `Settings!X464`); `SlabShear!E32` uses 0.10 | `min(kvo, 0.15)` | **0.10** (conservative, D1). Needs confirmation against the printed Standard (C2) |
| Simplified-method limits | Text error (`Settings!K323`) | Checks `f'c <= 65`, `dg >= 10`, `fsy <= 500` | **Adopted** as the `shearMethod` utilisation |
| `Vu.max` | `0.55 [0.9 f'c bv dv (cot theta + cot alpha)/(1 + cot^2 theta)]` with the design `theta.v` | Same expression, but `theta.v` from `eps.x` with `M* = V* dv` (the least moment) | Workbook form. Tedds' choice is more conservative but is not required by the Standard. **Not adopted**; noted |
| Shear `phi` | 0.75, or 0.7 when `Asv < Asv.min` or for Class L fitments | 0.75, or 0.7 when `V* >= Vu.max` (one variant also uses `Asv < Asv.min`) | Workbook form |
| Wider fitment spacing | Applied whenever "Increase limit = Y"; `Shear!K52` reports validity as text | Applied only where `V* <= phiVu.min` | **Adopted** (D2) |
| Crack-control stress tables | Table 8.6.2.2 and 9.5.2.1 values in `Settings`, interpolated by `CalcTable` | Same tabulated values | Workbook form, which agrees with Tedds at the tabulated points |
| `Ief`, `Ief.max`, `kcs` | 2018 Bischoff form, `0.6 Ig` below `rho = 0.005`, `max(2 - 1.2 Asc/Ast, 0.8)` | Same | Workbook form, which agrees with Tedds |
| Fire resistance (Section 5) | Not checked | Axis distance and minimum dimensions | Not adopted; future work |
| Minimum clear bar spacing | Not checked | Checked | Not adopted; future work |

## 3. Opinion on the theory

* **Bending.** The rectangular stress block, the compression steel treatment and the T-beam
  flange/web split are standard (WRH Eq 4.49 and 4.55; RCB Eq 3.78). The 2018 `phi` and
  ductility rules are applied correctly. Setting `Mu = 0` when `ku > kub` is a conservative
  simplification of an over-reinforced section.
* **Minimum strength.** `(Muo)min` with `Z` from the uncracked transformed section is
  correct. The workbook's basis option `M` (the lesser of the deemed and actual areas) follows
  Cl 8.1.6.1, which allows either.
* **Shear and torsion.** The Cl 8.2 general method is transcribed faithfully. So are the
  torsion interaction and the Cl 8.2.8 longitudinal force. The workbook's separate
  "no-fitment" `Vuc` for the fitment requirement is a sound reading of Cl 8.2.1.6, because it
  uses the `kdg` size-effect factor.
* **Crack control.** The stress-based check (Cl 8.6.2.2) is correct. The calculated crack
  width follows the Eurocode 2 Cl 7.3.4 structure, which Amendment 2 introduced. Some of its
  coefficients could not be confirmed (C4).
* **Deflection.** The deemed-to-comply and calculated methods are the Standard's methods.
  Scaling analysis deflections by `Ig/Iav` assumes that the analysis used gross section
  properties. You need to confirm that on input.
* **Scope.** A single section is checked. Envelope actions, anchorage and curtailment are
  outside the scope. You need to check them separately.

## 4. Areas of concern

| ID | Severity | Concern | Status in this module | Recommended action |
| --- | --- | --- | --- | --- |
| C1 | **High** | `SlabShear!E34` computes `Vuc = kv bv dv MAX(SQRT(fc), 8)`. `MAX` should be `MIN`: Cl 8.2.4.1 limits `sqrt(f'c)` to 8 MPa, so every slab with `f'c < 64` MPa is credited with `sqrt(f'c) = 8`. | `SlabShear` not transcribed. Slab shear uses the `Shear` sheet method with the correct cap | Correct the workbook. Withdraw the `SlabShear` sheet |
| C2 | **High** | The simplified `kv` without minimum fitments is `min(kvo, 0.15)` in `Shear!E85` and `Settings!X464`, but `min(kvo, 0.10)` in `SlabShear!E32`. The `concrete-column` module uses 0.10; Tedds uses 0.15. | 0.10 (D1). Changes `Settings!X464` from 0.1217 to 0.10 in the saved example | Confirm Cl 8.2.4.3 against the printed Amdt 2 and update `KV_SIMPLE_CAP` if needed |
| C3 | Medium | `Detailed!J129` limits the negative-moment `hc.ef` by `dna_n` (`kd`, the compression depth) instead of the tension depth `D - kd`. The crack width is underestimated: 0.385 mm against 0.698 mm in the saved example. | Corrected (D3). Changes `Detailed!J129:J131, J138:J141, J160:J164` and `Design!G68` | Correct the workbook |
| C4 | Medium | The crack width uses `sr.max = 3.4 c + 0.3 k1 k2 db/rho.eff` (`Detailed!D160`). Eurocode 2 uses `0.425 k1 k2`. It takes `sr.max = min(1.3 (D - kd), ...)` at all spacings, where EC2 uses `1.3 (h - x)` only above `5 (c + db/2)`. It also adds `+eps.cs` to `eps.sm - eps.cm`. None of these could be confirmed against the printed Amdt 2. | Reproduced. Optional group, off by default | Confirm against the printed Cl 8.6.2.3 before relying on the crack width |
| C5 | **High** | Many failures appear only as text. Examples: `Design!I8` `Top bar cts N.G.`; `Design!B11` `Ast.min > Ast`; `Design!B10` `fscr > Fscr`; the deemed-to-comply `q > g` error; `Settings!K323` for the simplified-method limits; `ku > 0.36`. The saved example shows `No Good` only for strength, although it fails six other checks. | Each counts towards `worstUtil` | None, beyond sign-off |
| C6 | Low | VBA `CalcIcrkna` drops `Asc` when `dsc < kd`, so compression steel is excluded from the neutral axis, but `CalcIcrkk` still includes `Asc` in `Icr` about that axis. This is internally inconsistent. | Reproduced; the effect is small | Rewrite both routines together |
| C7 | Medium | `Defl!D53` selects `bef` for `Icr` when `D42 < Tf`, but `D42` is the dimensionless `k`, not `kd`. A positive-moment T-beam therefore always uses `bef`, even with the neutral axis in the web, while `kappa` is normalised to `bw`. `Icr` and `Ief` are overestimated and the deflection is unconservative. | Corrected: `kd < Tf` (D4). No effect on the rectangular saved example | Correct the workbook |
| C8 | Medium | `BeamDefl!E30` shows the positive moment using the `SlabDefl` load and span (`w_star_s`, `L_s`). | Uses the beam load and span (D8). Display only | Correct the workbook |
| C9 | Low | `BeamDefl!D43` chooses the `Ec` formula on `f'c <= 40`, but applies it to `fcmi`. | Uses the `Defl!H18` form, which tests `fcmi` (D5). They agree for the saved example | Correct the workbook |
| C10 | Medium | `Creep&Shrink!E55` sets `k5 = 9999` for `f'c > 100` MPa, which gives a meaningless creep coefficient. | Requires a manual `phi.cc` above 100 MPa (D9) | Add the Cl 3.1.8.3 high-strength provisions if they are needed |
| C11 | Medium | `Settings!K315` holds `phi_c_o = 0.6`, the AS 3600-2009 compression value. Table 2.2.2 (2018) gives 0.65. It is used in the Cl 8.2.8 longitudinal compression check. | 0.65 (D6) | Correct the workbook |
| C12 | Medium | The wider fitment spacing (`0.75 D`, 500 mm) is applied whenever "Increase limit = Y". `Shear!K52` reports `Not Valid` as text only. | Applied only where `V* <= phiVu.min` (D2) | None, beyond sign-off |
| C13 | Low | `phi.cc.b` is taken from Table 3.1.8.2 as a step to the next tabulated grade, not interpolated. For intermediate strengths this is slightly unconservative. | Reproduced | Interpolate, or confirm the intended use |
| C14 | Medium | The saved state selects tested drying shrinkage but leaves `eps.csd.b*` blank, so `eps.cs` is autogenous only (90 x 10^-6). | Reproduced; the module warns | Enter a tested value or select the standard value |
| C15 | Low | `CalcAst2009` returns 0 when the moment cannot be reached. `Ast.min = min(deemed, 0)` can then pass. | Returns infinity (D7). A deflection position with an unattainable moment is rejected | None |
| C16 | Low | `Settings!P39` counts `Asv > Asv.max` as a shear failure. Excess fitments only make `phiVu` capped by `phiVu.max`; they are not unsafe. | Warning only (D10) | None |
| C17 | Low | `Settings!P39` counts fitment spacing and transverse spacing even when the user has waived them. | Waivers are honoured, with a warning (D13) | None |
| C18 | Low | `Shear!E166` computes `Tcr` with `sqrt(f'c)` uncapped, whereas the shear terms cap it at 8 MPa. | Reproduced | Confirm the Cl 8.2.5 intent |
| C19 | Low | Clause citations mix editions. For example, the longitudinal force is cited as Cl 8.2.7 (2018 Cl 8.2.8). | The report uses 2018 numbering where confident | None |
| C20 | Low | The minimum shear fitments for `D >= 750` mm (Cl 8.2.1.6) are reported as text but not included in the shear ratio. | Included in `shearDetailing` (D11) | None |
| C21 | Low | The `concrete-column` module uses `kdg = 1.0` for `f'c > 65` MPa, whereas this workbook and Tedds use 2.0. | Not modified (outside scope) | Review `concrete-column` |
| C22 | Low | The additional longitudinal force from shear is calculated only when fitments are effective (`Asv_v <> 0`). | Reproduced | Confirm the Cl 8.2.8 intent for members without fitments |
| C23 | Low | Torsion ratios use the flag value 99 (`Settings!P41`). | Finite ratios `Asw.min/Asw` and `s/s.max` (D14) | None |
| C24 | Low | `Ief = Icr` where `Ms* = 0` at a position (`Defl!D55`). This is odd but conservative. | Reproduced. Also used when `Icr = 0`, to avoid dividing by zero | None |
| C25 | Medium | There is no independent worked example. The saved example is a failing member with one top bar, so it is a weak test of the positive-moment and T-beam paths. | Added hand checks and the 72-case sweep | Obtain a textbook example (for example Warner, Foster and Kilpatrick) and run the same inputs in Tedds |

## 5. Deliberate departures from the workbook

| ID | Departure | Cells affected |
| --- | --- | --- |
| D1 | Simplified `kv` cap without minimum fitments is 0.10, not 0.15 (C2) | `Settings!X464` |
| D2 | Wider fitment spacing only where `V* <= phiVu.min` (C12) | None in the saved example |
| D3 | Negative-moment crack width `hc.ef` limited by `D - kd` (C3) | `Detailed!J129`, `J130`, `J131`, `J138`, `J139`, `J141`, `J160`, `J161`, `J164`, `Design!G68` |
| D4 | Calculated-deflection `Icr` uses `bef` only when `kd < Tf` (C7) | None in the saved example |
| D5 | Deemed beam `Ec` uses the `fcmi` test (C9) | None in the saved example |
| D6 | Compression `phi = 0.65` (C11) | None in the saved example |
| D7 | `CalcAst2009` returns infinity when the moment cannot be reached (C15) | None in the saved example |
| D8 | `BeamDefl` display moments use the beam load and span (C8) | `BeamDefl!E30` |
| D9 | `f'c > 100` MPa requires a manual creep coefficient (C10) | None |
| D10 | `Asv > Asv.max` is a warning, not a failure (C16) | None |
| D11 | `D >= 750` mm minimum fitments counted in `shearDetailing` (C20) | None |
| D12 | Every check counts towards `worstUtil`, including those the workbook reports as text (C5), with a `ductility` utilisation (Tedds rule) and a `shearMethod` utilisation | None |
| D13 | Shear detailing honours the spacing and transverse waivers (C17) | None |
| D14 | Torsion ratios are finite, with no 99 flags (C23) | None |
| D15 | Bending and shear actions are separate inputs, as in the workbook's manual mode. The Analysis link is not provided | None |
| D16 | Bars are given by an explicit mode (number, centres or area), not the workbook's value-range code (`< 75` number, `<= 600` centres, `> 600` area) | None |
| D17 | Where there is no tension steel, the crack-width `sr2` is infinite and `sr.max = 1.3 (D - kd)`, not `#DIV/0!` | None |
| D18 | The Preview drawing is replaced by the report's section and strain figure | None |

## 6. Future development

1. Confirm the simplified `kv` cap (C2) and the crack-width coefficients (C4) against the
   printed AS 3600:2018 Amdt 2.
2. Add an independent worked example and a Tedds run on the same inputs (C25).
3. Deferred workbook features:
   * the `Analysis` and `Results` link: envelope actions at discrete positions and automatic
     critical locations;
   * `Layers` custom bar layouts and the `CalcPure` strain-compatibility routine;
   * `SlabShear`, after correcting C1;
   * `SlabPrelim` preliminary slab sizing;
   * exposure classification (Table 4.10.3.2, VBA `calcexposure4`) and cover checks;
   * the Cl 9.7 moment-resisting width for concentrated loads (`Design!K62:N70`);
   * prestress (`Pv`, `Apt`, duct reductions to `bv`);
   * the AS 5100.5 options other than the `Act` definition (bridge minimum shear, `kc`
     and combinations);
   * automatic ductility class and mesh detection, and the extended layer and bar limits
     (`layermc2`);
   * the manual `gamma` override and the support-face distance options.
4. Add fire resistance (AS 3600 Section 5), minimum clear bar spacing, anchorage and
   curtailment.
5. Resolve the `CalcIcrkna`/`CalcIcrkk` inconsistency (C6) and interpolate `phi.cc.b` (C13).
6. Review `kdg` for `f'c > 65` MPa in the `concrete-column` module (C21).
