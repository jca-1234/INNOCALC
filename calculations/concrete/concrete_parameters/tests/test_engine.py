"""Engineering and interface tests for the Concrete Design Parameters module."""

from __future__ import annotations

import math
import unittest
from copy import deepcopy

from ic_concrete_parameters import engine, headless


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

    def test_optional_groups_start_disabled_and_are_fresh(self):
        values = headless.defaults()
        self.assertEqual(values["checks"], {"minimumSteel": False, "cracking": False})
        values["checks"]["cracking"] = True
        self.assertFalse(headless.defaults()["checks"]["cracking"])

    def test_descriptor_agrees_with_the_manifest_registration(self):
        descriptor = headless.descriptor()
        self.assertEqual(descriptor["id"], "concrete-parameters")
        self.assertEqual(descriptor["entry"], "ic_concrete_parameters.headless")
        self.assertEqual(descriptor["folder"], "05 - CONCRETE PARAMETERS")
        self.assertEqual(descriptor["status"], "planned")


class Arithmetic(unittest.TestCase):
    """Values taken from Structural Toolkit FORMULA V5.02."""

    def test_stress_block_factors_at_the_tabulated_grades(self):
        published = {32: (0.8019999999999999, 0.904), 40: (0.79, 0.88),
                     50: (0.775, 0.85), 65: (0.7525, 0.8049999999999999)}
        for grade, (alpha2, alpha1_raw) in published.items():
            with self.subTest(fc=grade):
                block = headless.compute(_inputs(fc=grade))["stressBlock"]
                self.assertAlmostEqual(block["alpha2"], alpha2, places=12)
                self.assertAlmostEqual(block["alpha1Unbounded"], alpha1_raw, places=12)

    def test_fcmi_curve_fit(self):
        published = {20: 22.1966, 25: 27.573600000000003, 32: 34.9754, 40: 43.2546,
                     50: 53.333600000000004, 65: 67.88959999999999, 80: 81.7706,
                     100: 99.2286, 120: 115.4866}
        for grade, value in published.items():
            with self.subTest(fc=grade):
                self.assertAlmostEqual(engine.fcmi_curve(float(grade)), value, places=10)

    def test_fcmi_as2327(self):
        published = {20: 22.5, 25: 27.914062500000004, 32: 35.352000000000004,
                     40: 43.650000000000006, 50: 53.71875000000001,
                     65: 68.18906250000002, 80: 81.9, 100: 99.00000000000001}
        for grade, value in published.items():
            with self.subTest(fc=grade):
                self.assertAlmostEqual(engine.fcmi_as2327(float(grade)), value, places=10)

    def test_strength_gain_table_at_120_mpa(self):
        ages = headless.compute(_inputs(fc=120))["strength"]["ages"]
        self.assertEqual([entry["day"] for entry in ages], [1, 3, 7, 28, 90, 365])
        self.assertAlmostEqual(ages[0]["normal"], 19.2, places=10)
        self.assertAlmostEqual(ages[0]["highEarly"], 40.800000000000004, places=10)
        self.assertAlmostEqual(ages[4]["normal"], 148.8, places=10)
        self.assertAlmostEqual(ages[5]["highEarly"], 144.0, places=10)

    def test_modulus_of_elasticity_brackets_the_published_table(self):
        # AS 3600 Table 3.1.2 gives Ec = 30100 MPa for N32 and 32800 MPa for N40.
        for grade, published in ((32, 30100.0), (40, 32800.0)):
            with self.subTest(fc=grade):
                Ec = headless.compute(_inputs(fc=grade, fcmiSource="table"))["material"]["Ec"]
                self.assertLess(abs(Ec - published) / published, 0.02)


class Branches(unittest.TestCase):
    def test_each_fcmi_source_selects_its_own_value(self):
        for source, path in (("table", "fcmiTable"), ("curve", "fcmiCurve"),
                             ("as2327", "fcmiAs2327")):
            with self.subTest(source=source):
                material = headless.compute(_inputs(fc=40, fcmiSource=source))["material"]
                self.assertEqual(material["fcmi"], material[path])

    def test_table_source_rejects_an_intermediate_grade(self):
        with self.assertRaises(ValueError):
            headless.compute(_inputs(fc=37, fcmiSource="table"))
        self.assertTrue(math.isfinite(
            headless.compute(_inputs(fc=37, fcmiSource="curve"))["material"]["fcmi"]))

    def test_cement_type_selects_the_design_strength(self):
        normal = headless.compute(_inputs(fc=32, cement="N", age=7))["strength"]["design"]
        early = headless.compute(_inputs(fc=32, cement="H", age=7))["strength"]["design"]
        self.assertAlmostEqual(normal, 32 * 0.66, places=10)
        self.assertAlmostEqual(early, 32 * 0.78, places=10)

    def test_factor_lower_bounds_bite_at_the_top_of_the_range(self):
        block = headless.compute(_inputs(fc=120))["stressBlock"]
        self.assertAlmostEqual(block["alpha2"], 0.67, places=12)
        self.assertAlmostEqual(block["gamma"], 0.67, places=12)
        self.assertAlmostEqual(block["alpha1"], 0.72, places=12)
        self.assertAlmostEqual(block["alpha1Unbounded"], 0.64, places=12)

    def test_alpha_b_for_each_section_type(self):
        self.assertEqual(engine.alpha_b("rect", bef=300, bw=300, Ds=600, D=600), 0.20)
        self.assertEqual(engine.alpha_b("slabCorner", bef=1, bw=1, Ds=1, D=1), 0.24)
        self.assertEqual(engine.alpha_b("slab4side", bef=1, bw=1, Ds=1, D=1), 0.19)
        web = engine.alpha_b("TLweb", bef=900, bw=300, Ds=150, D=600)
        self.assertAlmostEqual(web, max(0.20 + 2 * (0.4 * 0.25 - 0.18), 0.20 * 3 ** 0.25),
                               places=12)
        flange = engine.alpha_b("TLflange", bef=900, bw=300, Ds=150, D=600)
        self.assertAlmostEqual(flange, max(0.20 + 2 * (0.25 * 0.25 - 0.08),
                                           0.20 * 3 ** (2 / 3)), places=12)

    def test_minimum_steel_and_cracking_groups_activate(self):
        off = headless.compute(_inputs())
        self.assertIsNone(off["minimumSteel"])
        self.assertIsNone(off["cracking"])
        values = _inputs()
        values["checks"] = {"minimumSteel": True, "cracking": True}
        on = headless.compute(values)
        self.assertGreater(on["minimumSteel"]["Astmin"], 0.0)
        self.assertGreater(on["cracking"]["MuoTop"], 0.0)
        self.assertEqual(on["minimumSteel"]["reference"], "Cl 8.1.6.1")

    def test_slab_sections_cite_clause_9_1_1(self):
        values = _inputs(sectionType="slab4side")
        values["checks"] = {"minimumSteel": True, "cracking": False}
        self.assertEqual(headless.compute(values)["minimumSteel"]["reference"], "Cl 9.1.1")


class InputRejection(unittest.TestCase):
    def test_missing_required_fields(self):
        for key in ("fc", "density", "fcmiSource", "cement", "age"):
            with self.subTest(key=key):
                values = _inputs()
                del values[key]
                with self.assertRaises(ValueError):
                    headless.compute(values)

    def test_malformed_numbers(self):
        for value in (None, True, "", "strong", float("nan"), float("inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(fc=value))

    def test_concrete_strength_and_density_limits(self):
        for strength in (19.9, 120.1):
            with self.subTest(fc=strength):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(fc=strength))
        with self.assertRaises(ValueError):
            headless.compute(_inputs(density=0))

    def test_unsupported_enumerations_and_ages(self):
        for key, value in (("fcmiSource", "guess"), ("cement", "X")):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(**{key: value}))
        with self.assertRaises(ValueError):
            headless.compute(_inputs(age=14))

    def test_inconsistent_optional_geometry_is_rejected(self):
        values = _inputs(ds=700, D=600)
        values["checks"] = {"minimumSteel": True, "cracking": False}
        with self.assertRaises(ValueError):
            headless.compute(values)
        values = _inputs(sectionType="TLweb", bef=200, bw=300)
        values["checks"] = {"minimumSteel": True, "cracking": False}
        with self.assertRaises(ValueError):
            headless.compute(values)

    def test_non_dictionary_input(self):
        with self.assertRaises(ValueError):
            headless.compute([("fc", 32)])


class NoDesignCheck(unittest.TestCase):
    def test_no_utilisation_is_reported(self):
        result = headless.compute(_inputs())
        self.assertEqual(result["util"], {})
        self.assertEqual(result["worstUtil"], 0.0)

    def test_summary_does_not_imply_adequacy(self):
        summary = headless.summarise(headless.compute(_inputs(fc=50)))
        self.assertEqual(summary["worstUtil"], 0.0)
        self.assertIn("no design check", summary["headline"])
        self.assertEqual(summary["criticalCheck"], "Not applicable - parameter calculation")


class StateIsolation(unittest.TestCase):
    def test_compute_does_not_mutate_or_drift(self):
        values = _inputs()
        values["checks"] = {"minimumSteel": True, "cracking": True}
        before = deepcopy(values)
        first = headless.compute(values)
        second = headless.compute(values)
        self.assertEqual(values, before)
        self.assertEqual(first["material"], second["material"])

    def test_unrelated_manager_keys_are_preserved_not_rejected(self):
        values = _inputs(description="N32 properties", linkedFrom=[])
        self.assertEqual(headless.compute(values)["worstUtil"], 0.0)


class Reporting(unittest.TestCase):
    def test_navigation_anchors_and_appendix(self):
        values = _inputs()
        result = headless.compute(values)
        for standalone in (False, True):
            with self.subTest(standalone=standalone):
                document = headless.render(values, result, standalone=standalone,
                                           appendix=["<p>Appendix fixture</p>"],
                                           anchor_prefix="params-test",
                                           contents_href="#contents-test")
                self.assertIn('class="calc-page"', document)
                self.assertIn("params-test", document)
                self.assertIn("#contents-test", document)
                self.assertIn("Appendix fixture", document)

    def test_clauses_and_the_no_check_statement_are_printed(self):
        values = _inputs()
        values["checks"] = {"minimumSteel": True, "cracking": True}
        document = headless.render(values, headless.compute(values), standalone=True)
        for fragment in ("Cl 3.1.1.3", "Cl 3.1.2", "Cl 3.1.3", "Eq 8.1.3(1)", "Eq 8.1.3(2)",
                         "Eq 10.6.2.2", "Cl 10.6.1(d)", "AS 2327:2017 Table 3.6.2.3",
                         "Cl 8.1.6.1", "no utilisation", "not approved for design"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, document)

    def test_strength_table_provenance_is_disclosed(self):
        values = _inputs()
        document = headless.render(values, headless.compute(values), standalone=True)
        self.assertIn("no AS 3600 clause reference", document)

    def test_untrusted_identity_text_is_escaped(self):
        values = _inputs(memberType="<script>alert(1)</script>")
        document = headless.render(values, headless.compute(values), standalone=True)
        self.assertNotIn("<script>alert(1)</script>", document)


class ContractSurface(unittest.TestCase):
    def test_identity(self):
        record = headless.identity(_inputs(memberType="Grade", memberNumber="0003", fc=50))
        self.assertEqual(record["calcType"], "Concrete parameters")
        self.assertIn("f'c = 50 MPa", record["title"])

    def test_summary_shape(self):
        summary = headless.summarise(headless.compute(_inputs()))
        self.assertEqual(set(summary), {"worstUtil", "criticalCheck", "status", "headline"})

    def test_validate_compares_real_values_and_counts_them(self):
        report = headless.validate()
        self.assertTrue(report["ok"], report["failures"])
        self.assertGreater(report["compared"], 40)
        self.assertIn("approval", report)

    def test_validate_reports_a_supplied_case_that_disagrees(self):
        report = headless.validate([{"name": "Deliberately wrong", "inputs": headless.defaults(),
                                     "expect": {"material.fctf": 1.0}}])
        self.assertFalse(report["ok"])

    def test_validate_rejects_a_case_with_no_expected_values(self):
        self.assertFalse(headless.validate([{"name": "Empty",
                                             "inputs": headless.defaults()}])["ok"])


if __name__ == "__main__":
    unittest.main()
