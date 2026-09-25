# Technical Review: Concrete Punching Shear Design

| | |
| --- | --- |
| Module | `concrete-punching-shear` `v0.0.1` |
| Source | Structural Toolkit PUNCHING SHEAR V5.06 (8 December 2023), `Concrete_Punching_506.xls` |
| Standard | AS 3600:2018 incl. Amendments 1 and 2 |
| Reviewer | Automated transcription and review. **An independent engineer still needs to review this module.** |
| Date | 24 September 2026 |
| Overall opinion | **Sound in method; the transcription is exact; suitable for release after independent review and closure of C4, C8 and C12.** The Cl 9.3.3 and Cl 9.3.4 equations in the workbook agree with AS 3600:2018 and with the independent Tedds AS 3600-2018 implementation. The workbook's spandrel mean-depth geometry reproduces the author's own 120-point GoalSeek harness. The weaknesses are in the workbook's *reporting*, not its equations: it never selects a governing case, never applies its own Cl 6.10.4.5 minimum moment, never compares the integrity reinforcement, and lets applicability errors sit beside an OK. All four are corrected here. |

## 1. What the calculation does

The module checks a slab for punching shear around a column or concentrated load (AS 3600
Section 9.3). Working units are N, mm and MPa.

1. **Mean depth.** `dom` is entered, or taken as the mean of two bar layers (optional, from
   Tedds). With a spandrel beam at an edge or corner, and unless the spandrel is ignored, the
   perimeter crosses the deeper spandrel. `dom` is then the length-weighted mean of
   `do` in the slab and `dob = Db - (Ds - do)` in the spandrel. Because the perimeter depends
   on `dom`, the workbook solves `dom = sum(do.i l.i) / u(dom)` with the GoalSeek macro
   `RecalcDom`. The module solves the same fixed point by bisection between `do` and `dob`.
2. **Critical shear perimeter** at `dom/2` from the face (Cl 9.3.1.3), less the ineffective
   length for openings (Fig 9.3(A)):
   * rectangular: internal `2 (L + dom + W + dom)`; edge `2 (pY + dom/2) + pX + dom`; corner
     `pX + pY + dom`, where `pX` lies along the edge;
   * circular: internal `pi (D + dom)`; edge `pi (D + dom)/2 + D`; corner `pi (D + dom)/4 + D`,
     with straight legs from the quadrant to the edge.
3. **Dimension `a` parallel to `Mv*`** (Fig 9.3(B)): `L + dom` or `W + dom`, reduced to
   `+ dom/2` for the side running to a free edge. `betah = L / W`, or 1 for a circle.
4. **Strength without moment transfer** (Cl 9.3.3), `phi = 0.7`:
   * no shear head: `phiVuo = phi u dom (fcv + 0.3 sigma.cp)`,
     `fcv = 0.17 (1 + 2/betah) sqrt(f'c) <= 0.34 sqrt(f'c)` (Eq 9.3.3(1));
   * shear head: `phiVuo = phi u dom (0.5 sqrt(f'c) + 0.3 sigma.cp) <= phi 0.2 u dom f'c`
     (Eq 9.3.3(2)).
5. **Strength with moment transfer** (Cl 9.3.4):
   * (a) no closed fitments: `phiVu = phiVuo / [1 + u Mv* / (8 V* a dom)]`;
   * (b) minimum fitments in the torsion strip: `phiVu.min = 1.2 phiVuo / [1 + u Mv* / (2 V* a^2)]`;
   * (c) minimum fitments in a spandrel: `phiVu.min = 1.2 phiVuo (Db/Ds) / [1 + u Mv* / (2 V* a bw)]`;
   * (d) more than the minimum: `phiVu = phiVu.min sqrt((Asw/s) / (0.2 y1 / fsy.f))
     <= phiVu.max = 3 phiVu.min sqrt(x/y)`.
6. **Fitment rules**: `Asw/s >= 0.2 y1 / fsy.f` (Eq 9.3.5) and `s <= min(Ds or Db, 300)`
   (Cl 9.3.6 as the workbook applies it). `y1` is the larger centre-line dimension of the
   fitment, capped at `a` in a torsion strip.
7. **Minimum transferred moment** (Cl 6.10.4.5, interior supports, simplified method):
   `M.min* = 0.06 [(1.2 g + 0.75 q) Lt Lo^2 - 1.2 g Lt Lo'^2]`.
8. **Integrity reinforcement**: `As.min = 2 N* / (phi fsy)`, waived where every span has
   beams with shear reinforcement and two continuous bottom bars.

The governing punching strength is Cl 9.3.3 when `Mv* = 0`; otherwise Eq 9.3.4(4) when
compliant fitments are provided, else Eq 9.3.4(1).

## 2. Validation undertaken

| Check | Method | Outcome |
| --- | --- | --- |
| Transcription fidelity | Replayed the saved workbook state against 59 cached cells of `Design` and `Settings`, relative tolerance `1e-9` | All 59 agree |
| Circular perimeter geometry | Replayed the saved example with `col = Y` against 22 cached cells `Settings!T72:AE95`, which do not depend on `col` | All 22 agree |
| Spandrel mean depth solver | Replayed the author's GoalSeek harness (`Module2.Test`, `testtype = 2`): 500 mm circular column, 500 mm spandrel, `bw` = 25 to 1000 mm, for edge, corner one side and corner both sides (`Settings!Z139:AS178`), `+/- 0.51` mm for `CInt` rounding | All 120 agree. The harness depths were recorded with the Settings defaults `Ds = 200`, `do = 167` (proven by the 467 mm plateau) |
| Saved-state consistency | Compared every summary string `Design!B8:I14` with the cached numbers | Consistent; the baseline did not need splitting |
| Hand calculations | Independent arithmetic in `tests/test_engine.py`: Cl 9.3.3 with and without a shear head, `betah` governing, prestress, internal, edge and corner perimeters for both shapes, Eq 9.3.4(1) to (5), spandrel fixed point, Cl 6.10.4.5, integrity | Agree |
| Solver edge case | Rectangular edge column where the parallel face reaches the spandrel boundary at `dom = 400` | Average jumps from 550 to 390; the solver returns 400 and flags "no exact root" |
| Physical sense | 96-case sweep over shape, position, spandrel, fitments and actions: finite, repeatable, no input mutation, `domc` between `do` and `dob`, no negative strength, ceiling `3.6 phiVuo (Db/Ds)` never exceeded, overloaded never OK | Pass |
| Dimensional consistency | `u dom fcv` in mm x mm x MPa = N; `u Mv* / (V* a dom)` dimensionless; `M.min*` kPa x mm^3 / 1000 = N mm | Consistent |
| Clause check | Equations compared with AS 3600:2018 Cl 9.3.3 to 9.3.5 from the reviewer's knowledge and with Tedds 2018 (§2.1). The printed Standard was not available | Agree; see C4, C9, C12 for points to confirm |

### 2.1 Comparison with Tedds

Tedds items reviewed: *RC slab design (AS3600)* 1.0.21 "Punching shear cap no Mv" and
"Punching shear cap with Mv" (AS 3600-2018 Amdt 1 and 2); *Foundation analysis and design
(AS3600)* 2.0.02 (AS 3600-2018 Amdt 2); `AUPad.md` and `AustRC.md` (AS 3600-2001 numbering,
"cl. 9.2.3"/"cl. 9.2.4"); `AusFound.md`; *RC member design (AS3600)* (no punching);
General *Pile cap design* (generic shortest-perimeter search, no AS clauses).

| Aspect | Workbook | Tedds | Adopted here |
| --- | --- | --- | --- |
| `fcv`, `phi` | `0.17 (1 + 2/betah) sqrt(f'c) <= 0.34 sqrt(f'c)`, `phi = 0.7` | Identical (slab 1.0.21 and Foundations 2.0.02) | Workbook; confirmed |
| Eq 9.3.4(1) | `Vuo / [1 + u Mv* / (8 V* a dom)]`, `a = L + dom` | Identical in the slab and Foundations items | Workbook; confirmed |
| `a` in Eq 9.3.4(1) | Critical-perimeter dimension | `AUPad`/`AustRC` use the column length `Lped` | Workbook. The AS 3600-2001-era Tedds items are **outdated** here |
| `betah` | `max(L, W) / min(L, W)`, `L >= W` enforced | `bcx / bcy` (can fall below 1 if entered the other way round) | Workbook |
| Edge and corner perimeters | Internal, edge and corner, rectangular and circular, spandrels | Slab item: internal only (stated limitation). Foundations: perimeter clipped by the base | Workbook |
| Closed fitments, Eq 9.3.4(2) to (5) | Implemented | Not implemented ("does not include the design of shear reinforcement") | Workbook |
| Shear head, Eq 9.3.3(2) | Implemented | Not implemented | Workbook |
| Mean depth `dom` | Entered directly; hint `ds - cover - 16/2` (outer layer only) | Mean of the outer and inner layers, `((D - c - db1/2) + (D - c - db1 - db2/2)) / 2`; Foundations `(dx + dy)/2` | **Adopted** as the optional `effectiveDepth` group. It matches the Cl 9.3.1.4 definition of `dom` as the mean of `do` around the perimeter |
| Load inside the perimeter | Not deducted | Foundations deducts `(Fu/A - qpu) Ap` | Not adopted: `V*` is defined at the critical perimeter and is the designer's input. Noted as future work |
| Shear links (`Apv` per m2) | Not applicable | Foundations sizes shear links around the perimeter | **Rejected**: not an AS 3600 Section 9.3 method; AS 3600 credits closed fitments in the torsion strip or spandrel only |
| Shortest perimeter search | Position chosen by the user | General pile cap: minimum of internal, edge and corner perimeters | Not adopted: generic and not AS-specific; noted as future work for columns set back from an edge |
| Cl 6.10.4.5, integrity reinforcement | Computed, never used | Not implemented | Workbook values, now used (C2, C3) |

No Tedds item provides a check that the workbook omits and that AS 3600:2018 makes
mandatory for this scope.

## 3. Opinion on the theory

* **Cl 9.3.3 and Cl 9.3.4.** The workbook's equations are the Standard's, with `phi`
  applied consistently, including the ceiling `phiVu.max` (revision 5.01 "added ø"). The
  sub-case logic for torsion strip versus spandrel, `x` and `y`, and `y1` is correct. The
  change log shows the author tracked the 2009 to 2018 transition; nothing superseded remains.
* **Case selection.** AS 3600 structures Cl 9.3.4 by the fitments provided. The workbook
  prints all cases side by side and leaves the choice to the reader, so its saved example
  shows three "No Good" rows beside one "OK". The module selects the case (C1).
* **Mean depth with a spandrel.** Averaging `do` along the perimeter follows the definition
  of `dom` and is more refined than most tools. The fixed point has no solution where the
  perimeter's parallel face lands on the spandrel boundary, because the depth assigned to that
  face jumps. The workbook warns of this (`Design!K19:K20`). The module takes the jump point
  deterministically and warns; an engineer should check such cases with `ignorespan = Y`.
* **Circular columns at edges.** The straight-leg perimeter is conservative (author's note
  `Settings!X29`). But `a = D + dom` is used at every position (C8).
* **Integrity reinforcement and Cl 6.10.4.5.** The formulas are plausible and
  dimensionally correct, but the clause numbers, `phi` and load factors could not be verified
  against the printed Standard (C4, C12).

## 4. Areas of concern

| ID | Severity | Concern | Status in this module | Recommended action |
| --- | --- | --- | --- | --- |
| C1 | **High** | No governing case. `Design!I8`, `I9`, `I10`, `I11` and `I12` each print OK / No Good. The saved example reads No Good (1.12), No Good (1.28), No Good (1.17) and OK (0.49), and the user must work out that the slab passes with fitments. | Governing case chosen from `Mv*` and the fitments provided; all cases in a grid | None, beyond sign-off. |
| C2 | **High** | `Design!F105` computes `M.min* = 2.39 kNm` for the saved example, larger than `Mv* = 1 kNm` (`Design!D20`), but the minimum is never used. | `simplifiedMethod = Y` applies the minimum at interior supports; otherwise a warning | Confirm with users that the simplified-method flag is the right trigger. |
| C3 | **High** | `Design!F92:F93` compute `As.min` and the number of bars (20.2 N12) but never compare them with the bars provided. | `integrity` utilisation with the new `nIntegrity` input | None, beyond sign-off. |
| C4 | Medium | Integrity reinforcement: `phi = 0.7` (`Design!F91`, "Table 2.2.2(e)"), clause "Cl 9.2.2" and "Eq 9.2.2" are the workbook's and could not be verified. | Reproduced, labelled "as cited by the workbook" | Confirm the clause, `phi` and `N*` definition against AS 3600:2018 Amdt 2. |
| C5 | Medium | Applicability errors do not change the verdict: fitment width > `a` (`Settings!O37`, `Design!H13`), `do < 0.8 Ds` for prestress (`Design!F16`), fitments below minimum or too widely spaced (`Design!H27`). | Included in `util` and `worstUtil`; non-compliant fitments are ignored for strength | None, beyond sign-off. |
| C6 | Medium | Degenerate fitment inputs: `ctsp = 0` with a bar size, or `y1 = 0`, make `minasw = 0`, so `Design!F67` returns a non-zero `phiVu.min` with no fitments. | Treated as no fitments | None. |
| C7 | Medium | The spandrel `dom` depends on the macro being re-run (`Design!A6`, `Settings!T45`); the stored `dom_gs = 304.7` is stale but unused in the saved example. Some `bw` values have no solution. | Deterministic bisection; warning when no exact root | Review flagged cases with the spandrel ignored. |
| C8 | Medium | For a circular column at an edge or corner, `a = D + dom` (`Design!F39:F40`) regardless of the edge. For a rectangular column the side running to the edge uses `+ dom/2`. Where `Mv*` acts perpendicular to the edge this overstates `a` and `phiVu` (unconservative). | Reproduced with a warning | Add a direction-relative-to-edge input for circular columns and use `D/2 + Rdom` perpendicular to the edge. |
| C9 | Low | Maximum fitment spacing `min(Ds, 300)` or `min(Db, 300)` (`Design!F64`, changed in revision 5.00b). | Reproduced | Confirm the Cl 9.3.6 wording. |
| C10 | Low | With minimum fitments and `a < 4 dom`, Eq 9.3.4(2) can be lower than Eq 9.3.4(1) without fitments. | The fitment case is used when fitments are provided (conservative); a warning is issued | Reviewer to confirm whether Eq 9.3.4(1) may be relied on when fitments are present. |
| C11 | Low | The hidden setting `Curved` (`Settings!AB129 = N`) switches to a curved perimeter; the curved branch and its test columns (`Settings!V102:AG178`) are not reachable by a user. | Not transcribed | Transcribe only if the option is ever exposed. |
| C12 | Low | Cl 6.10.4.5 load factors `1.2 G + 0.75 Q` and `1.2 G` (`Design!F103:F104`). | Reproduced | Confirm against AS 3600:2018. |
| C13 | Low | `dom` is entered directly; the workbook hint `Settings!C20` (`ds - cover - 16/2`) is the outer-layer depth, which overstates `dom`. | Optional `effectiveDepth` group from Tedds | Consider making the layer calculation the default. |
| C14 | Low | Edge and corner columns are assumed flush with the edge; the internal perimeter is not checked as an alternative for columns set back from the edge. | Stated as an assumption | Add an edge distance and take the least perimeter. |
| C15 | Low | `V* = 0` with `Mv* > 0` gives `Design!F61 = 0` and `#DIV/0!` in `F67`. | Strengths set to zero, `punching = 0`, warning | None. |
| C16 | Low | No upper limit on `sqrt(f'c)` is applied in Section 9.3, by either the workbook or Tedds. | Reproduced | Confirm that no `sqrt(f'c)` cap applies to Cl 9.3. |

## 5. Deliberate departures from the workbook

These are listed in `README.md`: governing case selection (C1), the Cl 6.10.4.5 minimum
applied on request (C2), the integrity comparison (C3), applicability rules in `worstUtil`
(C5), degenerate fitments as no fitments (C6), bisection in place of GoalSeek (C7), invalid
geometry raised as `ValueError`, negative actions rejected, the `R` label for 250 MPa
fitments, the curved perimeter not transcribed (C11), and the optional Tedds mean depth (C13).

## 6. Future development

1. Close C4, C9, C12 and C16 against the printed AS 3600:2018 Amdt 2.
2. Resolve C8 with an input for the direction of `Mv*` relative to the free edge.
3. Add an edge distance so that columns set back from an edge take the least of the
   internal, edge and corner perimeters (C14, as the Tedds pile cap search does).
4. Allow the load inside the critical perimeter to be deducted from `V*` (Tedds Foundations).
5. Check both directions of moment transfer in one calculation.
6. Obtain an independent worked example, for example from Warner et al., *Concrete
   Structures* (1999), which the workbook cites, and add it to the baseline.
