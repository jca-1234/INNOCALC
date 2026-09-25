"""Engineering and interface tests for the Concrete Punching Shear module.

Run from the suite root with ``src`` and the suite root on PYTHONPATH::

    python -m unittest discover -s calculations/concrete/concrete_punching_shear/tests -v
"""

from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

from ic_concrete_punching_shear import engine, headless

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "worked-example.json"


def _inputs(**overrides):
    values = headless.defaults()
    values.update(overrides)
    return values


def _example(**overrides):
    values = json.loads(EXAMPLE.read_text(encoding="utf-8"))
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
        first["checks"]["punching"] = False
        self.assertTrue(second["checks"]["punching"])
        result = headless.compute(second)
        self.assertEqual(headless.summarise(result)["status"], "OK")

    def test_descriptor_matches_registration(self):
        descriptor = headless.descriptor()
        self.assertEqual(descriptor["id"], "concrete-punching-shear")
        self.assertEqual(descriptor["folder"], "13 - CONCRETE PUNCHING SHEAR")
        self.assertEqual(descriptor["status"], "planned")
        self.assertEqual(descriptor["version"], "v0.0.1")


class StrengthWithoutMoment(unittest.TestCase):
    """Cl 9.3.3 by hand."""

    def test_internal_rectangular_column(self):
        result = headless.compute(_inputs(fc=40, Ds=250, dom=200, pL=600, pW=400, Mvstar=0,
                                          Vstar=600, dialp="0", ctsp=0))
        fcv = min(0.17 * (1 + 2 / 1.5) * math.sqrt(40), 0.34 * math.sqrt(40))
        self.assertAlmostEqual(fcv, 0.34 * math.sqrt(40), places=12)
        u = 2 * (600 + 200 + 400 + 200)
        phi_vuo = 0.7 * u * 200 * fcv
        self.assertAlmostEqual(result["geometry"]["u"], u, places=9)
        self.assertAlmostEqual(result["strength"]["phiVuo"], phi_vuo, places=6)
        self.assertEqual(result["governing"]["equation"], "Eq 9.3.3(1)")
        self.assertAlmostEqual(result["util"]["punching"], 600e3 / phi_vuo, places=12)

    def test_elongated_column_uses_beta_h(self):
        result = headless.compute(_inputs(pL=1000, pW=250, Mvstar=0, fc=32))
        self.assertAlmostEqual(result["geometry"]["betaH"], 4.0, places=12)
        self.assertAlmostEqual(result["strength"]["fcv"], 0.17 * 1.5 * math.sqrt(32), places=12)

    def test_prestress_adds_to_fcv(self):
        base = headless.compute(_inputs(Mvstar=0, ps=0))
        stressed = headless.compute(_inputs(Mvstar=0, ps=2.0))
        g = base["geometry"]
        self.assertAlmostEqual(stressed["strength"]["phiVuo"] - base["strength"]["phiVuo"],
                               0.7 * g["u"] * g["domc"] * 0.6, places=6)
        self.assertIn("prestressDepth", stressed["util"])

    def test_shear_head_limits(self):
        result = headless.compute(_inputs(fc=20, shearhead="Y", Mvstar=0))
        g = result["geometry"]
        expected = 0.7 * g["u"] * g["domc"] * min(0.5 * math.sqrt(20), 0.2 * 20)
        self.assertAlmostEqual(result["strength"]["phiVuo"], expected, places=6)
        self.assertEqual(result["governing"]["equation"], "Eq 9.3.3(2)")

    def test_circular_internal_perimeter(self):
        result = headless.compute(_inputs(col="Y", pL=500, dom=180, Ds=220, Mvstar=0))
        self.assertAlmostEqual(result["geometry"]["u"], math.pi * 680, places=9)
        self.assertEqual(result["geometry"]["betaH"], 1.0)


class PerimeterGeometry(unittest.TestCase):
    def test_rectangular_edge_with_w_on_edge(self):
        result = headless.compute(_inputs(pPos="E", pface="W", pL=600, pW=400, dom=160, Ds=200))
        g = result["geometry"]
        # pX = W = 400 along the edge, pY = L = 600 away from it.
        self.assertAlmostEqual(g["u"], 2 * (600 + 80) + 400 + 160, places=9)
        self.assertAlmostEqual(g["aL"], 600 + 80, places=9)
        self.assertAlmostEqual(g["aW"], 400 + 160, places=9)

    def test_rectangular_corner(self):
        result = headless.compute(_inputs(pPos="C", pL=500, pW=300, dom=150, Ds=200, pmDir="W",
                                          wcl=375))
        g = result["geometry"]
        self.assertAlmostEqual(g["u"], 500 + 300 + 150, places=9)
        self.assertAlmostEqual(g["a"], 300 + 75, places=9)

    def test_circular_edge_and_corner(self):
        edge = headless.compute(_inputs(col="Y", pL=400, dom=150, Ds=200, pPos="E", wcl=550))
        corner = headless.compute(_inputs(col="Y", pL=400, dom=150, Ds=200, pPos="C", wcl=550))
        self.assertAlmostEqual(edge["geometry"]["u"], math.pi * 550 / 2 + 400, places=9)
        self.assertAlmostEqual(corner["geometry"]["u"], math.pi * 550 / 4 + 400, places=9)
        self.assertTrue(any("circular column" in item for item in edge["warnings"]))

    def test_ineffective_portion(self):
        full = headless.compute(_inputs())
        reduced = headless.compute(_inputs(ineffU=200))
        self.assertAlmostEqual(full["geometry"]["u"] - reduced["geometry"]["u"], 200, places=9)
        void = headless.compute(_inputs(ineffU=1e6))
        self.assertEqual(void["geometry"]["u"], 0.0)
        self.assertTrue(math.isinf(void["util"]["punching"]))
        self.assertEqual(headless.summarise(void)["status"], "FAIL")


class SpandrelMeanDepth(unittest.TestCase):
    """The bisection replacing the RecalcDom GoalSeek."""

    def _spandrel(self, **overrides):
        base = dict(pPos="E", pface="L", pL=400, pW=400, Ds=200, dom=150, span="Y",
                    ignorespan="N", Db=600, bw=300, wcl=600)
        return headless.compute(_inputs(**{**base, **overrides}))

    def test_fixed_point_is_the_weighted_average(self):
        result = self._spandrel()
        g = result["geometry"]
        d, dsp = g["domc"], 600 - 50
        leg = 400 + d / 2
        u = 2 * leg + 400 + d
        surface = 2 * (300 * dsp + (leg - 300) * 150) + (400 + d) * 150
        self.assertTrue(g["solution"]["exact"])
        self.assertAlmostEqual(d, surface / u, places=6)
        self.assertTrue(150 < d < dsp)

    def test_ignored_spandrel_uses_slab_depth(self):
        result = self._spandrel(ignorespan="Y")
        self.assertEqual(result["geometry"]["domc"], 150)

    def test_no_exact_solution_at_the_spandrel_boundary(self):
        # Below dom = 400 the whole perimeter is in the spandrel (average 550 > dom); at 400
        # the parallel face leaves it and the average drops to 390 < dom.
        result = self._spandrel(bw=600)
        g = result["geometry"]
        self.assertFalse(g["solution"]["exact"])
        self.assertAlmostEqual(g["domc"], 400, places=6)
        self.assertTrue(any("No exact mean depth" in item for item in result["warnings"]))

    def test_spandrel_must_be_deeper_than_slab(self):
        with self.assertRaises(ValueError):
            self._spandrel(Db=200)


class StrengthWithMoment(unittest.TestCase):
    """Cl 9.3.4 by hand."""

    def test_no_fitments_eq_9_3_4_1(self):
        result = headless.compute(_inputs(dialp="0", ctsp=0, Vstar=400, Mvstar=40))
        g, s = result["geometry"], result["strength"]
        expected = s["phiVuo"] / (1 + g["u"] * 40e6 / (8 * 400e3 * g["a"] * g["domc"]))
        self.assertAlmostEqual(result["transfer"]["phiVuA"], expected, places=6)
        self.assertEqual(result["governing"]["equation"], "Eq 9.3.4(1)")
        self.assertAlmostEqual(result["util"]["punching"], 400e3 / expected, places=12)

    def test_torsion_strip_fitments_eq_9_3_4_2_and_4(self):
        result = headless.compute(_inputs(Vstar=500, Mvstar=25))
        g, s, f = result["geometry"], result["strength"], result["fitments"]
        vu_min = 1.2 * s["phiVuo"] / (1 + g["u"] * 25e6 / (2 * 500e3 * g["a"] ** 2))
        y1 = min(g["a"], max(767 - 12, 200 - 50 - 12))
        enhanced = vu_min * math.sqrt((math.pi * 36 / 200) / (0.2 * y1 / 500))
        ceiling = 3 * vu_min * math.sqrt(200 / g["a"])
        self.assertAlmostEqual(f["phiVuB"], vu_min, places=6)
        self.assertAlmostEqual(f["phiVuD"], min(enhanced, ceiling), places=6)
        self.assertEqual(result["governing"]["equation"], "Eq 9.3.4(4)")

    def test_spandrel_fitments_eq_9_3_4_3(self):
        result = headless.compute(_inputs(pPos="E", span="Y", ignorespan="Y", Db=500, bw=400,
                                          dialp="12", ctsp=150, wcl=0))
        g, s, f = result["geometry"], result["strength"], result["fitments"]
        vu_min = (1.2 * s["phiVuo"] * (500 / 200)
                  / (1 + g["u"] * 25e6 / (2 * 500e3 * g["a"] * 400)))
        self.assertAlmostEqual(f["phiVuC"], vu_min, places=6)
        self.assertEqual(f["y1"], 500 - 50 - 12)
        self.assertEqual(f["maxcts"], 300)
        self.assertNotIn("fitmentWidth", result["util"])

    def test_fitments_do_not_help_when_mv_is_zero(self):
        result = headless.compute(_inputs(Mvstar=0))
        self.assertEqual(result["governing"]["capacity"], result["strength"]["phiVuo"])
        self.assertTrue(any("do not increase" in item for item in result["warnings"]))


class WorkbookCorrections(unittest.TestCase):
    def test_saved_example_governs_on_the_fitments(self):
        # The workbook shows No Good for the no-fitment and minimum-fitment rows but the
        # fitments provided satisfy Eq 9.3.4(4): 50 / 102.5 = 0.49 (Design!I12).
        result = headless.compute(_example())
        self.assertAlmostEqual(result["util"]["punching"], 50 / 102.5445307664274, places=9)
        self.assertGreater(50e3 / result["transfer"]["phiVuA"], 1.0)
        self.assertEqual(headless.summarise(result)["status"], "OK")

    def test_fitments_below_minimum_are_ignored_and_fail(self):
        result = headless.compute(_inputs(dialp="6", ctsp=200, wcl=767))
        self.assertFalse(result["fitments"]["valid"])
        self.assertEqual(result["governing"]["equation"], "Eq 9.3.4(1)")
        self.assertGreater(result["util"]["fitmentArea"], 1.0)
        self.assertEqual(headless.summarise(result)["status"], "FAIL")

    def test_zero_spacing_means_no_fitments(self):
        # Design!F67 gives a non-zero strength here because Asw.min = 0.
        result = headless.compute(_inputs(dialp="12", ctsp=0))
        self.assertFalse(result["fitments"]["provided"])
        self.assertEqual(result["fitments"]["phiVuB"], 0.0)
        self.assertNotIn("fitmentArea", result["util"])

    def test_fitment_spacing_limit(self):
        result = headless.compute(_inputs(ctsp=250))
        self.assertAlmostEqual(result["util"]["fitmentSpacing"], 250 / 200, places=12)
        self.assertFalse(result["fitments"]["valid"])

    def test_minimum_transferred_moment(self):
        reported = headless.compute(_inputs())
        v1, v2 = 1.2 * 6 + 0.75 * 4, 1.2 * 6
        m_min = 0.06 * (v1 * 6000 * 6350 ** 2 - v2 * 6000 * 5850 ** 2) / 1000
        self.assertAlmostEqual(reported["moment"]["MvMin"], m_min, places=3)
        self.assertEqual(reported["moment"]["Mdesign"], 25e6)
        self.assertTrue(any("Cl 6.10.4.5" in item for item in reported["warnings"]))
        applied = headless.compute(_inputs(simplifiedMethod="Y"))
        self.assertAlmostEqual(applied["moment"]["Mdesign"], m_min, places=3)
        self.assertGreater(applied["util"]["punching"], reported["util"]["punching"])
        edge = headless.compute(_inputs(simplifiedMethod="Y", pPos="E", wcl=500))
        self.assertEqual(edge["moment"]["Mdesign"], 25e6)

    def test_integrity_reinforcement(self):
        result = headless.compute(_inputs(Nstar=500, fsy="500", ibar="16", nIntegrity=10))
        as_min = 2 * 500e3 / (0.7 * 500)
        self.assertAlmostEqual(result["integrity"]["AsMin"], as_min, places=9)
        self.assertAlmostEqual(result["util"]["integrity"], as_min / (10 * math.pi * 64), places=12)
        waived = headless.compute(_inputs(beams="Y", nIntegrity=0))
        self.assertNotIn("integrity", waived["util"])
        missing = headless.compute(_inputs(nIntegrity=0))
        self.assertTrue(math.isinf(missing["util"]["integrity"]))
        self.assertEqual(headless.summarise(missing)["status"], "FAIL")

    def test_excel_text_is_case_insensitive(self):
        upper = headless.compute(_example())
        lower = headless.compute(_example(pPos="i", pface="l", shearhead="n", ignorespan="y"))
        self.assertEqual(upper["util"], lower["util"])


class OptionalChecks(unittest.TestCase):
    def test_mean_depth_from_layers(self):
        values = _inputs(Ds=250, domCover=30, barOuter="16", barInner="12")
        values["checks"] = {**values["checks"], "effectiveDepth": True}
        result = headless.compute(values)
        expected = ((250 - 30 - 8) + (250 - 30 - 16 - 6)) / 2
        self.assertAlmostEqual(result["geometry"]["domInput"], expected, places=12)
        self.assertEqual(result["geometry"]["domSource"], "layers")

    def test_layers_off_by_default(self):
        result = headless.compute(_inputs())
        self.assertIsNone(result["layers"])


class InvalidInput(unittest.TestCase):
    def test_rejections(self):
        for overrides in ({"fc": 15}, {"fc": 125}, {"pL": 300, "pW": 400}, {"dom": 200},
                          {"dom": 10}, {"pLod": 7000}, {"Vstar": -1}, {"Mvstar": -5},
                          {"dialp": "11"}, {"pPos": "X"}, {"Vstar": ""}, {"Vstar": True},
                          {"nIntegrity": 2.5}, {"fc": float("nan")}, {"span": "maybe"},
                          {"span": "Y", "Db": 150}):
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(**overrides))

    def test_missing_field(self):
        values = _inputs()
        del values["Ds"]
        with self.assertRaises(ValueError):
            engine.compute(values)


class Rendering(unittest.TestCase):
    def test_sheet_contains_column_style_sections(self):
        values = _example()
        html = headless.render(values, headless.compute(values), standalone=True)
        for heading in ("Design Summary", "Design Inputs - Slab and Column",
                        "Plan of Loaded Area and Critical Shear Perimeter",
                        "Critical Shear Perimeter - Cl 9.3.1",
                        "Ultimate Shear Strength Where Mv* = 0 - Cl 9.3.3",
                        "Ultimate Shear Strength Where Mv* > 0 - Cl 9.3.4",
                        "Closed Fitments - Cl 9.3.5 and Cl 9.3.6", "Punching Shear Check - Cl 9.3",
                        "Integrity Reinforcement - Cl 9.2",
                        "Design Basis, Assumptions and Limitations",
                        "Slab-SP01 - Concrete Punching Shear Design v0.0.1"):
            self.assertIn(heading, html)
        self.assertNotIn("&amp;#", html)
        self.assertNotIn("&amp;amp;", html)

    def test_drawings_for_every_position(self):
        for overrides in ({"pPos": "E"}, {"pPos": "C", "spanbothsides": "N"},
                          {"pPos": "C", "col": "Y"}, {"pPos": "E", "col": "Y", "span": "Y",
                                                     "ignorespan": "N"},
                          {"pPos": "E", "pface": "L", "pmDir": "W"}):
            with self.subTest(overrides=overrides):
                values = _inputs(wcl=500, **overrides)
                html = headless.render(values, headless.compute(values))
                self.assertIn("<svg", html)
                self.assertNotIn("nan", html.split("<svg", 1)[1].split("</svg>", 1)[0])


class Baseline(unittest.TestCase):
    def test_workbook_baseline_reproduced(self):
        from ic_concrete_punching_shear.validation import baseline
        report = baseline()
        self.assertTrue(report["ok"], report["failures"])
        self.assertGreaterEqual(report["compared"], 30)


if __name__ == "__main__":
    unittest.main()
