"""Engineering and interface tests for the Concrete Beam and Slab Design module.

Run from the suite root with ``src`` and the suite root on PYTHONPATH::

    python -m unittest discover -s calculations/concrete/concrete_member/tests -v
"""

from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

from ic_concrete_member import engine, headless
from ic_concrete_member.common import bar_area, calc_ast

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "worked-example.json"
ALPHA2, GAMMA = 0.85 - 0.0015 * 32, 0.97 - 0.0025 * 32  # f'c = 32 MPa


def _inputs(**overrides):
    values = headless.defaults()
    values.update(overrides)
    return values


def _beam(**overrides):
    base = {"sectionType": "R", "fc": 32, "D": 600, "W": 400, "cover": 30, "coverTop": 30,
            "coverSide": 30, "ligs": "10", "barBot": "20", "botMode": "N", "botValue": 3,
            "barTop": "12", "topMode": "N", "topValue": 0, "Mstar": 150}
    return _inputs(**{**base, **overrides})


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
        first["checks"]["flexure"] = False
        self.assertTrue(second["checks"]["flexure"])
        result = headless.compute(second)
        for key in engine.ALWAYS_ON:
            self.assertIn(key, result["util"])

    def test_descriptor_matches_registration(self):
        descriptor = headless.descriptor()
        self.assertEqual(descriptor["id"], "concrete-member")
        self.assertEqual(descriptor["folder"], "17 - CONCRETE MEMBER")
        self.assertEqual(descriptor["status"], "planned")
        self.assertEqual(descriptor["version"], "v0.0.1")

    def test_optional_groups_off_by_default(self):
        result = headless.compute(headless.defaults())
        self.assertIsNone(result["deflection"])
        self.assertIsNone(result["crackWidth"])
        for key in ("crackWidth", "deflectionTotalCalc", "slenderness", "secondarySteel"):
            self.assertNotIn(key, result["util"])


class BendingHandCalculations(unittest.TestCase):
    def test_singly_reinforced_rectangle(self):
        result = headless.compute(_beam())
        face = result["flexure"]["governing"]
        ast = 3 * bar_area(20)
        d = 600 - 30 - 10 - 10
        ku = ast * 500 / (ALPHA2 * 32 * GAMMA * 400 * d)
        mu = ast * 500 * (d - GAMMA * ku * d / 2) / 1e6
        phi = min(0.85, max(0.65, 1.24 - 13 * ku / 12))
        self.assertAlmostEqual(face["d"], d, places=12)
        self.assertAlmostEqual(face["ku"], ku, places=12)
        self.assertAlmostEqual(face["Mu"], mu, places=9)
        self.assertAlmostEqual(face["phiMu"], phi * mu, places=9)
        self.assertAlmostEqual(result["util"]["flexure"], 150 / (phi * mu), places=12)

    def test_doubly_reinforced_compression_steel_yields(self):
        result = headless.compute(_beam(D=700, botMode="A", botValue=5500, barBot="28",
                                        topMode="A", topValue=1000, barTop="16", coverTop=20,
                                        Mstar=900))
        face = result["flexure"]["governing"]
        d, dc = 700 - 30 - 10 - 14, 20 + 10 + 8
        ku = (5500 - 1000) * 500 / (ALPHA2 * GAMMA * 32 * 400 * d)
        self.assertTrue(face["yieldValid"])
        self.assertGreaterEqual(0.003 * (ku * d - dc) / (ku * d), 500 / 200000)
        mu = (500 * 1000 * (d - dc) + ALPHA2 * 32 * 400 * GAMMA * ku * d
              * (d - 0.5 * GAMMA * ku * d)) / 1e6
        self.assertAlmostEqual(face["ku"], ku, places=12)
        self.assertAlmostEqual(face["Mu"], mu, places=9)
        # kuo > 0.36 is accepted with Asc >= 0.01 b kuo do (Tedds AS3600-2018 rule).
        self.assertGreater(face["kuo"], 0.36)
        self.assertAlmostEqual(result["util"]["ductility"], 0.01 * 400 * ku * d / 1000, places=9)

    def test_tee_beam_stress_block_in_web(self):
        result = headless.compute(_beam(sectionType="F", W=300, Bf=800, Tf=100, Lm=6000,
                                        botMode="A", botValue=5000, barBot="28", Mstar=800))
        face = result["flexure"]["governing"]
        self.assertEqual(result["section"]["bef"], 800)
        self.assertFalse(face["inFlange"])
        d = 600 - 30 - 10 - 14
        cf = ALPHA2 * 32 * 100 * (800 - 300) / 1000
        cw = 5000 * 500 / 1000 - cf
        kud = cw * 1000 / (ALPHA2 * 32 * GAMMA * 300)
        mu = (cf * (d - 50) + cw * (d - 0.5 * GAMMA * kud)) / 1000
        self.assertAlmostEqual(face["kud"], kud, places=9)
        self.assertAlmostEqual(face["Mu"], mu, places=9)

    def test_effective_flange_width(self):
        result = headless.compute(_beam(sectionType="F", W=300, Bf=3000, Tf=150, Lm=8000,
                                        supportType="C"))
        self.assertAlmostEqual(result["section"]["bef"], 300 + 0.2 * 0.7 * 8000, places=12)
        result = headless.compute(_beam(sectionType="F", btype="L", W=300, Bf=3000, Tf=150,
                                        Lm=8000))
        self.assertAlmostEqual(result["section"]["bef"], 300 + 0.1 * 8000, places=12)

    def test_minimum_steel_deemed_to_comply(self):
        result = headless.compute(_beam(astMinBasis="D"))
        d = 600 - 30 - 10 - 10
        expected = 0.2 * 0.6 * math.sqrt(32) / 500 * (600 / d) ** 2 * 400 * d
        self.assertAlmostEqual(result["minimum"]["AsMin"], expected, places=9)
        self.assertAlmostEqual(result["util"]["minimumSteel"], expected / (3 * bar_area(20)),
                               places=12)

    def test_negative_moment_without_top_steel_is_unattainable(self):
        result = headless.compute(_beam(Mstar=-50))
        self.assertTrue(math.isinf(result["util"]["flexure"]))
        self.assertEqual(headless.summarise(result)["status"], "FAIL")

    def test_bar_layers_and_centroid(self):
        result = headless.compute(_beam(W=300, botValue=7, barBot="24", clearBot=40, vclearBot=40))
        bottom = result["reinforcement"]["bottom"]
        per_layer = 1 + int((300 - 60 - 20 - 24) / (24 + 40))
        self.assertEqual(per_layer, 4)
        self.assertEqual(bottom["perLayer"], per_layer)
        self.assertEqual(bottom["layers"], 2)
        # 4 bars in the outer layer and 3 in the inner layer, 64 mm apart.
        self.assertAlmostEqual(bottom["offset"], 3 * 64 / 7, places=9)
        self.assertAlmostEqual(result["reinforcement"]["ds"], 600 - 30 - 10 - 12 - 3 * 64 / 7,
                               places=9)


class ShearHandCalculations(unittest.TestCase):
    def test_general_method_with_fitments(self):
        result = headless.compute(_beam(botValue=4, Vstar=300, MstarV=200, NstarV=0, Tstar=0,
                                        s=150, legs=2, shearMethod="G", dg=20))
        s = result["shear"]
        d = 600 - 30 - 10 - 10
        dv = max(0.72 * 600, 0.9 * d)
        ast = 4 * bar_area(20)
        eps = min((200 / (dv / 1000) + 300) / (2 * 200000 * ast / 1000), 0.003)
        kv = 0.4 / (1 + 1500 * eps)
        theta = math.radians(29 + 7000 * eps)
        vuc = kv * 400 * dv * math.sqrt(32) / 1000
        asv = 2 * math.pi * 25
        vus = asv * 500 * dv / 150 / math.tan(theta) / 1000
        vu_max = 0.55 * 0.9 * 32 * 400 * dv / 1000 / math.tan(theta) / (1 + 1 / math.tan(theta) ** 2)
        self.assertGreaterEqual(asv, 0.08 * math.sqrt(32) * 400 * 150 / 500)
        self.assertAlmostEqual(s["kv"], kv, places=12)
        self.assertAlmostEqual(s["Vuc"], vuc, places=9)
        self.assertAlmostEqual(s["Vus"], vus, places=9)
        self.assertAlmostEqual(s["phiVu"], min(0.75 * (vuc + vus), 0.7 * vu_max), places=9)
        self.assertAlmostEqual(result["util"]["shear"], 300 / s["phiVu"], places=12)

    def test_shear_above_threshold_without_fitments_fails(self):
        result = headless.compute(_beam(botValue=4, Vstar=150, MstarV=80, ligs="0"))
        s = result["shear"]
        self.assertGreater(s["V"], s["ksPhiVuc"])
        self.assertGreater(result["util"]["shear"], 1.0)

    def test_simplified_kv_cap_without_fitments(self):
        values = _inputs(sectionType="S", D=200, botMode="S", botValue=200, barBot="12",
                         topMode="S", topValue=300, barTop="10", ligs="0", legs=0, Mstar=20,
                         Vstar=60, MstarV=20, shearMethod="S")
        s = headless.compute(values)["shear"]
        self.assertAlmostEqual(s["kv"], min(200 / (1000 + 1.3 * s["dv"]), 0.10), places=12)
        self.assertAlmostEqual(s["theta"], 36.0)

    def test_wider_spacing_rejected_when_shear_exceeds_minimum_capacity(self):
        result = headless.compute(_beam(botValue=4, Vstar=450, MstarV=100, s=150))
        self.assertTrue(result["shear"]["wideRejected"])
        self.assertAlmostEqual(result["shear"]["sLimit"], 300.0)

    def test_torsion_strength(self):
        result = headless.compute(_beam(botValue=4, Vstar=100, MstarV=50, Tstar=30, s=150))
        s = result["shear"]
        xo, yo = 400 - 60 - 10, 600 - 60 - 10
        ao = 0.85 * xo * yo
        tus = 2 * ao * math.pi * 25 * 500 / 150 / math.tan(math.radians(s["theta"])) / 1e6
        self.assertTrue(s["considerTorsion"])
        self.assertAlmostEqual(s["Tus"], tus, places=9)
        self.assertAlmostEqual(result["util"]["torsion"], 30 / (0.75 * tus), places=9)

    def test_compression_phi_uses_2018_value(self):
        result = headless.compute(_beam(botValue=4, Vstar=200, MstarV=100, NstarV=5000))
        self.assertAlmostEqual(result["shear"]["phiTt"], 0.65, places=12)


class ServiceabilityHandCalculations(unittest.TestCase):
    def test_crack_control_steel_stress(self):
        result = headless.compute(_beam(botValue=4, Mstar=200, msMode="M", Ms=120))
        face = result["crack"]["governing"]
        n = result["materials"]["n"]
        ast = 4 * bar_area(20)
        d = 550
        p = ast / (400 * d)
        k = -n * p + math.sqrt((n * p) ** 2 + 2 * n * p)
        icr = (4 * k ** 3 + 12 * n * p * (1 - k) ** 2) * 400 * d ** 3 / 12
        self.assertAlmostEqual(face["k"], k, places=12)
        self.assertAlmostEqual(face["fscr"], n * 120e6 * (d - k * d) / icr, places=9)

    def test_crack_width_uses_tension_depth_for_negative_bending(self):
        values = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        width = headless.compute(values)["crackWidth"]["negative"]
        self.assertAlmostEqual(width["hca"], min(width["hc"], 600 - 40.54245125061332), places=6)
        self.assertAlmostEqual(width["hca"], 120.0, places=12)

    def test_deemed_to_comply_beam(self):
        result = headless.compute(_beam(botValue=4, Lm=6000, spanType="S", wsdl=10, wll=8))
        d = result["deemed"]
        k1, k2 = d["k1"], 5 / 384
        expected = 6000 / ((k1 / 250 * 400 * d["Ec"] / (k2 * d["Fdef"])) ** (1 / 3))
        self.assertAlmostEqual(d["dmin"], expected, places=9)
        g = result["section"]["swt"] + 10
        self.assertAlmostEqual(result["util"]["liveLoadLimit"], 8 / g, places=12)

    def test_deemed_to_comply_slab(self):
        values = _inputs(sectionType="S", D=200, botMode="S", botValue=200, barBot="12",
                         topMode="S", topValue=300, barTop="10", ligs="0", legs=0, Mstar=20,
                         spanType="E", wsdl=1.0, wll=3.0, Lm=5000)
        d = headless.compute(values)["deemed"]
        expected = 5000 / (1.0 * 1.75 * (d["Ec"] / 250 / (d["Fdef"] / 1000)) ** (1 / 3))
        self.assertAlmostEqual(d["dmin"], expected, places=9)

    def test_creep_needs_manual_value_above_100_mpa(self):
        with self.assertRaises(ValueError):
            headless.compute(_inputs(fc=110))
        result = headless.compute(_inputs(fc=110, fccMode="M", fccManual=1.1))
        self.assertEqual(result["creep"]["fcc"], 1.1)

    def test_calc_ast_unattainable_is_infinite(self):
        self.assertTrue(math.isinf(calc_ast(500, 32, 300, 400, 5000, 0.85, ALPHA2)))

    def test_calculated_deflection_rejects_unattainable_position_moment(self):
        values = _beam()
        values["checks"]["calcDeflection"] = True
        headless.compute(values)
        values["mX"] = 5000
        with self.assertRaises(ValueError):
            headless.compute(values)


class WorkbookExample(unittest.TestCase):
    def test_saved_example_outcome(self):
        values = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        result = headless.compute(values)
        self.assertAlmostEqual(result["flexure"]["phiMu"], 26.426724337950624, places=9)
        self.assertAlmostEqual(result["util"]["minimumSteel"], 3.914418765908511, places=9)
        self.assertEqual(headless.summarise(result)["status"], "FAIL")


class InvalidInput(unittest.TestCase):
    def test_rejections(self):
        for overrides in ({"fc": 15}, {"fc": 125}, {"D": 0}, {"W": -5}, {"sectionType": "X"},
                          {"barBot": "11"}, {"botMode": "Q"}, {"botValue": 2.5},
                          {"botValue": 31}, {"fsy": "450"}, {"wmax": "0.25"},
                          {"cover": 700}, {"sectionType": "F", "Bf": 300},
                          {"sectionType": "F", "Tf": 0}, {"Mstar": ""}, {"Mstar": True},
                          {"Vstar": "abc"}, {"s": 0}, {"alphaV": 30}, {"density": 1500},
                          {"environment": "Z"}, {"legs": 1.5}, {"Mstar": math.nan}):
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(**overrides))

    def test_case_folding(self):
        result = headless.compute(_inputs(useFcmi="n", extend="n", spanType="s"))
        self.assertIn("flexure", result["util"])


class Rendering(unittest.TestCase):
    def test_sheet_contains_column_style_sections(self):
        values = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        html = headless.render(values, headless.compute(values), standalone=True)
        for heading in ("Design Summary", "Design Inputs - Section and Material",
                        "Section, Reinforcement and Ultimate Strain", "Strength in Bending",
                        "Minimum Strength Requirements - Cl 8.1.6.1", "Crack Control - Cl 8.6",
                        "Shear Strength - Cl 8.2", "Deemed-to-Comply Deflection - Cl 8.5.4",
                        "Calculated Deflection - Cl 8.5.3",
                        "Design Basis, Assumptions and Limitations"):
            self.assertIn(heading, html)
        self.assertIn("<svg", html)
        self.assertNotIn("&amp;#", html)
        self.assertIn("CB - Concrete Beam and Slab Design v0.0.1", html)

    def test_slab_and_tee_render(self):
        for overrides in ({"sectionType": "S", "D": 200, "botMode": "S", "botValue": 200,
                           "topMode": "S", "topValue": 300, "ligs": "0", "legs": 0, "Mstar": 20},
                          {"sectionType": "F", "W": 300, "Bf": 1200, "Tf": 120, "Mstar": -150,
                           "topValue": 4}):
            with self.subTest(overrides=overrides):
                values = _inputs(**overrides)
                html = headless.render(values, headless.compute(values), standalone=True)
                self.assertIn("Design Summary", html)
                self.assertNotIn("&amp;#", html)


if __name__ == "__main__":
    unittest.main()
