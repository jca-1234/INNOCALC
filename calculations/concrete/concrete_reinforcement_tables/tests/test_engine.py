"""Engineering and interface tests for the Reinforcement Tables module."""

from __future__ import annotations

import math
import unittest
from copy import deepcopy

from ic_concrete_reinforcement_tables import engine, headless


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
        first["db"] = 99
        self.assertEqual(second["db"], 16.0)
        self.assertEqual(headless.compute(headless.defaults())["worstUtil"], 0.0)

    def test_descriptor_agrees_with_the_manifest_registration(self):
        descriptor = headless.descriptor()
        self.assertEqual(descriptor["id"], "concrete-reinforcement-tables")
        self.assertEqual(descriptor["entry"], "ic_concrete_reinforcement_tables.headless")
        self.assertEqual(descriptor["folder"], "10 - REINFORCEMENT TABLES")
        self.assertEqual(descriptor["status"], "planned")


class Arithmetic(unittest.TestCase):
    """Values taken from Structural Toolkit REINFORCEMENT V5.00."""

    def setUp(self):
        self.result = headless.compute(_inputs())

    def test_rounddown_matches_excel(self):
        self.assertEqual(engine.rounddown(113.097, -1), 110.0)
        self.assertEqual(engine.rounddown(402.124, -1), 400.0)
        self.assertEqual(engine.rounddown(1881.62, -1), 1880.0)
        self.assertEqual(engine.rounddown(113.097, 0), 113.0)

    def test_single_bar_row_of_the_number_table(self):
        # Number!C7:H7 caches 110, 200, 310, 450, 610, 800.
        self.assertEqual(self.result["numberTable"][0]["areas"][:6],
                         [110.0, 200.0, 310.0, 450.0, 610.0, 800.0])

    def test_thirty_bar_row_of_the_number_table(self):
        # Number!C36:H36 caches 3390, 6030, 9420, 13570, 18470, 24120.
        self.assertEqual(self.result["numberTable"][29]["areas"][:6],
                         [3390.0, 6030.0, 9420.0, 13570.0, 18470.0, 24120.0])

    def test_the_published_centres_rows(self):
        # Centres!C7, D7, I7 cache 1880, 3350, 20940; row 37 caches 110, 200, 1250.
        first, last = self.result["centresTable"][0], self.result["centresTable"][-1]
        self.assertEqual(first["centres"], 60.0)
        self.assertEqual([first["areas"][0], first["areas"][1], first["areas"][6]],
                         [1880.0, 3350.0, 20940.0])
        self.assertEqual(last["centres"], 1000.0)
        self.assertEqual([last["areas"][0], last["areas"][1], last["areas"][6]],
                         [110.0, 200.0, 1250.0])

    def test_rectangular_fabric_full_precision(self):
        # Fabric!F9 and I9 cache 1112.20233919 and 226.822989589.
        mesh = self.result["fabricTable"][0]
        self.assertEqual(mesh["name"], "RL1218")
        self.assertAlmostEqual(mesh["longArea"], 1112.20233919, places=8)
        self.assertAlmostEqual(mesh["crossArea"], 226.822989589, places=9)

    def test_square_and_trench_fabric(self):
        published = {"SL81": 453.646, "SL102": 354.411, "SL92": 290.440, "SL82": 226.823,
                     "SL72": 178.924, "SL62": 141.372, "SL52": 89.350, "SL63": 94.248,
                     "SL53": 59.567, "L12TM": 444.881, "L11TM": 359.681, "L8TM": 45.365}
        actual = {mesh["name"]: mesh["longArea"] for mesh in self.result["fabricTable"]}
        for name, area in published.items():
            with self.subTest(mesh=name):
                self.assertAlmostEqual(actual[name], area, places=3)

    def test_selected_reinforcement(self):
        selected = headless.compute(_inputs(db=16, count=4, centres=200))["selected"]
        self.assertAlmostEqual(selected["single"], math.pi * 64.0, places=9)
        self.assertAlmostEqual(selected["countArea"], 4 * math.pi * 64.0, places=9)
        self.assertAlmostEqual(selected["centresArea"], math.pi * 64.0 * 5.0, places=9)
        self.assertEqual(selected["countAreaRounded"], 800.0)
        self.assertEqual(selected["centresAreaRounded"], 1000.0)


class Branches(unittest.TestCase):
    def test_rounding_option_changes_the_tables(self):
        coarse = headless.compute(_inputs(rounding="-1"))["numberTable"][0]["areas"][0]
        fine = headless.compute(_inputs(rounding="0"))["numberTable"][0]["areas"][0]
        self.assertEqual(coarse, 110.0)
        self.assertEqual(fine, 113.0)

    def test_every_fabric_designation_resolves(self):
        for entry in engine.FABRIC:
            with self.subTest(mesh=entry["name"]):
                mesh = headless.compute(_inputs(mesh=entry["name"]))["mesh"]
                self.assertEqual(mesh["name"], entry["name"])
                self.assertGreater(mesh["longArea"], 0.0)

    def test_trench_mesh_is_reported_per_sheet_not_per_metre(self):
        mesh = headless.compute(_inputs(mesh="L12TM"))["mesh"]
        self.assertFalse(mesh["perMetre"])
        self.assertIsNone(mesh["crossArea"])
        self.assertEqual(mesh["wires"], 4.0)

    def test_western_australia_products_carry_a_note(self):
        result = headless.compute(_inputs(mesh="SL63"))
        self.assertTrue(any("Western Australia" in note for note in result["warnings"]))

    def test_designation_is_case_insensitive(self):
        self.assertEqual(headless.compute(_inputs(mesh="sl82"))["mesh"]["name"], "SL82")

    def test_a_non_tabulated_bar_size_is_warned_not_rejected(self):
        result = headless.compute(_inputs(db=10))
        self.assertTrue(any("not a tabulated size" in note for note in result["warnings"]))
        self.assertGreater(result["selected"]["single"], 0.0)


class InputRejection(unittest.TestCase):
    def test_missing_required_fields(self):
        for key in ("db", "count", "centres", "rounding", "mesh"):
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

    def test_impossible_values(self):
        with self.assertRaises(ValueError):
            headless.compute(_inputs(db=0))
        with self.assertRaises(ValueError):
            headless.compute(_inputs(count=-1))
        with self.assertRaises(ValueError):
            headless.compute(_inputs(centres=0))

    def test_unsupported_enumerations(self):
        with self.assertRaises(ValueError):
            headless.compute(_inputs(mesh="SL99"))
        with self.assertRaises(ValueError):
            headless.compute(_inputs(rounding="2"))

    def test_non_dictionary_input(self):
        with self.assertRaises(ValueError):
            headless.compute([("db", 16)])


class NoDesignCheck(unittest.TestCase):
    def test_no_utilisation_is_reported(self):
        result = headless.compute(_inputs())
        self.assertEqual(result["util"], {})
        self.assertEqual(result["worstUtil"], 0.0)

    def test_summary_does_not_imply_adequacy(self):
        summary = headless.summarise(headless.compute(_inputs()))
        self.assertEqual(summary["worstUtil"], 0.0)
        self.assertIn("no design check", summary["headline"])
        self.assertEqual(summary["criticalCheck"], "Not applicable - reference tables")

    def test_rounded_values_never_exceed_the_exact_values(self):
        result = headless.compute(_inputs(db=24, count=7, centres=175))
        selected = result["selected"]
        self.assertLessEqual(selected["countAreaRounded"], selected["countArea"])
        self.assertLessEqual(selected["centresAreaRounded"], selected["centresArea"])


class StateIsolation(unittest.TestCase):
    def test_compute_does_not_mutate_or_drift(self):
        values = _inputs()
        before = deepcopy(values)
        first = headless.compute(values)
        second = headless.compute(values)
        self.assertEqual(values, before)
        self.assertEqual(first["selected"], second["selected"])

    def test_unrelated_manager_keys_are_preserved_not_rejected(self):
        values = _inputs(description="Bar schedule", linkedFrom=[])
        self.assertEqual(headless.compute(values)["worstUtil"], 0.0)


class Reporting(unittest.TestCase):
    def test_navigation_anchors_and_appendix(self):
        values = _inputs()
        result = headless.compute(values)
        for standalone in (False, True):
            with self.subTest(standalone=standalone):
                document = headless.render(values, result, standalone=standalone,
                                           appendix=["<p>Appendix fixture</p>"],
                                           anchor_prefix="tables-test",
                                           contents_href="#contents-test")
                self.assertIn('class="calc-page"', document)
                self.assertIn("tables-test", document)
                self.assertIn("#contents-test", document)
                self.assertIn("Appendix fixture", document)

    def test_the_no_check_statement_and_provenance_are_printed(self):
        values = _inputs()
        document = headless.render(values, headless.compute(values), standalone=True)
        for fragment in ("no utilisation", "onemesh 500",
                         "current manufacturer", "rounded down"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, document)

    def test_the_tendon_exclusion_is_disclosed(self):
        values = _inputs()
        document = headless.render(values, headless.compute(values), standalone=True)
        self.assertIn("prestressing tendon table", document)

    def test_long_tables_are_split_across_blocks(self):
        values = _inputs()
        document = headless.render(values, headless.compute(values), standalone=True)
        self.assertIn("continued", document)

    def test_untrusted_identity_text_is_escaped(self):
        values = _inputs(memberType="<script>alert(1)</script>")
        document = headless.render(values, headless.compute(values), standalone=True)
        self.assertNotIn("<script>alert(1)</script>", document)


class ContractSurface(unittest.TestCase):
    def test_identity(self):
        record = headless.identity(_inputs(memberType="Table", memberNumber="0001", db=20))
        self.assertEqual(record["calcType"], "Reinforcement tables")
        self.assertIn("20 mm bar", record["title"])

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
                                     "expect": {"selected.single": 1.0}}])
        self.assertFalse(report["ok"])

    def test_validate_rejects_a_case_with_no_expected_values(self):
        self.assertFalse(headless.validate([{"name": "Empty",
                                             "inputs": headless.defaults()}])["ok"])


if __name__ == "__main__":
    unittest.main()
