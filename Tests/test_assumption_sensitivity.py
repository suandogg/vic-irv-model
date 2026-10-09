import unittest
from SRC.assumption_sensitivity import FINDINGS, finding_for_seat


class SensitivityTests(unittest.TestCase):
    def test_only_documented_seats_are_flagged(self):
        self.assertEqual(set(FINDINGS), {'Bellarine','Point Cook','Pascoe Vale','Narre Warren North'})
        self.assertIsNone(finding_for_seat('Ashwood'))

    def test_each_flag_crosses_final_count_threshold(self):
        for _, _, baseline, stress in FINDINGS.values():
            self.assertLess((baseline - 50) * (stress - 50), 0)
