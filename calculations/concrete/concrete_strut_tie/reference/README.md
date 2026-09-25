# Reference Evidence

## Source

| Item | Value |
| --- | --- |
| Document | `Concrete_NonFlexural_504.xls`, Structural Toolkit module **STRUT & TIE V5.04** (revision 5.04c) |
| Description | Design of Strut and Ties (AS3600-2018 Section 7 and 12) |
| Standards cited | AS 3600:2018 incl. Amdt 1 and 2; Foster, Kilpatrick and Warner, *Reinforced Concrete Basics* 2E (Pearson, 2010) and *Reinforced Concrete Basics* (Pearson, 2021) |
| Source SHA-256 | `e3986278aff3394bab4708fa5bbbf6079bb770cb4dd10568e9d7a7ec8347d922` |
| Decoded XLS SHA-256 | `169f9caab1f82685bb64854e4d43713acff77ffb75b383e2c2567f16adf85053` |
| Static review | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_NonFlexural_504.md` |
| Complete extract | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_NonFlexural_504.audit.json` |
| VBA extract | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_NonFlexural_504.vba.txt` |
| Cell listing used | `artifacts/workbook-extracts/Concrete_NonFlexural_504.cells.txt` |
| Extracted | 24 September 2026 |

The originals are held in the workbook review workspace and are not copied here.

## Extraction procedure

The expected values were taken cell by cell from the cached values in the cell listing,
covering sheet `Design` (`E20:E227`, `D77:J91`, `I8:I16`) and sheet `Settings` (`O28`,
`N45:O50`). Excel was not re-run. Forces are cached in kN; the baseline stores them x 1000
in N. The VBA module `Module1.bas` holds `FindAngle` (a GoalSeek of `angerror` on `ang`)
and the example loaders `example73`, `exampletest1` and `exampletest2`. The saved sheet
matches `example73`, followed by `FindAngle`.

## Saved-state notes

* Converged: `Design!L46` (`angerror`) is 0.
* `Cserv`, `Vr*` and `Vr.serv` are example formulas (`E21`, `E23`, `E24`) and are entered as values.
* `dz` is `Design!E118 = Lsyh`, entered as a manual 150.32875 mm.
* The bar centres were not re-spaced (`D78`/`H78` against `I90`/`I91`). The example fails the
  cracking check (`I13`, 1.29).
* `Settings!P51` refers to an undefined name, `Tbstaruu`. This does not affect the saved values.

## Outstanding

There is no worked example independent of Structural Toolkit. Agreement with this baseline
shows transcription fidelity only.
