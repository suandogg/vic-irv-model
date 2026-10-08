import unittest
from tools.trial_candidate_endogenous_count import count_candidates


class EndogenousCandidateTests(unittest.TestCase):
    def test_missing_field_stops_without_inventing_flows(self):
        result = count_candidates({'a': 60, 'b': 30, 'c': 10}, {'a': 'ALP', 'b': 'LNP', 'c': 'OTH'}, {})
        self.assertEqual(result['status'], 'unresolved')
        self.assertEqual(result['next_eliminated'], 'c')

    def test_exact_field_completes(self):
        result = count_candidates({'a': 60, 'b': 30, 'c': 10}, {'a': 'ALP', 'b': 'LNP', 'c': 'OTH'}, {'c': {'field': ['a', 'b'], 'shares': {'ALP': .7, 'LNP': .3}}})
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['final_shares_pct'], [67, 33])

    def test_mismatched_field_stops(self):
        result = count_candidates({'a': 60, 'b': 30, 'c': 10}, {'a': 'ALP', 'b': 'LNP', 'c': 'OTH'}, {'c': {'field': ['a'], 'shares': {'ALP': 1}}})
        self.assertEqual(result['status'], 'unresolved')
