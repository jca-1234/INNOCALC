"""Engineering and interface tests for the Plain Concrete Design module."""

from __future__ import annotations

import math
import unittest
from copy import deepcopy

from ic_concrete_plain import headless

WORKBOOK = {
    "fc": 120, "Dt": 250, "B": 1000, "L": 90, "W": 90,
    "uMode": "calculated", "um": 0, "Mstar": 2, "Vstar": 7, "Dir": "W",
    "Lpx": 800, "Wpy": 500, "Pstar": -250, "Mxstar": -50, "Mystar": -50,
    "eccx": 0, "eccy": 0, "ignoreEcc": "Y",
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
        values = headless.defaults()
        for field_id in seen:
            self.assertIn(field_id, values)

    def test_defaults_are_fresh_and_valid(self):
        first, second = headless.defaults(), headless.defaults()
        first["checks"]["bending"] = False
        self.assertTrue(second["checks"]["bending"])
        self.assertTrue(math.isfinite(headless.compute(headless.defaults())["worstUtil"]))

    def test_descriptor_agrees_with_the_manifest_registration(self):
        descriptor = headless.descriptor()
        self.assertEqual(descriptor["id"], "concrete-plain")
        self.assertEqual(descriptor["entry"], "ic_concrete_plain.headless")
        self.assertEqual(descriptor["folder"], "04 - CONCRETE PLAIN")
        self.assertEqual(descriptor["status"], "planned")


class Arithmetic(unittest.TestCase):
    """Values taken from Structural Toolkit PLAIN CONCRETE V5.02, sheet ``Design``."""

    def setUp(self):
        self.result = headless.compute(_inputs(**WORKBOOK))

    def test_footing_capacities(self):
        self.assertEqual(self.result["geometry"]["D"], 200.0)
        self.assertAlmostEqual(self.result["material"]["fcf"], 6.57267069006, places=10)
        self.assertAlmostEqual(self.result["footing"]["phiMuo"] / 1e6, 26.2906827602, places=8)
        self.assertAlmostEqual(self.result["footing"]["phiVu1"] / 1e3, 88.7836346759, places=8)

    def test_punching_capacities(self):
        punching = self.result["punching"]
        self.assertEqual((punching["aL"], punching["aW"], punching["uc"]), (290.0, 290.0, 1160.0))
        self.assertEqual(punching["bh"], 1.0)
        self.assertAlmostEqual(punching["phiVumax"] / 1e3, 304.971920019, places=8)
        self.assertAlmostEqual(punching["phiVuu"] / 1e3, 457.457880028, places=8)
        self.assertAlmostEqual(punching["phiVum"] / 1e3, 177.900286678, places=8)

    def test_pedestal_stresses(self):
        pedestal = self.result["pedestal"]
        self.assertEqual(pedestal["Ag"], 400000.0)
        self.assertEqual(pedestal["maxHeight"], 1500.0)
        self.assertEqual(pedestal["sigmaA"], -0.625)
        self.assertEqual(pedestal["sigmaBx"], 0.9375)
        self.assertEqual(pedestal["sigmaBy"], 1.5)
        self.assertEqual(pedestal["sigmaTc"], 1.8125)
        self.assertEqual(pedestal["sigmaTt"], -3.0625)
        self.assertAlmostEqual(pedestal["sigmaCmax"], 28.8, places=10)
        self.assertAlmostEqual(pedestal["sigmaTmax"], 2.95770181053, places=10)

    def test_saved_example_reproduces_the_workbook_printed_ratios(self):
        # Design!G87 reads "OK (0.06)" and Design!G88 reads "No Good (1.04)".
        self.assertAlmostEqual(self.result["util"]["pedestalCompression"], 0.06, places=2)
        self.assertAlmostEqual(self.result["util"]["pedestalTension"], 1.04, places=2)
        self.assertEqual(headless.summarise(self.result)["status"], "FAIL")
        self.assertEqual(headless.summarise(self.result)["criticalCheck"],
                         "Pedestal tensile stress")


class Branches(unittest.TestCase):
    def test_direction_selects_the_matching_perimeter_dimension(self):
        along_l = headless.compute(_inputs(L=200, W=500, Dir="L"))
        along_w = headless.compute(_inputs(L=200, W=500, Dir="W"))
        self.assertEqual(along_l["punching"]["a"], along_l["punching"]["aL"])
        self.assertEqual(along_w["punching"]["a"], along_w["punching"]["aW"])

    def test_excel_compares_direction_case_insensitively(self):
        self.assertEqual(headless.compute(_inputs(Dir="w"))["punching"]["direction"], "W")
        self.assertEqual(headless.compute(_inputs(ignoreEcc="y"))["pedestal"]["ignoreEcc"], "Y")

    def test_manual_shear_perimeter_overrides_the_calculated_one(self):
        auto = headless.compute(_inputs())
        manual = headless.compute(_inputs(uMode="manual", um=900))
        self.assertEqual(manual["punching"]["u"], 900.0)
        self.assertNotEqual(manual["punching"]["u"], auto["punching"]["uc"])
        self.assertTrue(any("manually" in note for note in manual["warnings"]))

    def test_minimum_eccentricity_and_its_override(self):
        applied = headless.compute(_inputs(ignoreEcc="N", Lpx=800, Wpy=500))
        ignored = headless.compute(_inputs(ignoreEcc="Y", Lpx=800, Wpy=500))
        self.assertEqual((applied["pedestal"]["ax"], applied["pedestal"]["ay"]), (80.0, 50.0))
        self.assertEqual((ignored["pedestal"]["ax"], ignored["pedestal"]["ay"]), (0.0, 0.0))
        self.assertTrue(any("overridden" in note for note in ignored["warnings"]))

    def test_supplied_eccentricity_governs_when_larger(self):
        result = headless.compute(_inputs(Lpx=800, Wpy=500, eccx=200, eccy=10, ignoreEcc="N"))
        self.assertEqual(result["pedestal"]["dax"], 200.0)
        self.assertEqual(result["pedestal"]["day"], 50.0)

    def test_zero_moment_removes_the_punching_reduction(self):
        result = headless.compute(_inputs(Mstar=0, Vstar=100))
        self.assertEqual(result["punching"]["phiVum"], result["punching"]["phiVu"])

    def test_moment_reduction_never_increases_capacity(self):
        result = headless.compute(_inputs(Mstar=40, Vstar=100))
        self.assertLess(result["punching"]["phiVum"], result["punching"]["phiVu"])


class InputRejection(unittest.TestCase):
    def test_missing_required_fields(self):
        for key in ("fc", "Dt", "B", "L", "W", "Mstar", "Vstar", "Lpx", "Wpy", "Pstar"):
            with self.subTest(key=key):
                values = _inputs()
                del values[key]
                with self.assertRaises(ValueError):
                    headless.compute(values)

    def test_malformed_numbers(self):
        for value in (None, True, False, "", "deep", float("nan"), float("inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(Dt=value))

    def test_concrete_strength_limits(self):
        for strength in (19.9, 120.1):
            with self.subTest(fc=strength):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(fc=strength))

    def test_impossible_geometry(self):
        with self.assertRaises(ValueError):
            headless.compute(_inputs(Dt=50))
        with self.assertRaises(ValueError):
            headless.compute(_inputs(L=0))
        with self.assertRaises(ValueError):
            headless.compute(_inputs(Lpx=-400))

    def test_unsupported_enumerations(self):
        for key, value in (("Dir", "X"), ("uMode", "auto"), ("ignoreEcc", "maybe")):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(**{key: value}))

    def test_manual_perimeter_must_be_positive(self):
        with self.assertRaises(ValueError):
            headless.compute(_inputs(uMode="manual", um=0))

    def test_moment_reduction_without_shear_is_rejected(self):
        with self.assertRaises(ValueError):
            headless.compute(_inputs(Mstar=10, Vstar=0))

    def test_negative_demands_are_rejected(self):
        with self.assertRaises(ValueError):
            headless.compute(_inputs(Vstar=-1))
        with self.assertRaises(ValueError):
            headless.compute(_inputs(Mstar=-1))


class StatusAndLimits(unittest.TestCase):
    def test_status_flips_across_a_utilisation_of_one(self):
        satisfactory = headless.compute(_inputs(fc=32, Dt=400, Lpx=600, Wpy=600, Pstar=1200))
        overloaded = headless.compute(_inputs(fc=32, Dt=400, Lpx=600, Wpy=600, Pstar=1400))
        self.assertLess(satisfactory["worstUtil"], 1.0)
        self.assertGreater(overloaded["worstUtil"], 1.0)
        self.assertEqual(headless.summarise(satisfactory)["status"], "OK")
        self.assertEqual(headless.summarise(overloaded)["status"], "FAIL")
        self.assertEqual(headless.summarise(overloaded)["criticalCheck"],
                         "Pedestal compressive stress")

    def test_minimum_nominal_depth_is_a_mandatory_rule(self):
        shallow = headless.compute(_inputs(Dt=150))
        self.assertGreater(shallow["util"]["minimumDepth"], 1.0)
        self.assertEqual(headless.summarise(shallow)["status"], "FAIL")

    def test_zero_actions_give_zero_demand_ratios(self):
        result = headless.compute(_inputs(Mstar=0, Vstar=0, Pstar=0, Mxstar=0, Mystar=0))
        self.assertEqual(result["util"]["bending"], 0.0)
        self.assertEqual(result["util"]["oneWayShear"], 0.0)
        self.assertEqual(result["util"]["punchingShear"], 0.0)
        self.assertFalse(any(math.isnan(value) for value in result["util"].values()))

    def test_pure_tension_is_carried_by_the_tensile_check(self):
        result = headless.compute(_inputs(Pstar=-400, Mxstar=0, Mystar=0, ignoreEcc="Y"))
        self.assertLess(result["pedestal"]["sigmaTt"], 0.0)
        self.assertEqual(result["pedestal"]["sigmaTc"], 0.0)
        self.assertGreater(result["util"]["pedestalTension"], 0.0)

    def test_every_check_is_mandatory(self):
        values = _inputs()
        values["checks"] = {key: False for key in values["checks"]}
        self.assertTrue(all(headless.compute(values)["checks"].values()))


class StateIsolation(unittest.TestCase):
    def test_compute_does_not_mutate_or_drift(self):
        values = _inputs(**WORKBOOK)
        before = deepcopy(values)
        first = headless.compute(values)
        second = headless.compute(values)
        self.assertEqual(values, before)
        self.assertEqual(first["util"], second["util"])

    def test_unrelated_manager_keys_are_preserved_not_rejected(self):
        values = _inputs(description="Pad footing F1", linkedFrom=[])
        self.assertTrue(math.isfinite(headless.compute(values)["worstUtil"]))


class Reporting(unittest.TestCase):
    def test_navigation_anchors_and_appendix(self):
        values = _inputs(**WORKBOOK)
        result = headless.compute(values)
        for standalone in (False, True):
            with self.subTest(standalone=standalone):
                document = headless.render(values, result, standalone=standalone,
                                           appendix=["<p>Appendix fixture</p>"],
                                           anchor_prefix="plain-test",
                                           contents_href="#contents-test")
                self.assertIn('class="calc-page"', document)
                self.assertIn("plain-test", document)
                self.assertIn("#contents-test", document)
                self.assertIn("Appendix fixture", document)

    def test_engineering_content_and_clauses_are_printed(self):
        values = _inputs(**WORKBOOK)
        document = headless.render(values, headless.compute(values), standalone=True)
        for fragment in ("Cl 20.4.2", "Eq 20.4.3(1)", "Cl 20.4.3(b)", "Eq 20.4.3(2)",
                         "Cl 20.3", "Cl 20.1(a)", "Table 2.2.2(g)", "not approved for design"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, document)

    def test_eccentricity_override_is_stated_on_the_sheet(self):
        values = _inputs(ignoreEcc="Y")
        document = headless.render(values, headless.compute(values), standalone=True)
        self.assertIn("Warnings", document)
        self.assertIn("overridden", document)

    def test_untrusted_identity_text_is_escaped(self):
        values = _inputs(memberType="<script>alert(1)</script>")
        document = headless.render(values, headless.compute(values), standalone=True)
        self.assertNotIn("<script>alert(1)</script>", document)


class ContractSurface(unittest.TestCase):
    def test_identity(self):
        values = _inputs(memberType="Pedestal", memberNumber="0012", package="P02", level="GF")
        record = headless.identity(values)
        self.assertEqual(record["memberType"], "Pedestal")
        self.assertEqual(record["memberNumber"], "0012")
        self.assertEqual(record["calcType"], "Plain concrete")
        self.assertIn("400 x 400", record["title"])

    def test_summary_shape(self):
        summary = headless.summarise(headless.compute(_inputs()))
        self.assertEqual(set(summary), {"worstUtil", "criticalCheck", "status", "headline"})

    def test_validate_compares_real_values_and_counts_them(self):
        report = headless.validate()
        self.assertTrue(report["ok"], report["failures"])
        self.assertGreater(report["compared"], 30)
        self.assertIn("approval", report)

    def test_validate_reports_a_supplied_case_that_disagrees(self):
        report = headless.validate([{"name": "Deliberately wrong", "inputs": headless.defaults(),
                                     "expect": {"geometry.D": 1.0}}])
        self.assertFalse(report["ok"])

    def test_validate_rejects_a_case_with_no_expected_values(self):
        self.assertFalse(headless.validate([{"name": "Empty",
                                             "inputs": headless.defaults()}])["ok"])


if __name__ == "__main__":
    unittest.main()
