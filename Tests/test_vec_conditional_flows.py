import unittest
from tools.validate_vec_conditional_flows import distance


class ConditionalFlowTests(unittest.TestCase):
    def test_identical_shares(self):
        self.assertEqual(distance({'ALP': .6, 'LNP': .4}, {'ALP': .6, 'LNP': .4}, ['ALP', 'LNP']), 0)

    def test_two_party_distance_is_share_error(self):
        self.assertAlmostEqual(distance({'ALP': .6, 'LNP': .4}, {'ALP': .7, 'LNP': .3}, ['ALP', 'LNP']), 10)

    def test_disjoint_distributions(self):
        self.assertEqual(distance({'ALP': 1}, {'LNP': 1}, ['ALP', 'LNP']), 100)
