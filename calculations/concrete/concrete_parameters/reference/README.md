# Reference Evidence

## Source

| Item | Value |
| --- | --- |
| Document | `Concrete_Formula_502.xls`, Structural Toolkit module **FORMULA V5.02** |
| Description | Concrete formula; formulas for common concrete calculations (`Settings!C5`) |
| Standard cited | AS 3600:2018 incl. Amendments 1 and 2; AS 2327:2017 Table 3.6.2.3 |
| Workbook revision | 5.02, 29-Jun-21, "Revised fcmi curve fit, added AS 2327 fcmi, incorporated AS 3600 - 2018 Amendment 2, added 120 MPa to fcmi table" |
| Static review | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_Formula_502.md` |
| Complete extract | `C:/CODING/STK/Temp/Workbook_Reviews/Concrete/Concrete_Formula_502.audit.json` |
| Extracted | 10 September 2026 |
| Permitted use | Internal transcription evidence for the InnoCalc `concrete-parameters` module. |

The originals are held in the workbook review workspace and are not copied here.

## Extraction procedure

The workbook has 28 live formulas on the `Formula` sheet and 15 on the
`Strength` sheet. All were read from the review export's formula register with
their cached values. The `Formula` sheet's remaining content is definition text,
which supplied the clause references and the stated factor bounds.

## Coverage and gaps

* Stress block factors are tabulated by the workbook at **only** 32, 40, 50 and
  65 MPa (`Formula!O117:R120`), so those four grades are the whole published
  factor evidence.
* The AS 2327 `fcmi` row was captured to `f'c = 100 MPa`; the 120 MPa value is
  therefore not asserted in the baseline.
* The workbook prints no capacity comparison, ratio or pass/fail cell, so there
  is nothing of that kind to reproduce.

## Provenance not established

The `Strength` sheet's ratios of `f'c(T)` to `f'c(28)` — 0.16, 0.45, 0.66, 1.00,
1.24, 1.34 for normal cement and 0.34, 0.60, 0.78, 1.00, 1.14, 1.20 for high
early cement — carry **no clause reference and no cited source** anywhere in the
workbook. This must be resolved before release: either an authoritative source is
recorded here, or the table is removed from the module.

The `fcmi` polynomial `-0.0015 f'c^2 + 1.1429 f'c - 0.0614` is described in the
workbook's own revision history as a curve fit and is not a code equation.

## Independent corroboration performed

`Ec` computed from Table 3.1.2 `fcmi` was compared with the AS 3600 Table 3.1.2
published values of 30 100 MPa at N32 and 32 800 MPa at N40; both agree within
2 per cent. This is recorded in `tests/test_engine.py`.

## Outstanding

An independent review of the transcription against AS 3600:2018 Sections 3, 8 and
10, recorded here with reviewer, date and version.
