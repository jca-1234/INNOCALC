# Calculation Modules

New modules are filed here by discipline and stable module ID, using the shared
scaffold. Run `python -m tooling new` from the suite root; see
`../docs/DEVELOPMENT.md` for the complete workflow.

Existing repositories are now grouped here:

- `steel/member/`: Steel calculation engine and retained standalone application.
- `concrete/column/`: Concrete engine and retained standalone application.
- `general/calculation_pad/`: Calculation Pad, using the `src/cpd` package layout.

Their Git histories remain independent and are excluded from the suite's root Git
repository. New scaffolded modules belong to the root repository. Do not copy a
standalone application's server, frontend, project data, environment or report
exporter into a new calculation.