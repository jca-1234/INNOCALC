# Technical Review: Concrete Industrial Pavement Design

| | |
| --- | --- |
| Module | `concrete-industrial-pavement` `v0.0.1` |
| Source | Structural Toolkit INDUSTRIAL FLOOR SLABS V5.07 (revision 5.07a), `Pavements_Industrial_507.xls` |
| Standard | As cited by the workbook (`Info!B10:B29`): AS 3600:2018 incl. Amdt 1 and 2; C&CA TR550 (Chandler, 1982); CCAA T48 (1999 and 2009); C&CA *Concrete Industrial Floor and Pavement Design* (1985); Smorgan ARC Slabex manual (1998, as spelt in the workbook; not used); Austroads *Guide to Pavement Technology Part 2* (2010) |
| Reviewer | Automated transcription and review. **An independent engineer still needs to review this module.** |
| Date | 24 September 2026 |
| Overall opinion | **Faithful transcription of a recognised but dated method; suitable for release only after independent review and verification of the digitised charts.** All 415 cached workbook values are reproduced to `1e-9`, and the closed-form stress expressions agree with independent Westergaard, Pickett and Hetenyi hand calculations. The adjacent-load and aisle-moment charts are curve fits of digitised charts with no retained source, which is the main residual risk. Two unconservative defects in the aisle-moment interpolation and one geometry defect in the dual axle layout have been corrected, and every printed check now governs the result. |

## 1. What the calculation does

The slab is treated as an unreinforced plate on a dense liquid (Winkler) subgrade. Stresses
are working stresses, compared with the 90-day flexural tensile strength reduced by the T48
material factor `k1` and load repetition factor `k2`.

1. **Materials.** `fcmi = -0.0015 f'c^2 + 1.1392 f'c + 0.3481` (a fit to AS 3600 Table 3.1.2,
   or `f'c`); `Ec = rho^1.5 0.043 sqrt(fcmi)` for `fcmi <= 40`, else
   `rho^1.5 (0.024 sqrt(fcmi) + 0.12)` (Cl 3.1.2). Flexural strength by method: C&CA
   `0.438 f'c^(2/3)`, T48 `0.7 sqrt(f'c)`, AS 3600 `0.6 sqrt(f'c)` or a manual value.
   `Z = h^2 b / 6`.
2. **Radius of relative stiffness** `l = [E h^3 / (12 (1 - mu^2) k)]^0.25` (Westergaard).
3. **Loaded area.** `r = sqrt(A / pi)` for a rack foot, `r = 1000 sqrt(10 WPL / (pi Pr))` for a
   tyre; Westergaard equivalent radius `b = sqrt(1.6 r^2 + h^2) - 0.675 h` for `r < 1.72 h`,
   else `b = r`.
4. **Stresses per tonne** (constants are the inch-pound coefficients times 9.81 kN):
   * internal, Westergaard: `2.7 (1 + mu) / h^2 [4 log(l / b) + 1.069] 10^3`;
   * edge, Kelley: `5.19 (1 + 0.54 mu) / h^2 [4 log(l / b) + log(b / 25.4)] 10^3`;
   * corner, Pickett: `41.2 / h^2 [1 - sqrt(r / l) / (0.925 + 0.22 r / l)] 10^3`.
5. **Adjacent loads.** Each adjacent load raises the stress at the point under
   consideration by a percentage read from Chandler's stress-increase curves at
   `distance / l`, tangential (T), radial (R) or the critical of both (C), with separate
   internal and edge curves. The increase is `1 + max(sum X, sum Y) / 100`. Joint load
   transfer reduces edge stress by 0.85 and corner stress by 0.7 (Chandler).
6. **Rack posts.** `RPL = levels x pallet mass x 10 N/kg`. Bearing `1.5 RPL / Fa <= 0.6 x
   0.9 f'c` (Cl 12.6). Punching `1.5 RPL <= 0.7 u dom fcv` with `dom = 0.9 h`,
   `fcv = min(0.17 (1 + 2 / betah), 0.34) sqrt(f'c)` (Cl 9.3.3) and an internal, edge or
   corner perimeter at `dom / 2`. Flexure: `sigma_r / (Rk1 Rk2)` plus the aisle UDL stress
   `M q / Z / (Uk1 Uk2)` from Chandler Fig 3.
7. **Wheels.** Single or dual axle, 2 or 4 wheels per axle. `Wk2` from T48 Table 1.17:
   `(11.791 - log N) / 12.136`, 0.84 below 50 and 0.50 above 400 000 repetitions.
8. **Uniform loads.** C&CA Cl 5.6.3 variable layout `W = 0.33 fca sqrt(h K)`; Hetenyi beam on
   elastic foundation with `lambda = [3 K / (E h^3)]^0.25`, critical aisle `2a = pi / (2 lambda)`,
   `Mc = q / (2 lambda^2) [e^(-lambda a) sin(lambda a) - e^(-lambda b) sin(lambda b)]`.
9. **Shrinkage steel.** AS 3600 `1.75 b h 10^-3` (250 mm per face above 500 mm), T48 0.14 %,
   T48 Appendix F `rho g mu h L / 2 / (0.67 fsy)` and Austroads `mu L / 2 rho g h / (0.6 fsy)`.
10. **Subgrade.** `K = 23.372 ln(CBR) + 0.7047` (Chandler Fig 1 fit) and bound sub-base
    quadratic fits to T48-2009 Fig 1.26 or T48-1999 Fig 1.17.

## 2. Validation undertaken

| Check | Method | Outcome |
| --- | --- | --- |
| Transcription fidelity | 250 cached cells of the saved example (Design, Racking, Wheels, Custom, Uniform, Reinft, Settings) in `data/workbook-baseline.json`, relative tolerance `1e-9` | All 250 agree |
| VBA chart functions | 160 cached UDF results `Settings!AO71:AR110` (`Radial4`, `RadialEdge4`, `Trans4`, `TransEdge4` for `x = 0.1` to `4.0`), including the cut-offs at 3 and 4 and the clamp of negatives | All 160 agree |
| VBA scalar functions | `Moment` (Racking!F61, Custom!F59, including Integer coercion of `l`), `StressRatio`, `MSR`, `CBR` | All 5 agree |
| Westergaard interior (independent) | 1926 exact form `3 (1 + mu) P / (2 pi h^2) [ln(l / b) + 0.6159]` with `P = 9.81 kN` | Ratio 1.0012 (the constant 2.7 is 0.275 x 9.81 rounded) |
| Kelley edge (independent comparison) | Westergaard 1926 edge `0.572 P / h^2 [4 log(l / b) + 0.359]` | Kelley is 1.4 % (rack) and 4.4 % (wheel) higher |
| Pickett corner (independent) | `4.2 P / h^2 [...]` with `P = 9.81 kN`; compared with the Westergaard corner `3 P / h^2 [1 - (a sqrt2 / l)^0.6]` | Constant reproduced; Pickett is 35 % to 37 % above Westergaard, as expected for a corner without full subgrade support |
| Hetenyi aisle moment (independent) | Closed-form maximum `0.16817 q / lambda^2` at `a = pi / (4 lambda)` | Workbook coefficient 5.313 is 0.09 % below the exact 5.318 |
| C&CA variable layout, punching perimeters, transfer multipliers | Hand calculations (`tests/test_engine.py`) | Agree |
| Digitised charts | Curve fits compared with the retained digitised points (`Graphs 1`, `Graphs 2`) | Stress increase within 0.4 percentage points; aisle moment within 0.012 kNm/m per kPa |
| T48 Table 1.17 | `StressRatio` against the retained table `Settings!X55:Y65` | Within 0.01 |
| Physical sense | 72-case sweep over thickness, subgrade, position, flexural method and axle arrangement: finite, repeatable, inputs not mutated, adjacent loads never reduce stress unless negatives are included, dual axle used when `Bogie > 0` | Pass |

### 2.1 Comparison with Tedds

**No Australian-Standard-based Tedds ground-floor or pavement calculation exists.** The
`calculations/AU` folder contains `AuRoad` (road curve setting out), `AusFound` and `AUPad`
(foundations), none relevant. The only ground-floor calculation is the UK TR34 library
(`General/Concrete industrial ground floors-x-x-x`, `GB/Concrete industrial ground floors-TR34-si-engb`),
used here for code-independent theory only; its partial factors and material rules were not
adopted. The benchmark is therefore the independent hand calculations in §2. The Tedds AS
3600-2018 slab calculation (`AU RC slab design`) was used for the punching expression only.

| Aspect | Workbook | Tedds | Adopted here |
| --- | --- | --- | --- |
| Radius of relative stiffness | `[E h^3 / (12 (1 - mu^2) K)]^0.25` | Same, with `Ecm` | Workbook; identical theory |
| Beam on elastic foundation | `lambda = [3 K / (E h^3)]^0.25` (Hetenyi) | Same `lambda` | Workbook; identical theory |
| Contact radius | `sqrt(A / pi)` | `sqrt(A / pi)` | Same |
| Point load analysis | Elastic Westergaard, Kelley and Pickett stresses against `k1 k2 f'ct.f` (T48, Chandler) | Meyerhof yield-line collapse loads: internal `2 pi (Mp + Mn)` to `4 pi (Mp + Mn) / (1 - a / 3l)`, edge and corner forms, with TR34 partial factors and `Mn`, `Mp` from TR34 material rules | **Not adopted.** An ultimate method needs load and material factors that have no AS or T48 basis; importing TR34's would mix codes. The elastic T48 basis is retained |
| Adjacent loads | Chandler stress-increase charts in fractions of `l` | Meyerhof dual and quadruple load equations (TR34 Eqn 29, 30) | Not adopted, for the same reason |
| Load position | User selects internal, edge or corner; only a warning when not internal | Internal when the load centre is more than `a + l` from an edge; edge when more than `a + l` from a corner | **Adopted** as the optional `location` group, `positionApplicability`. It is code-independent and turns a warning into a check |
| Punching | AS 3600 Cl 9.3.3 at `dom / 2`, internal, edge and corner, `phi = 0.7` | TR34: EC2 checks at the face and at `2d` (GB). AU slab: Cl 9.3.3, `fcv = min(0.17 (1 + 2 / betah), 0.34) sqrt(f'c)`, `phi = 0.7`, internal only, `betah = bcx / bcy` | Workbook. Same expression and `phi` as Tedds AS 3600-2018; the workbook's `max / min` for `betah` and its edge and corner perimeters are better |
| Joint load transfer | Chandler 0.85 edge and 0.7 corner multipliers | Aggregate interlock, dowel, fabric or proprietary transfer capacities | Not adopted; joint design is future work |
| Uniform loads | C&CA `0.33 fca sqrt(h K)` and Hetenyi | TR34 UDL capacity | Workbook; TR34 formula is code-specific |

## 3. Opinion on the theory

* **Westergaard, Kelley and Pickett.** These are the classical closed-form solutions used by
  Chandler (TR550) and T48 for slabs on grade. The transcribed constants reproduce the
  inch-pound coefficients multiplied by 9.81 kN per tonne. The interior form is exact to
  0.12 %. The edge form (Kelley) and corner form (Pickett) are empirically adjusted
  expressions and are more conservative than Westergaard's originals; that is appropriate.
* **Working stress with `k1 k2`.** Dividing the elastic stress by the material and repetition
  factors is equivalent to T48's reduced design flexural strength. The repetition factor is a
  single-load-level fatigue allowance, not a cumulative (Miner) fatigue check.
* **Adjacent-load charts.** Chandler's charts are an elastic superposition of neighbouring
  loads in terms of `distance / l`. The polynomial fits follow the digitised points closely,
  but the digitisation itself is unverified and the fits oscillate outside the digitised range
  (they are cut to zero beyond 3l or 4l).
* **Punching of a plain slab.** AS 3600 Cl 9.3 is written for reinforced slabs. Its use for an
  unreinforced slab on grade with `dom = 0.9 h` follows T48 Cl 3.3.8.6 (as cited by the
  workbook) and is conservative in ignoring subgrade support within the perimeter.
* **Uniform loads.** The C&CA variable-layout formula and the Hetenyi patterned-aisle solution
  are standard. The workbook reports three results; all three now govern.

## 4. Areas of concern

| ID | Severity | Concern | Status in this module | Recommended action |
| --- | --- | --- | --- | --- |
| C1 | **High** | VBA `Moment` (`Racking!F61`, `Custom!F59`): for `570 < l < 675` mm the later `If` block overwrites `y1` with the 450 mm curve, so the result extrapolates the 450 and 570 curves. At `l = 620`, aisle 2 m, it gives 0.0998 instead of 0.1081 (8 % low). | Corrected: interpolates 570 to 675 | None beyond sign-off |
| C2 | **High** | `Moment` returns 0 for `l < 450` mm, so the aisle UDL stress vanishes for thin slabs on stiff subgrades. | Corrected: 450 mm curve (conservative) and a warning | Consider extending the chart |
| C3 | Medium | `Design!I12` summarises only `q / W`; the Hetenyi checks (`Uniform!I37`, `Uniform!I52`) print OK or No Good on their tab only. `Wheels!I9` and `Uniform!I9` print "Accept" up to 1.025. | Corrected: all in `util`, pass at `<= 1.0` | None |
| C4 | Medium | Dual axle point G (`Wheels!C46`) uses `sqrt(Bogie^2 + (Wcts - WPC / 2)^2)` for both 2 and 4 wheels per axle, inconsistent with points C (`Wheels!C42`) and H (`Wheels!C47`). | Corrected; the workbook value is kept as `wheels.dual.workbookG`. The saved example (single axle) is unaffected | Confirm the intended geometry |
| C5 | Medium | T48 flexural strength: `Design!N23` displays `0.7 sqrt(1.1 f'c)` labelled "0.7*sqrt(f'c)", while `Design!E25` uses `0.7 sqrt(f'c)` for method T. Revision 5.07a says the default changed to T48, but the saved `Design!E23` is A (`Settings!C24` stores T). | Reproduced; both values displayed | Confirm the T48 Cl 3.3.6 value and the intended default |
| C6 | Medium | Digitised charts with no retained source: Chandler Fig 2 stress increases (VBA `Trans`, `Radial`, `TransEdge`, `RadialEdge`; points `Graphs 1!B10:D65`), Fig 3 aisle moment (VBA `Moment`; points `Graphs 2!A3:J36`), bound sub-base (`Settings!H87:H89`, `Graphs 3`), CBR to K (VBA `MSR`). | Reproduced; flagged as a risk | Verify against TR550 and T48 scans |
| C7 | Medium | The Chandler stress constants (2.7, 5.19, 41.2) and the Kelley edge form could not be checked against TR550. They agree with Westergaard 1926 (interior 0.12 %, edge 1.4 % to 4.4 %). | Reproduced | Verify against TR550 |
| C8 | Low | Custom loads are entered in kN and converted to tonnes as `CPL / 10` (`Custom!H30:H32`), while the per-tonne constants use 9.81 kN. Custom stresses are 1.9 % low for a given kN. Rack loads are consistent (both use 10 N/kg). | Reproduced | Convert with 9.81, or enter the custom load as mass |
| C9 | Low | `Moment` takes Integer arguments, so `l` and the aisle are rounded (banker's rounding). | Reproduced | None |
| C10 | Low | `f'c < 25` MPa gives "Unsuitable" and "Error" (`Settings!N64:N65`) without affecting any result. | Corrected: `abrasionGrade` | Confirm the thresholds against T48 Tables 1.6 and 1.7 |
| C11 | Low | Clause references: `Reinft!D20` cites AS 3600 Cl 9.5.3.3 and 9.5.3.1 for shrinkage; the Tedds AS 3600-2018 slab calculation cites Cl 9.4.3. Punching references (Cl 9.3.1.3, 9.3.1.4, 9.3.3, `phi = 0.7`) match Tedds. | Module cites Cl 9.4.3 for shrinkage | Confirm against the printed Standard |
| C12 | Low | `Uniform!E49` uses `0.031387`, 1.5 % below `6 x 5.313 x 10^-3`; its provenance is unknown. `Uniform!E34` uses 5.313 against the exact 5.318. | Reproduced | Confirm with Hetenyi (1946) |
| C13 | Low | `Design!E60` uses the quadratic 1999 fit when T48 2009 is not selected and ignores the `useold1999` switch and the log fit (`Settings!H87`, `I90`). The quadratic is 10 % below the `Graphs 3` table at CBR 5, 150 mm. Information only. | Reproduced | Review the 1999 fit |
| C14 | Low | For `250 < h <= 500` the AS 3600 shrinkage mesh is labelled "Top & Bottom" (`Reinft!G20`) while the area is for the full thickness. | Reproduced | Clarify whether the area is per face |
| C15 | Medium | Rack, wheel and uniform loads are checked in isolation, and only the post punching and bearing use a load factor (1.5). No combination of rack post and forklift wheel near the same point is made. | By design | Consider a combined check for racks beside aisles |
| C16 | Low | Edge and corner stresses use the internal Dexian layout of adjacent posts; the workbook only warns. | Reproduced with a warning; the `location` group checks applicability | Use the custom layout at edges and corners |
| C17 | Low | `Settings!C11:C123` is a stored copy of settings that differs from the live inputs (fmethod T, cjlen 24 000, CustomA 2863.43). It is not stale results, but it is misleading. | Not used | None |

## 5. Deliberate departures from the workbook

These are listed in `README.md`: C1, C2, C3 (including the removal of the 1.025 "Accept"
band), C4, C10, `ValueError` for inputs outside a method, `inf` for invalid stresses, the
`SAME` or `LIST` custom load mode, the optional `location` check, and the ARC Slabex, ARC
table and drawing macro exclusions. When `Bogie = 0` and distances are reduced by the loaded
radius, the unused dual axle point F is taken as absent rather than negative.

## 6. Future development

1. Verify the Chandler constants and digitised charts against TR550 and T48 (C5 to C7), and
   store verified chart data with provenance.
2. Add a combined rack and wheel check and cumulative fatigue (Miner) over a load spectrum.
3. Add joint design: dowel and aggregate interlock load transfer, sawn joint spacing and
   curling stresses.
4. Add an optional ultimate (yield-line) check only if an Australian basis for its factors is
   identified; do not import TR34 factors.
5. Add the ARC Slabex fibre option only with the supplier's current data.
6. Obtain a T48 or TR550 worked example and add it to the baseline.
