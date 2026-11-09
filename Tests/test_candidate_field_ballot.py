import unittest
from tools.build_candidate_field_ballot import name_key, default_strength


class BallotBuilderTests(unittest.TestCase):
    def test_name_forms_match(self):
        self.assertEqual(name_key('BRIFFA, Tony'), name_key('Tony Briffa'))
        self.assertEqual(name_key('YILDIZ, Oscar'), name_key('Oscar Yildiz'))
        self.assertNotEqual(name_key('HOPPER, Paul'), name_key('HOPPER, Meghan'))

    def test_returning_independent_keeps_retained_share(self):
        history = {('Kew', name_key('TORNEY, Sophie')): .211}
        row = default_strength('Kew', 'TORNEY, Sophie', history)
        self.assertAlmostEqual(row['median_pp'], 18.146)
        self.assertLess(row['p10_pp'], row['median_pp'])
        self.assertLess(row['median_pp'], row['p90_pp'])

    def test_new_independent_gets_first_time_prior(self):
        row = default_strength('Melton', 'FRASER, Jason', {})
        self.assertEqual((row['p10_pp'], row['median_pp'], row['p90_pp']), (0.49, 2.17, 9.43))
        other_seat = default_strength('Melton', 'TORNEY, Sophie', {('Kew', name_key('TORNEY, Sophie')): .211})
        self.assertEqual(other_seat['median_pp'], 2.17)
