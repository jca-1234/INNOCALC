"""Engineering and interface tests for the Concrete Stair Design module."""

from __future__ import annotations

import math
import unittest
from copy import deepcopy

from ic_concrete_stair import engine, headless

WORKBOOK = {
    "fc": 100, "L": 5000, "W": 2556, "th": 150, "cover": 20, "spanType": "I",
    "riser": 190, "going": 250, "conc": 25, "density": 2400,
    "wsdl": 0, "wll": 4, "loadtype": "Floor",
    "bar": "10", "fsy": "500", "ductilityClass": "N",
    "reoMode": "centres", "reoValue": 100,
    "Asc": 100, "dc": 40, "usefcmi": "N",
    "useVertM": "N", "useVertD": "Y", "deflectionBasis": "L", "k3": 1,
    "spanOverDeflection": 250, "spanOverDeflectionIncremental": 500,
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
        first["checks"]["bending"] = False
        self.assertTrue(second["checks"]["bending"])
        self.assertTrue(math.isfinite(headless.compute(headless.defaults())["worstUtil"]))

    def test_descriptor_agrees_with_the_manifest_registration(self):
        descriptor = headless.descriptor()
        self.assertEqual(descriptor["id"], "concrete-stair")
        self.assertEqual(descriptor["entry"], "ic_concrete_stair.headless")
        self.assertEqual(descriptor["folder"], "07 - CONCRETE STAIR")
        self.assertEqual(descriptor["status"], "planned")


class Arithmetic(unittest.TestCase):
    """Values taken from Structural Toolkit CONCRETE STAIRS V5.06, sheet ``Design``."""

    def setUp(self):
        self.result = headless.compute(_inputs(**WORKBOOK))

    def test_stepped_geometry(self):
        geometry = self.result["geometry"]
        self.assertAlmostEqual(geometry["ang"], 314.006369362, places=9)
        self.assertAlmostEqual(geometry["f"], 1.25602547745, places=11)
        self.assertAlmostEqual(geometry["incline"], 37.2348339816, places=10)
        self.assertAlmostEqual(geometry["ath"], 225.635408442, places=9)
        self.assertEqual(geometry["ds"], 125.0)
        self.assertEqual(geometry["eds"], 125.0)
        self.assertEqual(geometry["D"], 150.0)

    def test_loading(self):
        loads = self.result["loads"]
        self.assertAlmostEqual(loads["wdl"], 7.08509554043, places=10)
        self.assertAlmostEqual(loads["wstar"], 14.5021146485, places=10)
        self.assertAlmostEqual(loads["Mstar"] / 1e6, 45.3191082766, places=9)

    def test_bending_capacity(self):
        bending, reo = self.result["bending"], self.result["reinforcement"]
        self.assertEqual(reo["nbars"], 10.0)
        self.assertEqual(reo["cts"], 100.0)
        self.assertAlmostEqual(reo["Ast"], 785.398163397, places=9)
        self.assertAlmostEqual(reo["Astmin"], 432.0, places=10)
        self.assertAlmostEqual(bending["alpha2"], 0.7, places=12)
        self.assertAlmostEqual(bending["gamma"], 0.72, places=12)
        self.assertAlmostEqual(bending["kuo"], 0.0623331875712, places=12)
        self.assertAlmostEqual(bending["phi"], 0.85, places=12)
        self.assertAlmostEqual(bending["phiMuo"] / 1e6, 40.7879868344, places=9)

    def test_serviceability_chain(self):
        material, deflection = self.result["material"], self.result["deflection"]
        self.assertAlmostEqual(material["fcmi"], 100.0, places=12)
        self.assertAlmostEqual(material["Ec"], 42327.1827553, places=6)
        self.assertAlmostEqual(material["n"], 4.72509595444, places=10)
        self.assertAlmostEqual(deflection["p"], 0.00628318530718, places=12)
        self.assertAlmostEqual(deflection["pc"], 0.0008, places=12)
        self.assertAlmostEqual(deflection["dcOverDs"], 0.32, places=12)
        self.assertAlmostEqual(deflection["ku"], 0.217034697883, places=11)
        self.assertAlmostEqual(deflection["NA"], 27.1293372354, places=9)
        self.assertAlmostEqual(deflection["kcs"], 2.0, places=12)
        self.assertAlmostEqual(deflection["fdef"], 27.2552866213, places=9)
        self.assertAlmostEqual(deflection["fdefIncremental"], 20.1701910809, places=9)

    def test_minimum_thickness(self):
        deflection = self.result["deflection"]
        self.assertAlmostEqual(deflection["inclineModifier"], 1.12072542465, places=11)
        self.assertAlmostEqual(deflection["dmin"], 145.157807633, places=8)
        self.assertAlmostEqual(deflection["thmin"], 170.157807633, places=8)
        self.assertAlmostEqual(deflection["dminIncremental"], 165.425892025, places=8)
        self.assertAlmostEqual(deflection["thminIncremental"], 190.425892025, places=8)

    def test_the_saved_example_fails_in_bending(self):
        # Settings!O29 caches 1.11108960735 and Design!I9 reads "No Good (1.11)".
        self.assertAlmostEqual(self.result["util"]["bending"], 1.11108960735, places=10)
        summary = headless.summarise(self.result)
        self.assertEqual(summary["status"], "FAIL")
        self.assertEqual(summary["criticalCheck"], "Bending")

    def test_the_saved_example_exercises_the_compression_steel_warning(self):
        self.assertTrue(self.result["deflection"]["compressionInTension"])
        self.assertEqual(self.result["deflection"]["effectiveAsc"], 0.0)
        self.assertTrue(any("cracked tension zone" in note
                            for note in self.result["warnings"]))


class Branches(unittest.TestCase):
    def test_span_type_selects_k4(self):
        for code, k4 in (("S", 1.4), ("I", 2.1), ("E", 1.75)):
            with self.subTest(spanType=code):
                self.assertEqual(
                    headless.compute(_inputs(spanType=code))["deflection"]["k4"], k4)

    def test_reinforcement_entry_modes_agree(self):
        centres = headless.compute(_inputs(reoMode="centres", reoValue=100, bar="10"))
        area = headless.compute(_inputs(reoMode="area", reoValue=785.398163397, bar="10"))
        count = headless.compute(_inputs(reoMode="count", reoValue=10, W=1000, bar="10"))
        self.assertAlmostEqual(centres["reinforcement"]["Ast"], 785.398163397, places=9)
        self.assertAlmostEqual(area["reinforcement"]["Ast"], 785.398163397, places=9)
        self.assertAlmostEqual(count["reinforcement"]["Ast"], 785.398163397, places=9)

    def test_count_mode_is_spread_over_the_flight_width(self):
        narrow = headless.compute(_inputs(reoMode="count", reoValue=10, W=1000))
        wide = headless.compute(_inputs(reoMode="count", reoValue=10, W=2000))
        self.assertAlmostEqual(narrow["reinforcement"]["nbars"], 10.0, places=12)
        self.assertAlmostEqual(wide["reinforcement"]["nbars"], 5.0, places=12)

    def test_vertical_depth_option_increases_the_capacity(self):
        perpendicular = headless.compute(_inputs(useVertM="N"))
        vertical = headless.compute(_inputs(useVertM="Y"))
        self.assertGreater(vertical["geometry"]["eds"], perpendicular["geometry"]["eds"])
        self.assertGreater(vertical["bending"]["phiMuo"], perpendicular["bending"]["phiMuo"])

    def test_deflection_basis_changes_the_incline_modifier(self):
        local = headless.compute(_inputs(deflectionBasis="L"))["deflection"]["inclineModifier"]
        globally = headless.compute(_inputs(deflectionBasis="G"))["deflection"]["inclineModifier"]
        self.assertGreater(local, globally)
        self.assertGreater(globally, 1.0)

    def test_live_load_type_selects_the_service_factors(self):
        floor = headless.compute(_inputs(loadtype="Floor"))["loads"]
        other = headless.compute(_inputs(loadtype="Other"))["loads"]
        self.assertEqual((floor["psiS"], floor["psiL"]), (0.7, 0.4))
        self.assertEqual((other["psiS"], other["psiL"]), (1.0, 0.6))

    def test_excel_matches_text_case_insensitively(self):
        self.assertEqual(headless.compute(_inputs(loadtype="floor"))["loads"]["psiS"], 0.7)
        self.assertEqual(headless.compute(_inputs(spanType="i"))["geometry"]["spanType"], "I")

    def test_class_l_reinforcement_fixes_phi(self):
        result = headless.compute(_inputs(ductilityClass="L"))
        self.assertEqual(result["bending"]["phi"], engine.PHI_CLASS_L)

    def test_fcmi_option_changes_the_modulus(self):
        plain = headless.compute(_inputs(fc=32, usefcmi="N"))["material"]
        curved = headless.compute(_inputs(fc=32, usefcmi="Y"))["material"]
        self.assertEqual(plain["fcmi"], 32.0)
        self.assertNotEqual(curved["fcmi"], 32.0)
        self.assertNotEqual(plain["Ec"], curved["Ec"])

    def test_compression_steel_outside_the_tension_zone_reduces_kcs(self):
        result = headless.compute(_inputs(Asc=600, dc=15, th=250, cover=20, bar="12"))
        self.assertFalse(result["deflection"]["compressionInTension"])
        self.assertLess(result["deflection"]["kcs"], 2.0)
        self.assertGreaterEqual(result["deflection"]["kcs"], engine.KCS_FLOOR)


class InputRejection(unittest.TestCase):
    def test_missing_required_fields(self):
        for key in ("fc", "L", "W", "th", "riser", "going", "conc", "density",
                    "wll", "bar", "fsy", "reoValue", "k3", "spanOverDeflection"):
            with self.subTest(key=key):
                values = _inputs()
                del values[key]
                with self.assertRaises(ValueError):
                    headless.compute(values)

    def test_malformed_numbers(self):
        for value in (None, True, "", "steep", float("nan"), float("inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(th=value))

    def test_concrete_strength_limits(self):
        for strength in (19.9, 120.1):
            with self.subTest(fc=strength):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(fc=strength))

    def test_unsupported_enumerations(self):
        for key, value in (("spanType", "X"), ("loadtype", "Roof"), ("bar", "14"),
                           ("fsy", "300"), ("ductilityClass", "E"), ("reoMode", "spacing"),
                           ("deflectionBasis", "X"), ("useVertM", "maybe")):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(**{key: value}))

    def test_impossible_geometry(self):
        with self.assertRaises(ValueError):
            headless.compute(_inputs(th=20, cover=20, bar="16"))
        with self.assertRaises(ValueError):
            headless.compute(_inputs(going=0))
        with self.assertRaises(ValueError):
            headless.compute(_inputs(reoValue=0))

    def test_negative_loads_are_rejected(self):
        with self.assertRaises(ValueError):
            headless.compute(_inputs(wll=-1))
        with self.assertRaises(ValueError):
            headless.compute(_inputs(Asc=-1))

    def test_non_dictionary_input(self):
        with self.assertRaises(ValueError):
            headless.compute([("fc", 32)])


class StatusAndLimits(unittest.TestCase):
    def test_status_flips_across_a_utilisation_of_one(self):
        satisfactory = headless.compute(_inputs(th=200, reoValue=150, wll=3))
        overloaded = headless.compute(_inputs(th=200, reoValue=150, wll=25))
        self.assertLess(satisfactory["worstUtil"], 1.0)
        self.assertGreater(overloaded["worstUtil"], 1.0)
        self.assertEqual(headless.summarise(satisfactory)["status"], "OK")
        self.assertEqual(headless.summarise(overloaded)["status"], "FAIL")

    def test_minimum_steel_is_a_mandatory_rule(self):
        result = headless.compute(_inputs(th=250, bar="12", reoMode="centres", reoValue=500,
                                          wll=0, wsdl=0))
        self.assertGreater(result["util"]["minimumSteel"], 1.0)
        self.assertEqual(headless.summarise(result)["status"], "FAIL")

    def test_ductility_limit_is_a_mandatory_rule(self):
        result = headless.compute(_inputs(fc=20, th=200, bar="24", reoMode="centres",
                                          reoValue=80))
        self.assertGreater(result["bending"]["kuo"], engine.KUO_DUCTILITY_LIMIT)
        self.assertGreater(result["util"]["ductility"], 1.0)
        self.assertEqual(headless.summarise(result)["status"], "FAIL")
        self.assertTrue(any("non-ductile" in note for note in result["warnings"]))

    def test_zero_live_load_still_carries_self_weight(self):
        result = headless.compute(_inputs(wll=0, wsdl=0))
        self.assertGreater(result["loads"]["wstar"], 0.0)
        self.assertGreater(result["util"]["bending"], 0.0)
        self.assertFalse(any(math.isnan(value) for value in result["util"].values()))

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
        values = _inputs(description="Stair flight S1", linkedFrom=[])
        self.assertTrue(math.isfinite(headless.compute(values)["worstUtil"]))


class Reporting(unittest.TestCase):
    def test_navigation_anchors_and_appendix(self):
        values = _inputs(**WORKBOOK)
        result = headless.compute(values)
        for standalone in (False, True):
            with self.subTest(standalone=standalone):
                document = headless.render(values, result, standalone=standalone,
                                           appendix=["<p>Appendix fixture</p>"],
                                           anchor_prefix="stair-test",
                                           contents_href="#contents-test")
                self.assertIn('class="calc-page"', document)
                self.assertIn("stair-test", document)
                self.assertIn("#contents-test", document)
                self.assertIn("Appendix fixture", document)

    def test_clauses_and_the_per_metre_statement_are_printed(self):
        values = _inputs(**WORKBOOK)
        document = headless.render(values, headless.compute(values), standalone=True)
        for fragment in ("Cl 9.1", "Eq 8.1.6.1(2)", "Cl 8.1.5", "Cl 9.4.4", "Cl 8.5.3.2",
                         "Eq 8.1.3(1)", "Table 2.3.2", "Table 2.2.2(b)", "Cl 3.1.2",
                         "per metre width", "not approved for design"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, document)

    def test_compression_steel_warning_is_stated_on_the_sheet(self):
        values = _inputs(**WORKBOOK)
        document = headless.render(values, headless.compute(values), standalone=True)
        self.assertIn("Warnings", document)
        self.assertIn("cracked tension zone", document)

    def test_untrusted_identity_text_is_escaped(self):
        values = _inputs(memberType="<script>alert(1)</script>")
        document = headless.render(values, headless.compute(values), standalone=True)
        self.assertNotIn("<script>alert(1)</script>", document)


class ContractSurface(unittest.TestCase):
    def test_identity(self):
        record = headless.identity(_inputs(memberType="Stair", memberNumber="0002"))
        self.assertEqual(record["calcType"], "Concrete stair")
        self.assertIn("3800 span", record["title"])

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
                                     "expect": {"geometry.ath": 1.0}}])
        self.assertFalse(report["ok"])

    def test_validate_rejects_a_case_with_no_expected_values(self):
        self.assertFalse(headless.validate([{"name": "Empty",
                                             "inputs": headless.defaults()}])["ok"])


if __name__ == "__main__":
    unittest.main()
