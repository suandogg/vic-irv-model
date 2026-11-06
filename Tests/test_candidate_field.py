import unittest
import numpy as np
import pandas as pd
from SRC.constants import PARTIES
from SRC import candidate_field as cf

DISTRICTS = ['A', 'B', 'C', 'D']


def seats():
    rows = [[.3, .3, .1, .1, .1, .1], [.35, .25, .15, .1, .05, .1],
            [.25, .35, .1, .15, .05, .1], [.3, .3, .1, .1, .1, .1]]
    return pd.DataFrame([dict(district=d, region='Western Metro', seat_type='Outer Metro', held_by='ALP',
                              **dict(zip(PARTIES, r))) for d, r in zip(DISTRICTS, rows)])


def config(candidates=(), retention=1., mode='combined'):
    groups = {d: ['ALP', 'GRN', 'IND', 'LNP', 'ON', 'OTH'] for d in DISTRICTS}
    groups['A'] = ['ALP', 'GRN', 'LNP', 'ON', 'OTH']
    return dict(residual_retention=retention, residual_mode=mode, groups=groups,
                affinity={g: [1, 1, 2, 1, 0, 1.5] for g in ('metro', 'nonmetro')},
                candidates=list(candidates))


def entrant(cid, group='IND', median=.1, district='B', **extra):
    return dict(dict(district=district, candidate_id=cid, kind='entrant', model_group=group, median=median,
                     low=median/2, high=min(.9, median*2), brand='', brand_share=0, prior_vote=0), **extra)


TARGETS = dict(zip(PARTIES, [30, 30, 11.25, 11.25, 7.5, 10]))


class FieldTests(unittest.TestCase):
    def test_no_independent_means_zero_ind_under_any_scale(self):
        for scale in (.5, 1, 2):
            frame = seats()
            frame.loc[0, 'IND'] = .1*scale
            frame.loc[0, 'ALP'] = .4-.1*scale
            out = cf.apply_candidate_field(frame, TARGETS, config())
            self.assertEqual(out.loc[0, 'IND'], 0)

    def test_seat_totals_and_retained_residual(self):
        out = cf.apply_candidate_field(seats(), TARGETS, config())
        np.testing.assert_allclose(out[PARTIES].sum(axis=1), 1, atol=1e-10)
        np.testing.assert_allclose(out[['ALP', 'LNP', 'GRN', 'ON']].mean()*100, [30, 30, 11.25, 11.25], atol=1e-6)
        self.assertAlmostEqual((out.IND+out.OTH).mean()*100, 17.5, places=6)

    def test_zero_retention_gives_residual_to_named_parties(self):
        keep = cf.apply_candidate_field(seats(), TARGETS, config(retention=1))
        give = cf.apply_candidate_field(seats(), TARGETS, config(retention=0))
        self.assertLess((give.IND+give.OTH).mean(), (keep.IND+keep.OTH).mean())
        self.assertGreater(give.ALP.mean(), keep.ALP.mean())
        field = give.attrs['candidate_field']
        self.assertAlmostEqual(field['field_residual'], field['wanted_residual'])

    def test_second_entrant_reduces_first(self):
        votes = seats()[PARTIES].to_numpy()[1]
        affinity = np.array([1, 1, 2, 1, 0, 1.5])
        solo = dict(candidate_id='a', model_group='IND', strength=.1)
        other = dict(candidate_id='b', model_group='OTH', strength=.05)
        _, alone = cf.enter(votes, [solo], affinity)
        out, both = cf.enter(votes, [solo, other], affinity)
        self.assertAlmostEqual(alone['a'], .1, places=8)
        self.assertLess(both['a'], .1)
        self.assertLess(both['a']+both['b'], .15)
        self.assertAlmostEqual(out.sum(), 1)

    def test_named_entrant_replaces_old_surface(self):
        frame = seats()
        out = cf.apply_candidate_field(frame, dict(TARGETS), config([entrant('x', median=.2)]), None)
        self.assertGreater(out.loc[1, 'IND'], .15)
        self.assertEqual(out.attrs['candidate_field']['candidates'][0]['candidate_id'], 'x')

    def test_switcher_only_credits_voters_new_to_party(self):
        votes = np.array([.4, .3, .1, .1, 0, .1])
        affinity = np.ones(6)
        out, uplift = cf.carry_switcher(votes, 1, .1, .5, affinity)
        self.assertAlmostEqual(uplift, .5*.7*.1)
        self.assertAlmostEqual(out.sum(), 1)
        self.assertAlmostEqual(out[1]-votes[1], uplift)

    def test_draws_never_fail_when_surface_varies(self):
        rng = np.random.default_rng(1)
        cfg = config([entrant('x'), entrant('y', 'OTH', .05, brand='W', brand_share=.5)])
        for draw in range(100):
            frame = seats()
            frame[PARTIES] = rng.dirichlet(frame[PARTIES].to_numpy()[0]*40, size=4)
            out = cf.apply_candidate_field(frame, TARGETS, cfg, np.random.default_rng(draw))
            self.assertEqual(out.loc[0, 'IND'], 0)
            np.testing.assert_allclose(out[PARTIES].sum(axis=1), 1, atol=1e-10)

    def test_seeded_draw_reproducible_and_row_order_safe(self):
        cfg = config([entrant('x')])
        a = cf.apply_candidate_field(seats(), TARGETS, cfg, np.random.default_rng(4))
        b = cf.apply_candidate_field(seats(), TARGETS, cfg, np.random.default_rng(4))
        pd.testing.assert_frame_equal(a, b, check_exact=True)

    def test_brand_shock_is_shared(self):
        c = entrant('x', 'OTH', brand='W', brand_share=1.)
        high = cf.sample_strength(c, {'W': 2.}, np.random.default_rng(1))
        low = cf.sample_strength(c, {'W': -2.}, np.random.default_rng(1))
        self.assertGreater(high, c['median'])
        self.assertLess(low, c['median'])

    def test_invalid_inputs_rejected(self):
        with self.assertRaises(ValueError):
            cf.validate_config(config(retention=2), DISTRICTS)
        with self.assertRaises(ValueError):
            cf.validate_config(config([entrant('x', district='A')]), DISTRICTS)
        with self.assertRaises(ValueError):
            cf.validate_config(dict(config(), groups={'A': ['ALP']}), DISTRICTS)

    def test_shipped_tables_load(self):
        frame = cf.load_field_config()
        self.assertEqual(len(frame['groups']), 88)
        self.assertNotIn('IND', frame['groups']['Melton'])
        self.assertIn('IND', frame['groups']['Essendon'])
