import copy
import unittest
from SRC.params_loader import load_params
from SRC.preference_sensitivity import configure, CONFIGURATIONS, SPARSE_KEYS
from SRC.fallback_projection import pass_through_prior
from SRC.preference_engine import diagnose_preference_weights
from SRC.matrix_loader import load_synth_pref_matrices


class SensitivityTest(unittest.TestCase):
    def test_all_configurations_leave_inputs_unchanged(self):
        params = load_params()
        posterior = {key: {'__federal_on_trial__': True, '__reliability__': .13}
                     for key in SPARSE_KEYS}
        before = copy.deepcopy((params, posterior))
        for name in CONFIGURATIONS:
            changed, post = configure(params, posterior, name)
            self.assertIsNot(changed, params)
            self.assertEqual((params, posterior), before)
            if not name.startswith('Special priors:'):
                self.assertEqual(changed.get('on_special_scenario_priors'),
                                 params.get('on_special_scenario_priors'))
        central = configure(params, posterior, 'Central model')
        self.assertEqual(central, before)

    def test_sparse_switch_only_changes_flagged_pools(self):
        params = load_params()
        posterior = {SPARSE_KEYS[0]: {'__federal_on_trial__': True, '__reliability__': .13},
                     SPARSE_KEYS[1]: {'__reliability__': .5},
                     'OTHER': {'__federal_on_trial__': True, '__reliability__': .8}}
        _, post = configure(params, posterior, 'Sparse federal evidence off')
        self.assertEqual(post[SPARSE_KEYS[0]]['__reliability__'], 0)
        self.assertEqual(post[SPARSE_KEYS[1]], posterior[SPARSE_KEYS[1]])
        self.assertEqual(post['OTHER'], posterior['OTHER'])

    def test_unknown_configuration_rejected(self):
        with self.assertRaises(ValueError):
            configure({}, {}, 'unknown')

    def test_absent_prior_mass_is_transferred_and_unsupported_paths_rejected(self):
        prior = {'ALP': {'ON': .2, 'IND': .2, 'GRN': .6},
                 'GRN': {'ON': .25, 'IND': .75}}
        projected = pass_through_prior('ALP', ['ON','IND'], prior)
        self.assertAlmostEqual(projected['ON'], .35)
        self.assertAlmostEqual(projected['IND'], .65)
        self.assertIsNone(pass_through_prior('ALP',['ON'],{'ALP':{'GRN':1}}))

    def test_pass_through_keeps_locked_special_flows_identical(self):
        params = load_params()
        alternative, _ = configure(params, {}, 'Generic fallback pass-through')
        matrix = next(iter(load_synth_pref_matrices().values()))['matrix']
        for donor in ('LNP','GRN','IND','OTH'):
            a = diagnose_preference_weights(donor,['ALP','ON'],matrix,'Inner Ring',params)
            b = diagnose_preference_weights(donor,['ALP','ON'],matrix,'Inner Ring',alternative)
            self.assertEqual(a['final_flows'], b['final_flows'])
