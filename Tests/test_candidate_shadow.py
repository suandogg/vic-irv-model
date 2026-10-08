import unittest
from SRC.candidate_shadow import allocate_category_flow


class CandidateShadowTests(unittest.TestCase):
    def test_proportional_allocation_conserves_categories(self):
        candidates = {'a': {'category': 'OTH', 'tally': 30}, 'b': {'category': 'OTH', 'tally': 10}, 'on': {'category': 'ON', 'tally': 20}}
        movements = allocate_category_flow(100, {'OTH': .6, 'ON': .4}, candidates)
        self.assertEqual(movements, {'a': 45, 'b': 15, 'on': 40})
        self.assertEqual(candidates['a']['tally'], 30)

    def test_zero_mass_recipient_is_unresolved(self):
        with self.assertRaises(ValueError):
            allocate_category_flow(10, {'OTH': 1}, {'a': {'category': 'OTH', 'tally': 0}})

    def test_invalid_shares_rejected(self):
        with self.assertRaises(ValueError):
            allocate_category_flow(10, {'OTH': .5}, {'a': {'category': 'OTH', 'tally': 1}})
