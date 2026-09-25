# Technical Review: Concrete Strut-and-Tie Design

| | |
| --- | --- |
| Module | `concrete-strut-tie` `v0.0.1` |
| Source | Structural Toolkit STRUT & TIE V5.04 (revision 5.04c), `Concrete_NonFlexural_504.xls` |
| Standard | AS 3600:2018 incl. Amendments 1 and 2 |
| Reviewer | Automated transcription and review. **An independent engineer still needs to review this module.** |
| Date | 24 September 2026 |
| Overall opinion | **Sound in principle, but the workbook's own checks were incomplete; suitable for release only after independent review and confirmation of five cited clauses.** The strut, tie, node and bearing formulas are the standard AS 3600 Section 7 expressions and agree with Tedds. The transcription is exact (149 values). The workbook's summary could report OK while its own geometric rules failed, and its strut ratio is always 1.00 by construction; both are corrected. The bursting-reinforcement logic is the author's interpretation of Cl 7.2.4 and is reproduced, not endorsed. |

## 1. What the calculation does

The model is a single bottle-shaped strut between a support node, through which the tie
passes (CCT by default), and a loaded node. The workbook draws both nodes as hydrostatic:
a strut of depth `dc` has a bearing footprint `w = dc sin(theta)` and a tie face `Omega = dc
cos(theta)` (Fig 7.2.4(A)). The calculation runs in seven steps.

1. **Strut angle.** `theta` is found so that `theta = theta_az = atan(z / a)`, where the node
   centres are separated by `a = Lstrut - 2 w1` and `z = D - Omega`, with
   `w1 = dc / (2 sin(theta)) - w / 2`. Either distance may be entered instead. When both are
   calculated, `z / a = tan(theta)` holds exactly at `theta = atan(D / Lstrut)`, because
   `a = Lstrut - dc cos^2(theta) / sin(theta)` and `z = D - dc cos(theta)`.
2. **Strut.** `betas = 1 / (1 + 0.66 cot^2(theta))`, limited to 0.3 to 1.0 (Eq 7.2.2).
   The design stress is `phi fcu = 0.65 betas 0.9 f'c` (Cl 7.2.3). The depth for full capacity is
   `dc.max = C* / (phi fcu bc)`. The strut needs a support length `Lrg = dc.max sin(theta) + dz`,
   where `dz` is the tie development zone.
3. **Bottle.** The strut length is `Ls = sqrt(a^2 + z^2)` and the bursting length is `lb = Ls - dc`.
   The vertical and horizontal bars cross `lb.1 = lb sin(gamma1)` and `lb.2 = lb sin(gamma2)`, giving
   crossing areas `Asi1` and `Asi2`.
4. **Bursting forces (Cl 7.2.4).**
   * Strength: `Tb* = C* tan alpha*` with `tan alpha* >= 0.2`. Capacity
     `phiTb = 0.85 [(Asi1 - Asvr) fsy1 sin(gamma1) + Asi2 fsy2 sin(gamma2)]`, where
     `Asvr = Vr* / (0.85 fsy1)` is the vertical steel used by the additional load.
   * Serviceability: `Tb.s = Cserv tan alpha.s` with `tan alpha.s >= 0.5`, steel at `fsi` =
     350, 250 or 200 MPa for minor, moderate or strong crack control (Cl 12.7 as cited).
   * Cracking: `Tb.cr = 0.7 bc lb f'ct`, `f'ct = 0.36 sqrt(f'c)` (Eq 7.2.4(1), Cl 3.1.1.3), carried
     at `0.85 fsy` ("reference 2") or `fsi`.
   * Reinforcement is required only if `Tbb* = 0.5 C* > 0.5 Tb.cr`.
   * Required areas split the bursting force as `Tb sin(gamma1)` and `Tb sin(gamma2)`
     between the directions, giving the maximum bar centres for each case.
5. **Tie (Cl 7.3.2).** `phiT = 0.85 fsy Ast`.
6. **Development zone (Cl 7.3.3, Cl 13.1.2.2).**
   `Lsy.tb = 0.5 k1 k3 fsy db / (k2 sqrt(f'c)) >= 0.058 fsy k1 db`, then the bundle,
   epoxy, lightweight and slip-form multipliers, and 50 % for a cog. By default,
   `dz = max(50% Lsy.h, 50% Lsy.t) + cover`.
7. **Node and bearing.** The nodal stress limit is `sigma3 = 0.65 betan 0.9 f'c`, with
   `betan` = 1.0, 0.8 or 0.6 for CCC, CCT or CTT nodes (Cl 7.4.2). The bearing limit is
   `0.6 min(1.8 f'c, 0.9 f'c sqrt(A2/A1))` (Cl 12.6).

## 2. Validation undertaken

| Check | Method | Outcome |
| --- | --- | --- |
| Transcription fidelity | Replayed the saved example against 142 cached cell values plus 7 printed two-decimal ratios (`Design!I8:I16`) in `data/workbook-baseline.json`. Relative tolerance `1e-9`; the printed ratios are compared at half a display unit | All 149 agree |
| GoalSeek replacement | The saved state is converged (`Design!L46 = 0`). Direct `atan(z/a)` reproduces `Design!E34` exactly. The scan-and-bisection solver was tested with one manual distance, and the residual is below `1e-9` degrees | Agree |
| Geometry identity | Proved algebraically (section 1). Tested with `a` and `z` calculated: `theta_az = theta` to `1e-9` | Agree |
| Hand calculations | Independent calculations of `betas`, `dc.max`, `Tb.cr`, bursting capacity, tie, development length and bearing for a 3 m x 3 m, 400 mm, 40 MPa panel (`tests/test_engine.py`) | Agree |
| Dimensional consistency | `dc.max = C*(N) / (MPa x mm)` gives mm. `Tb.cr = mm x mm x MPa` gives N. `Asvr = N / MPa` gives mm2 | Consistent |
| Physical sense | 96-case sweep over geometry, angle modes, strength and reinforcement. Checked that results repeat, inputs are not mutated, there is no NaN, `worstUtil` is the finite maximum, any infinite value has a reason and forces FAIL, and `dc = dc.max` gives `phiC = C*` | Pass |
| Hydrostatic node | Strut face stress equals `phi fcu`; the tie face `Omega = dc cos(theta)` reproduces `Design!E44` | Consistent with `ws = lb sin(theta) + u cos(theta)` (Tedds half joint) |
| Independent benchmark | Tedds *RC corbel design (AS3600)* 1.0.00 and the generic parts of *Precast half joint* and *RC nib design* (section 2.1) | Same Section 7 formulas and factors |

### 2.1 Comparison with Tedds

| Aspect | Workbook | Tedds | Adopted here |
| --- | --- | --- | --- |
| Strut efficiency factor | `1/(1 + 0.66 cot^2 theta)`, 0.3 to 1.0 | Same (AU corbel, "cl. 7.2.2") | Same, confirmed |
| Strut strength | `phi betas 0.9 f'c bc dc` | Same ("eqn 7.2.3") | Same |
| Capacity reduction factors | 0.65 strut, 0.85 tie, 0.6 bearing (editable) | `phi.st.c = 0.65`, `phi.st.t = 0.85`, `phi.b = 0.6` | Same, fixed |
| Strut width | `dc = dc.max`, then support length `Lrg <= Lr` (printed only) | Solves the strut width from the node stress and statics (quadratic), then checks `Fstrut >= F` | Workbook sizing retained, and `supportLength` now counts. The two are equivalent statements of fit |
| Node check | User-entered `sigma_o` (0 in the example) against `phi betan 0.9 f'c` | Required node depth `F / (phi betan 0.9 f'c b)` from the tie force, against the provided depth. The half joint uses `F/(tan theta u b)` | **Added** as optional `nodeFaces`: strut, bearing and tie face stresses from `C*`, `Cv*` and `T*`. `u` defaults to the workbook's hydrostatic `dc cos(theta)` |
| `betan` | 1.0 / 0.8 / 0.6 | CCT 0.8 | Same |
| Bearing | `phi 0.9 f'c sqrt(A2/A1) <= phi 1.8 f'c`; A1 and A2 default to `bc Lr` | Same form; A2 is built from the plate position and edge distances | Workbook form, with manual A1 and A2. Geometric A2 needs plan inputs; not adopted |
| Tie | `T* / (phi fsy)` | Same | Same |
| Bursting reinforcement | Cl 7.2.4 strength, serviceability and cracking | Not in Tedds. The corbel uses stirrups `>= 0.5 Ast`, a corbel detailing rule | Workbook. The stirrup rule is not adopted: it is specific to corbels |
| Minimum tie steel | None | `0.20 (D/d)^2 fct.f / fsy b d` (Cl 8.1.6.1) | Not adopted. It is a flexural-member rule and does not apply to a general tie |
| Strut angle | 30 degrees minimum | Nib (EN 1992): `1 <= cot theta <= 2.5` | AS 30 degree rule. The EN 1992 limit is rejected as not AS-based |
| Edition | 2018 | The AU corbel is labelled AS 3600-2001, which is **superseded**; its Section 7 formulas and factors match the 2009/2018 editions | No edition-specific item adopted from Tedds |
| Pile cap, deep beam | Not applicable | ACI 318 / EN 1992 / BS 8110 only | Not used |

## 3. Opinion on the theory

* **Section 7 expressions.** `betas`, `phi fcu`, `betan`, the tie capacity and the Cl 12.6
  bearing limits are the standard AS 3600:2018 expressions. Tedds uses the same expressions
  independently.
* **Strut sizing.** Setting `dc = dc.max` makes `C*/phiC = 1.00` by construction. The real test
  is whether the strut fits: `Lrg <= Lr`, or equivalently `dc.max <= dcg = (Lr - dz)/sin(theta)`.
  The workbook printed this only as an error. It is now a utilisation. The hydrostatic node
  geometry is internally consistent: bearing face `dc sin(theta)`, tie face `dc cos(theta)`,
  and strut width `ws = Lb sin(theta) + u cos(theta) = dc`.
* **Bursting.** Splitting the force into `Tb sin^2(gamma)` shares, and the capacity
  `sum(Asi fsy sin(gamma))`, are correct for orthogonal bars. Several parts are the author's
  interpretation and are not code text: subtracting `Asvr` from the crossing area,
  the `Tbb* = 0.5 C*` threshold, and the choice between `phi fsy` and `fsi` in the cracking
  check. The saved example fails the cracking check (1.29), because the bar centres were not
  re-spaced after the 2018 update (C4).
* **Development zone.** `dz = 50 % Lsy + cover` is a reasonable reading of Cl 7.3.3. The
  saved example overrides it with `dz = Lsyh` (150 mm, against 398 mm calculated). That
  shortens `Lrg` and flatters `supportLength`.

## 4. Areas of concern

| ID | Severity | Concern | Status in this module | Recommended action |
| --- | --- | --- | --- | --- |
| C1 | **High** | With `dc` blank, `Design!E68 = dc.max`, so `E130 = C*` and `I8` always shows `OK (1.00)`. The governing fit check `Lrg > Lr` (`E64` against `E31`) appears only as text in `E18`/`G31`, and is absent from the summary `B8:I17`. | `supportLength` added to `worstUtil`; `strut = dc.max/dc` | None, beyond sign-off. |
| C2 | **High** | The node and bearing checks are vacuous in the saved example: `sigma_o = 0` (`E209`) and `B* = 0` (`E217`) are user entries. The node stress is never derived from the model. | Reproduced. The optional `nodeFaces` group computes face stresses. `bearingMode = C` (default) uses `Cv*`, as `Settings!C70` intended | Make `nodeFaces` mandatory after review. |
| C3 | Medium | Several of the workbook's own rules are printed but do not affect the status: `G33` (`theta < 30`, `theta <> theta_az`), `G157`/`G172`/`C70` (vertical steel less than `Asvr`), and `E25` (f'c range). When `Asvr > Asi1`, `tbmax1` goes negative and just lowers the capacity. | Counted as `strutAngle`, `angleCompatibility` and `verticalLoadSteel`; f'c raises `ValueError` | None. |
| C4 | Medium | The saved centres of 208 and 225 mm (`D78`, `H78`) exceed the required 181 and 159 mm (`I90:I91`). The "Auto Reinf't Spacing" routine that `T8` refers to is not in the VBA extract. `I13` shows `No Good (1.29)`. | Reproduced: the example FAILS | Designers must re-space. Record this as a known saved-state defect. |
| C5 | Medium | Bursting reinforcement is required when `Tbb* = C* x 0.5 > 0.5 Tb.cr` (`E182:E184`, `Settings!O50`). This is the v5.01 author note "bursting requirement checked using alpha=0.5". `Settings!T48` marks a variant "NOT PART OF CODE". | Reproduced | Confirm the Cl 7.2.4 wording. |
| C6 | Medium | In the `fsi` branch (`useref2 = N`), the cracking capacity `E191` subtracts the strength area `Asvr` (`I148`), not `Asvr.s` (`I164`). `Design!T9` also records that Tb.cr was previously misused from the older reference. | Reproduced | Decide on the intended area and correct it in a future version. |
| C7 | Medium | `E110:F110` use `sqrt(f'c)` without the 65 MPa cap stated in `K110`. | Corrected (`f'c <= 65`) | None. |
| C8 | Medium | The slip-form input `Settings!N83` (`sk`, "Cl 13.1.2.2 (c)") is marked "< Not used" (`S83`), so the factor is never applied. | The module applies 1.3 when `sk = Y` | Confirm the 1.3 factor against the printed Standard. |
| C9 | Low | `C70` tests `OR(gamma1 < 40, gamma2 < 40)` for one-way bars, whichever direction is present. The rule has no clause reference; it resembles the ACI 318 provision. | Tests the angle of the bars provided | Confirm the source, or remove the check. |
| C10 | Low | `Settings!N77` repeats the same condition twice. `Settings!P51` refers to the undefined name `Tbstaruu`, which would give `#NAME?` when false. `J91` labels the horizontal governing case from the vertical variables. | Presentation only; not reproduced | None. |
| C11 | Low | The φ values are editable cells (`E126`, `E201`, `E218`). Table 2.2.4 may give a lower tie φ for Class L bars. | Fixed at 0.65, 0.85 and 0.6; Class L not offered (`fsy` 400 or 500) | Confirm Table 2.2.4 for Class L before adding it. |
| C12 | Low | A manual `dz` (`E118 = Lsyh`) is accepted even when it is less than 50 % Lsy + cover. | Warning | Consider making this a check. |
| C13 | Low | These clause citations are the workbook's and were not verified: Cl 7.1 (30 degrees), Eq 7.2.4(4) (`lb`), Cl 12.7 (`fsi` and spacing classes). | Cited as the workbook | Verify against the Standard. |
| C14 | Low | `Cserv > C*` is flagged in `E18` but the calculation continues. A custom `fsi <= 0` becomes 0.001 (`E74`). | `ValueError` | None. |
| C15 | Low | In the saved example, `Vr*` and `Vr.serv` (`E23:E24`) are formulas tied to `gamma2` (Michael's example). | Entered as values | None. |
| C16 | Low | The Excel strut ratio `5424/5423.999999999999` is 1-ulp above 1. It shows OK only because Excel compares with tolerance. | `dc.max/dc` gives exactly 1.0 | None. |

## 5. Deliberate departures from the workbook

These are listed in `README.md`:

* C1: `supportLength` is counted, and the strut ratio is `dc.max/dc`.
* C3: `strutAngle`, `angleCompatibility` and `verticalLoadSteel` are counted.
* `bottleLength` is counted, and a zero bursting length is treated as unattainable.
* A non-positive bursting capacity gives `inf`.
* C7: f'c is capped at 65 MPa for development.
* C8: the slip-form factor is applied.
* C9: the one-way angle is taken from the bars provided.
* C11: φ values are fixed.
* C14: invalid inputs raise `ValueError`.
* The GoalSeek is replaced by a deterministic solver.
* The optional `nodeFaces` group is added (§2.1).
* A warning is given for a short manual `dz`.

## 6. Future development

1. Confirm the five unverified citations (C5, C8, C13) and Table 2.2.4 for Class L ties.
2. Make the node face stresses mandatory. Also check the loaded node, with its own `betan`
   and face lengths.
3. Resolve C6 and decide whether `dz` below the calculated value should fail (C12).
4. Add a truss module that finds member forces and passes each strut and tie to this module.
5. Obtain an independent worked example, for example the *Reinforced Concrete Basics* (2021)
   transfer-wall example that the workbook cites, and add it to the baseline.
