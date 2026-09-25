"""Engineering and interface tests for the Concrete Flat Slab module.

Run from the suite root with ``src`` and the suite root on PYTHONPATH::

    python -m unittest discover -s calculations/concrete/concrete_flat_slab/tests -v
"""

from __future__ import annotations

import math
import unittest

from ic_concrete_flat_slab import engine, headless


def _inputs(**overrides):
    values = headless.defaults()
    values.update(overrides)
    return values


def _with(groups, **overrides):
    values = _inputs(**overrides)
    values["checks"] = {**values["checks"], **{group: True for group in groups}}
    return values


class SchemaAndDefaults(unittest.TestCase):
    def test_every_field_has_a_default_and_a_unique_id(self):
        layout = headless.schema()
        seen = [field["id"] for group in layout["groups"] for field in group["fields"]]
        seen += [field["id"] for group in layout["optional"] for field in group["fields"]]
        self.assertEqual(len(seen), len(set(seen)))
        values = headless.defaults()
        for field_id in seen:
            self.assertIn(field_id, values)

    def test_defaults_compute_and_are_fresh(self):
        first, second = headless.defaults(), headless.defaults()
        first["checks"]["minimumSteel"] = False
        self.assertTrue(second["checks"]["minimumSteel"])
        result = headless.compute(second)
        self.assertEqual(set(result["util"]), set(headless.ALWAYS_ON))

    def test_descriptor_matches_registration(self):
        descriptor = headless.descriptor()
        self.assertEqual(descriptor["id"], "concrete-flat-slab")
        self.assertEqual(descriptor["folder"], "14 - CONCRETE FLAT SLAB")
        self.assertEqual(descriptor["status"], "planned")
        self.assertEqual(descriptor["version"], "v0.0.1")


class HandCalculation(unittest.TestCase):
    """Independent arithmetic for an interior-column slab without drops."""

    def setUp(self):
        self.values = _inputs(Ly=7000, Lx=6000, Cy=500, Cx=400, Oy=300, Ox=250, th=220,
                              hasDrop="N", slabType="I", wdl=5.5, wsdl=1.0, wll=4.0,
                              fc=40, bar="12", cover=20, insideLayer="N", Ast=800, fsy="500",
                              Asc=0, spanType="E", lefDelta=250, lefDeltaInc=500)
        self.result = headless.compute(self.values)

    def test_static_moment_and_strip_distribution(self):
        g, q = 6.5, 4.0
        fd = max(1.35 * g, 1.2 * g + 1.5 * q)
        self.assertAlmostEqual(self.result["loads"]["Fd"], fd, places=12)
        # Integral columns: a_sup = c/2 each end, so Lo = L - 0.7 c.
        lo_y = 7000 - 0.7 * 500
        self.assertAlmostEqual(self.result["spans"]["Loy1"], lo_y, places=9)
        mo = fd * 6.0 * (lo_y / 1000) ** 2 / 8
        self.assertAlmostEqual(self.result["static"]["Moy1"], mo, places=9)
        strip = self.result["strips"]["y"]
        # Table 6.10.4.3 end span: -0.25 / +0.5 / -0.75; column strip takes 1.0 / 0.5 / 0.75.
        self.assertAlmostEqual(strip["total"][2], -0.75 * mo, places=9)
        self.assertAlmostEqual(strip["csPerM"][0], -0.25 * mo / 3.0, places=9)
        self.assertAlmostEqual(strip["msPerM"][1], 0.5 * 0.5 * mo / 2 / 1.5, places=9)
        edge = self.result["strips"]["edgeY"]
        self.assertAlmostEqual(edge["width"], 3000 + 250, places=9)
        self.assertAlmostEqual(edge["csWidth"], 250 + 1500, places=9)

    def test_minimum_steel_and_deflection(self):
        ds = 220 - 20 - 6
        ast_min = 0.24 * (220 / ds) ** 2 * 0.6 * math.sqrt(40) / 500 * 1000 * ds
        self.assertAlmostEqual(self.result["minimum"]["Astmin"], ast_min, places=9)
        self.assertAlmostEqual(self.result["util"]["minimumSteel"], ast_min / 800, places=12)
        d = self.result["deflection"]
        lef = min(7000 - 500 + 220, 7000)
        self.assertEqual(d["Lef"], lef)
        fcmi = -0.0015 * 1600 + 1.1429 * 40 - 0.0614
        self.assertGreater(fcmi, 40)
        ec = 2400 ** 1.5 * (0.024 * math.sqrt(fcmi) + 0.12)
        fdef = 3 * 6.5 + (0.7 + 0.4 * 2) * 4.0
        dmin = lef / (0.95 * 1.75 * (ec / 250 / (fdef / 1000)) ** (1 / 3))
        self.assertAlmostEqual(d["dmin"], dmin, places=9)
        self.assertAlmostEqual(self.result["util"]["deflectionTotal"], dmin / ds, places=12)

    def test_moment_transfer_interior_column(self):
        lo = 7000 - 0.7 * 500
        expected = 0.06 * 0.75 * 4.0 * 6.0 * (lo / 1000) ** 2
        self.assertAlmostEqual(self.result["transfer"]["interiorY"], expected, places=9)

    def test_applicability_ratios(self):
        util = self.result["util"]
        self.assertAlmostEqual(util["spanRatio"], 7000 / 6000 / 2, places=12)
        self.assertAlmostEqual(util["liveLoadRatio"], 4.0 / 13.0, places=12)
        self.assertAlmostEqual(util["liveLoadDeflection"], 4.0 / 6.5, places=12)
        self.assertEqual(util["ductilityClass"], 0.0)


class DeliberateDepartures(unittest.TestCase):
    def test_lo_lower_limit(self):
        values = _with(["customSupports"], asY1=4000, Ly=7000)
        result = headless.compute(values)
        self.assertAlmostEqual(result["spans"]["Loy1"], 0.65 * 7000, places=9)
        self.assertIn("Loy1", result["spans"]["floorApplied"])

    def test_wall_edge_strip_carries_no_span_moment(self):
        result = headless.compute(_inputs(slabType="F"))
        self.assertEqual(result["spans"]["Loye"], 0.0)
        self.assertEqual(result["static"]["Moye"], 0.0)

    def test_class_l_is_not_permitted(self):
        result = headless.compute(_inputs(reo="L"))
        self.assertTrue(math.isinf(result["util"]["ductilityClass"]))
        self.assertEqual(headless.summarise(result)["status"], "FAIL")
        self.assertTrue(math.isfinite(result["worstUtil"]))

    def test_live_load_over_twice_dead_fails(self):
        result = headless.compute(_inputs(wdl=5.0, wsdl=0.0, wll=12.0, th=200))
        self.assertAlmostEqual(result["util"]["liveLoadRatio"], 1.2, places=12)
        self.assertEqual(headless.summarise(result)["status"], "FAIL")

    def test_spans_are_swapped_with_their_properties(self):
        result = headless.compute(_inputs(Ly=5000, Lx=8000, Oy=100, Ox=300, Cy=450, Cx=350))
        geometry = result["geometry"]
        self.assertEqual((geometry["Ly"], geometry["Oy"], geometry["Cy"]), (8000, 300, 350))
        self.assertTrue(geometry["swapped"])

    def test_lef_replaces_workbook_lo(self):
        result = headless.compute(_inputs())
        d = result["deflection"]
        self.assertGreater(d["Lef"], d["LoWorkbook"])
        self.assertGreater(d["dmin"], d["workbook"]["dminDrop"])

    def test_custom_distribution_range(self):
        values = _with(["customDistribution"], cf2=0.8)
        result = headless.compute(values)
        self.assertAlmostEqual(result["util"]["distributionRange"], 0.8 / 0.7, places=12)


class OptionalChecks(unittest.TestCase):
    def test_flexure_hand_calculation(self):
        values = _with(["flexure"], barCt="16", sCt=150, coverTop=25, insideLayer="Y")
        result = headless.compute(values)
        location = next(item for item in result["flexure"]["locations"] if item["key"] == "Ct")
        As = math.pi * 64.0 * 1000.0 / 150.0
        d = 250 - 25 - 16 - 8
        alpha2, gamma = 0.85 - 0.0015 * 32, 0.97 - 0.0025 * 32
        ku = As * 500 / (alpha2 * 32 * gamma * 1000 * d)
        phi = max(0.65, min(0.85, 1.24 - 13 * ku / 12))
        phi_mu = phi * As * 500 * d * (1 - As * 500 / (2 * alpha2 * 32 * 1000 * d)) / 1e6
        self.assertAlmostEqual(location["phiMu"], phi_mu, places=9)
        peak = -min(result["strips"]["y"]["csPerM"] + result["strips"]["x"]["csPerM"])
        self.assertAlmostEqual(location["Mstar"], peak, places=12)
        self.assertAlmostEqual(location["ratioMoment"], peak / phi_mu, places=12)

    def test_edge_column_strip_excluded_with_edge_beam(self):
        result = headless.compute(_with(["flexure"], slabType="C"))
        keys = {item["key"] for item in result["flexure"]["locations"]}
        self.assertEqual(keys, {"Ct", "Cb", "Mt", "Mb"})

    def test_shrinkage_alone_and_with_flexure(self):
        alone = headless.compute(_with(["shrinkage"], restraint="STRONG"))
        self.assertAlmostEqual(alone["util"]["shrinkage"], 0.75 * 0.006 * 250 * 1000 / 1000,
                               places=12)
        both = headless.compute(_with(["shrinkage", "flexure"], restraint="STRONG"))
        self.assertNotIn("shrinkage", both["util"])
        self.assertTrue(all(item["AsMin"] >= 1125.0 for item in both["flexure"]["locations"]))


class InvalidInput(unittest.TestCase):
    def test_rejections(self):
        for overrides in ({"fc": 15}, {"fc": 125}, {"th": 0}, {"slabType": "X"},
                          {"bar": "11"}, {"loadType": "R"}, {"cover": 240}, {"dc": 400},
                          {"wll": ""}, {"Cy": 8000}, {"spanType": "S"}, {"hasDrop": "maybe"},
                          {"Oy": -1}, {"wdl": True}):
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(**overrides))

    def test_custom_factor_outside_zero_to_one(self):
        with self.assertRaises(ValueError):
            headless.compute(_with(["customDistribution"], cf3=1.2))

    def test_lower_case_options_accepted(self):
        result = headless.compute(_inputs(hasDrop="y", limitStrip="n", slabType="c"))
        self.assertEqual(result["analysis"]["fstype"], 3)


class Rendering(unittest.TestCase):
    def test_sheet_contains_column_style_sections(self):
        values = _with(["flexure", "shrinkage", "customDistribution"])
        html = headless.render(values, headless.compute(values), standalone=True)
        for heading in ("Design Summary", "Design Inputs - Geometry and Material",
                        "Slab Plan and Design Strips", "Design Strip Moments",
                        "Applicability of the Simplified Method - Cl 6.10.4.1",
                        "Total Static Moments - Cl 6.10.4.2",
                        "Moment Transfer to Interior Columns - Cl 6.10.4.5",
                        "Deflection by Deemed-to-Comply Span-to-Depth - Cl 9.4.4.1",
                        "Flexural Capacity - Cl 8.1", "Design Basis, Assumptions and Limitations"):
            self.assertIn(heading, html)
        self.assertNotIn("&amp;#", html)
        self.assertIn("Concrete Flat Slab Design v0.0.1", html)

    def test_every_slab_type_renders(self):
        for slab in engine.SLAB_TYPES:
            with self.subTest(slab=slab):
                values = _inputs(slabType=slab)
                self.assertIn("<svg", headless.render(values, headless.compute(values)))


if __name__ == "__main__":
    unittest.main()
