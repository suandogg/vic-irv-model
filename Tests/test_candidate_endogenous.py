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

    def test_exact_candidate_evidence_takes_precedence(self):
        result = count_candidates({'a': 60, 'b': 30, 'c': 10}, {'a': 'ALP', 'b': 'LNP', 'c': 'OTH'}, {'c': {'field': ['a', 'b'], 'shares': {'ALP': .7, 'LNP': .3}, 'candidate_shares': {'a': .8, 'b': .2}}}, prefer_exact=True)
        self.assertEqual(result['final_shares_pct'], [68, 32])
        self.assertEqual(result['rounds'][0]['recipient_method'], 'exact candidate evidence')

    def test_exact_mode_retains_proportional_fallback(self):
        result = count_candidates({'a': 60, 'b': 30, 'c': 10}, {'a': 'ALP', 'b': 'LNP', 'c': 'OTH'}, {'c': {'field': ['a', 'b'], 'shares': {'ALP': .7, 'LNP': .3}}}, prefer_exact=True)
        self.assertEqual(result['final_shares_pct'], [67, 33])

    def test_missing_evidence_invokes_approved_fallback(self):
        def fallback(eliminated, remaining):
            return {'field': sorted(remaining), 'shares': {'ALP': .7, 'LNP': .3}, 'training_seats': 3, 'method': 'subtype pool'}
        result = count_candidates({'a': 60, 'b': 30, 'c': 10}, {'a': 'ALP', 'b': 'LNP', 'c': 'OTH'}, {}, prefer_exact=True, fallback=fallback)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['rounds'][0]['training_seats'], 3)

    def test_exact_evidence_does_not_invoke_fallback(self):
        def fallback(*args):
            raise AssertionError('Exact evidence must have precedence')
        result = count_candidates({'a': 60, 'b': 30, 'c': 10}, {'a': 'ALP', 'b': 'LNP', 'c': 'OTH'}, {'c': {'field': ['a', 'b'], 'shares': {'ALP': .7, 'LNP': .3}, 'candidate_shares': {'a': .8, 'b': .2}}}, prefer_exact=True, fallback=fallback)
        self.assertEqual(result['final_shares_pct'], [68, 32])
