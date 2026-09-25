"""Engineering and interface tests for the Concrete Strut-and-Tie module.

Run from the suite root with ``src`` and the suite root on PYTHONPATH::

    python -m unittest discover -s calculations/concrete/concrete_strut_tie/tests -v
"""

from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

from ic_concrete_strut_tie import engine, headless

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "worked-example.json"


def _inputs(**overrides):
    values = headless.defaults()
    values.update(overrides)
    return values


def _example(**overrides):
    values = headless.defaults()
    values.update(json.loads(EXAMPLE.read_bytes()))
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
        first["checks"]["tie"] = False
        self.assertTrue(second["checks"]["tie"])
        result = headless.compute(second)
        self.assertEqual(headless.summarise(result)["status"], "OK")

    def test_descriptor_matches_registration(self):
        descriptor = headless.descriptor()
        self.assertEqual(descriptor["id"], "concrete-strut-tie")
        self.assertEqual(descriptor["folder"], "12 - CONCRETE STRUT AND TIE")
        self.assertEqual(descriptor["status"], "planned")
        self.assertEqual(descriptor["version"], "v0.0.1")

    def test_mandatory_checks_cannot_be_switched_off(self):
        values = _inputs()
        values["checks"] = {key: False for key in values["checks"]}
        result = headless.compute(values)
        for key in headless.ALWAYS_ON:
            self.assertIn(key, result["util"])


class HandCalculation(unittest.TestCase):
    """Independent hand calculations on the defaults: 3000 x 3000 x 400 mm, f'c = 40 MPa."""

    def setUp(self):
        self.result = headless.compute(_inputs())

    def test_strut_efficiency_and_depth(self):
        # theta = 45 deg, cot = 1: betas = 1 / 1.66; phi fcu = 0.65 betas 0.9 x 40.
        betas = 1.0 / 1.66
        stress = 0.65 * betas * 0.9 * 40.0
        strut = self.result["strut"]
        self.assertAlmostEqual(self.result["geometry"]["theta"], 45.0, places=12)
        self.assertAlmostEqual(strut["betas"], betas, places=12)
        self.assertAlmostEqual(strut["dcmax"], 3.0e6 / (stress * 400.0), places=9)
        self.assertEqual(self.result["util"]["strut"], 1.0)

    def test_geometry_identity_when_a_and_z_are_calculated(self):
        g = self.result["geometry"]
        self.assertAlmostEqual(g["thetaAz"], g["theta"], places=9)
        dc = self.result["strut"]["dc"]
        root = math.sqrt(0.5)
        self.assertAlmostEqual(g["a"], 3000.0 - dc * 0.5 / root, places=9)
        self.assertAlmostEqual(g["z"], 3000.0 - dc * root, places=9)

    def test_bursting_forces(self):
        c = self.result["cracking"]
        lb = self.result["geometry"]["lb"]
        self.assertAlmostEqual(c["Tbcr"], 0.7 * 400.0 * lb * 0.36 * math.sqrt(40.0), places=6)
        self.assertAlmostEqual(self.result["strength"]["Tb"], 0.2 * 3.0e6, places=9)
        self.assertAlmostEqual(self.result["service"]["Tb"], 0.5 * 2.0e6, places=9)
        self.assertTrue(c["required"])

    def test_bursting_strength_capacity(self):
        # N16 at 200 in two layers each way, gamma1 = gamma2 = 45 deg, no Vr*.
        lb = self.result["geometry"]["lb"]
        asi = math.pi * 16 ** 2 / 4 * 2 * 1000 / 200 * lb * math.sqrt(0.5) / 1000
        capacity = 2 * 0.85 * asi * 500 * math.sqrt(0.5)
        self.assertAlmostEqual(self.result["strength"]["phiTb"], capacity, delta=1e-6 * capacity)
        self.assertAlmostEqual(self.result["util"]["burstingStrength"], 0.6e6 / capacity, places=9)

    def test_tie_capacity(self):
        ast = 6 * 2 * math.pi * 28 ** 2 / 4
        self.assertAlmostEqual(self.result["tie"]["phiT"], 0.85 * 500 * ast, places=6)
        self.assertAlmostEqual(self.result["util"]["tie"], 2.2e6 / (0.85 * 500 * ast), places=12)

    def test_development_zone(self):
        # N28 tie, cd = min(100/2, 40) = 40: k3 = 1 - 0.15 x 12 / 28; cogged halves Lsy.t.
        k3 = 1 - 0.15 * (40 - 28) / 28
        basic = 0.5 * 1.3 * k3 * 500 * 28 / (1.04 * math.sqrt(40))
        half = 0.5 * 0.5 * max(basic, 0.058 * 500 * 1.3 * 28)
        self.assertAlmostEqual(self.result["anchorage"]["tie"]["half"], half, places=9)
        self.assertAlmostEqual(self.result["anchorage"]["dz"], half + 40.0, places=9)

    def test_bearing_uses_strut_vertical_component(self):
        b = self.result["bearing"]
        self.assertAlmostEqual(b["Bstar"], 3.0e6 * math.sqrt(0.5), places=6)
        self.assertAlmostEqual(b["phiB"], 0.6 * 0.9 * 40 * 400 * 800, places=6)


class WorkbookBehaviour(unittest.TestCase):
    def test_example_reproduces_saved_failure(self):
        result = headless.compute(_example())
        self.assertAlmostEqual(result["util"]["burstingCracking"], 4386.847994478952 /
                               3393.4100466173772, places=9)
        summary = headless.summarise(result)
        self.assertEqual(summary["status"], "FAIL")
        self.assertEqual(summary["criticalCheck"], "Bursting reinforcement, transfer at cracking")

    def test_solver_matches_goalseek_with_one_manual_distance(self):
        result = headless.compute(_example(zMode="C"))
        g = result["geometry"]
        self.assertTrue(g["solver"]["converged"])
        self.assertLess(abs(g["theta"] - g["thetaAz"]), 1e-9)
        self.assertEqual(result["util"]["angleCompatibility"], 0.0)

    def test_incompatible_manual_angle_fails(self):
        result = headless.compute(_example(thetaMode="M", theta=45.0))
        self.assertEqual(result["util"]["angleCompatibility"], math.inf)
        self.assertEqual(headless.summarise(result)["status"], "FAIL")
        self.assertTrue(result["unattainable"])

    def test_support_length_counts(self):
        result = headless.compute(_inputs(Lr=500))
        self.assertGreater(result["util"]["supportLength"], 1.0)
        self.assertEqual(headless.summarise(result)["status"], "FAIL")

    def test_shallow_strut_fails_the_angle_rule(self):
        result = headless.compute(_inputs(Lstrut=6000, D=2500))
        self.assertAlmostEqual(result["util"]["strutAngle"],
                               30.0 / math.degrees(math.atan(2500 / 6000)), places=12)

    def test_no_reinforcement_needed_below_threshold(self):
        # Small C* on a long strut: Tbb* = 0.5 C* <= 0.5 Tb.cr.
        result = headless.compute(_inputs(Cstar=500, Cserv=350, Tstar=350))
        self.assertFalse(result["cracking"]["required"])
        self.assertIn("burstingThreshold", result["util"])
        self.assertNotIn("burstingStrength", result["util"])

    def test_missing_reinforcement_is_unattainable(self):
        result = headless.compute(_inputs(bar1=0, bar2=0))
        self.assertEqual(result["util"]["burstingStrength"], math.inf)
        self.assertEqual(headless.summarise(result)["status"], "FAIL")

    def test_vertical_load_steel(self):
        result = headless.compute(_inputs(Vrstar=3000, Vrserv=2000))
        asi1 = result["reinforcement"]["Asi1"]
        expected = max(3.0e6 / 0.85 / 500, 2.0e6 / 250) / asi1
        self.assertAlmostEqual(result["util"]["verticalLoadSteel"], expected, places=12)

    def test_one_way_reinforcement_angle(self):
        result = headless.compute(_inputs(bar2=0, Lstrut=2500, D=4000))
        gamma1 = 90.0 - result["geometry"]["theta"]
        self.assertAlmostEqual(result["util"]["oneWayAngle"], 40.0 / gamma1, places=12)
        self.assertGreater(result["util"]["oneWayAngle"], 1.0)

    def test_text_options_fold_case(self):
        upper = headless.compute(_example(useRef2="Y", cogged="Y"))
        lower = headless.compute(_example(useRef2="y", cogged="y"))
        self.assertEqual(upper["util"], lower["util"])

    def test_development_caps_fc_at_65(self):
        at65 = headless.compute(_inputs(fc=65))["anchorage"]["tie"]["basic"]
        at100 = headless.compute(_inputs(fc=100))["anchorage"]["tie"]["basic"]
        self.assertEqual(at65, at100)

    def test_slip_form_factor(self):
        plain = headless.compute(_inputs())["anchorage"]["tie"]["full"]
        slip = headless.compute(_inputs(sk="Y"))["anchorage"]["tie"]["full"]
        self.assertAlmostEqual(slip, 1.3 * plain, places=9)

    def test_bundle_multiplier(self):
        single = headless.compute(_inputs())["anchorage"]["tie"]["full"]
        four = headless.compute(_inputs(bundle="4"))["anchorage"]["tie"]["full"]
        self.assertAlmostEqual(four, 1.33 * single, places=9)


class OptionalNodeFaces(unittest.TestCase):
    """Nodal face stresses computed from the model forces, following the Tedds approach."""

    def test_face_stresses(self):
        values = _inputs(tieHeightMode="M", tieHeight=250)
        values["checks"]["nodeFaces"] = True
        result = headless.compute(values)
        faces, strut = result["nodeFaces"], result["strut"]
        sigma3 = 0.65 * 0.8 * 0.9 * 40
        self.assertAlmostEqual(faces["sigmaStrut"], strut["Ca"], places=9)
        self.assertAlmostEqual(result["util"]["nodeStrutFace"], strut["Ca"] / sigma3, places=12)
        self.assertAlmostEqual(result["util"]["nodeTieFace"], 2.2e6 / (400 * 250) / sigma3,
                               places=12)
        self.assertAlmostEqual(result["util"]["nodeBearingFace"],
                               strut["Cvstar"] / (400 * 800) / sigma3, places=12)

    def test_hydrostatic_tie_face(self):
        # Workbook node geometry: tie face height Omega = dc cos(theta) (Design!E44).
        values = _example()
        values["checks"]["nodeFaces"] = True
        result = headless.compute(values)
        omega = 428.44173148245596
        self.assertAlmostEqual(result["nodeFaces"]["tieHeight"], omega, places=9)
        self.assertAlmostEqual(result["util"]["nodeTieFace"],
                               5.131e6 / (600 * omega) / (0.65 * 0.8 * 0.9 * 50), places=9)
        self.assertAlmostEqual(result["util"]["nodeStrutFace"], 0.54 / 0.8, places=12)

    def test_off_by_default(self):
        result = headless.compute(_inputs())
        self.assertIsNone(result["nodeFaces"])
        self.assertNotIn("nodeTieFace", result["util"])


class Solver(unittest.TestCase):
    def test_scan_and_bisection_finds_the_fixed_point(self):
        def evaluate(theta):
            return engine.strut_state(theta, Cstar=3.0e6, fc=40, bc=400, Lstrut=3000, D=3000,
                                      a_manual=2700)
        found = engine.solve_theta(evaluate)
        self.assertTrue(found["converged"])
        state = evaluate(found["theta"])
        self.assertAlmostEqual(state["thetaAz"], found["theta"], places=9)


class InvalidInput(unittest.TestCase):
    def test_rejections(self):
        for overrides in ({"fc": 15}, {"fc": 125}, {"Cstar": 0}, {"Cserv": 4000},
                          {"Lstrut": 0}, {"thetaMode": "X"}, {"thetaMode": "M", "theta": 95},
                          {"aMode": "M", "aManual": 0}, {"crack": "Q"},
                          {"crack": "C", "fsic": 0}, {"fsy1": 450}, {"bundle": "5"},
                          {"ntype": "TTT"}, {"areaMode": "M", "A1": 400000, "A2": 300000},
                          {"tieBar": 140}, {"cts1": 0}, {"Tstar": ""}, {"Vrstar": -1},
                          {"layer1": 0}):
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(**overrides))


class Rendering(unittest.TestCase):
    def test_sheet_contains_column_style_sections(self):
        values = _example()
        values["checks"]["nodeFaces"] = True
        html = headless.render(values, headless.compute(values), standalone=True)
        for heading in ("Design Summary", "Design Inputs - Geometry", "Strut-and-Tie Model",
                        "Strut Geometry - Fig 7.2.4(A)", "Compression Strut - Cl 7.2",
                        "Bursting Strength - Cl 7.2.4(b)", "Bursting at Cracking - Eq 7.2.4(1)",
                        "Tension Tie - Cl 7.3", "Nodes - Cl 7.4.2", "Bearing Surfaces - Cl 12.6",
                        "Nodal Face Stresses - Cl 7.4.2",
                        "Design Basis, Assumptions and Limitations"):
            self.assertIn(heading, html)
        self.assertNotIn("&amp;#", html)
        self.assertNotIn("&amp;le;", html)
        self.assertLess(html.index("Design Summary"), html.index("Design Inputs - Actions"))
        self.assertLess(html.index("Design Inputs - Actions"), html.index("<svg"))

    def test_member_text_is_escaped(self):
        values = _inputs(memberNumber="<b>1</b>")
        html = headless.render(values, headless.compute(values), standalone=True)
        self.assertNotIn("<b>1</b>", html)


if __name__ == "__main__":
    unittest.main()
