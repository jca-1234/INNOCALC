# Technical Review: Concrete Wall Design

| | |
| --- | --- |
| Module | `concrete-wall` `v0.0.1` |
| Source | Structural Toolkit CONCRETE WALLS V5.11, `Concrete_Wall_511.xls` |
| Standard | AS 3600:2018 incl. Amendments 1 and 2; AS/NZS 1170.0:2002 |
| Reviewer | Automated transcription and review. **An independent engineer still needs to review this module.** |
| Date | 24 September 2026 |
| Overall opinion | **Sound in method for braced walls under axial load, after correction; suitable for release after independent review.** The Cl 11.5 simplified method, Cl 11.4 effective heights and Cl 11.6 in-plane shear are standard and are reproduced exactly (115 of 115 saved values). Three workbook defects could overstate capacity or understate steel: the single-layer 3 MPa branch, the omitted in-plane stress in the axial check, and a typo in the minimum vertical steel threshold. All three are corrected. Several workbook rules print "Error" but still report the capacity as OK; these now count towards `worstUtil`. The fire and horizontal-steel branches reproduce the workbook but contain interpretation questions (C7, C8, C9, C13, C14) that need checking against the printed Standards. |

## 1. What the calculation does

The module designs a planar wall per metre run in six steps.

1. **Actions (AS/NZS 1170.0 Cl 4.2).** Dead load at mid-height is
   `G = Ndl + 25 tw Hw / 2` when self weight is included (`Design!D30`, `Settings!O48`).
   * Strength: `N* = max(1.35 G, 1.2 G + 1.5 Q)`.
   * Earthquake: `Ne* = G + Eu + psi_E Q`, with `psi_E` = 0.3, 0.6, 0 or a user value.
   * Design action: `N* = max(N*, Ne*)`.
   * Fire: `Nf* = G + psi_l Q`, with `psi_l` = 0.6 (floor), 1.0 (storage), 0 (roof) or a
     user value (`Design!H28`).
   * Design eccentricity `e = max(e.input, 0.05 tw)` (Cl 11.5.4), giving
     `Moe* = N* e`.
   * Mid-height stresses `sigma.n = N* / tw` and `sigma.in = 6 Mi* / (tw Lw^2)`, giving
     `sigma.max` and `sigma.min`.
2. **Effective height (Cl 11.4).** `Hwe = k Hw` with:
   * top and bottom support: `k = 0.75` if restrained against rotation, else `1.0`;
   * three sides: `k = 1/(1 + (Hw/3L1)^2) >= 0.3`, but not above the one-way value;
   * four sides: `k = 1/(1 + (Hw/L1)^2)` if `Hw <= L1`, else `k = L1/(2 Hw)`;
   * `L1 = Lw`. A user `k` may be adopted; the module warns if it differs from the
     calculated value.
3. **Design method (Cl 11.1, Cl 11.2.1).** The workbook's `desmode` (`Settings!X130`):
   * 2, slab permitted: `sigma.min > 0`, `sigma.max <= 0.03 f'c` and `Hwe/tw <= 50`
     (Cl 11.1(b)(i));
   * 0, part tension: `sigma.min < 0` (Cl 11.2.1(b));
   * 3, column and slab: `Mo* > 0` (Cl 11.1(b)(ii));
   * 1, wall or column otherwise (Cl 11.2.1(a)).

   In mode 2 the wall is designed as a slab (`phiNuo`) when `Hwe/tw` exceeds the
   simplified limit or the user chooses "Design as wall = N"; otherwise as a wall.
4. **Design axial strength (Cl 11.5).** `ea = Hwe^2 / (2500 tw)` and
   `phiNus = phi (tw - 1.2 e - 2 ea) 0.6 f'c`, with `phi = 0.65` (Eq 11.5.3).
   * The simplified method is limited to `Hwe/tw <= 20` for one layer and 30 for two
     layers (Cl 11.5.2(c)).
   * One layer is limited to 3 MPa, so `phiNu <= 3 tw` (Cl 11.5.2(a)).
   * As a slab, `phiNuo = (0.03 f'c - sigma.in) tw`.
5. **Reinforcement (Cl 11.7).**
   * Vertical: `pwv >= 0.0015` if `sigma.max <= min(2, 0.03 f'c)`, else 0.0025.
   * Horizontal: `pwh >= 0.0025`, reduced to 0 (`Lw <= 2500`) or 0.0015 for walls
     unrestrained against horizontal shrinkage with `0.75 <= k <= 1`.
   * Limited ductile walls use 0.0025 each way and `pwv <= 16/fsy` (Cl 14.6.7).
   * Spacing `<= min(350, 2.5 tw)`, clear gap `>= 3 db` (Cl 11.7.3).
   * Crack-control ratios 0.0025, 0.0035 and 0.006 are tabulated (Cl 11.7.2).
6. **In-plane shear (Cl 11.6).**
   * `Vu.max = 0.2 f'c (0.8 Lw tw)`.
   * `Vuc = (0.66 sqrt(f'c) - 0.21 (H/Lw) sqrt(f'c)) 0.8 Lw tw` for `H/Lw <= 1`.
   * Otherwise the lesser of that and `(0.05 sqrt(f'c) + 0.1 sqrt(f'c)/(H/Lw - 1)) 0.8 Lw tw`.
   * In all cases `Vuc >= 0.17 sqrt(f'c) 0.8 Lw tw`.
   * `Vus = pw fsy 0.8 Lw tw`, where `pw = min(pwv, pwh)` if `H/Lw <= 1` and `pwh`
     otherwise.
   * `phiVu = 0.7 min(Vuc + Vus, Vu.max)`.

The optional fire group interpolates Table 5.7.1 (insulation, on `tw`) and Table 5.7.2
(structural adequacy at `mu.fi` = 0.35 and 0.70, one or two sides exposed, on the axis
distance and on `tw`). It then interpolates between the two load levels on
`mu.fi = Nf*/phiNu`, or 0.7 if selected. Adequacy is zero when `mu.fi > 0.7` or
`Hwe > 40 tw` (top support needs an FRL) or `50 tw` (otherwise). It is deemed equal to
insulation when the top support is on one side only and needs no FRL (Cl 5.7.2).
Finally `FRL = min(adequacy, insulation)`.

## 2. Validation undertaken

| Check | Method | Outcome |
| --- | --- | --- |
| Transcription fidelity | Replayed the saved state against 115 cached values from `Design`, `Shear` and `Settings` in `data/workbook-baseline.json`, relative tolerance `1e-9` | All 115 agree. `Design!E64` is excluded (departure D1) |
| Effective height | Hand-checked four-sided `k = L1/(2 Hw)` for `Hw > L1`, and the three-sided cap at 0.75 | Agree |
| Simplified method | Hand calculation of the default wall: `N*`, `ea`, `Nus`, `phiNu`, utilisation | Agree |
| Single-layer correction | Wall with `Hwe/tw = 19`, `e = 60 mm`: `phiNus = 433 < 3 tw = 450 kN/m` is adopted | Agree; the workbook would report 450 |
| In-plane shear | Hand calculation of a squat wall (`H/Lw = 0.5`, `pw = min(pwv, pwh)`) | Agree |
| Fire tables | Hand interpolation of Table 5.7.1 at 130 mm (140 min), Table 5.7.2 at `a.s = 30` (105 min) and `tw = 185` (150 min) | Agree |
| Exposure | The VBA `CalcExposure` reproduces `Design!H24 = C1`; required-cover table spot checks | Agree |
| Method selection | Tension, out-of-plane moment, slab, unbraced and ductile Class L cases | Each reports `FAIL` with a "Not applicable" or "Unattainable" headline, or the slab capacity |
| Physical sense | 54-case sweep: geometry, restraint, layers, strength, loads and in-plane moment. Checks `k`, `phiNu <= 3 tw` for one layer, `Vuc.min <= Vuc`, `Vu <= Vu.max`, repeatability, no mutation, and no OK for a failing case | Pass |
| Independent benchmark | Compared with Tedds *RC wall design (AS3600)* 1.0.10 (AS 3600-2018 Amdt 1 and 2) and *Tilt-up wall panel design (AS3600)* 1.0.10 | See section 2.1 |

### 2.1 Comparison with Tedds

Tedds *RC Wall Design (AS 3600-2001)* keeps its 2001 library name, but version 1.0.10
(27 October 2021) is "enhanced to AS3600-2018 incorporating Amendment No. 2". The tilt-up
calculation 1.0.10 is also 2018 Amdt 1 and 2, but takes its P-delta method from ACI 318-08
Section 14.8. The generic *RC Shear wall design* (ACI 318) and *Basement wall design*
calculations contain no AS 3600 content and were not used. The only AS-NZS Tedds data
table for walls, `Aust_ 3600-94-4.10.3.2`, is the superseded 1994 cover table and was not
used.

| Aspect | Workbook | Tedds | Adopted here |
| --- | --- | --- | --- |
| Design route | Cl 11.5 simplified method, with slab/column routing (Cl 11.1, 11.2.1) | Designs every wall as a column strip to Section 10: short/slender, moment magnifier, P-M interaction | Workbook. The column route belongs to the concrete column module; the workbook's `As Column` sheet says the same |
| `phi` for the simplified method | 0.65 (2018) | Not used. 2001 editions used 0.6 | 0.65. **Tedds-era 0.6 is outdated** |
| Effective height | Cl 11.4 calculated for 2, 3 and 4-sided support | User `k` from a drop list | Workbook |
| Minimum vertical steel | `0.0015` if `sigma.max < MIN(2, 3 f'c)` (typo) | `0.0015` if `N*/Ag <= min(0.03 f'c, 2 MPa)`, else 0.0025 | **Tedds threshold**, with the workbook's `sigma.max` (D2) |
| Maximum vertical steel | Only `16/fsy` for ductile walls | `0.04 Ag` (a column rule) | Workbook; the 4 % limit is a Section 10 provision |
| Horizontal steel, restrained walls | Cl 11.7.2 ratios tabulated for information | Required `pw` = 0.0025, 0.0035 or 0.006 by degree of control, and 0.006 for B1 to C2 | **Added** as the optional `crackControl` group |
| Horizontal steel, unrestrained walls | 0 or 0.0015 when `0.75 <= k <= 1` | 0.0015 for one-way buckling, chosen by a checkbox | Workbook (concern C8) |
| Walls over 500 mm thick | Not treated | Minimum steel near each face based on 250 mm | Not adopted: the clause basis could not be confirmed |
| Bar spacing | `<= min(350, 2.5 tw)`, clear gap `>= 3 db` | Same maximum; centre spacing `> 3 db` | Workbook (stricter) |
| In-plane shear | Cl 11.6, `phi = 0.7` | Not checked | Workbook |
| Out-of-plane shear | Not checked | Cl 8.2.4 (2018), simplified or general `kv`, `phi = 0.7` | Not adopted; out-of-plane loading is outside scope. Future work with the slab route |
| Fire | Tables 5.7.1 and 5.7.2 interpolated to an FRL; never compared with a requirement | Required FRP gives `bmin` and `a.s` by table look-up, then checks thickness and cover | Workbook tables, plus a **required FRL comparison** (optional `fire` group) |
| Durability | Exposure class achieved by the cover (VBA `CalcExposure`) | Checks the cover against the required class (Tables 4.10.3.2/3) | **Added** as the optional `durability` group, with bracketed values flagged as needing the Cl 4.3.2 concession |
| Bar restraint | Note: not required if `N* <= 0.5 phiNu` (Cl 11.7.4) | Note on fitments; uses `pv <= 0.01` in one item and `0.02` in another | Informative ratio and warning only |
| Slab route limits | `Hwe/tw <= 50` | Tilt-up: `lambda = Hwe/Lw <= 50` | Workbook. Tedds' use of `Lw` appears to be a defect |

## 3. Opinion on the theory

* **Simplified method.** `phi (tw - 1.2 e - 2 ea) 0.6 f'c` with `ea = Hwe^2/(2500 tw)` is
  the long-standing AS 3600 wall equation. It applies to braced walls with limited
  slenderness, so the module now asks whether the wall is braced. The 2018 `phi = 0.65`
  is used; the 0.6 of earlier editions is superseded.
* **Single layer.** The 3 MPa limit is a condition on the simplified method, not a
  resistance. The workbook uses `3 tw` as the capacity whenever the stress exceeds 3 MPa,
  even for a wall too slender for any capacity, and it zeroes the displayed `Nus`. The
  module takes the lesser of `3 tw` and `phi Nus`, and reports the stress rule separately.
* **In-plane bending.** The simplified method is applied per metre. With in-plane bending,
  the most compressed metre carries `N* + sigma.in tw`. The workbook uses the in-plane
  stress to choose the method but leaves it out of the axial check. The module includes
  it. In slab mode the workbook already deducts `sigma.in` from `phiNuo`, so the module
  does not add it twice.
* **Effective height.** The Cl 11.4 expressions are transcribed correctly. See C9 for the
  four-sided case.
* **In-plane shear.** The Cl 11.6 expressions and the "lesser of" rule for `H/Lw > 1` are
  consistent with AS 3600 practice. The `Vu.max` crushing limit is applied.
* **Fire.** The table interpolation follows Cl 5.3.2 practice. The load-level
  extrapolation above 0.7 is suppressed, as it should be. C13 and C14 are clause
  interpretations to confirm.

## 4. Areas of concern

| ID | Severity | Concern | Status in this module | Recommended action |
| --- | --- | --- | --- | --- |
| C1 | **High** | One layer with `sigma.max > 3 MPa` gives `phiNu = 3 tw` whatever the slenderness and `Nus` (`Settings!X125:X128`, `Design!E64:E66`). With in-plane stress, a wall with `N*/tw < 3 MPa` could pass while too slender. | Corrected (D1). `singleLayer` also reports `sigma.max / 3` | None, beyond sign-off |
| C2 | **High** | The axial check `Design!I9` compares the uniform `N*` with `phiNu`; `sigma.in` (`Design!I35`) is ignored for walls. | Corrected (D3) | Reviewer to confirm the per-metre treatment of in-plane bending |
| C3 | Medium | `Design!H41` uses `MIN(2, 3*fc)`, which is always 2 MPa. `Settings!X112` (2009 rule) and Tedds use `min(2, 0.03 f'c)`; `Settings!Y113` says "2018 removed the 2MPa limit". | Corrected to `min(2, 0.03 f'c)` (D2), which is conservative | Confirm AS 3600:2018 Cl 11.7.1(a). If only `0.03 f'c` applies, the module is conservative for `f'c > 66.7` MPa |
| C4 | Medium | Reinforcement, single-layer and ductile-wall rules print "Error" (`Design!D39`, `G45:G48`, `G55:G56`), but `Design!I9` shows only the axial ratio. | Counted in `worstUtil` (D4) | None |
| C5 | Medium | For walls in tension, walls needing column design, or `desmode2error`, `Design!I9` shows text rather than a failure. | `designMethod` is infinite and the summary says "Not applicable" (D4) | None |
| C6 | Medium | The workbook never asks whether the wall is braced. | `braced` input added (D5) | None |
| C7 | Medium | `psi_l` = 0.6 (floor) and 1.0 (storage) (`Design!H28`, labelled "Table 4.1 (Conc.)") exceed the distributed-action values of AS/NZS 1170.0 Table 4.1. This is conservative for `Nf*`. | Reproduced | Confirm the intended Table 4.1 row. Consider offering distributed and concentrated rows |
| C8 | Medium | The unrestrained horizontal-steel reduction is triggered by `0.75 <= k <= 1` (`Design!H52`), not by one-way buckling. A user `k`, or a four-sided `k = 0.8`, can trigger it for a two-way wall. | Reproduced | Replace with an explicit one-way/two-way condition, as Tedds does |
| C9 | Low | The four-sided `k` (`Design!G106`) is not capped at the one-way value. For `Hw/L1 < 0.58` with rotational restraint it exceeds 0.75. The three-sided case is capped. | Reproduced | Confirm Cl 11.4(c); cap if intended |
| C10 | Low | `Design!G55` checks the horizontal clear gap against `3 db.v`. | Corrected to `3 db.h` (D6) | None |
| C11 | Low | `Shear!E36` guards `Vucb` with `hwe = Lw` instead of `H = Lw`. | `Vucb` is computed only for `H/Lw > 1` (D6) | None |
| C12 | Low | Table 5.7.1 is interpolated from (0, 0) below 60 mm (`Settings!U35:V37`), giving FRLs below 30 min. | Reproduced | Treat walls under 60 mm as having no FRL |
| C13 | Medium | Adequacy is deemed equal to insulation when the top support is on one side only and needs no FRL (`Settings!O52`, `Design!E83`). This bypasses both `mu.fi > 0.7` and the `Hwe` limit. The saved example reports FRL 240 min while printing "Error - mu.fi > 0.7". | Reproduced, with a warning | Confirm the scope of the Cl 5.7.2 deemed-to-satisfy provision |
| C14 | Low | The fire height limit is `40 tw` when the top support needs an FRL, else `50 tw` (`Design!E84`, Cl 5.7.3). | Reproduced | Confirm against Cl 5.7.3 |
| C15 | Low | The axis distance is `cover + db.v/2` (`Design!D23`) for any layer order. With one central layer, the input cover can disagree with the geometric cover: the saved example has 64 mm against 82 or 94 mm. | Reproduced. The module warns if the input exceeds the geometric cover | Derive the axis distance from the geometry for one central layer |
| C16 | Medium | Openings beyond the Cl 11.4 limits are only a message (`Design!D87`). The saved example has `Ho = 5000 > Hw/3`. | Warning and limitation | Add a design of the portions between openings, or block the check |
| C17 | Low | The `Lw/tw < 4` warning cites Cl 5.6.2 (`Design!B12`). | Reproduced as a warning | Confirm the clause (the member definition may be intended) |
| C18 | Low | The `Settings!B19:C153` "Save Properties" block stores a different member (`f'c = 40`, `tw = 150`). The `ACI` sheet is unverified. | Not used | None |

## 5. Deliberate departures from the workbook

| ID | Departure | Effect on the saved example |
| --- | --- | --- |
| D1 | One-layer capacity `min(3 tw, phi Nus)` within the slenderness limit; `Nus` always reported per Eq 11.5.3 | None on `phiNu` (600 kN/m); `Design!E64` excluded from the baseline |
| D2 | `pwv.min` threshold `min(2, 0.03 f'c)`, compared with `<=` | None (4.05 MPa gives 0.0025 either way) |
| D3 | Wall-mode axial demand `N* + sigma.in tw` | None (`Mi* = 0`) |
| D4 | Rule failures and method applicability counted in `util`: `designMethod`, `singleLayer`, `ductileWall` and all reinforcement rules | `singleLayer` = 1.35 is now reported |
| D5 | `braced` input | None (`Y`) |
| D6 | Horizontal gap uses `db.h`; `Vucb` guard on `H/Lw` | None |
| D7 | Optional `fire` group with a required FRL; optional `crackControl` and `durability` groups from Tedds | Fire values unchanged; utilisation added |
| D8 | `kMode` chooses a calculated or user `k`, with warnings | None (`USER`, `k = 0.74`) |
| D9 | `ACI`, `Thermal` and `As Column` sheets and the `MeshName` routine not transcribed | Presentation and superseded content only |
| D10 | `f'c` outside 20 to 120 MPa, negative `Mo*`, `Mi*` or `V*`, and impossible bar layouts raise `ValueError` | None |

## 6. Future development

1. Confirm C3, C7, C8, C9, C13 and C14 against the printed Standards.
2. Add the out-of-plane design of walls treated as slabs (Section 9 with second-order
   moments), including out-of-plane shear to Cl 8.2.4. The workbook's `ACI` P-delta sheet
   and Tedds' tilt-up method are the starting points, but both need 2018 verification.
3. Hand walls needing column design to the concrete column module through an exchange
   action (the `As Column` sheet's route).
4. Treat openings and the wall portions between them (Cl 11.4).
5. Add a worked example from Foster, Kilpatrick and Warner, *Reinforced Concrete Basics*
   2E. The workbook's `RCB58` macro loads such an example, but its expected values are
   not retained.
