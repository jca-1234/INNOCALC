"""Engineering and interface tests for the Concrete Deep Beam Design module."""

from __future__ import annotations

import math
import unittest
from copy import deepcopy

from ic_concrete_deep_beam import engine, headless

WORKBOOK = {
    "spanType": "c", "L": 3000, "D": 4000, "bw": 300, "support": 900, "Df": 100,
    "fc": 100, "fsy": "500", "bar": "16", "mesh": 10, "crack": "W", "fsic": 351,
    "gs": 1.15, "gc": 1.5, "Mstar": 2000, "Mstarn": 1000, "Vstar": 900, "Rstar": 1800,
    "Pstar": 100, "wstar": 10, "reodiste": 1,
}


def _inputs(**overrides):
    values = headless.defaults()
    values["date"] = "01/01/2026"
    values.update(overrides)
    return values


class SchemaAndDefaults(unittest.TestCase):
    def test_every_field_has_a_default_and_a_unique_id(self):
        layout = headless.schema()
        seen: list[str] = []
        for group in layout["groups"] + layout["optional"]:
            for field in group["fields"]:
                self.assertIn("default", field, field["id"])
                seen.append(field["id"])
        self.assertEqual(len(seen), len(set(seen)))
        for field_id in seen:
            self.assertIn(field_id, headless.defaults())

    def test_defaults_are_fresh_and_valid(self):
        first, second = headless.defaults(), headless.defaults()
        first["checks"]["diagonalCompression"] = False
        self.assertTrue(second["checks"]["diagonalCompression"])
        self.assertTrue(math.isfinite(headless.compute(headless.defaults())["worstUtil"]))

    def test_descriptor_agrees_with_the_manifest_registration(self):
        descriptor = headless.descriptor()
        self.assertEqual(descriptor["id"], "concrete-deep-beam")
        self.assertEqual(descriptor["entry"], "ic_concrete_deep_beam.headless")
        self.assertEqual(descriptor["folder"], "06 - CONCRETE DEEP BEAM")
        self.assertEqual(descriptor["status"], "planned")


class Arithmetic(unittest.TestCase):
    """Values taken from Structural Toolkit DEEP BEAMS V5.02, sheet ``Design``."""

    def setUp(self):
        self.result = headless.compute(_inputs(**WORKBOOK))

    def test_geometry_and_lever_arm(self):
        geometry = self.result["geometry"]
        self.assertEqual(geometry["ldActual"], 0.75)
        self.assertEqual(geometry["ldLimit"], 1.0)
        self.assertEqual(geometry["z"], 2700.0)
        self.assertEqual(geometry["supportLimit"], 600.0)

    def test_design_stress_and_tie_areas(self):
        self.assertEqual(self.result["serviceability"]["fsi"], 365.0)
        self.assertEqual(self.result["serviceability"]["fsyd"], 365.0)
        reo = self.result["reinforcement"]
        self.assertAlmostEqual(reo["AstPositive"], 2029.42668696, places=8)
        self.assertAlmostEqual(reo["AstNegative"], 1014.71334348, places=8)
        self.assertAlmostEqual(reo["barsPositive"], 10.0935402773, places=9)
        self.assertAlmostEqual(reo["barsNegative"], 5.04677013863, places=9)

    def test_diagonal_compression_and_support_capacities(self):
        self.assertAlmostEqual(self.result["material"]["fcd"], 66.6666666667, places=9)
        shear = self.result["shear"]
        self.assertAlmostEqual(shear["phiVuDepth"] / 1e3, 8000.0, places=7)
        self.assertAlmostEqual(shear["phiVuSpan"] / 1e3, 6000.0, places=7)
        self.assertAlmostEqual(shear["phiVu"] / 1e3, 6000.0, places=7)
        self.assertAlmostEqual(self.result["support"]["phiRe"] / 1e3, 16000.0, places=7)
        self.assertAlmostEqual(self.result["support"]["phiRi"] / 1e3, 26400.0, places=7)

    def test_web_reinforcement_spacing(self):
        web = self.result["web"]
        self.assertAlmostEqual(web["Asw"], 78.5398163397, places=9)
        self.assertAlmostEqual(web["meshSpacing"], 104.71975512, places=8)
        self.assertAlmostEqual(web["barSpacing"], 130.8996939, places=7)

    def test_indicative_actions(self):
        loads = self.result["loads"]
        self.assertAlmostEqual(loads["indicativeM"] / 1e6, 345.0, places=9)
        self.assertAlmostEqual(loads["indicativeV"] / 1e3, 130.0, places=9)

    def test_workbook_summary_ratio_and_the_rule_it_ignores(self):
        # Settings!O21 caches 0.15; Design!D23 simultaneously reads "Error - c > L/5".
        self.assertAlmostEqual(self.result["util"]["diagonalCompression"], 0.15, places=10)
        self.assertAlmostEqual(self.result["util"]["supportWidthLimit"], 1.5, places=10)
        self.assertEqual(headless.summarise(self.result)["status"], "FAIL")
        self.assertEqual(headless.summarise(self.result)["criticalCheck"],
                         "Support width limit c <= L/5")


class Branches(unittest.TestCase):
    def test_lever_arm_for_each_span_type_and_slenderness(self):
        self.assertEqual(engine.lever_arm("S", 3000, 4000), 0.6 * 3000)
        self.assertEqual(engine.lever_arm("S", 8000, 4000), 0.15 * 4000 * (3 + 2))
        self.assertEqual(engine.lever_arm("D", 3000, 4000), 0.45 * 3000)
        self.assertEqual(engine.lever_arm("D", 8000, 4000), 0.1 * 4000 * (2.5 + 4))
        self.assertEqual(engine.lever_arm("M", 3000, 4000), 0.45 * 3000)
        self.assertEqual(engine.lever_arm("M", 8000, 4000), 0.15 * 4000 * (2 + 2))
        self.assertEqual(engine.lever_arm("C", 1000, 4000), 1.2 * 1000)
        self.assertEqual(engine.lever_arm("C", 3000, 4000), 0.15 * 4000 * (3 + 1.5))

    def test_span_type_selects_the_applicable_support_checks(self):
        cantilever = headless.compute(_inputs(spanType="C"))
        simple = headless.compute(_inputs(spanType="S"))
        multi = headless.compute(_inputs(spanType="M"))
        self.assertNotIn("externalSupport", cantilever["util"])
        self.assertIn("internalSupport", cantilever["util"])
        self.assertIn("externalSupport", simple["util"])
        self.assertNotIn("internalSupport", simple["util"])
        self.assertIn("externalSupport", multi["util"])
        self.assertIn("internalSupport", multi["util"])

    def test_excel_matches_the_span_type_case_insensitively(self):
        self.assertEqual(headless.compute(_inputs(spanType="c"))["geometry"]["spanType"], "C")

    def test_crack_control_classes(self):
        for code, fsi in (("M", 350.0), ("O", 250.0), ("S", 200.0), ("W", 365.0)):
            with self.subTest(crack=code):
                self.assertEqual(
                    headless.compute(_inputs(crack=code))["serviceability"]["fsi"], fsi)
        self.assertEqual(
            headless.compute(_inputs(crack="C", fsic=280))["serviceability"]["fsi"], 280.0)

    def test_a_non_positive_custom_stress_falls_back_to_the_workbook_floor(self):
        result = headless.compute(_inputs(crack="C", fsic=0))
        self.assertEqual(result["serviceability"]["fsi"], engine.CUSTOM_FSI_FLOOR)

    def test_yield_governs_the_design_stress_when_it_is_the_lesser(self):
        result = headless.compute(_inputs(crack="W", gs=1.15, fsy="400"))
        self.assertAlmostEqual(result["serviceability"]["fsyd"], 400 / 1.15, places=10)
        self.assertTrue(any("gamma_s governs" in note for note in result["warnings"]))

    def test_negative_distribution_fraction_follows_the_span_to_depth_ratio(self):
        shallow = headless.compute(_inputs(L=3000, D=4000))
        deep = headless.compute(_inputs(L=8000, D=4000))
        self.assertEqual(shallow["distribution"]["fraction"], 0.0)
        self.assertAlmostEqual(deep["distribution"]["fraction"], 0.5, places=12)

    def test_non_standard_mesh_wire_is_warned_not_rejected(self):
        result = headless.compute(_inputs(mesh=10))
        self.assertTrue(any("not a standard size" in note for note in result["warnings"]))
        self.assertTrue(math.isfinite(result["web"]["meshSpacing"]))


class InputRejection(unittest.TestCase):
    def test_missing_required_fields(self):
        for key in ("spanType", "L", "D", "bw", "support", "fc", "fsy", "bar", "mesh",
                    "gs", "gc", "Mstar", "Vstar", "Rstar", "reodiste"):
            with self.subTest(key=key):
                values = _inputs()
                del values[key]
                with self.assertRaises(ValueError):
                    headless.compute(values)

    def test_malformed_numbers(self):
        for value in (None, True, "", "deep", float("nan"), float("inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(D=value))

    def test_concrete_strength_limits(self):
        for strength in (19.9, 120.1):
            with self.subTest(fc=strength):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(fc=strength))

    def test_unsupported_enumerations(self):
        for key, value in (("spanType", "X"), ("crack", "Z"), ("fsy", "250"), ("bar", "10")):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(**{key: value}))

    def test_out_of_range_and_negative_values(self):
        with self.assertRaises(ValueError):
            headless.compute(_inputs(reodiste=1.5))
        with self.assertRaises(ValueError):
            headless.compute(_inputs(Vstar=-1))
        with self.assertRaises(ValueError):
            headless.compute(_inputs(gs=0))
        with self.assertRaises(ValueError):
            headless.compute(_inputs(Df=-10))

    def test_non_dictionary_input(self):
        with self.assertRaises(ValueError):
            headless.compute([("fc", 32)])


class StatusAndLimits(unittest.TestCase):
    def test_status_flips_across_a_utilisation_of_one(self):
        satisfactory = headless.compute(_inputs(D=4500, Vstar=2500))
        overloaded = headless.compute(_inputs(D=4500, Vstar=3000))
        self.assertLess(satisfactory["worstUtil"], 1.0)
        self.assertGreater(overloaded["worstUtil"], 1.0)
        self.assertEqual(headless.summarise(satisfactory)["status"], "OK")
        self.assertEqual(headless.summarise(overloaded)["status"], "FAIL")
        self.assertEqual(headless.summarise(overloaded)["criticalCheck"],
                         "Diagonal compressive stress")

    def test_span_depth_limit_is_a_mandatory_rule(self):
        result = headless.compute(_inputs(spanType="S", L=12000, D=4000))
        self.assertGreater(result["util"]["spanDepthLimit"], 1.0)
        self.assertEqual(headless.summarise(result)["status"], "FAIL")

    def test_zero_actions_give_zero_demand_ratios(self):
        result = headless.compute(_inputs(Mstar=0, Mstarn=0, Vstar=0, Rstar=0))
        self.assertEqual(result["util"]["diagonalCompression"], 0.0)
        self.assertEqual(result["reinforcement"]["AstPositive"], 0.0)
        self.assertFalse(any(math.isnan(value) for value in result["util"].values()))

    def test_the_superseded_warning_is_always_present(self):
        self.assertTrue(any("superseded" in note.lower()
                            for note in headless.compute(_inputs())["warnings"]))

    def test_summary_headline_names_the_superseded_method(self):
        self.assertIn("Superseded CEB method",
                      headless.summarise(headless.compute(_inputs()))["headline"])


class StateIsolation(unittest.TestCase):
    def test_compute_does_not_mutate_or_drift(self):
        values = _inputs(**WORKBOOK)
        before = deepcopy(values)
        first = headless.compute(values)
        second = headless.compute(values)
        self.assertEqual(values, before)
        self.assertEqual(first["util"], second["util"])

    def test_unrelated_manager_keys_are_preserved_not_rejected(self):
        values = _inputs(description="Transfer beam TB1", linkedFrom=[])
        self.assertTrue(math.isfinite(headless.compute(values)["worstUtil"]))


class Reporting(unittest.TestCase):
    def test_navigation_anchors_and_appendix(self):
        values = _inputs(**WORKBOOK)
        result = headless.compute(values)
        for standalone in (False, True):
            with self.subTest(standalone=standalone):
                document = headless.render(values, result, standalone=standalone,
                                           appendix=["<p>Appendix fixture</p>"],
                                           anchor_prefix="deep-test",
                                           contents_href="#contents-test")
                self.assertIn('class="calc-page"', document)
                self.assertIn("deep-test", document)
                self.assertIn("#contents-test", document)
                self.assertIn("Appendix fixture", document)

    def test_superseded_warning_and_references_are_printed(self):
        values = _inputs(**WORKBOOK)
        document = headless.render(values, headless.compute(values), standalone=True)
        for fragment in ("SUPERSEDED METHOD", "WRHF Eq 24.24", "WRHF Eq 24.26",
                         "WRHF Eq 24.27", "WRHF Eq 24.25", "Cl 12.7",
                         "not approved for design"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, document)

    def test_inapplicable_support_checks_are_stated_not_hidden(self):
        values = _inputs(spanType="C")
        document = headless.render(values, headless.compute(values), standalone=True)
        self.assertIn("not applicable to a cantilever", document)

    def test_untrusted_identity_text_is_escaped(self):
        values = _inputs(memberType="<script>alert(1)</script>")
        document = headless.render(values, headless.compute(values), standalone=True)
        self.assertNotIn("<script>alert(1)</script>", document)


class ContractSurface(unittest.TestCase):
    def test_identity(self):
        record = headless.identity(_inputs(memberType="Deep beam", memberNumber="0005"))
        self.assertEqual(record["calcType"], "Concrete deep beam")
        self.assertIn("8000 x 4000", record["title"])

    def test_summary_shape(self):
        summary = headless.summarise(headless.compute(_inputs()))
        self.assertEqual(set(summary), {"worstUtil", "criticalCheck", "status", "headline"})

    def test_validate_compares_real_values_and_counts_them(self):
        report = headless.validate()
        self.assertTrue(report["ok"], report["failures"])
        self.assertGreater(report["compared"], 25)
        self.assertIn("approval", report)

    def test_validate_reports_a_supplied_case_that_disagrees(self):
        report = headless.validate([{"name": "Deliberately wrong", "inputs": headless.defaults(),
                                     "expect": {"geometry.z": 1.0}}])
        self.assertFalse(report["ok"])

    def test_validate_rejects_a_case_with_no_expected_values(self):
        self.assertFalse(headless.validate([{"name": "Empty",
                                             "inputs": headless.defaults()}])["ok"])


if __name__ == "__main__":
    unittest.main()
