"""Optional detailing checks: lateral restraint (Cl 8.9) and slab shrinkage steel (Cl 9.5.3).

* ``slenderness`` compares the restraint spacing with ``Design!H28``
  (Cl 8.9.2 simply supported / continuous, Cl 8.9.3 cantilever).
* ``secondary`` compares the provided secondary steel with ``Secondary!E9:E26``.
"""

from __future__ import annotations

from typing import Any

from .common import ratio
from .section import SLAB

RESTRAINT = {
    "U": ("Unrestrained slab - Cl 9.5.3.3", 1.75),
    "IMIN": ("Restrained, internal, minor control - Cl 9.5.3.4(a)", 1.75),
    "IMOD": ("Restrained, internal, moderate control - Cl 9.5.3.4(a)", 3.5),
    "ISTR": ("Restrained, internal, strong control - Cl 9.5.3.4(a)", 6.0),
    "AMOD": ("Restrained, external A1 and A2, moderate - Cl 9.5.3.4(b)", 3.5),
    "ASTR": ("Restrained, external A1 and A2, strong - Cl 9.5.3.4(b)", 6.0),
    "B": ("Restrained, external B1, B2, C1 and C2 - Cl 9.5.3.4(c)", 6.0),
}


def slenderness(geom: dict[str, Any], *, spacing: float, cantilever: bool) -> dict[str, Any]:
    bef, D = geom["bef"], geom["D"]
    if cantilever:
        limit = min(25.0 * bef, 100.0 * bef * bef / D)
        clause, basis = "Cl 8.9.3", "L1 = min(25 bef, 100 bef^2 / D)"
    else:
        limit = min(60.0 * bef, 180.0 * bef * bef / D)
        clause, basis = "Cl 8.9.2", "L1 = min(60 bef, 180 bef^2 / D)"
    applicable = geom["section"] != SLAB
    return {"spacing": spacing, "cantilever": cantilever, "limit": limit, "clause": clause,
            "basis": basis, "applicable": applicable,
            "ratio": ratio(spacing, limit) if applicable else 0.0}


def secondary(geom: dict[str, Any], *, restraint: str, sigma_cp: float,
              provided: float) -> dict[str, Any]:
    D, W = geom["D"], geom["W"]
    design_thickness = 250.0 if D > 500 else D
    label, coefficient = RESTRAINT[restraint]
    applicable = geom["section"] == SLAB
    required = max(0.0, coefficient - 2.5 * sigma_cp) * W * design_thickness / 1000.0
    return {"restraint": restraint, "label": label, "coefficient": coefficient,
            "sigmaCp": sigma_cp, "D": D, "designThickness": design_thickness,
            "eachFace": D > 500, "required": required if applicable else 0.0,
            "provided": provided, "applicable": applicable,
            "ratio": ratio(required, provided) if applicable else 0.0}
