"""Engineering and interface tests for the Concrete Two-Way Slab module.

Run from the suite root with ``src`` and the suite root on PYTHONPATH::

    python -m unittest discover -s calculations/concrete/concrete_two_way_slab/tests -v
"""

from __future__ import annotations

import math
import unittest

from ic_concrete_two_way_slab import engine, headless


def _inputs(**overrides):
    values = headless.defaults()
    values.update(overrides)
    return values


class SchemaAndDefaults(unittest.TestCase):
    def test_every_field_has_a_default_and_a_unique_id(self):
        seen = [field["id"] for group in headless.schema()["groups"] for field in group["fields"]]
        self.assertEqual(len(seen), len(set(seen)))
        values = headless.defaults()
        for field_id in seen:
            self.assertIn(field_id, values)

    def test_defaults_compute_and_are_fresh(self):
        first, second = headless.defaults(), headless.defaults()
        first["checks"]["minimumSteel"] = False
        self.assertTrue(second["checks"]["minimumSteel"])
        headless.compute(second)

    def test_descriptor_matches_registration(self):
        descriptor = headless.descriptor()
        self.assertEqual(descriptor["id"], "concrete-two-way-slab")
        self.assertEqual(descriptor["folder"], "11 - CONCRETE TWO-WAY SLAB")
        self.assertEqual(descriptor["status"], "planned")


class TableInterpolation(unittest.TestCase):
    """Independent hand checks of the Ly/Lx interpolation."""

    def test_table_b_all_continuous_at_1_25(self):
        # Midway between 1.2 (0.029) and 1.3 (0.032).
        self.assertAlmostEqual(engine.table_value(engine.TABLE_B[1], 1.25), 0.0305, places=12)

    def test_step_above_two_for_table_b(self):
        row = engine.TABLE_B[3]
        self.assertAlmostEqual(engine.table_value(row, 2.0), 0.085, places=12)
        self.assertAlmostEqual(engine.table_value(row, 2.0001), 0.125, places=12)

    def test_below_one_uses_first_column(self):
        self.assertEqual(engine.table_value(engine.TABLE_A[9], 0.9), 0.056)

    def test_k4_interpolation(self):
        # Code 1 between 1.25 (3.1) and 1.5 (2.8) at 1.375.
        self.assertAlmostEqual(engine.k4_value(engine.TABLE_K4[1], 1.375), 2.95, places=12)
        self.assertEqual(engine.k4_value(engine.TABLE_K4[9], 3.0), 1.5)

    def test_formula_matches_table_a_extremes(self):
        # All edges discontinuous, Ly/Lx = 2: Table A gives 0.111 and 0.056.
        beta_x, beta_y = engine.formula_coefficients(2.0, 2.0, 0.5)
        self.assertAlmostEqual(beta_y, 1.0 / 18.0, places=12)
        self.assertAlmostEqual(beta_x, 0.5 / 18.0 + 1.0 / 12.0, places=12)
        self.assertAlmostEqual(beta_x, 0.111, delta=0.0005)


class HandCalculation(unittest.TestCase):
    def test_simply_supported_square_panel_class_n(self):
        # 6 m x 6 m, 200 mm, all edges discontinuous, Class N with redistribution.
        result = headless.compute(_inputs(
            Ly=6000, Lx=6000, th=200, contLong="0", contShort="0", reo="N", redist="Y",
            wsdl=1.0, wll=3.0, fc=32, cover=25, dia="12", Ast=600))
        fd = max(1.35 * 6.0, 1.2 * 6.0 + 1.5 * 3.0)
        self.assertAlmostEqual(result["loads"]["Fd"], fd, places=12)
        self.assertEqual(result["analysis"]["code"], 9)
        self.assertAlmostEqual(result["moments"]["Mx"], 0.056 * fd * 36.0, places=12)
        self.assertAlmostEqual(result["moments"]["MxDisc"], 0.5 * 0.056 * fd * 36.0, places=12)
        ds = 200 - 25 - 6
        ast_min = 0.19 * (200 / ds) ** 2 * 0.6 * math.sqrt(32) / 500 * 1000 * ds
        self.assertAlmostEqual(result["minimum"]["Astmin"], ast_min, places=9)

    def test_live_load_limit_uses_dead_load_only(self):
        # wdl = 25 x 0.15 + 1 = 4.75 kPa, wll = 5 kPa: the workbook's wdl + wsdl test would pass.
        result = headless.compute(_inputs(th=150, wsdl=1.0, wll=5.0))
        self.assertAlmostEqual(result["util"]["liveLoadLimit"], 5.0 / 4.75, places=12)
        self.assertEqual(headless.summarise(result)["status"], "FAIL")

    def test_spans_are_sorted(self):
        result = headless.compute(_inputs(Ly=5000, Lx=8000))
        self.assertEqual(result["analysis"]["Ly"], 8000)
        self.assertTrue(result["warnings"])

    def test_formula_ignored_for_class_l(self):
        result = headless.compute(_inputs(reo="L", useFormula="Y"))
        self.assertEqual(result["analysis"]["source"], "B")


class OptionalChecks(unittest.TestCase):
    """Flexure and shrinkage groups added from the Tedds AS 3600-2018 slab approach."""

    def _flexure_inputs(self, **overrides):
        base = {"th": 200, "fc": 32, "cover": 25, "contLong": "2", "contShort": "1",
                "reo": "N", "redist": "Y"}
        values = _inputs(**{**base, **overrides})
        values["checks"] = {**values["checks"], "flexure": True}
        return values

    def test_midspan_capacity_hand_calculation(self):
        result = headless.compute(self._flexure_inputs(barXb="12", sXb=200))
        location = result["flexure"]["locations"][0]
        As = math.pi * 36.0 * 1000.0 / 200.0
        d = 200 - 25 - 6
        alpha2, gamma = 0.85 - 0.0015 * 32, 0.97 - 0.0025 * 32
        ku = As * 500 / (alpha2 * 32 * gamma * 1000 * d)
        phi = min(0.85, 1.24 - 13 * ku / 12)
        phi_mu = phi * As * 500 * d * (1 - As * 500 / (2 * alpha2 * 32 * 1000 * d)) / 1e6
        self.assertAlmostEqual(location["ku"], ku, places=12)
        self.assertAlmostEqual(location["phiMu"], phi_mu, places=9)
        self.assertAlmostEqual(location["ratioMoment"], result["moments"]["Mx"] / phi_mu, places=12)

    def test_locations_follow_edge_conditions(self):
        result = headless.compute(self._flexure_inputs())
        keys = {item["key"] for item in result["flexure"]["locations"]}
        # Both long edges continuous, one short edge continuous and one discontinuous.
        self.assertEqual(keys, {"Xb", "Yb", "Xtc", "Ytc", "Ytd"})
        for key in ("flexure", "ductility", "flexuralMinimum", "barSpacing"):
            self.assertIn(key, result["util"])

    def test_class_l_uses_fixed_phi(self):
        result = headless.compute(self._flexure_inputs(reo="L"))
        self.assertTrue(all(item["phi"] == 0.65 for item in result["flexure"]["locations"]))

    def test_shrinkage_raises_minimum_at_each_location(self):
        values = self._flexure_inputs(restraint="STRONG")
        values["checks"]["shrinkage"] = True
        result = headless.compute(values)
        self.assertAlmostEqual(result["shrinkage"]["AsCrack"], 0.75 * 0.006 * 200 * 1000, places=9)
        self.assertTrue(all(item["AsMin"] >= 900.0 for item in result["flexure"]["locations"]))

    def test_optional_groups_off_by_default(self):
        result = headless.compute(_inputs())
        self.assertIsNone(result["flexure"])
        self.assertNotIn("flexure", result["util"])


class InvalidInput(unittest.TestCase):
    def test_rejections(self):
        for overrides in ({"fc": 15}, {"fc": 125}, {"th": 0}, {"contLong": "3"},
                          {"dia": "11"}, {"loadType": "X"}, {"cover": 200},
                          {"dc": 500}, {"wll": ""}):
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(**overrides))


class Rendering(unittest.TestCase):
    def test_sheet_contains_column_style_sections(self):
        values = _inputs()
        html = headless.render(values, headless.compute(values), standalone=True)
        for heading in ("Design Summary", "Design Inputs - Geometry and Material",
                        "Slab Panel and Design Moments", "Moment Coefficients - Cl 6.10.3.2",
                        "Deflection by Deemed-to-Comply Span-to-Depth"):
            self.assertIn(heading, html)
        self.assertNotIn("&amp;#", html)


if __name__ == "__main__":
    unittest.main()
