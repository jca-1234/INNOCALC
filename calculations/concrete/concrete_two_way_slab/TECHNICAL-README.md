# Technical Review: Concrete Two-Way Slab Design

| | |
| --- | --- |
| Module | `concrete-two-way-slab` `v0.0.1` |
| Source | Structural Toolkit TWO-WAY SLABS V5.02 (revision 5.02f), `Concrete_TwoWaySlab_502.xls` |
| Standard | AS 3600:2018 incl. Amendments 1 and 2; AS/NZS 1170.0:2002 |
| Reviewer | Automated transcription and review. **An independent engineer still needs to review this module.** |
| Date | 24 September 2026 |
| Overall opinion | **Sound in method; suitable for release after independent review.** The engineering method is standard and the transcription is exact. All 270 coefficient values agree with an independent AS 3600 transcription (Tedds). Two workbook logic defects have been corrected. Optional flexure and shrinkage checks have been added, following the Tedds AS 3600-2018 slab calculation. |

## 1. What the calculation does

The module applies the AS 3600 simplified method (Cl 6.10.3) to a rectangular slab panel.
Beams or walls support the panel on all four sides. Each edge is either continuous or
discontinuous. The calculation runs in five steps:

1. **Actions.** It forms `Fd = max(1.35 g, 1.2 g + 1.5 q)` from self weight
   (`25 kN/m3 x th`), superimposed dead load and live load (AS/NZS 1170.0 Cl 4.2.2). It
   takes the serviceability factors `psi_s` and `psi_l` from AS/NZS 1170.0 Table 4.1 for
   normal, storage and roof use.
2. **Moment coefficients.** It builds an edge code from the number of discontinuous long
   and short edges.
   * Class N reinforcement with redistribution uses Table 6.10.3.2(A), or optionally the
     closed-form Warner, Rangan and Hall (WRH) coefficients.
   * Class L reinforcement, or a slab without redistribution, uses Table 6.10.3.2(B).
   * Coefficients are interpolated linearly in Ly/Lx between 1.0 and 2.0.
3. **Design moments.**
   * Positive midspan moments are `Mx* = betax Fd Lx^2` and `My* = betay Fd Lx^2`.
   * At a continuous edge, the negative moment is `1.33 M*` for Table A, or `alpha M*` for
     Table B.
   * At a discontinuous edge, the negative moment is `0.5 M*` for Table A, or `0.8 M*` for
     Table B.
4. **Minimum strength reinforcement.** The minimum area is
   `Ast.min = 0.19 (D/d)^2 f'ct.f / fsy b d` for slabs supported on four sides
   (Cl 9.1.1(b)).
5. **Deflection.** This is the deemed-to-comply span-to-depth check
   `d.min = Lef / (k3 k4 [(Delta/Lef) Ec / Fd.ef]^(1/3))`, where:
   * `Fd.ef = (1 + kcs) g + (psi_s + kcs psi_l) q` for total deflection;
   * `Fd.ef.inc = kcs g + (psi_s + kcs psi_l) q` for incremental deflection;
   * `kcs = 2 - 1.2 Asc/Ast >= 0.8`;
   * `k4` is interpolated in Ly/Lx.

## 2. Validation undertaken

| Check | Method | Outcome |
| --- | --- | --- |
| Transcription fidelity | Replayed the saved workbook state against 51 cached cell values in `data/workbook-baseline.json`, with relative tolerance `1e-9` | All 51 agree exactly |
| Interpolation logic | Hand-checked Table B at Ly/Lx = 1.25, the step at 2.0, values below 1.0, and k4 at 1.375 and 3.0 (`tests/test_engine.py`) | Agree |
| Closed-form coefficients | Compared the WRH formula with Table 6.10.3.2(A) for all 9 edge codes and 8 ratios | Within -3.65 % to +3.06 % of Table A. Exact at the all-discontinuous extreme (`betay = 1/18`, `betax = 0.111`) |
| Strength combination | Hand calculation for a simply supported 6 m square panel | Agrees |
| Dimensional consistency of `d.min` | `Ec` in MPa. `Fd.ef` converted from kPa to MPa (N/mm2) by /1000. The cube-root term is dimensionless and `d.min` has units of `Lx` | Consistent |
| Physical sense | 96-case sweep over spans, edge codes, classes and strengths. Checked that moments are positive, continuous-edge moments exceed midspan moments, results repeat identically and inputs are not mutated | Pass |
| Table B against Table A | Table B positive coefficients are 71 % to 96 % of Table A at Ly/Lx = 1.0. This is expected: without redistribution, the elastic distribution sends more moment to the supports | Plausible |
| Cracked neutral axis | Checked `ku` against the transformed-section quadratic for a doubly reinforced section (WRH Eq 5.22) | Correct form |
| Independent benchmark: coefficient tables | Compared all 270 values of Table 6.10.3.2(A) `betax`/`betay`, Table 6.10.3.2(B) `betax`/`betay` and `alphax`/`alphay` with the Tedds data tables `AU3600-01-7.3.2` and `AU3600-01-7.3.2(B)`, after mapping Tedds' edge order onto the edge codes | **0 differences** |
| Independent benchmark: k4 | Compared with the Tedds table `AU3600-01-9.3.4.2` | Identical for all 9 edge conditions. Tedds' extra 1.10 column is consistent with linear interpolation. Tedds agrees with the workbook's 5.01 correction for 1 short edge discontinuous |
| Independent benchmark: method | Compared with Tedds *RC slab design (AS3600)* 1.0.21, which implements AS 3600-2018 Amdt 1 and 2 (`C:/CODING/Tedds/_TEDDS_MDs/calculations/AU/AU RC slab design.md`) | Same edge factors (1.33 and alpha at continuous edges; 0.5 and 0.8 at discontinuous edges). Same `Fd.ef`, `k3 = 1.0` and span-to-depth form. Same applicability rule, `q <= g`, compared with the total dead load |

### 2.1 Comparison with the Tedds AS 3600-2018 slab calculation

| Aspect | Workbook | Tedds | Adopted here |
| --- | --- | --- | --- |
| Coefficient tables | Transcribed, with author notes | Independent data tables | Workbook values, now shown to agree with Tedds |
| `q <= g` rule | `wll > wdl + wsdl` (counts `wsdl` twice) | `q > g` with total dead load | Tedds form |
| `kcs` | `2 - 1.2 Asc/Ast >= 0.8` | Fixed at 2.0 | Workbook form, which is permitted and less conservative when compression steel is present |
| `fcmi` | Curve fit, or `f'c` | Stepped Table 3.1.2 approximation | Workbook form. The two differ by less than 1 MPa across 25 to 100 MPa |
| Effective depth for deflection | `th - cover - db/2` | `dxb` of the short-span bottom bars, as outer or inner layer | Workbook form. The flexure group assumes the short-span bars are the outer layer |
| Flexural capacity | Not checked | Checked at midspan and at every edge: `ku <= 0.36`, Table 2.2.2 `phi`, minimum steel and bar spacing | **Added** as the optional `flexure` group |
| Shrinkage reinforcement, Cl 9.4.3 | Not checked | `0.75 p D` in each direction, applied to every location | **Added** as the optional `shrinkage` group |
| Slab shear | Not checked | Uses the AS 3600-2009 `beta1 beta2 beta3 fcv` expression | **Not adopted.** That expression was superseded by the 2018 Cl 8.2.4 method |
| Fire axis distance | Not checked | Table 5.5.2 axis distance | Not adopted; future work |

## 3. Opinion on the theory

* **Simplified method.** Cl 6.10.3 is a long-established and well-understood method. The
  workbook's edge-code scheme (`long + 3 short + 1`) matches the nine table rows. Its
  choice between Table A and Table B follows the Standard's intent: Class L reinforcement
  may not be redistributed.
* **Closed-form coefficients.** These come from WRH and the AS 3600-1994 era. They are not
  in AS 3600:2018. For a panel with all edges continuous, they give coefficients up to
  3.65 % below Table A, which is slightly unconservative. They are acceptable only as a
  comparison. The module keeps Table A as the default.
* **Deflection.** The deemed-to-comply rule is the Standard's method. The workbook's `kcs`
  and `Fd.ef` expressions are correct. The module uses the short span as the effective span.
  That is the right quantity for a two-way slab, provided you enter effective spans, not
  clear spans.
* **Minimum reinforcement.** The coefficient 0.19 for slabs supported on four sides is
  correct for Cl 9.1.1(b).

## 4. Areas of concern

| ID | Severity | Concern | Status in this module | Recommended action |
| --- | --- | --- | --- | --- |
| C1 | Medium (was High) | The workbook author annotated the Standard's tables. `Settings!AB65` reads "2.04 in code appears to be an error", `Settings!AA69` reads "was 1.87", and `Settings!AA66` reads "Confirmed: changed in 2009 code". | All 270 values agree with Tedds' independent tables, including 2.10 at code 1, Ly/Lx = 1.3 | A final check against the printed AS 3600:2018 Amdt 2 remains good practice, because both transcriptions could share a source. The risk is now low. |
| C2 | **High** | The applicability test `wll > wdl + wsdl` counts superimposed dead load twice, because `wdl` already includes `wsdl`. The workbook therefore accepts live loads up to `wdl + wsdl`, which is unconservative. | Corrected to `wll / wdl <= 1`. Tedds uses the same rule, `q > g` | None, beyond sign-off. |
| C3 | **High** | The workbook computes `Ast.min` but never compares it with the steel provided. A slab below minimum steel is not flagged. | Added as `minimumSteel` | None, beyond sign-off. |
| C4 | Medium | Table B has a step at Ly/Lx = 2. For example, `betax` jumps from 0.085 to 0.125 for code 3. The "> 2" column represents one-way action. A small change in span can change the moment by 47 %. | Reproduced, with a warning above 2.0 | Consider requiring a one-way design for Ly/Lx > 2, or confirm how the Standard intends this column to be used. |
| C5 | Low | Clause numbers are inconsistent. `Settings!R77` says "Table 9.3.4.2" (AS 3600-2009 numbering), but the calculation sheet cites Cl 9.4.4.2 and Table 9.4.4.2. Tedds' 2018 calculation also cites Cl 9.4.4 and Table 9.4.4.2. | Uses the 2018 citations | None. |
| C6 | Low | The discontinuous-edge factor for Table B (`0.8 M*`) and the continuous-edge factor 1.33 for Table A come from the workbook. | Tedds uses the same factors | None. |
| C7 | Medium | The conditions for the simplified method (uniform load, adjacent-span ratios, corners held down, and torsional corner reinforcement to Cl 9.1.3.3) and the adjacent-span conditions for deflection are not checked. | Listed as assumptions | Add explicit applicability inputs or confirmations in a future version. |
| C8 | Low | With `useFcmi = N` (the workbook default), `fcmi` is taken as `f'c`. This underestimates `Ec` by about 3 % to 9 % and makes `d.min` about 1 % to 3 % conservative. The `fcmi` curve fit is labelled "+ 0.0614" on the sheet but uses "- 0.0614". This is negligible. | Reproduced | Consider using Table 3.1.2 `Ec` values directly. |
| C9 | Low | The test for compression steel in the tension zone is `kud - db/2 < dc`. The tension bar diameter has no role in that test. The logical test is `kud < dc`. | Reproduced | Review the intent. The effect on `kcs` is marginal. |
| C10 | Low | Self weight uses a fixed 25 kN/m3, but the density input (default 2400 kg/m3) affects only `Ec`. For lightweight concrete these two are inconsistent. | Reproduced | Derive self weight from density plus a reinforcement allowance. |
| C11 | Low | The workbook's saved example has Ly/Lx = 5 and `f'c = 120` MPa, so every coefficient comes from the "> 2" column. The saved example is therefore a weak test of the interpolation path. | Added hand checks | Obtain an independent two-way worked example with 1 < Ly/Lx < 2. |
| C12 | Medium | The optional shrinkage group follows Tedds: it applies `0.75 p D` at **every** flexure location, top and bottom. Cl 9.4.3 may allow the reinforcement in both faces to be counted together. This is conservative. | As Tedds | Confirm how Cl 9.4.3 intends the requirement to be shared between faces. Allow a combined check if permitted. |
| C13 | Low | The optional flexure group assumes the short-span bars are the outer layer, top and bottom, and treats the section as singly reinforced (`ku <= 0.36`). Compression steel is not credited. | By design | Add a layer-order selector, as Tedds has. |

## 5. Deliberate departures from the workbook

These are listed in `README.md`. They are C2, C3, applicability failures counted in
`worstUtil`, the `Prelim` sheet not transcribed, and mesh naming omitted.

## 6. Future development

1. Confirm the tables against the printed Standard (C1). If they are copyright-cleared for
   internal use, move them into a data file with provenance.
2. Add slab shear at the supports using the Cl 6.10.3.4 simplified shears and the 2018
   Cl 8.2.4 method. Do not use the superseded 2009 expression that Tedds uses.
3. Add fire axis distance to Table 5.5.2, crack width control (Cl 9.5), and torsional
   corner reinforcement (Cl 9.1.3.3).
4. Add confirmation inputs for the simplified-method applicability conditions (C7).
5. Obtain a worked example from a textbook or design guide, for example Warner et al.,
   *Concrete Structures* (Chapter 16), and add it to the baseline. Running Tedds on the
   same inputs would also give a numerical cross-check.
