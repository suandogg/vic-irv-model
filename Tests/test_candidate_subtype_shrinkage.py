import unittest
from tools.validate_candidate_subtype_shrinkage import blend


class ShrinkageTests(unittest.TestCase):
    def test_evidence_weight_and_conservation(self):
        result = blend({'ALP': .8, 'LNP': .2}, {'ALP': .4, 'LNP': .6}, 1, 3)
        self.assertAlmostEqual(result['ALP'], .5)
        self.assertAlmostEqual(sum(result.values()), 1)

    def test_zero_strength_preserves_subtype(self):
        result = blend({'ALP': .8, 'LNP': .2}, {'ALP': .4, 'LNP': .6}, 2, 0)
        self.assertAlmostEqual(result['ALP'], .8)
