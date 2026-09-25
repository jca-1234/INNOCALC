"""Engineering and interface tests for the Concrete Wall module.

Run from the suite root with ``src`` and the suite root on PYTHONPATH::

    python -m unittest discover -s calculations/concrete/concrete_wall/tests -v
"""

from __future__ import annotations

import math
import unittest

from ic_concrete_wall import engine, headless


def _inputs(**overrides):
    values = headless.defaults()
    checks = overrides.pop("checks", None)
    values.update(overrides)
    if checks:
        values["checks"] = {**values["checks"], **checks}
    return values


class SchemaAndDefaults(unittest.TestCase):
    def test_every_field_has_a_default_and_a_unique_id(self):
        layout = headless.schema()
        seen = [field["id"] for group in layout["groups"] + layout["optional"]
                for field in group["fields"]]
        self.assertEqual(len(seen), len(set(seen)))
        values = headless.defaults()
        for field_id in seen:
            self.assertIn(field_id, values)

    def test_defaults_compute_and_are_fresh(self):
        first, second = headless.defaults(), headless.defaults()
        first["checks"]["axial"] = False
        self.assertTrue(second["checks"]["axial"])
        result = headless.compute(second)
        self.assertEqual(headless.summarise(result)["status"], "OK")

    def test_descriptor_matches_registration(self):
        descriptor = headless.descriptor()
        self.assertEqual(descriptor["id"], "concrete-wall")
        self.assertEqual(descriptor["folder"], "15 - CONCRETE WALL")
        self.assertEqual(descriptor["status"], "planned")
        self.assertEqual(descriptor["version"], "v0.0.1")


class HandCalculation(unittest.TestCase):
    """Independent hand checks of the Section 11 expressions."""

    def test_default_wall_simplified_method(self):
        result = headless.compute(_inputs())
        tw, hw, fc = 200.0, 3000.0, 32.0
        g = 200.0 + 25.0 * tw * hw / 2e6
        n_star = max(1.35 * g, 1.2 * g + 1.5 * 60.0)
        self.assertAlmostEqual(result["loads"]["Nstard"], n_star, places=12)
        hwe = 0.75 * hw
        ea = hwe ** 2 / (2500 * tw)
        nus = (tw - 1.2 * 33.3 - 2 * ea) * 0.6 * fc
        self.assertAlmostEqual(result["axial"]["Nus"], nus, places=9)
        self.assertAlmostEqual(result["axial"]["fNu"], 0.65 * nus, places=9)
        self.assertAlmostEqual(result["util"]["axial"], n_star / (0.65 * nus), places=12)
        self.assertAlmostEqual(result["util"]["slenderness"], hwe / tw / 30.0, places=12)

    def test_four_sided_support_when_height_exceeds_length(self):
        heights = engine.effective_height(6000.0, 2500.0, True, 2)
        self.assertAlmostEqual(heights["kCalc"], 2500.0 / (2 * 6000.0), places=12)
        three = engine.effective_height(3000.0, 2000.0, True, 1)
        self.assertAlmostEqual(three["k3"], 1 / (1 + (3000 / 6000) ** 2), places=12)
        self.assertAlmostEqual(three["kCalc"], 0.75, places=12)

    def test_squat_wall_shear(self):
        result = headless.compute(_inputs(Lw=6000, H=3000, Vstar=500, sv=200, sh=300))
        area = 0.8 * 6000 * 200 / 1000
        root = math.sqrt(32)
        vuc = max(0.17 * root * area, (0.66 * root - 0.21 * 0.5 * root) * area)
        pwv = 2 * 1000 / 200 * math.pi * 36 / 1000 / 200
        pwh = 2 * 1000 / 300 * math.pi * 36 / 1000 / 200
        vus = min(pwv, pwh) * 500 * area
        fvu = 0.7 * min(vuc + vus, 0.2 * 32 * area)
        self.assertIsNone(result["shear"]["Vucb"])
        self.assertAlmostEqual(result["shear"]["fVu"], fvu, places=9)
        self.assertAlmostEqual(result["util"]["inPlaneShear"], 500 / fvu, places=12)

    def test_single_layer_capacity_is_the_lesser_of_3tw_and_phi_nus(self):
        # Departure D1: the workbook returns 3 tw whenever the stress exceeds 3 MPa.
        result = headless.compute(_inputs(
            layers="1", tw=150, Hw=3800, Lw=5000, wallecc=60, Ndl=350, Nll=0, cover=40))
        ea = 2850.0 ** 2 / (2500 * 150)
        phi_nus = 0.65 * (150 - 1.2 * 60 - 2 * ea) * 0.6 * 32
        self.assertTrue(result["axial"]["exceedsSingleStress"])
        self.assertLess(phi_nus, 450.0)
        self.assertAlmostEqual(result["axial"]["fNu"], phi_nus, places=9)
        self.assertGreater(result["util"]["singleLayer"], 1.0)

    def test_in_plane_stress_is_added_to_the_wall_demand(self):
        result = headless.compute(_inputs(Mstari=800.0, Lw=4000))
        sigma_in = 6 * 800e6 / (200 * 4000 ** 2)
        self.assertAlmostEqual(result["loads"]["smidIn"], sigma_in, places=12)
        self.assertAlmostEqual(result["axial"]["demand"],
                               result["loads"]["Nstard"] + sigma_in * 200, places=9)

    def test_minimum_vertical_ratio_threshold(self):
        # sigma = 1.7 MPa lies between 0.03 f'c = 0.96 MPa and 2 MPa: departure D2 gives 0.0025.
        result = headless.compute(_inputs())
        self.assertLess(result["loads"]["smidMax"], 2.0)
        self.assertGreater(result["loads"]["smidMax"], 0.96)
        self.assertEqual(result["reinforcement"]["pwmin"], 0.0025)
        light = headless.compute(_inputs(Ndl=50, Nll=10))
        self.assertEqual(light["reinforcement"]["pwmin"], 0.0015)

    def test_fire_tables(self):
        self.assertAlmostEqual(engine.table_interp(engine.FIRE_INSULATION, 130.0), 140.0,
                               places=12)
        self.assertEqual(engine.table_interp(engine.FIRE_INSULATION, 400.0), 240.0)
        axis, thickness = engine.FIRE_ADEQUACY[(0.70, 1)]
        self.assertAlmostEqual(engine.table_interp(axis, 30.0), 105.0, places=12)
        self.assertAlmostEqual(engine.table_interp(thickness, 185.0), 150.0, places=12)

    def test_fire_resistance_utilisation(self):
        result = headless.compute(_inputs(checks={"fire": True}, frlRequired=120, ll07="Y"))
        fire = result["fire"]
        self.assertEqual(fire["ufi"], 0.7)
        self.assertAlmostEqual(result["util"]["fireResistance"], 120 / fire["frl"], places=12)

    def test_exposure_and_cover(self):
        self.assertEqual(engine.calc_exposure("S", 50, 64), "C1")
        self.assertEqual(engine.calc_exposure("R", 32, 30), "B1")
        self.assertEqual(engine.required_cover("S", 32, "B1"), (40.0, False))
        self.assertEqual(engine.required_cover("S", 25, "B1"), (60.0, True))
        result = headless.compute(_inputs(checks={"durability": True}, exposureClass="B1",
                                          cover=30))
        self.assertAlmostEqual(result["util"]["cover"], 40 / 30, places=12)

    def test_crack_control(self):
        result = headless.compute(_inputs(checks={"crackControl": True}, crackDegree="STRONG"))
        pwh = 2 * 1000 / 300 * math.pi * 36 / 1000 / 200
        self.assertAlmostEqual(result["util"]["crackControl"], 0.006 / pwh, places=12)


class MethodSelection(unittest.TestCase):
    def test_wall_in_tension_is_not_applicable(self):
        result = headless.compute(_inputs(Ndl=50, Nll=0, Mstari=3000, Lw=4000))
        self.assertEqual(result["method"]["desmode"], 0)
        self.assertTrue(math.isinf(result["util"]["designMethod"]))
        summary = headless.summarise(result)
        self.assertEqual(summary["status"], "FAIL")
        self.assertTrue(summary["headline"].startswith("Not applicable"))

    def test_out_of_plane_moment_requires_column_design(self):
        result = headless.compute(_inputs(Mstar=10.0))
        self.assertEqual(result["method"]["desmode"], 3)
        self.assertTrue(math.isinf(result["util"]["designMethod"]))

    def test_lightly_loaded_wall_designed_as_slab(self):
        result = headless.compute(_inputs(Ndl=40, Nll=0, includeSW="N", designAsWall="N"))
        self.assertEqual(result["method"]["approach"], "slab")
        self.assertAlmostEqual(result["axial"]["fNu"], 0.03 * 32 * 200, places=9)
        self.assertEqual(result["util"]["designMethod"], 0.0)
        self.assertTrue(any("Section 9" in item for item in result["warnings"]))

    def test_unbraced_wall_is_not_designed_by_simplified_method(self):
        result = headless.compute(_inputs(braced="N"))
        self.assertTrue(math.isinf(result["util"]["designMethod"]))

    def test_limited_ductile_wall_needs_class_n(self):
        result = headless.compute(_inputs(dwall="Y", reoClass="L"))
        self.assertTrue(math.isinf(result["util"]["ductileWall"]))
        self.assertEqual(result["reinforcement"]["pwmin"], 0.0025)

    def test_user_k_below_calculated_warns(self):
        result = headless.compute(_inputs(kMode="USER", k=0.6))
        self.assertTrue(result["effectiveHeight"]["kDiffers"])
        self.assertTrue(any("unconservative" in item for item in result["warnings"]))


class InvalidInput(unittest.TestCase):
    def test_rejections(self):
        for overrides in ({"fc": 15}, {"fc": 125}, {"tw": 0}, {"layers": "3"},
                          {"dbv": "11"}, {"loadType": "X"}, {"cover": 100},
                          {"wallIntersect": "3"}, {"Ndl": ""}, {"Ndl": True},
                          {"Nll": float("nan")}, {"kMode": "USER", "k": 0},
                          {"layers": "1", "tw": 30}, {"braced": "maybe"}):
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(**overrides))

    def test_optional_group_inputs_validated_only_when_enabled(self):
        headless.compute(_inputs(exposureClass="Z9"))
        with self.assertRaises(ValueError):
            headless.compute(_inputs(checks={"durability": True}, exposureClass="Z9"))


class Rendering(unittest.TestCase):
    def test_sheet_contains_column_style_sections(self):
        values = _inputs(checks={"fire": True, "crackControl": True, "durability": True},
                         dwall="Y", memberNumber="W<1>")
        html = headless.render(values, headless.compute(values), standalone=True)
        for heading in ("Design Summary", "Design Inputs - Geometry and Material",
                        "Wall Elevation, Restraint and Load Eccentricity",
                        "Wall Section and Reinforcement", "Effective Height - Cl 11.4",
                        "Design Method Selection - Cl 11.1 and Cl 11.2.1",
                        "Design Axial Strength - Cl 11.5", "Wall Reinforcement - Cl 11.7",
                        "In-Plane Shear - Cl 11.6", "Fire Resistance - Cl 5.7",
                        "Horizontal Crack Control - Cl 11.7.2", "Limited Ductile Wall - Cl 14.6",
                        "Cover for Durability - Section 4",
                        "Design Basis, Assumptions and Limitations"):
            self.assertIn(heading, html)
        self.assertNotIn("&amp;#", html)
        self.assertNotIn("&amp;lt;", html)
        self.assertNotIn("W<1>", html.split('<script id="concrete-wall-inputs"')[0])

    def test_single_layer_drawing(self):
        values = _inputs(layers="1")
        html = headless.render(values, headless.compute(values))
        self.assertIn("Single layer check", html)


if __name__ == "__main__":
    unittest.main()
