import unittest
from tools.validate_candidate_subtype_pool import pooled_share


class CandidateSubtypePoolTests(unittest.TestCase):
    def row(self, seat, share, subtype='DLP', field=None):
        return {'seat': seat, 'category': 'OTH', 'subtype': subtype, 'field': field or ['ALP', 'LNP'], 'shares': {'ALP': share, 'LNP': 1-share}}

    def test_held_out_seat_excluded_and_seat_balanced(self):
        target = self.row('HELD', 1)
        observations = [target, self.row('A', .8), self.row('A', .6), self.row('B', .3)]
        shares, seats = pooled_share(observations, target, True, 2)
        self.assertAlmostEqual(shares['ALP'], .5)
        self.assertEqual(seats, 2)

    def test_minimum_and_field_are_strict(self):
        target = self.row('HELD', 1)
        observations = [self.row('A', .8, field=['ALP', 'LNP', 'OTH']), self.row('B', .3)]
        self.assertIsNone(pooled_share(observations, target, True, 2))

    def test_subtype_is_not_broad_category(self):
        target = self.row('HELD', 1)
        observations = [self.row('A', .8, subtype='AJP')]
        self.assertIsNone(pooled_share(observations, target, True, 1))
        self.assertIsNotNone(pooled_share(observations, target, False, 1))
