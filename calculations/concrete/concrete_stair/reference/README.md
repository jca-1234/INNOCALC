# Reference Evidence

## Source

| Item | Value |
| --- | --- |
| Document | `Concrete_Stair_506.xls`, Structural Toolkit module **CONCRETE STAIRS V5.06** |
| Description | Concrete stair design (`Settings!C5`) |
| Standard cited | AS 3600:2018 incl. Amendments 1 and 2; AS/NZS 1170.0:2002; AS/NZS 1170.1:2002 |
| Workbook revision | 5.06, Mar 2025, "Added inclined deflection modifier; default depth for moment capacity now based on perpendicular throat thickness" |
| Source SHA-256 | `a4595c0259739f751cc6efbb2cce54bce57dbd03f528867ad8442f9988b8a262` |
| Static review | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_Stair_506.md` |
| Complete extract | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_Stair_506.audit.json` |
| Extracted | 11 September 2026 |
| Permitted use | Internal transcription evidence for the InnoCalc `concrete-stair` module. |

The originals are held in the workbook review workspace and are not copied here.

## Extraction procedure

All 66 `Design` sheet formulas and the 15 `Settings` sheet formulas were read
from the review export's formula register with their cached values, cell by cell.
No Excel recalculation was performed. Every named cell referenced by a formula
was resolved back to its stored value, including `_k3`, `den`, `usefcmi`,
`layers`, `useVertD` and `UseGlobDef`.

## State of the saved example

The workbook is internally consistent: no GoalSeek, no circular references, no
broken names. It records one external link to `Footings_Pad.xls`, which was not
refreshed and which no `Design` sheet formula depends on.

The example is a **failed design** (`Settings!O29` = `1.11108960735`, bending
governing) and it also exercises the compression-steel-in-tension branch of
`Design!D54`. Both are reproduced by the baseline deliberately.

The `Design` sheet inputs differ from the `Settings` reset block; the cached
`Design` values are the design state and are the ones transcribed.

## Not transcribed

`Module1.bas` defines a `MeshName` VBA function that matches a rounded pair of
steel areas to a standard mesh designation such as `RL1218`. It is used only to
build descriptive text and affects no capacity, so it has not been transcribed.
The mesh inputs that feed it (`wdiav`, `ctswv`, `wdiah`, `ctswh`, `layers`) are
therefore also omitted. If a mesh designation is required, the full lookup must
be transcribed from the VBA and independently checked.

## Outstanding

No third-party worked example independent of Structural Toolkit has been
supplied. An independent hand calculation to AS 3600:2018 Sections 8, 9 and
Table 2.3.2 is required before release and must be recorded here with reviewer,
date and version.

The review must also decide whether the Cl 8.1.5 ductility limit and the
incremental deflection limit should contribute to the governing ratio. The
workbook computes both but excludes them from `Settings!O29`; this module
includes them.
