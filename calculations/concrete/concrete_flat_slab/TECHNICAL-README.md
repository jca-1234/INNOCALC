# Technical Review: Concrete Flat Slab Design

| | |
| --- | --- |
| Module | `concrete-flat-slab` `v0.0.1` |
| Source | Structural Toolkit FLAT SLABS V5.04 (revision 5.04, 20 September 2021), `Concrete_FlatSlab_504.xls` |
| Standard | AS 3600:2018 incl. Amendments 1 and 2; AS/NZS 1170.0:2002 |
| Reviewer | Automated transcription and review. **An independent engineer still needs to review this module.** |
| Date | 24 September 2026 |
| Overall opinion | **Sound in method and exact in transcription; suitable for release after independent review and closure of C5, C6 and C10.** The workbook applies the AS 3600 Cl 6.10.4 simplified method correctly: its Table 6.10.4.3 coefficients satisfy statics in every span (`(M.neg1 + M.neg2)/2 + M.pos = Mo`) and its default strip shares lie inside the Table 6.9.5.3 ranges. All 224 cached values reproduce to `1e-9`. Its weaknesses are in *verification*, not analysis: it never compares the minimum steel, prints applicability errors beside an OK, omits the `Lo >= 0.65 L` limit and the `q <= g` deflection condition, and uses `Lo` where the Standard uses `Lef`. All five are corrected here. No independent AS flat slab calculation exists in Tedds, so the coefficient tables rest on this review and the printed Standard. |

## 1. What the calculation does

The module applies AS 3600 Cl 6.10.4 to a flat slab with equal spans `Ly >= Lx` in each
direction, columns `Cy x Cx`, edge overhangs `Oy`, `Ox` and optional drop panels. Loads are
area loads in kPa; lengths are in mm.

1. **Actions.** `g = wdl + wsdl` (the dead load includes self weight) and
   `Fd = max(1.35 g, 1.2 g + 1.5 q)` (AS/NZS 1170.0 Cl 4.2.2), with `psi_s` and `psi_l` from
   AS/NZS 1170.0 Table 4.1 for normal and storage use.
2. **Drop panels.** Where present, `thd = 0.3 th` (overall `1.3 D`) and the drop extends
   `DL = roundup(L/6, 10 mm)` each side: the minimum for `k3 = 1.05` in Cl 9.4.4.1.
3. **Support lengths and effective spans** (Cl 6.10.4.2). `Lo = L - 0.7 (a_sup1 + a_sup2)`,
   `Lo >= 0.65 L`. The workbook's support table (`Analysis!M32:AB35`) takes `a_sup` as half
   the column dimension at a column, `c/2 + thd` at a drop panel, zero at an unrestrained
   edge or wall, and no drops at edge columns with an edge beam. Along a wall (type F) the
   edge strip is supported continuously, so `Lo = 0` (`a_sup = L/0.7`).
4. **Total static moment** (Eq 6.10.4.2). `Mo = Fd Lt Lo^2 / 8` for the interior design strip
   (`Lt = Lx` for `My*`, `Ly` for `Mx*`) and the edge design strip (`Lt = L/2 + O`), for an end
   span and an interior span.
5. **Design moments** (Table 6.10.4.3). At the six critical sections (exterior support, end
   span positive, first interior support from each side, interior span positive, interior
   support):

   | Exterior edge | Exterior -ve | End span +ve | First interior -ve | Interior -ve / +ve |
   | --- | --- | --- | --- | --- |
   | S, unrestrained | 0 | 0.60 | 0.80 | 0.65 / 0.35 |
   | I, integral columns | 0.25 | 0.50 | 0.75 | 0.65 / 0.35 |
   | C, columns and edge beam | 0.30 | 0.50 | 0.70 | 0.65 / 0.35 |
   | F, fully restrained | 0.65 | 0.35 | 0.65 | 0.65 / 0.35 |

6. **Transverse distribution** (Table 6.9.5.3). The column strip is `Lt/2` wide (optionally
   limited to `L/2`, after WRH), and takes 0.75 of the negative and 0.5 of the positive
   moment. The exterior negative moment goes wholly to the column strip, except 0.75 with an
   edge beam. The middle strip halves take the remainder. The edge column strip is
   `O + L/4` wide and takes the same shares, or 1.0 / 0.7 / 1.0 with an edge beam.
7. **Moment transfer** (Cl 6.10.4.5, as transcribed from PUNCHING SHEAR V5.06):
   `M*v = 0.06 [(1.2 g + 0.75 q) Lt Lo^2 - 1.2 g Lt Lo.min^2]` at the first and typical
   interior columns.
8. **Minimum strength reinforcement** (Cl 9.1.1(a)): `Ast.min = 0.24 (D/d)^2 f'ct.f/fsy b d`.
9. **Deflection** (Cl 9.4.4.1): `d.min = Lef / (k3 k4 [(Delta/Lef) Ec / Fd.ef]^(1/3))` with
   `k3 = 0.95` (no drops) or `1.05` (drops), `k4 = 2.1` (interior) or `1.75` (end span),
   `Fd.ef = (1 + kcs) g + (psi_s + kcs psi_l) q`, `Fd.ef.inc = kcs g + (psi_s + kcs psi_l) q`,
   `kcs = 2 - 1.2 Asc/Ast >= 0.8`, and `Lef = min(Ln + D, L)` of the longer span.

## 2. Validation undertaken

| Check | Method | Outcome |
| --- | --- | --- |
| Transcription fidelity | Replayed the saved workbook state against 224 cached cells of `Analysis` and `Settings` (every support length, effective span, static moment, coefficient, strip share and all 120 strip moments), relative tolerance `1e-9` | All 224 agree |
| Saved-state consistency | Compared the summary strings `Analysis!B7:B9` and the flags `Settings!O19`, `O46`, `P67`, `P68`, `P73`, `P76` with the cached numbers | Consistent; the baseline did not need splitting |
| Statics of Table 6.10.4.3 | `(M.neg,left + M.neg,right)/2 + M.pos` for every row and the interior span | Exactly `1.00 Mo` in all five cases |
| Distribution ranges | Default column strip shares against Table 6.9.5.3 as tabulated by the workbook (`Analysis!M58:O61`: interior -ve 0.60-1.00, exterior -ve 0.75-1.00, +ve 0.50-0.70) | All inside the ranges, positive shares at the lower limit 0.5 (WRH and RCB recommendation) |
| Hand calculations | Independent arithmetic in `tests/test_engine.py`: `Fd`, `Lo`, `Mo`, strip and per-metre moments, edge strip widths, `Ast.min`, `Ec` above 40 MPa, `d.min` with `Lef`, `M*v`, flexural capacity | Agree |
| Physical sense | 48-case sweep over spans, the four edge types, drops and strengths: finite, repeatable, no input mutation, `0.65 L <= Lo <= L`, column plus middle strip shares sum to the strip moment, positive moments positive | Pass |
| Dimensional consistency | `Mo = kPa x mm x mm^2 / 8e9 = kNm`; `M*v` likewise with `/1e9`; `Ec / (Lef/Delta) / (Fd.ef/1000)` is dimensionless | Consistent |
| Clause check | Method compared with AS 3600:2018 Cl 6.10.4 and Cl 9.4.4.1 from the reviewer's knowledge and with the Tedds AS 3600-2018 slab calculation (section 2.1). The printed Standard was not available | Agree; see C5, C10 and C15 for points to confirm |

### 2.1 Comparison with Tedds

Tedds items reviewed: *RC slab design (AS3600)* 1.0.21 (`calculations/AU/AU RC slab design.md`,
AS 3600-2018 Amdt 1 and 2: one-way Cl 6.10.2, two-way on four sides Cl 6.10.3, flexure per
location, Cl 9.4.3 shrinkage, Cl 9.4.4 deflection, Cl 9.3 punching); *RC member design
(AS3600)* (beams and columns only); *AU Concrete sub-frame analysis* (`AustAnal.md`,
AS 3600:1994 Cl 6.1.2, superseded); the AS-NZS data tables `AU3600-01-7.3.2`,
`AU3600-01-7.3.2(B)` and `AU3600-01-9.3.4.2`. Tedds has **no AS flat slab calculation and no
Table 6.10.4.3 or Table 6.9.5.3 data table**. Its flat slab items are BS 8110 and its two-way
items ACI 318 and CSA A23.3; these are not Australian and were not used.

| Aspect | Workbook | Tedds | Adopted here |
| --- | --- | --- | --- |
| Cl 6.10.4 static moment and strip distribution | Implemented | Not available for AS | Workbook. The coefficients could not be cross-checked value by value against Tedds; they were checked for statics and against the reviewer's knowledge of Table 6.10.4.3 |
| Minimum reinforcement | `0.24 (D/d)^2 f'ct.f/fsy b d` computed, never compared | `0.19` at every location (slabs on four sides, a different case) | 0.24 for flat slabs, compared as `minimumSteel` and at every strip in the flexure group |
| Flexural capacity | Not checked | At midspan and every edge: `ku <= 0.36`, Table 2.2.2 `phi`, minimum steel, spacing `min(300, 2D)` | **Adopted** as the optional `flexure` group, per strip |
| Shrinkage, Cl 9.4.3 | Not checked | `0.75 p D` in each direction at every location | **Adopted** as the optional `shrinkage` group |
| `q <= g` for the deemed-to-comply rule | Only `q <= 2 g` (Cl 6.10.4.1(g)) | Warns when `q > g` for Cl 9.4.4.1 (one-way) and Cl 9.4.4.2 | **Adopted** as `liveLoadDeflection`, counted in the verdict |
| Span in the span-to-depth rule | Largest `Lo` | `Lef` (effective span) | `Lef = min(Ln + D, L)`, longer span (C4) |
| `k3` | 0.95 / 1.05 for flat slabs | 1.0 (one-way and two-way on four sides only) | Workbook; Tedds does not cover flat slabs |
| `kcs` | `2 - 1.2 Asc/Ast >= 0.8` | Fixed 2.0 | Workbook (permitted, less conservative with compression steel) |
| `fcmi` | Curve fit, or `f'c` | Stepped Table 3.1.2 approximation | Workbook; the two differ by less than 1 MPa from 25 to 100 MPa |
| Punching shear | Not checked | Cl 9.3.3 / 9.3.4 (2018), internal columns only, `M*v` entered | Delegated to `concrete-punching-shear` (already benchmarked against Tedds). The Cl 6.10.4.5 `M*v` it needs is now reported, which Tedds does not compute |
| Beam shear | Not checked | AS 3600-2009 `beta1 beta2 beta3 fcv` expression | **Rejected**: superseded by the 2018 Cl 8.2.4 method |
| Sub-frame (idealised frame) analysis | Not applicable | `AustAnal`, AS 3600:1994 | **Rejected**: superseded edition and a different analysis method (Cl 6.9) |
| Fire axis distance, durability cover | Not checked | Table 5.5.2, Table 4.10.3.2 | Not adopted; future work |

## 3. Opinion on the theory

* **Simplified method.** Cl 6.10.4 is the Standard's direct design method for flat slabs.
  The workbook's coefficients are those of Table 6.10.4.3 and satisfy statics exactly. Using
  the more negative of the two first-interior-support values (`Analysis!F51` "Critical") is
  correct.
* **Support length.** Taking `a_sup` as the distance from the column centreline to the face,
  so that `Lo = L - 0.7 c` between equal columns, gives `Lo` slightly larger than the clear
  span and is the reading consistent with the `0.65 L` lower limit. Extending `a_sup` by the
  drop depth (a 45 degree spread) and zeroing it at walls are the workbook author's choices
  (C5).
* **Strip distribution.** The default shares are defensible choices within Table 6.9.5.3:
  0.75 of the negative moment and 0.5 of the positive moment, as WRH and RCB recommend. With
  an edge beam, sending all of the edge strip's negative moment and 0.7 of its positive
  moment to the edge column strip reflects the beam's stiffness, but the beam itself is not
  designed (C18).
* **Walls.** At a fully restrained (wall) edge the workbook assigns the whole exterior
  negative moment to the column strip, leaving the middle strips with no hogging moment at
  the wall. For a slab built into a continuous wall the hogging moment is closer to uniform
  across the width (C6).
* **Deflection.** The deemed-to-comply rule and its `k3`, `k4`, `kcs` and `Fd.ef` are
  correct for flat slabs. Using `Lo` for `Lef` was unconservative by about 2 % in `d.min` for
  the saved example (C4).

## 4. Areas of concern

| ID | Severity | Concern | Status in this module | Recommended action |
| --- | --- | --- | --- | --- |
| C1 | **High** | `Analysis!D164` computes `Ast.min = 633 mm2/m` but never compares it with `Ast` (`Analysis!D170`). A slab below minimum steel is not flagged. | `minimumSteel` utilisation | None, beyond sign-off. |
| C2 | **High** | Applicability errors do not change the verdict: `Analysis!D10` ("Shorter span is less than 1/2 the longer span"), `D26` ("LL > 2 * DL - Cl 6.10.4.1(g)") and `E162` (Class L not to be used, Cl 6.10.4.1(i)) are text beside "Slab thickness OK" (`B9`, `I192`). | `spanRatio`, `liveLoadRatio`, `ductilityClass` in `util`; Class L gives `inf` and FAIL | None, beyond sign-off. |
| C3 | Medium | `Lo >= 0.65 L` (Cl 6.10.4.2) is not applied in `Analysis!D38:H39` or `D97:H98`. It governs with deep drops or large custom supports. | Applied, with a warning; the wall-supported edge strip keeps `Lo = 0` | None. |
| C4 | Medium | `Analysis!C189:G190` use `MAX(Lox, Loy, Lox_, Loy_)` as the span in the span-to-depth rule, although revision 5.03 says "deflections changed to use Lef". For the saved example `Lo = 5720 mm` against `Lef = min(5600 + 250, 6000) = 5850 mm`: `d.min` is 2.2 % low. | `Lef` used for the verdict; workbook values in `deflection.workbook` | Confirm the definition of `Lef` for flat slabs (longer span) against the printed Standard. |
| C5 | Medium | The `a_sup` definition: half the column dimension per end, plus `thd` at drops (`Analysis!O33`), zero at an unrestrained edge (`M32:AB32`), zero at a wall end (`M35`, "Not reduced at fully restrained end", `K26`), `L/0.7` for a wall edge strip (`U35:AB35`). | Reproduced | Confirm against the Cl 6.10.4.2 definition and figure. |
| C6 | Medium | Type F (walls): the edge column strip share of the exterior negative moment is 1.0 (`Analysis!M74`, `M84`), so the middle strips have zero hogging moment at the wall and the "column strip" at a wall is a notional 3 m strip. | Reproduced | Use `customDistribution` with a lower exterior share, or provide top steel across the full wall length. Consider a uniform distribution at walls. |
| C7 | Low | Type S sets every support length to zero (`Analysis!M32:AB32`), including interior columns, so `Lo = L`. This overstates `Mo` by about 10 % for 400 mm columns at 6 m. | Reproduced (conservative) | Consider `a_sup = c/2` at interior columns. |
| C8 | Medium | The `q <= g` condition of the deemed-to-comply method is not checked (only `q <= 2 g`). | `liveLoadDeflection` (Tedds approach) | Confirm the Cl 9.4.4.1 wording for flat slabs. |
| C9 | Low | The WRH column strip limit `L/2` is optional (`Analysis!M53`); `Settings!P76` computes a warning flag that no formula references. | Optional; warning issued when spans differ | Confirm whether AS 3600 limits the column strip width. |
| C10 | Low | Clause numbering: the workbook cites "Cl 6.1.4.1 & Table 6.9.5.3" and "Cl 6.1.4.3" for strip distribution (`Analysis!F53`, `F61`). The module's headings cite Cl 6.10.4.4, which is the reviewer's understanding of the 2018 numbering. | Table 6.9.5.3 cited throughout | Confirm Cl 6.10.4.4 and the Cl 6.1.4 strip definitions against AS 3600:2018. |
| C11 | Low | The compression-steel test `kud - db/2 - db.inner < dc` (`Settings!P73`) subtracts the tension bar sizes from the neutral axis depth; the logical test is `kud < dc`. | Reproduced | Review the intent; the effect on `kcs` is marginal. |
| C12 | Low | Drop panels are fixed at the minimum `0.3 th` deep and `L/6` each way; the user cannot enter actual drop sizes, and the drop weight is not added to the loads. | Reproduced; stated as an assumption | Add drop dimension inputs and self weight. |
| C13 | Low | `Analysis!D26` warns "Applied dead load less than slab self weight" when `wdl <> th/1000*25`, so any superimposed dead load entered in `wdl` also triggers it. | Warns only when `wdl < 25 th` | None. |
| C14 | Low | The Cl 6.10.4.1(a), (b), (d) and (e) conditions (`Analysis!K11:K15`) are notes only, and the workbook assumes equal spans in each direction. | Stated as assumptions | Add span-by-span inputs or confirmation fields. |
| C15 | Low | The Cl 6.10.4.5 transfer moment and its factors `0.06`, `1.2 g + 0.75 q` and `1.2 g` come from PUNCHING SHEAR V5.06 (`Design!F97:F105`), not this workbook. | Reported, not checked | Confirm against AS 3600:2018 (same as punching C12). |
| C16 | Low | Presentation: `Analysis!A41` reads "Column & Middle beam" for type C; the `Ec` label (`Analysis!C182`) switches on `f'c <= 40` while the formula switches on `fcmi <= 40`; `Settings!O42` holds `#VALUE!` from the `ChangeFlatCols` macro. | Not carried over | None. |
| C17 | Low | The optional flexure group ignores the drop panel depth for negative moments and uses the inner layer depth in both directions when `insideLayer = Y`. | By design (conservative) | Add drop depth for column strip negative moments. |
| C18 | Low | With an edge beam (type C) the edge column strip moments are carried by the beam, which is not designed; the edge column strip is excluded from the flexure group. | Warning issued | Design the edge beam separately. |

## 5. Deliberate departures from the workbook

These are listed in `README.md`: C1, C2 and C8 counted in `worstUtil`; the `0.65 L` limit
(C3); `Lef` for deflection (C4); the self-weight warning (C13); swapping directions instead
of an "Error" text; a reinforcement class input; fixed `k3`; eight custom support sums and a
Table 6.9.5.3 range check for custom shares; the Cl 6.10.4.5 transfer moment; the optional
Tedds flexure and shrinkage groups; SVG drawings in place of the drawing macros; and the
`Prelim` sheet and mesh naming omitted. The workbook's `Type = S` branch of `k4` (1.4) is
unreachable (`Settings!I13:I14` permits I and E) and is not offered, because Cl 6.10.4 needs
at least two spans.

## 6. Future development

1. Close C5, C6, C10 and C15 against the printed AS 3600:2018 Amdt 2, and confirm the
   Table 6.10.4.3 coefficients directly.
2. Allow unequal spans and check the Cl 6.10.4.1 span conditions explicitly (C14).
3. Add drop panel dimensions and weight (C12) and use the drop depth for column strip
   negative moments (C17).
4. Add beam shear at the supports by the 2018 Cl 8.2.4 method (not the superseded 2009
   expression Tedds uses), edge beam design, fire axis distance and durability cover.
5. Pass `M*v`, `V*` and the slab geometry to `concrete-punching-shear` through the module
   exchange contract.
6. Obtain an independent worked example, for example from Warner et al., *Concrete
   Structures* (1999), or Foster, Kilpatrick and Warner, *Reinforced Concrete Basics* (2010),
   which the workbook cites, and add it to the baseline.
