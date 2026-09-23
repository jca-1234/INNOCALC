import unittest
from ic_concrete_deep_beam import headless


class ReleaseGate(unittest.TestCase):
    def test_module_contract(self):
        from packages.innocalc_sdk import check_contract
        report = check_contract(headless)
        self.assertTrue(report["ok"], report["failures"])

    def test_reference_validation(self):
        report = headless.validate()
        self.assertTrue(report["ok"], report)