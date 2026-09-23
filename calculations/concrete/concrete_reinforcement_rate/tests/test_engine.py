"""Engineering and interface tests for the Reinforcement Rate module."""

from __future__ import annotations

import math
import unittest
from copy import deepcopy

from ic_concrete_reinforcement_rate import engine, headless

WORKBOOK = {
    "title": "Default", "L": 1000, "rb": 1000, "rd": 150, "cover": 30,
    "ligs": 8, "density": 7860,
}


def _inputs(**overrides):
    values = headless.defaults()
    values["date"] = "01/01/2026"
    values.update(overrides)
    return values


def _rate(schedule="", **overrides):
    return _inputs(**WORKBOOK, schedule=schedule, **overrides)


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
        first["title"] = "changed"
        self.assertEqual(second["title"], "Default")
        self.assertGreater(headless.compute(headless.defaults())["totals"]["rate"], 0.0)

    def test_descriptor_agrees_with_the_manifest_registration(self):
        descriptor = headless.descriptor()
        self.assertEqual(descriptor["id"], "concrete-reinforcement-rate")
        self.assertEqual(descriptor["entry"], "ic_concrete_reinforcement_rate.headless")
        self.assertEqual(descriptor["folder"], "08 - REINFORCEMENT RATE")
        self.assertEqual(descriptor["status"], "planned")


class Arithmetic(unittest.TestCase):
    """Values taken from Structural Toolkit REINFORCEMENT RATE V5.00, sheet ``Rate``."""

    def test_member_geometry_chain(self):
        member = headless.compute(_rate())["member"]
        self.assertAlmostEqual(member["area"], 0.15, places=12)
        self.assertAlmostEqual(member["volume"], 0.15, places=12)
        self.assertEqual(member["hook"], 150.0)
        self.assertEqual(member["ties"], 6)
        self.assertAlmostEqual(member["ligature"], 2.32, places=12)
        self.assertAlmostEqual(member["tieSet"], 2.46, places=12)

    def test_empty_schedule_gives_a_zero_rate(self):
        totals = headless.compute(_rate())["totals"]
        self.assertEqual(totals["weight"], 0.0)
        self.assertEqual(totals["rate"], 0.0)
        self.assertEqual(totals["rows"], 0)

    def test_hook_length_lookup(self):
        for size, hook in ((6, 150), (8, 150), (10, 165), (12, 185), (16, 225), (20, 275)):
            with self.subTest(ligs=size):
                self.assertEqual(engine.hook_length(float(size)), float(hook))
        self.assertEqual(engine.hook_length(24.0), 0.0)

    def test_bar_row_at_centres(self):
        row = headless.compute(_rate("B, 200, 12, 1000, Bottom"))["schedule"][0]
        self.assertEqual(row["count"], 5.0)
        self.assertEqual(row["totalLength"], 5.0)
        self.assertAlmostEqual(row["weight"], 4.44472528629, places=9)
        self.assertEqual(row["mark"], "N12-200")

    def test_bar_row_as_a_count(self):
        row = headless.compute(_rate("B, 6, 12, 1000, Six"))["schedule"][0]
        self.assertEqual(row["count"], 6.0)
        self.assertEqual(row["totalLength"], 6.0)
        self.assertEqual(row["mark"], "6-N12")

    def test_ligature_and_transverse_rows(self):
        result = headless.compute(_rate("L, 300, 10, 3000, Ligs\nT, 300, 10, 3000, Ties"))
        ligature, transverse = result["schedule"]
        self.assertEqual(ligature["count"], 11.0)
        self.assertAlmostEqual(ligature["totalLength"], 25.52, places=10)
        self.assertEqual(ligature["mark"], "N10-300 L")
        self.assertEqual(transverse["count"], 11.0)
        self.assertAlmostEqual(transverse["totalLength"], 52.58, places=10)
        self.assertEqual(transverse["mark"], "N10-300 L*")

    def test_rate_is_the_weight_over_the_volume(self):
        result = headless.compute(_rate("B, 200, 12, 1000, Bottom"))
        self.assertAlmostEqual(result["totals"]["rate"],
                               result["totals"]["weight"] / result["member"]["volume"],
                               places=9)
        self.assertAlmostEqual(result["totals"]["rate"], 29.6315019086, places=8)


class ScheduleParsing(unittest.TestCase):
    def test_comments_and_blank_lines_are_ignored(self):
        result = headless.compute(_rate("# header\n\nB, 200, 12, 1000, Bottom\n\n"))
        self.assertEqual(result["totals"]["rows"], 1)

    def test_description_may_contain_commas(self):
        row = headless.compute(
            _rate("B, 200, 12, 1000, Bottom bars, main direction"))["schedule"][0]
        self.assertEqual(row["description"], "Bottom bars, main direction")

    def test_type_is_case_insensitive(self):
        result = headless.compute(_rate("b, 200, 12, 1000, lower case"))
        self.assertEqual(result["schedule"][0]["type"], "B")

    def test_a_zero_quantity_row_contributes_nothing(self):
        row = headless.compute(_rate("B, 0, 12, 1000, Nothing"))["schedule"][0]
        self.assertEqual(row["count"], 0.0)
        self.assertEqual(row["weight"], 0.0)
        self.assertEqual(row["mark"], "")

    def test_malformed_lines_are_rejected_with_the_line_number(self):
        for schedule in ("B, 200, 12", "X, 200, 12, 1000, bad type",
                         "B, wide, 12, 1000, bad number", "B, 200, 0, 1000, zero size",
                         "B, 200, -12, 1000, negative", "L, 300, 10, 0, no length"):
            with self.subTest(schedule=schedule):
                with self.assertRaises(ValueError):
                    headless.compute(_rate(schedule))

    def test_the_row_limit_is_enforced(self):
        schedule = "\n".join(["B, 200, 12, 1000, row"] * (engine.MAX_ROWS + 1))
        with self.assertRaises(ValueError):
            headless.compute(_rate(schedule))
        allowed = "\n".join(["B, 200, 12, 1000, row"] * engine.MAX_ROWS)
        self.assertEqual(headless.compute(_rate(allowed))["totals"]["rows"], engine.MAX_ROWS)

    def test_a_non_text_schedule_is_rejected(self):
        with self.assertRaises(ValueError):
            headless.compute(_rate(42))


class InputRejection(unittest.TestCase):
    def test_missing_required_fields(self):
        for key in ("L", "rb", "rd", "cover", "ligs", "density"):
            with self.subTest(key=key):
                values = _inputs()
                del values[key]
                with self.assertRaises(ValueError):
                    headless.compute(values)

    def test_malformed_numbers(self):
        for value in (None, True, "", "wide", float("nan"), float("inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    headless.compute(_inputs(rb=value))

    def test_impossible_geometry(self):
        with self.assertRaises(ValueError):
            headless.compute(_inputs(rd=0))
        with self.assertRaises(ValueError):
            headless.compute(_inputs(cover=-10))
        with self.assertRaises(ValueError):
            headless.compute(_inputs(density=0))

    def test_non_dictionary_input(self):
        with self.assertRaises(ValueError):
            headless.compute([("L", 1000)])


class NoDesignCheck(unittest.TestCase):
    def test_no_utilisation_is_reported(self):
        result = headless.compute(_inputs())
        self.assertEqual(result["util"], {})
        self.assertEqual(result["worstUtil"], 0.0)

    def test_summary_does_not_imply_adequacy(self):
        summary = headless.summarise(headless.compute(_inputs()))
        self.assertEqual(summary["worstUtil"], 0.0)
        self.assertIn("no design check", summary["headline"])
        self.assertEqual(summary["criticalCheck"], "Not applicable - quantity calculation")

    def test_an_oversized_ligature_is_warned_not_rejected(self):
        result = headless.compute(_inputs(ligs=24))
        self.assertEqual(result["member"]["hook"], 0.0)
        self.assertTrue(any("largest tabulated" in note for note in result["warnings"]))


class StateIsolation(unittest.TestCase):
    def test_compute_does_not_mutate_or_drift(self):
        values = _rate("B, 200, 12, 1000, Bottom")
        before = deepcopy(values)
        first = headless.compute(values)
        second = headless.compute(values)
        self.assertEqual(values, before)
        self.assertEqual(first["totals"], second["totals"])

    def test_unrelated_manager_keys_are_preserved_not_rejected(self):
        values = _inputs(description="Slab S1", linkedFrom=[])
        self.assertTrue(math.isfinite(headless.compute(values)["totals"]["rate"]))


class Reporting(unittest.TestCase):
    def test_navigation_anchors_and_appendix(self):
        values = _inputs()
        result = headless.compute(values)
        for standalone in (False, True):
            with self.subTest(standalone=standalone):
                document = headless.render(values, result, standalone=standalone,
                                           appendix=["<p>Appendix fixture</p>"],
                                           anchor_prefix="rate-test",
                                           contents_href="#contents-test")
                self.assertIn('class="calc-page"', document)
                self.assertIn("rate-test", document)
                self.assertIn("#contents-test", document)
                self.assertIn("Appendix fixture", document)

    def test_exclusions_and_the_no_check_statement_are_printed(self):
        values = _inputs()
        document = headless.render(values, headless.compute(values), standalone=True)
        for fragment in ("no utilisation", "LAPS AND LIGATURE COGS ARE EXCLUDED",
                         "Cl 8.3.2.2", "read as centres"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, document)

    def test_row_interpretation_is_printed_for_audit(self):
        values = _inputs(schedule="B, 6, 12, 1000, Six bars")
        document = headless.render(values, headless.compute(values), standalone=True)
        self.assertIn("a count of 6", document)

    def test_a_long_schedule_is_split_across_blocks(self):
        values = _inputs(schedule="\n".join(["B, 200, 12, 1000, row"] * 20))
        document = headless.render(values, headless.compute(values), standalone=True)
        self.assertIn("Reinforcement schedule continued", document)

    def test_untrusted_text_is_escaped(self):
        values = _inputs(schedule="B, 200, 12, 1000, <script>alert(1)</script>")
        document = headless.render(values, headless.compute(values), standalone=True)
        self.assertNotIn("<script>alert(1)</script>", document)


class ContractSurface(unittest.TestCase):
    def test_identity(self):
        record = headless.identity(_inputs(memberType="Beam", memberNumber="0004",
                                           title="Band beam"))
        self.assertEqual(record["calcType"], "Reinforcement rate")
        self.assertIn("Band beam", record["title"])

    def test_summary_shape(self):
        summary = headless.summarise(headless.compute(_inputs()))
        self.assertEqual(set(summary), {"worstUtil", "criticalCheck", "status", "headline"})

    def test_validate_compares_real_values_and_counts_them(self):
        report = headless.validate()
        self.assertTrue(report["ok"], report["failures"])
        self.assertGreater(report["compared"], 20)
        self.assertIn("approval", report)

    def test_validate_reports_a_supplied_case_that_disagrees(self):
        report = headless.validate([{"name": "Deliberately wrong", "inputs": headless.defaults(),
                                     "expect": {"member.volume": 1.0}}])
        self.assertFalse(report["ok"])

    def test_validate_rejects_a_case_with_no_expected_values(self):
        self.assertFalse(headless.validate([{"name": "Empty",
                                             "inputs": headless.defaults()}])["ok"])


if __name__ == "__main__":
    unittest.main()
