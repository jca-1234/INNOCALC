"""Engineering and interface tests for the Concrete Industrial Pavement module.

Run from the suite root with ``src`` and the suite root on PYTHONPATH::

    python -m unittest discover -s calculations/concrete/concrete_industrial_pavement/tests -v
"""

from __future__ import annotations

import math
import unittest

from ic_concrete_industrial_pavement import engine, headless

TONNE = 9810.0  # N


def _inputs(**overrides):
    values = headless.defaults()
    values.update(overrides)
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
        first["checks"]["rackFlexure"] = False
        self.assertTrue(second["checks"]["rackFlexure"])
        headless.compute(second)

    def test_descriptor_matches_registration(self):
        descriptor = headless.descriptor()
        self.assertEqual(descriptor["id"], "concrete-industrial-pavement")
        self.assertEqual(descriptor["folder"], "16 - INDUSTRIAL PAVEMENT")
        self.assertEqual(descriptor["status"], "planned")
        self.assertEqual(descriptor["version"], "v0.0.1")


class IndependentTheory(unittest.TestCase):
    """Hand calculations of the Westergaard, Kelley, Pickett and Hetenyi expressions."""

    h, u, K, E = 150.0, 0.15, 40.0, 30023.85807160702

    def setUp(self):
        self.l = (self.E * self.h ** 3 / (12 * (1 - self.u ** 2) * (self.K / 1000))) ** 0.25
        self.r = math.sqrt(140 * 80 / math.pi)
        self.b = math.sqrt(1.6 * self.r ** 2 + self.h ** 2) - 0.675 * self.h

    def test_radius_of_relative_stiffness(self):
        result = headless.compute(_inputs())
        self.assertAlmostEqual(result["material"]["l"], self.l, places=9)
        self.assertAlmostEqual(result["racking"]["Rb"], self.b, places=12)

    def test_westergaard_interior_1926(self):
        # sigma = 3 (1 + mu) P / (2 pi h^2) [ln(l / b) + 0.6159] with P = 1 tonne.
        exact = 3 * (1 + self.u) * TONNE / (2 * math.pi * self.h ** 2) * (
            math.log(self.l / self.b) + 0.6159)
        engine_value = engine.internal_stress(self.h, self.u, self.l, self.b)
        self.assertAlmostEqual(engine_value / exact, 1.0, delta=0.003)

    def test_kelley_edge_against_westergaard_1926_edge(self):
        westergaard = 0.572 * TONNE / self.h ** 2 * (4 * math.log10(self.l / self.b) + 0.359)
        kelley = engine.edge_stress(self.h, self.u, self.l, self.b)
        self.assertAlmostEqual(kelley / westergaard, 1.0, delta=0.03)

    def test_pickett_corner(self):
        a = self.r / self.l
        pickett = 4.2 * TONNE / self.h ** 2 * (1 - math.sqrt(a) / (0.925 + 0.22 * a))
        self.assertAlmostEqual(engine.corner_stress(self.h, self.l, self.r) / pickett, 1.0,
                               delta=1e-4)
        westergaard_corner = 3 * TONNE / self.h ** 2 * (1 - (self.r * math.sqrt(2) / self.l) ** 0.6)
        self.assertGreater(engine.corner_stress(self.h, self.l, self.r), westergaard_corner)

    def test_equivalent_radius_limit(self):
        self.assertEqual(engine.equivalent_radius(300.0, 150.0), 300.0)
        # Small contact areas are enlarged: b = sqrt(1.6 r^2 + h^2) - 0.675 h > r.
        self.assertAlmostEqual(engine.equivalent_radius(50.0, 150.0),
                               math.sqrt(1.6 * 2500 + 22500) - 101.25, places=12)
        self.assertGreater(engine.equivalent_radius(50.0, 150.0), 50.0)

    def test_hetenyi_critical_moment(self):
        # At a = pi / (4 lambda) the aisle moment is q / (2 lambda^2) (e^-x sin x - e^-5x sin 5x).
        result = headless.compute(_inputs())
        critical = result["uniform"]["criticalAisle"]
        check = headless.compute(_inputs(IsleUDL=critical))["uniform"]
        self.assertAlmostEqual(check["Mc"] / check["Mcmax"], 1.0, delta=0.002)

    def test_cca_variable_layout(self):
        result = headless.compute(_inputs())
        fca = 0.6 * math.sqrt(32) * 0.85 * 0.75
        self.assertAlmostEqual(result["uniform"]["UDLall"], 0.33 * fca * math.sqrt(150 * 40),
                               places=12)

    def test_punching_perimeters(self):
        dom = 0.9 * 150
        expected = {"I": 2 * (80 + dom) + 2 * (140 + dom), "E": 2 * (80 + dom / 2) + 140 + dom,
                    "C": 80 + dom / 2 + 140 + dom / 2}
        for where, perimeter in expected.items():
            with self.subTest(where=where):
                result = headless.compute(_inputs(whereinput=where))
                self.assertAlmostEqual(result["racking"]["uu"], perimeter, places=12)
        fcv = min(0.17 * (1 + 2 / 1.75), 0.34) * math.sqrt(32)
        self.assertAlmostEqual(result["racking"]["fcv"], fcv, places=12)

    def test_transfer_multiplier_at_edge(self):
        plain = headless.compute(_inputs(whereinput="E"))["racking"]
        transfer = headless.compute(_inputs(whereinput="E", Transfer="Y"))["racking"]
        self.assertAlmostEqual(transfer["Rset"], 0.85 * plain["Rset"], places=12)
        self.assertAlmostEqual(transfer["Rst"], transfer["Rset"], places=12)


class ChartsAndInterpolation(unittest.TestCase):
    def test_moment_interpolation_at_saved_stiffness(self):
        x = 1.68
        expected = (engine.moment_curve(675, x)
                    + 7 / 125 * (engine.moment_curve(800, x) - engine.moment_curve(675, x)))
        self.assertAlmostEqual(engine.chandler_moment(1680, 681.7035695)["value"], expected,
                               places=14)

    def test_moment_corrected_between_570_and_675(self):
        value = engine.chandler_moment(2000, 620)
        low, high = engine.moment_curve(570, 2.0), engine.moment_curve(675, 2.0)
        self.assertAlmostEqual(value["value"], low + 50 / 105 * (high - low), places=14)
        self.assertEqual(value["note"], "corrected570")

    def test_moment_below_450_uses_450_curve(self):
        value = engine.chandler_moment(2000, 400)
        self.assertAlmostEqual(value["value"], engine.moment_curve(450, 2.0), places=14)
        self.assertGreater(value["value"], 0.0)

    def test_moment_aisle_is_clamped(self):
        self.assertEqual(engine.chandler_moment(1000, 700)["aisle"], 1500)
        self.assertEqual(engine.chandler_moment(6000, 700)["aisle"], 4500)

    def test_moment_curves_match_digitised_chart(self):
        # Graphs 2 row y = 2.0 m: 675 -> 0.138, 800 -> 0.200, 1200 -> 0.441, 1800 -> 0.850.
        for stiffness, table in ((675, 0.138), (800, 0.2), (1200, 0.441), (1800, 0.85)):
            with self.subTest(stiffness=stiffness):
                self.assertAlmostEqual(engine.moment_curve(stiffness, 2.0), table, delta=0.012)

    def test_stress_increase_fits_match_digitised_points(self):
        # Graphs 1 digitised Chandler Fig 2 points (x / l, % increase).
        self.assertAlmostEqual(engine.trans(0.545), 27.4, delta=1.0)
        self.assertAlmostEqual(engine.trans(0.205), 49.8, delta=1.0)
        self.assertAlmostEqual(engine.radial(0.48), 16.5, delta=1.0)
        self.assertAlmostEqual(engine.edge_increase(0.46), 9.0, delta=1.0)

    def test_chart_cut_offs_and_negative_values(self):
        self.assertEqual(engine.trans(3.0000001), 0.0)
        self.assertEqual(engine.radial(0.0), 0.0)
        self.assertEqual(engine.radial(2.0), 0.0)
        self.assertLess(engine.radial(2.0, include_negative=True), 0.0)

    def test_stress_ratio(self):
        self.assertEqual(engine.stress_ratio(40), 0.84)
        self.assertEqual(engine.stress_ratio(400001), 0.5)
        self.assertAlmostEqual(engine.stress_ratio(1000), (11.791 - 3) / 12.136, places=14)
        self.assertAlmostEqual(engine.stress_ratio(1000), 0.73, delta=0.01)  # T48 Table 1.17

    def test_cbr_conversions_are_inverse(self):
        self.assertAlmostEqual(engine.cbr(engine.msr(7.5)), 7.5, places=12)


class Behaviour(unittest.TestCase):
    def test_saved_example_outcome(self):
        result = headless.compute(_inputs())
        self.assertAlmostEqual(result["util"]["rackFlexure"], 1.2096072144523815, places=12)
        self.assertEqual(headless.summarise(result)["status"], "FAIL")

    def test_negative_chart_values_reduce_stress(self):
        plain = headless.compute(_inputs())["racking"]
        relieved = headless.compute(_inputs(Includeneg="Y"))["racking"]
        self.assertLess(relieved["Rsx"], plain["Rsx"])

    def test_dual_axle_point_g_corrected(self):
        result = headless.compute(_inputs(Bogie=1500))
        wheels = result["wheels"]
        point_g = next(item for item in wheels["dual"]["points"] if item["point"] == "G")
        self.assertAlmostEqual(point_g["dist"], math.hypot(1500, 2600), places=9)
        self.assertAlmostEqual(wheels["dual"]["workbookG"], math.hypot(1500, 2600 - 250), places=9)
        self.assertEqual(wheels["axleCase"], "dual")

    def test_invalid_stresses_are_unattainable(self):
        # A very large foot on a thin stiff slab drives the corner formula negative.
        result = headless.compute(_inputs(h=60, K=150, Fl=1500, Fw=1500))
        self.assertTrue(result["racking"]["invalid"])
        self.assertEqual(result["util"]["rackFlexure"], math.inf)
        self.assertEqual(headless.summarise(result)["status"], "FAIL")

    def test_low_grade_fails_abrasion(self):
        result = headless.compute(_inputs(fc=20))
        self.assertAlmostEqual(result["util"]["abrasionGrade"], 1.25, places=12)
        self.assertTrue(any("unsuitable" in item for item in result["warnings"]))

    def test_overlap_warning(self):
        result = headless.compute(_inputs(WheelsPerAxle="4", WheelPairCentres=250))
        self.assertTrue(result["wheels"]["overlapping"])
        self.assertTrue(any("overlap" in item for item in result["warnings"]))

    def test_optional_groups_off_by_default(self):
        result = headless.compute(_inputs())
        self.assertIsNone(result["custom"])
        self.assertIsNone(result["location"])
        self.assertNotIn("customFlexure", result["util"])

    def test_custom_list_loads_scale_increases(self):
        values = _inputs(customLoads="LIST", **{f"load{name}": 20.0 for name in engine.CUSTOM_POINTS})
        values["loadF"] = 10.0
        values["checks"] = {**values["checks"], "custom": True}
        points = {item["point"]: item for item in headless.compute(values)["custom"]["points"]}
        self.assertAlmostEqual(points["F"]["pctX"], engine.radial(381 / 681.7035695022776) / 2,
                               places=6)

    def test_location_applicability(self):
        values = _inputs(edgeDistX=500, edgeDistY=5000)
        values["checks"] = {**values["checks"], "location": True}
        internal = headless.compute(values)
        # The wheel contact radius exceeds the rack foot radius, so it governs a + l.
        self.assertEqual(internal["location"]["required"], internal["wheels"]["WRadius"]
                         + internal["material"]["l"])
        self.assertEqual(internal["location"]["classified"], "E")
        self.assertGreater(internal["util"]["positionApplicability"], 1.0)
        edge = headless.compute({**values, "whereinput": "E"})
        self.assertLess(edge["util"]["positionApplicability"], 1.0)
        corner = headless.compute({**values, "whereinput": "C"})
        self.assertEqual(corner["util"]["positionApplicability"], 0.0)


class InvalidInput(unittest.TestCase):
    def test_rejections(self):
        for overrides in ({"fc": 15}, {"fc": 125}, {"h": 0}, {"whereinput": "X"},
                          {"fmethod": "C", "fc": 60}, {"WheelsPerAxle": "3"},
                          {"WheelsPerAxle": "4", "WheelPairCentres": 0}, {"bt": "110"},
                          {"u": 0.5}, {"PRl": 0}, {"K": ""}, {"K": True}, {"Rk1": 1.2},
                          {"reom": "Z"}, {"fsy": "450"}, {"dAB": 0}, {"K": float("nan")}):
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(**overrides))

    def test_custom_rejections(self):
        for overrides in ({"ltype": "W", "CReps": 0}, {"consider": "Y", "distF": 30.0},
                          {"dirA": "Q"}, {"CPL": 0}):
            with self.subTest(overrides=overrides):
                values = _inputs(**overrides)
                values["checks"] = {**values["checks"], "custom": True}
                with self.assertRaises(ValueError):
                    headless.compute(values)


class Rendering(unittest.TestCase):
    def test_sheet_contains_column_style_sections(self):
        values = _inputs(Fork="Reach <truck> & co")
        values["checks"] = {**values["checks"], "custom": True, "location": True}
        html = headless.render(values, headless.compute(values), standalone=True)
        for heading in ("Design Summary", "Design Inputs - Concrete and Slab",
                        "Pavement Section and Subgrade", "Rack Post Layout and Load Position",
                        "Rack Post Punching Shear - AS 3600 Cl 9.3.3",
                        "Rack Flexural Stress - T48 Cl 3.3.6",
                        "Uniform Load, Variable Storage Layout - C&amp;CA Cl 5.6.3",
                        "Custom Load Flexural Stress", "Load Position Applicability",
                        "Design Basis, Assumptions and Limitations",
                        "Concrete Industrial Pavement Design v0.0.1"):
            self.assertIn(heading, html)
        self.assertNotIn("&amp;#", html)
        sheets = html.split('<script id="concrete-industrial-pavement-inputs"')[0]
        self.assertNotIn("<truck>", sheets)
        self.assertIn("Reach &lt;truck&gt; &amp; co", sheets)
        self.assertLess(html.index("Design Summary"), html.index("Design Inputs"))


if __name__ == "__main__":
    unittest.main()
