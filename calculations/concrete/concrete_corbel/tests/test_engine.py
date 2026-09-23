"""Engineering and interface tests for the Concrete Corbel Design module.

Run from the suite root::

    python -m unittest discover -s calculations/concrete/concrete_corbel/tests -v
"""

from __future__ import annotations

import math
import unittest
from copy import deepcopy

from ic_concrete_corbel import engine, headless


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

    def test_defaults_are_fresh_documents(self):
        first, second = headless.defaults(), headless.defaults()
        first["checks"]["bearing"] = False
        self.assertTrue(second["checks"]["bearing"])

    def test_conditional_fields_declare_string_conditions(self):
        fields = {field["id"]: field
                  for group in headless.schema()["groups"] for field in group["fields"]}
        self.assertEqual(fields["mu"]["showWhen"], {"scond": ["O"]})
        self.assertEqual(fields["mlt"]["showWhen"], {"loadtype": ["M"]})

    def test_descriptor_agrees_with_the_manifest_registration(self):
        descriptor = headless.descriptor()
        self.assertEqual(descriptor["id"], "concrete-corbel")
        self.assertEqual(descriptor["entry"], "ic_concrete_corbel.headless")
        self.assertEqual(descriptor["folder"], "03 - CONCRETE CORBEL")
        self.assertEqual(descriptor["status"], "planned")


class Arithmetic(unittest.TestCase):
    """Values taken from Structural Toolkit CORBEL V5.06, sheet ``Design``."""

    def test_workbook_saved_example(self):
        result = headless.compute(_inputs())
        self.assertAlmostEqual(result["geometry"]["Ab"], 18000.0, places=9)
        self.assertAlmostEqual(result["geometry"]["lever"], 254.0, places=9)
        self.assertAlmostEqual(result["loads"]["Vstar"], 162000.0, places=6)
        self.assertAlmostEqual(result["loads"]["Ndstar"], 32400.0, places=6)
        self.assertAlmostEqual(result["loads"]["gp"], -28.0, places=9)
        self.assertAlmostEqual(result["reinforcement"]["As"], 678.584013175, places=8)
        self.assertAlmostEqual(result["reinforcement"]["cts"], 101.6, places=9)
        self.assertAlmostEqual(result["reinforcement"]["Asmin"], 288.633193202, places=8)
        self.assertAlmostEqual(result["bearing"]["phiB"], 14.976, places=9)
        self.assertAlmostEqual(result["shearFriction"]["tau"], 3.34663343156, places=9)
        self.assertAlmostEqual(result["shearFriction"]["phiVu"], 421675.812377, places=4)
        self.assertAlmostEqual(result["tie"]["phiFt"], 288398.2056, places=4)
        self.assertAlmostEqual(result["util"]["bearing"], 0.600961538462, places=10)

    def test_strut_chain_at_the_workbook_strut_width(self):
        state = engine.strut_state(18.7954083212, lever=254.0, av=105.0, b=600.0, fc=32.0,
                                   Vstar=162000.0)
        self.assertAlmostEqual(state["ang2"], 0.0341991305346, places=10)
        self.assertAlmostEqual(state["theta"], 1.14460483779, places=10)
        self.assertAlmostEqual(state["betas"], 0.880244319346, places=10)
        self.assertAlmostEqual(state["x"], 45.4647711087, places=8)
        self.assertAlmostEqual(state["phiCa"], 185828.401375, places=4)
        self.assertAlmostEqual(state["Cf"], 177915.070475, places=4)
        self.assertAlmostEqual(state["w"], 17.114099103, places=8)
        # Design!L17, the workbook's unconverged GoalSeek residual, in newtons.
        self.assertAlmostEqual(state["residual"], -7903.33089991, places=3)
        tie = engine.tie_force(Vstar=162000.0, av=105.0, lever=254.0, x=state["x"],
                               Ndstar=32400.0)
        self.assertAlmostEqual(tie, 105951.154323, places=4)

    def test_strut_solve_reaches_the_workbook_goalseek_target(self):
        result = headless.compute(_inputs())
        strut = result["strut"]
        self.assertTrue(strut["converged"])
        self.assertLess(abs(strut["residual"]), 1e-3)
        self.assertAlmostEqual(strut["Cf"] + engine.STRUT_RESIDUAL_OFFSET_N, strut["phiCa"],
                               places=3)
        self.assertLess(strut["dc"], result["geometry"]["lever"])

    def test_actions_scale_linearly_with_the_supplied_kilonewtons(self):
        single = headless.compute(_inputs())
        double = headless.compute(_inputs(Vdl=120.0, Vll=120.0, Ndl=12.0, Nll=12.0))
        self.assertAlmostEqual(double["loads"]["Vstar"], 2 * single["loads"]["Vstar"], places=6)
        self.assertAlmostEqual(double["loads"]["Ndstar"], 2 * single["loads"]["Ndstar"], places=6)
        self.assertAlmostEqual(double["bearing"]["Bstar"], 2 * single["bearing"]["Bstar"],
                               places=9)

    def test_numeric_strings_are_accepted_at_the_input_boundary(self):
        self.assertEqual(headless.compute(_inputs(Vdl="60"))["loads"]["Vdl"],
                         headless.compute(_inputs())["loads"]["Vdl"])


class Branches(unittest.TestCase):
    def test_table_8_4_3_surface_conditions(self):
        expected = {"S": (0.6, 0.1), "T": (0.6, 0.2), "R": (0.7, 0.4), "M": (0.9, 0.5)}
        for condition, (mu, kco) in expected.items():
            with self.subTest(condition=condition):
                interface = headless.compute(_inputs(scond=condition))["interface"]
                self.assertEqual((interface["mu"], interface["kco"]), (mu, kco))
        manual = headless.compute(_inputs(scond="O", mu=0.55, kco=0.15))["interface"]
        self.assertEqual((manual["mu"], manual["kco"]), (0.55, 0.15))

    def test_long_term_factors(self):
        self.assertEqual(headless.compute(_inputs(loadtype="N"))["loads"]["psiL"], 0.4)
        self.assertEqual(headless.compute(_inputs(loadtype="S"))["loads"]["psiL"], 0.6)
        self.assertEqual(headless.compute(_inputs(loadtype="M", mlt=0.25))["loads"]["psiL"], 0.25)

    def test_hidden_fields_do_not_influence_an_inactive_branch(self):
        active = headless.compute(_inputs(scond="R", mu=9.9, kco=9.9))["interface"]
        self.assertEqual((active["mu"], active["kco"]), (0.7, 0.4))

    def test_reinforcement_entry_modes(self):
        counted = headless.compute(_inputs(reoMode="count", reoValue=6))["reinforcement"]
        centred = headless.compute(_inputs(reoMode="centres", reoValue=120))["reinforcement"]
        area = headless.compute(_inputs(reoMode="area", reoValue=678.584013175))["reinforcement"]
        self.assertAlmostEqual(counted["nbars"], 6.0)
        self.assertAlmostEqual(counted["cts"], 101.6)
        self.assertAlmostEqual(centred["nbars"], 600 / 120 + 1)
        self.assertAlmostEqual(area["As"], 678.584013175)
        self.assertAlmostEqual(area["nbars"], 1.0)

    def test_per_metre_length_uses_the_workbook_unit_switch(self):
        discrete = headless.compute(_inputs(b=600))
        per_metre = headless.compute(_inputs(b=1000, reoMode="centres", reoValue=200))
        self.assertFalse(discrete["geometry"]["perMetre"])
        self.assertTrue(per_metre["geometry"]["perMetre"])
        self.assertAlmostEqual(per_metre["reinforcement"]["nbars"], 5.0)
        self.assertAlmostEqual(per_metre["reinforcement"]["cts"], 200.0)

    def test_high_strength_concrete_is_accepted_across_the_permitted_range(self):
        for strength in (20.0, 32.0, 65.0, 120.0):
            with self.subTest(fc=strength):
                self.assertTrue(math.isfinite(
                    headless.compute(_inputs(fc=strength))["worstUtil"]))


class InputRejection(unittest.TestCase):
    def test_missing_required_fields(self):
        for key in ("fc", "b", "D", "av", "bw", "th", "Vdl", "bar", "cover", "reoValue"):
            with self.subTest(key=key):
                values = _inputs()
                del values[key]
                with self.assertRaises(ValueError):
                    headless.compute(values)

    def test_malformed_numbers(self):
        for value in (None, True, False, "", "wide", float("nan"), float("inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(b=value))

    def test_impossible_geometry(self):
        with self.assertRaises(ValueError):
            headless.compute(_inputs(b=0))
        with self.assertRaises(ValueError):
            headless.compute(_inputs(av=-10))
        with self.assertRaises(ValueError):
            headless.compute(_inputs(D=100, df=150))
        with self.assertRaises(ValueError):
            headless.compute(_inputs(D=100, df=100, cover=200))

    def test_concrete_strength_limits(self):
        for strength in (19.9, 120.1):
            with self.subTest(fc=strength):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(fc=strength))

    def test_unsupported_enumerations(self):
        for key, value in (("scond", "X"), ("loadtype", "Q"), ("reoMode", "spacing"),
                           ("bar", "10"), ("fsy", "250")):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(**{key: value}))

    def test_negative_actions_are_rejected(self):
        with self.assertRaises(ValueError):
            headless.compute(_inputs(Vll=-1))

    def test_non_dictionary_input(self):
        with self.assertRaises(ValueError):
            headless.compute([("fc", 32)])


class StatusAndLimits(unittest.TestCase):
    def test_status_flips_across_a_utilisation_of_one(self):
        satisfactory = headless.compute(_inputs(bw=18.2))
        overloaded = headless.compute(_inputs(bw=17.8))
        self.assertLess(satisfactory["worstUtil"], 1.0)
        self.assertGreater(overloaded["worstUtil"], 1.0)
        self.assertEqual(headless.summarise(satisfactory)["status"], "OK")
        self.assertEqual(headless.summarise(overloaded)["status"], "FAIL")
        self.assertEqual(headless.summarise(overloaded)["criticalCheck"],
                         "Bearing at the corbel node")

    def test_minimum_steel_failure_forces_a_failed_design(self):
        result = headless.compute(_inputs(reoMode="count", reoValue=2))
        self.assertGreater(result["util"]["minimumSteel"], 1.0)
        self.assertEqual(headless.summarise(result)["status"], "FAIL")

    def test_depth_limit_failure_forces_a_failed_design(self):
        result = headless.compute(_inputs(av=200))
        self.assertGreater(result["util"]["depthLimit"], 1.0)
        self.assertEqual(headless.summarise(result)["status"], "FAIL")

    def test_unattainable_shear_friction_reports_fail(self):
        result = headless.compute(_inputs(b=400, scond="O", mu=0.9, kco=0.0,
                                          reoMode="count", reoValue=2,
                                          Vdl=50, Vll=0, Ndl=200, Nll=0))
        self.assertLessEqual(result["shearFriction"]["tau"], 0.0)
        self.assertTrue(math.isinf(result["util"]["shearFriction"]))
        self.assertTrue(result["unattainable"])
        summary = headless.summarise(result)
        self.assertEqual(summary["status"], "FAIL")
        self.assertIn("unattainable", summary["headline"].lower())
        self.assertTrue(math.isfinite(result["worstUtil"]))

    def test_zero_actions_give_zero_demand_ratios(self):
        result = headless.compute(_inputs(Vdl=0, Vll=0, Ndl=0, Nll=0))
        self.assertEqual(result["util"]["bearing"], 0.0)
        self.assertEqual(result["util"]["shearFriction"], 0.0)
        self.assertFalse(any(math.isnan(value) for value in result["util"].values()))

    def test_every_check_is_mandatory(self):
        values = _inputs()
        values["checks"] = {key: False for key in values["checks"]}
        result = headless.compute(values)
        self.assertTrue(all(result["checks"].values()))


class StateIsolation(unittest.TestCase):
    def test_compute_does_not_mutate_or_drift(self):
        values = _inputs()
        before = deepcopy(values)
        first = headless.compute(values)
        second = headless.compute(values)
        self.assertEqual(values, before)
        self.assertEqual(first["util"], second["util"])
        self.assertEqual(first["strut"]["dc"], second["strut"]["dc"])

    def test_interleaved_cases_do_not_leak(self):
        light = headless.compute(_inputs())
        heavy = headless.compute(_inputs(Vdl=300, Vll=300))
        repeat = headless.compute(_inputs())
        self.assertEqual(light["util"], repeat["util"])
        self.assertGreater(heavy["loads"]["Vstar"], light["loads"]["Vstar"])

    def test_unrelated_manager_keys_are_preserved_not_rejected(self):
        values = _inputs(description="Precast beam seating", linkedFrom=[])
        self.assertTrue(math.isfinite(headless.compute(values)["worstUtil"]))


class Reporting(unittest.TestCase):
    def test_navigation_anchors_and_appendix(self):
        values = _inputs()
        result = headless.compute(values)
        for standalone in (False, True):
            with self.subTest(standalone=standalone):
                document = headless.render(values, result, standalone=standalone,
                                           appendix=["<p>Appendix fixture</p>"],
                                           anchor_prefix="corbel-test",
                                           contents_href="#contents-test")
                self.assertIn('class="calc-page"', document)
                self.assertIn("corbel-test", document)
                self.assertIn("#contents-test", document)
                self.assertIn("Appendix fixture", document)

    def test_engineering_content_and_clauses_are_printed(self):
        values = _inputs()
        document = headless.render(values, headless.compute(values), standalone=True)
        for fragment in ("Cl 7.4.2", "Cl 8.4.3", "Cl 7.2.3", "Cl 7.3.2", "Eq 8.1.6.1(2)",
                         "Table 8.4.3", "Table 2.2.4", "not approved for design"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, document)

    def test_unattainable_condition_is_stated_on_the_sheet(self):
        values = _inputs(b=400, scond="O", mu=0.9, kco=0.0, reoMode="count", reoValue=2,
                         Vdl=50, Vll=0, Ndl=200, Nll=0)
        document = headless.render(values, headless.compute(values), standalone=True)
        self.assertIn("Warnings and unattainable checks", document)
        self.assertIn("tau_u", document)

    def test_untrusted_identity_text_is_escaped(self):
        values = _inputs(memberType="<script>alert(1)</script>")
        document = headless.render(values, headless.compute(values), standalone=True)
        self.assertNotIn("<script>alert(1)</script>", document)

    def test_report_does_not_recompute(self):
        values = _inputs()
        result = headless.compute(values)
        tampered = deepcopy(result)
        tampered["bearing"]["phiB"] = 1.0
        self.assertIn("1.0", headless.render(values, tampered, standalone=True))


class ContractSurface(unittest.TestCase):
    def test_identity(self):
        values = _inputs(memberType="Corbel", memberNumber="0007", package="P01", level="L02")
        record = headless.identity(values)
        self.assertEqual(record["memberType"], "Corbel")
        self.assertEqual(record["memberNumber"], "0007")
        self.assertEqual(record["package"], "P01")
        self.assertEqual(record["level"], "L02")
        self.assertEqual(record["calcType"], "Concrete corbel")
        self.assertIn("600 x 300", record["title"])

    def test_summary_shape(self):
        summary = headless.summarise(headless.compute(_inputs()))
        self.assertEqual(set(summary), {"worstUtil", "criticalCheck", "status", "headline"})

    def test_validate_compares_real_values_and_counts_them(self):
        report = headless.validate()
        self.assertTrue(report["ok"], report["failures"])
        self.assertGreater(report["compared"], 40)
        self.assertGreater(report["tested"], 2)
        self.assertIn("approval", report)

    def test_validate_reports_a_supplied_case_that_disagrees(self):
        report = headless.validate([{"name": "Deliberately wrong", "inputs": headless.defaults(),
                                     "expect": {"bearing.phiB": 1.0}}])
        self.assertFalse(report["ok"])
        self.assertEqual(report["tested"], 1)

    def test_validate_rejects_a_case_with_no_expected_values(self):
        report = headless.validate([{"name": "Empty", "inputs": headless.defaults()}])
        self.assertFalse(report["ok"])


if __name__ == "__main__":
    unittest.main()
