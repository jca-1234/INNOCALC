# Calculation Pad

A Mathcad-style calculation sheet for engineering work that does not belong in a dedicated
design module: load takedowns, design philosophy, assessments, sketches and marked-up
drawings. It prints on the same Innovis calculation pad as the steel and concrete modules, so
a pad sheet sits inside a calculation package alongside them without looking different.

It is a headless InnoCalc module — open it from **InnoCalc Manager → New calculation →
Calculation Pad** — and it also runs on its own:

```
python -m cpd.dev                        the starter pad
python -m cpd.dev pad.json --trace       every resolved variable
python -m cpd.dev pad.json --html out.html
python -m cpd.dev pad.json --notebook out.ipynb
python -m cpd.dev --validate             evaluator correctness and safety
```

---

## Cells

A pad is a list of cells. Add, reorder and delete them in the input panel.

| Cell | What it does |
|------|--------------|
| **Section heading** | A heading in the sheet. |
| **Narrative / assumptions** | Paragraphs; a line starting with `-` becomes a bullet. |
| **Calculation** | Evaluated and printed as a hand calculation. |
| **Figure or sketch** | An embedded image. |
| **PDF drawing or Bluebeam markup** | A page range from a PDF, spliced into the exported package at this position. |
| **Blank sheet** | An empty A4 or A3 gridded sheet for hand additions. |

A calculation is written **in the sheet itself**, in the place where it prints, and the
result under it follows each keystroke. The input panel keeps the cell list for ordering,
retyping declared values and everything that is not a sum.

---

## Writing calculations

Cells share one variable scope, top to bottom, so later cells see earlier results.

```
# Simply supported beam, uniformly distributed load
w = 5.0 kN/m
L = 6.0 m
M_max = w * L^2 / 8     # kNm
V_max = w * L / 2       # kN
```

prints as

> M<sub>max</sub> = w L² / 8 = 5 kN/m × (6 m)² / 8 = **22.5 kNm**

Conventions, which match `handcalcs`:

* `^` or `**` for powers.
* `_` for subscripts: `M_x`, `phi_c`, `M_x_max` → `M`<sub>`x,max`</sub>.
* Greek names are typeset: `alpha`, `beta`, `gamma`, `delta`, `theta`, `lambda_`, `mu`, `rho`,
  `sigma`, `tau`, `phi`, `psi`, `omega`.
* A whole comment line becomes a note in the sheet.
* Define a variable called `utilisation` (or `util`) and the manager reports it as the pad's
  governing utilisation in the library and package index.

Available functions: `abs min max round sum sqrt sin cos tan asin acos atan atan2 sinh cosh
tanh log log10 exp radians degrees floor ceil hypot`, with `pi` and `e`.

### Declared and calculated values

A line that is only a number — `w = 5.0 kN/m` — is a **declared** value: an input. Anything
that refers to another variable is **calculated**. Declared values collect in the *Declared
variables* panel in the input pane as they are written, where they can be retyped without
finding them in the sheet; the line in the sheet is rewritten and nothing else moves.

### Units

Units are real, through [Pint](https://pint.readthedocs.io/), and are written the way they
are written on paper:

```
w = 5 kN/m              a unit literal, as in unit-syntax
b = 250 mm
Z = b * d^2 / 6         # mm**3     the comment converts the result into that unit
sigma = M_max / Z       # MPa
```

A number followed by a unit is never valid Python, so the literal is unambiguous. The unit
runs to the first space, which is what makes `5 m / 2` a length divided by two rather than a
velocity. `unit("kN/m")` and `to(M, "kNm")` are available where that reads better.

A trailing `# kNm` comment converts the result into that unit. If the sum does not balance
dimensionally — a force added to a length — the line says so instead of printing a number.
Set **Units** to *Plain numbers* on the sheet panel to treat unit comments as labels, as the
pad did before.

### Symbols and algebra

[SymPy](https://docs.sympy.org/) is available for work that stays symbolic:

```
x = sym("x")
roots = solve(x^2 - 3*x - 10, x)        # [-2, 5]
shear = diff(w_0 * x * (L_0 - x) / 2, x)
```

`sym eq solve simplify expand factor together cancel nsimplify diff integrate limit subs
evaluate` are all callable. Tick **Typeset equations** on the sheet panel and each formula is
printed as MathML — real built-up fractions and roots — with the substitution line beneath it
still carrying its units.

### Why not raw Python

A pad is saved on the network drive and reopened by other people, so a pad must not be able
to run arbitrary code. Every statement is parsed and checked against an AST whitelist before
evaluation: assignments, arithmetic, comparisons and the functions above. Imports, attribute
access, subscripting, lambdas, comprehensions and calls to anything else are rejected with a
message in the sheet. `python -m cpd.dev --validate` proves the arithmetic, the units and the
rejections.

---

## Libraries

Run the suite's `setup.bat` to install the pinned `pint` and `sympy` dependencies.
Opening a pad and **Check Pint and SymPy** only inspect the environment; neither
installs packages. Unit-aware calculations fail explicitly if Pint is missing,
and symbolic calculations require SymPy. Plain-number mode remains available.

---

## Jupyter, Pint and handcalcs

**Export as Jupyter notebook** writes a `.ipynb` in which every calculation cell becomes a
`%%render` cell for [handcalcs](https://github.com/connorferster/handcalcs), with the same
Pint units the pad uses and SymPy imported alongside. Use it when a pad outgrows the built-in
editor.

```
pip install jupyterlab handcalcs pint unit-syntax sympy
jupyter lab "Roof load takedown.ipynb"
```

A pad literal `5 kN/m` is written `5 * kN/m` in the notebook so it survives the `%%render`
magic; [unit-syntax](https://github.com/ahupp/unit-syntax) is loaded as well, so the bare pad
form works in any cell handcalcs is not rendering.

The **Jupyter & handcalcs guide** button in the input panel links the training and reference
material, lists which libraries are installed, and explains the notation the pad uses.

---

## Drawings and markups

A **PDF** cell records a path and an optional page range (`1`, `1,3-5`, blank for all pages).
In the on-screen sheet it appears as a placeholder; when the manager exports a calculation
package the actual pages are spliced in at that position with `pypdf`.

This is how a Bluebeam Revu markup, a sketch or a drawing extract is carried inside a
calculation set to supplement the design philosophy.

---

## Files

The implementation lives under `src/cpd`. The small `cpd/__init__.py` wrapper
retains the old `python -m cpd.dev` command from this repository folder. Install
this module with `python -m pip install --no-build-isolation --no-deps -e CalculationPad`
from the suite root, or run `python -m tooling dev calculation-pad`.

| File | Purpose |
|------|---------|
| `src/cpd/headless.py` | The InnoCalc module contract: schema, compute, render, exchange, actions. |
| `src/cpd/evaluator.py` | The restricted evaluator and the three-step display. |
| `src/cpd/units.py` | Pint units, unit literals and unit-aware mathematics. |
| `src/cpd/symbolic.py` | SymPy algebra and the typeset equations. |
| `src/cpd/environment.py` | Read-only library availability checks. |
| `src/cpd/notebook.py` | Jupyter export and the learning resources. |
| `src/cpd/dev.py` | Thin shared development-runner wrapper. |
| `src/cpd/version.py` | Version register. |
