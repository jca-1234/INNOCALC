"""Engineering and interface tests for the Reinforcement Development and Laps module."""

from __future__ import annotations

import math
import unittest
from copy import deepcopy

from ic_concrete_development import engine, headless

WORKBOOK = {
    "fc": 40, "db": 12, "fsy": "500", "plain": "N",
    "lightweight": "N", "epoxy": "N", "bundle": "1",
    "cover": 50, "clear": 200, "below": 50, "rounding": "-1",
    "stress": 500, "stressc": 500,
    "element": "N", "sbb": 20, "twiceProvided": "N",
    "limitCompressionFc": "Y",
    "fitment": 10, "fitmentSpacing": 300, "threeFitments": "Y",
    "helical": "Y", "helixBars": 1,
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

    def test_optional_group_starts_disabled_and_is_fresh(self):
        values = headless.defaults()
        self.assertEqual(values["checks"], {"hooksAndCogs": False})
        values["checks"]["hooksAndCogs"] = True
        self.assertFalse(headless.defaults()["checks"]["hooksAndCogs"])

    def test_descriptor_agrees_with_the_manifest_registration(self):
        descriptor = headless.descriptor()
        self.assertEqual(descriptor["id"], "concrete-development")
        self.assertEqual(descriptor["entry"], "ic_concrete_development.headless")
        self.assertEqual(descriptor["folder"], "09 - REINFORCEMENT DEVELOPMENT")
        self.assertEqual(descriptor["status"], "planned")


class Arithmetic(unittest.TestCase):
    """Values taken from Structural Toolkit REINFORCEMENT DEVELOPMENT V5.06."""

    def setUp(self):
        self.result = headless.compute(_inputs(**WORKBOOK))

    def test_factors(self):
        factors = self.result["factors"]
        self.assertEqual(factors["k1"], 1.0)
        self.assertAlmostEqual(factors["k2"], 1.2, places=12)
        self.assertAlmostEqual(factors["k3"], 0.7, places=12)
        self.assertEqual(factors["cd"], 50.0)
        self.assertEqual(factors["mb"], 1.0)
        self.assertEqual(factors["k7"], 1.25)
        self.assertEqual(factors["sb"], 0.0)
        self.assertEqual((factors["rn"], factors["rh"]), (1.0, 0.8))

    def test_tension_development(self):
        tension = self.result["tension"]
        self.assertAlmostEqual(tension["Lsytb1"], 276.699295265, places=8)
        self.assertAlmostEqual(tension["Lsytb2"], 348.0, places=10)
        self.assertAlmostEqual(tension["Lsyt"], 348.0, places=10)
        self.assertAlmostEqual(tension["hookAllowance"], 174.0, places=10)
        self.assertAlmostEqual(tension["Lsytp"], 522.0, places=10)

    def test_tension_lap(self):
        lap = self.result["tensionLap"]
        self.assertAlmostEqual(lap["Lsytlap1"], 345.874119081, places=8)
        self.assertAlmostEqual(lap["Lsytlap2"], 348.0, places=10)
        self.assertAlmostEqual(lap["Lsytlap3"], 348.0, places=10)
        self.assertAlmostEqual(lap["Lsytlap"], 348.0, places=10)

    def test_compression(self):
        compression = self.result["compression"]
        self.assertAlmostEqual(compression["Lsycb1"], 208.7103, places=4)
        self.assertAlmostEqual(compression["Lsycb2"], 261.0, places=10)
        self.assertAlmostEqual(compression["Lsyc"], 261.0, places=10)
        self.assertAlmostEqual(compression["Lsycp"], 522.0, places=10)

    def test_compression_lap(self):
        lap = self.result["compressionLap"]
        self.assertAlmostEqual(lap["Atr"], 78.5398163397, places=9)
        self.assertAlmostEqual(lap["Ab"], 113.097335529, places=8)
        self.assertAlmostEqual(lap["AtrOverS"], 0.261799387799, places=11)
        self.assertTrue(lap["helicalOk"])
        self.assertAlmostEqual(lap["Lsyclap"], 384.0, places=10)

    def test_the_published_table_values(self):
        # Development!C29, E29, H29, C60, C73, C93, E93, C114 and C126.
        table = {row["db"]: row for row in self.result["table"]}
        self.assertEqual(table[12.0]["Lsytb"], 350.0)
        self.assertEqual(table[20.0]["Lsytb"], 580.0)
        self.assertEqual(table[32.0]["Lsytb"], 1160.0)
        self.assertEqual(table[12.0]["Lsytp"], 530.0)
        self.assertEqual(table[12.0]["Lsytlap"], 350.0)
        self.assertEqual(table[12.0]["Lsycb"], 270.0)
        self.assertEqual(table[20.0]["Lsycb"], 440.0)
        self.assertEqual(table[12.0]["Lsycp"], 540.0)
        self.assertEqual(table[12.0]["Lsyclap"], 390.0)

    def test_the_full_compression_table(self):
        # The workbook prints 220, 270, 350, 440, 530, 610, 700, 790 for db 10 to 36.
        self.assertEqual([row["Lsycb"] for row in self.result["table"]],
                         [220.0, 270.0, 350.0, 440.0, 530.0, 610.0, 700.0, 790.0])

    def test_hooks_and_cogs(self):
        values = _inputs(**WORKBOOK, bendDb=20, galvanised="N", rebent="N", maxInternal=8)
        values["checks"] = {"hooksAndCogs": True}
        bends = headless.compute(values)["bends"]
        self.assertEqual(bends["internalFactor"], 5.0)
        self.assertEqual(bends["nominal"], 120.0)
        self.assertEqual(bends["extension"], 80.0)
        self.assertAlmostEqual(bends["hook180"], 268.495559215, places=8)
        self.assertAlmostEqual(bends["hook135Extension"], 127.123889804, places=8)
        self.assertAlmostEqual(bends["cogHeight"], 244.247779608, places=8)
        self.assertAlmostEqual(bends["cogLengthMax"], 362.743338823, places=8)
        self.assertAlmostEqual(bends["cogHeightMax"], 321.371669412, places=8)


class Branches(unittest.TestCase):
    def test_roundup_matches_excel(self):
        self.assertEqual(engine.roundup(348.0, -1), 350.0)
        self.assertEqual(engine.roundup(580.0, -1), 580.0)
        self.assertEqual(engine.roundup(1158.19, -1), 1160.0)
        self.assertEqual(engine.roundup(348.2, 0), 349.0)
        self.assertAlmostEqual(engine.roundup(348.21, 1), 348.3, places=10)

    def test_k1_switches_at_300_mm_of_concrete_below(self):
        self.assertEqual(headless.compute(_inputs(below=300))["factors"]["k1"], 1.0)
        self.assertEqual(headless.compute(_inputs(below=301))["factors"]["k1"], 1.3)

    def test_epoxy_and_lightweight_multipliers(self):
        plain = headless.compute(_inputs())["tension"]["Lsytb"]
        epoxy = headless.compute(_inputs(epoxy="Y"))["tension"]["Lsytb"]
        light = headless.compute(_inputs(lightweight="Y"))["tension"]["Lsytb"]
        self.assertAlmostEqual(epoxy, 1.5 * plain, places=9)
        self.assertAlmostEqual(light, 1.3 * plain, places=9)

    def test_bundled_bar_multiplier(self):
        for count, multiplier in (("1", 1.0), ("2", 1.0), ("3", 1.2), ("4", 1.33)):
            with self.subTest(bundle=count):
                self.assertEqual(headless.compute(_inputs(bundle=count))["factors"]["mb"],
                                 multiplier)

    def test_tension_f_c_is_capped_at_65(self):
        for strength, expected in ((40, 40.0), (65, 65.0), (100, 65.0), (120, 65.0)):
            with self.subTest(fc=strength):
                self.assertEqual(
                    headless.compute(_inputs(fc=strength))["factors"]["fcTension"], expected)

    def test_the_compression_cap_is_optional(self):
        uncapped = headless.compute(_inputs(fc=100, limitCompressionFc="N"))
        capped = headless.compute(_inputs(fc=100, limitCompressionFc="Y"))
        self.assertEqual(uncapped["factors"]["fcCompression"], 100.0)
        self.assertEqual(capped["factors"]["fcCompression"], 65.0)

    def test_wide_and_narrow_elements_use_different_lap_terms(self):
        wide = headless.compute(_inputs(element="W", sbb=200, db=20))
        narrow = headless.compute(_inputs(element="N", sbb=200, db=20))
        self.assertGreaterEqual(narrow["tensionLap"]["Lsytlap"],
                                wide["tensionLap"]["Lsytlap"])

    def test_spliced_bar_distance_is_counted_only_above_three_diameters(self):
        self.assertEqual(headless.compute(_inputs(db=20, sbb=59))["factors"]["sb"], 0.0)
        self.assertEqual(headless.compute(_inputs(db=20, sbb=60))["factors"]["sb"], 60.0)

    def test_k7_follows_the_steel_provided(self):
        self.assertEqual(headless.compute(_inputs(twiceProvided="N"))["factors"]["k7"], 1.25)
        self.assertEqual(headless.compute(_inputs(twiceProvided="Y"))["factors"]["k7"], 1.0)

    def test_fitment_reductions(self):
        non_helical = headless.compute(_inputs(helical="N", threeFitments="Y",
                                               fitment=12, fitmentSpacing=200, db=20))
        helical = headless.compute(_inputs(helical="Y", threeFitments="Y",
                                           fitment=12, fitmentSpacing=200, db=20))
        none = headless.compute(_inputs(helical="N", threeFitments="N", db=20))
        self.assertEqual(non_helical["factors"]["rn"], 0.8)
        self.assertEqual(helical["factors"]["rh"], 0.8)
        self.assertEqual((none["factors"]["rn"], none["factors"]["rh"]), (1.0, 1.0))

    def test_internal_diameter_factor(self):
        self.assertEqual(engine.internal_diameter_factor(20, "N", "N"), 5.0)
        self.assertEqual(engine.internal_diameter_factor(16, "Y", "N"), 5.0)
        self.assertEqual(engine.internal_diameter_factor(20, "Y", "N"), 8.0)
        self.assertEqual(engine.internal_diameter_factor(16, "N", "Y"), 4.0)
        self.assertEqual(engine.internal_diameter_factor(24, "N", "Y"), 5.0)
        self.assertEqual(engine.internal_diameter_factor(32, "N", "Y"), 6.0)

    def test_text_options_are_case_insensitive(self):
        self.assertEqual(headless.compute(_inputs(plain="y"))["inputs"]["plain"], "Y")
        self.assertEqual(headless.compute(_inputs(element="n"))["inputs"]["element"], "N")


class InputRejection(unittest.TestCase):
    def test_missing_required_fields(self):
        for key in ("fc", "db", "fsy", "cover", "clear", "below", "stress", "stressc",
                    "sbb", "fitment", "fitmentSpacing", "helixBars"):
            with self.subTest(key=key):
                values = _inputs()
                del values[key]
                with self.assertRaises(ValueError):
                    headless.compute(values)

    def test_malformed_numbers(self):
        for value in (None, True, "", "big", float("nan"), float("inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(db=value))

    def test_concrete_strength_limits(self):
        for strength in (19.9, 120.1):
            with self.subTest(fc=strength):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(fc=strength))

    def test_unsupported_enumerations(self):
        for key, value in (("fsy", "400"), ("bundle", "5"), ("plain", "maybe"),
                           ("element", "X"), ("rounding", "2")):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(**{key: value}))

    def test_impossible_values(self):
        with self.assertRaises(ValueError):
            headless.compute(_inputs(db=0))
        with self.assertRaises(ValueError):
            headless.compute(_inputs(cover=0))
        with self.assertRaises(ValueError):
            headless.compute(_inputs(below=-1))
        with self.assertRaises(ValueError):
            headless.compute(_inputs(fitmentSpacing=0))

    def test_non_dictionary_input(self):
        with self.assertRaises(ValueError):
            headless.compute([("fc", 32)])


class LapValidity(unittest.TestCase):
    def test_reduced_tension_stress_raises_the_lap_error(self):
        result = headless.compute(_inputs(stress=400))
        self.assertTrue(result["errors"])
        summary = headless.summarise(result)
        self.assertEqual(summary["status"], "FAIL")
        self.assertEqual(summary["criticalCheck"], "Lapped splice validity")
        self.assertIn("Cl 13.2.2", summary["headline"])

    def test_reduced_compression_stress_raises_the_lap_error(self):
        result = headless.compute(_inputs(stressc=400))
        self.assertTrue(any("Cl 13.2.4" in message for message in result["errors"]))
        self.assertEqual(headless.summarise(result)["status"], "FAIL")

    def test_reduced_stress_shortens_the_development_length(self):
        full = headless.compute(_inputs())["tension"]["Lsyt"]
        reduced = headless.compute(_inputs(stress=250))["tension"]["Lsyt"]
        self.assertLess(reduced, full)

    def test_the_reduced_stress_minimum_of_twelve_diameters_applies(self):
        result = headless.compute(_inputs(stress=1, db=20))
        self.assertEqual(result["tension"]["Lsyt"], 12 * 20)

    def test_full_stress_reports_ok(self):
        self.assertEqual(headless.summarise(headless.compute(_inputs()))["status"], "OK")


class NoDesignCheck(unittest.TestCase):
    def test_no_utilisation_is_reported(self):
        result = headless.compute(_inputs())
        self.assertEqual(result["util"], {})
        self.assertEqual(result["worstUtil"], 0.0)

    def test_summary_does_not_imply_adequacy(self):
        summary = headless.summarise(headless.compute(_inputs()))
        self.assertEqual(summary["worstUtil"], 0.0)
        self.assertIn("no design check", summary["headline"])


class StateIsolation(unittest.TestCase):
    def test_compute_does_not_mutate_or_drift(self):
        values = _inputs(**WORKBOOK)
        before = deepcopy(values)
        first = headless.compute(values)
        second = headless.compute(values)
        self.assertEqual(values, before)
        self.assertEqual(first["tension"], second["tension"])

    def test_unrelated_manager_keys_are_preserved_not_rejected(self):
        values = _inputs(description="Beam B1 laps", linkedFrom=[])
        self.assertTrue(math.isfinite(headless.compute(values)["tension"]["Lsyt"]))


class Reporting(unittest.TestCase):
    def test_navigation_anchors_and_appendix(self):
        values = _inputs(**WORKBOOK)
        result = headless.compute(values)
        for standalone in (False, True):
            with self.subTest(standalone=standalone):
                document = headless.render(values, result, standalone=standalone,
                                           appendix=["<p>Appendix fixture</p>"],
                                           anchor_prefix="dev-test",
                                           contents_href="#contents-test")
                self.assertIn('class="calc-page"', document)
                self.assertIn("dev-test", document)
                self.assertIn("#contents-test", document)
                self.assertIn("Appendix fixture", document)

    def test_clauses_and_the_no_check_statement_are_printed(self):
        values = _inputs(**WORKBOOK)
        document = headless.render(values, headless.compute(values), standalone=True)
        for fragment in ("Eq 13.1.2.2", "Cl 13.1.2.4(a)", "Cl 13.1.3", "Cl 13.2.2",
                         "Eq 13.1.5.2", "Cl 13.1.6", "Cl 13.2.4(a)", "Cl 13.2.4(b)",
                         "Cl 13.1.7", "no utilisation", "not approved for design"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, document)

    def test_the_lap_error_is_stated_on_the_sheet(self):
        values = _inputs(stress=400)
        document = headless.render(values, headless.compute(values), standalone=True)
        self.assertIn("Lapped splice validity", document)

    def test_the_bar_size_table_is_printed_with_its_rounding_note(self):
        values = _inputs(**WORKBOOK)
        document = headless.render(values, headless.compute(values), standalone=True)
        self.assertIn("Lengths for the standard bar sizes", document)
        self.assertIn("rounded up at every step", document)

    def test_untrusted_identity_text_is_escaped(self):
        values = _inputs(memberType="<script>alert(1)</script>")
        document = headless.render(values, headless.compute(values), standalone=True)
        self.assertNotIn("<script>alert(1)</script>", document)


class ContractSurface(unittest.TestCase):
    def test_identity(self):
        record = headless.identity(_inputs(memberType="Bar", memberNumber="0009", db=24))
        self.assertEqual(record["calcType"], "Development and laps")
        self.assertIn("24 mm bar", record["title"])

    def test_summary_shape(self):
        summary = headless.summarise(headless.compute(_inputs()))
        self.assertEqual(set(summary), {"worstUtil", "criticalCheck", "status", "headline"})

    def test_validate_compares_real_values_and_counts_them(self):
        report = headless.validate()
        self.assertTrue(report["ok"], report["failures"])
        self.assertGreater(report["compared"], 50)
        self.assertIn("approval", report)

    def test_validate_reports_a_supplied_case_that_disagrees(self):
        report = headless.validate([{"name": "Deliberately wrong", "inputs": headless.defaults(),
                                     "expect": {"factors.k1": 99.0}}])
        self.assertFalse(report["ok"])

    def test_validate_rejects_a_case_with_no_expected_values(self):
        self.assertFalse(headless.validate([{"name": "Empty",
                                             "inputs": headless.defaults()}])["ok"])


if __name__ == "__main__":
    unittest.main()
