import ast
import copy
import subprocess
import unittest
import numpy as np
import pandas as pd
from SRC.constants import PARTIES
from SRC.forecast_params import defaults, validate, load_forecast_params
from SRC.forecast_engine import (simulate, simplex, perturb_local_primaries,
                                  draw_model_params, fingerprint)


def calculator_fixture():
    # Execute deployed calculator imports/function only: no UI, sync or writes.
    source = subprocess.check_output(['git','show','2f972c9c3a482a18beb3f186d56b236199538b97:app.py'],text=True)
    tree = ast.parse(source)
    selected = [node for node in tree.body if isinstance(node,(ast.Import,ast.ImportFrom))
                or isinstance(node,ast.FunctionDef) and node.name in ('run_model','params_for_scenario')]
    n = {'__file__':'app.py','log_checkpoint':lambda *args:None}
    exec(compile(ast.Module(body=selected,type_ignores=[]),'original-app','exec'),n)
    from tools.preference_review_trials import variant
    from tools.trial_vec_field_evidence import attach_vec_fields
    from SRC.oth_matrix_builder import rebuild_oth_matrices
    params = variant(n['load_params'](),'vec_field_coverage')
    primary = n['apply_seat_held_metadata'](n['load_legacy_primary_inputs'](),n['load_seat_held_metadata']())
    matrices = rebuild_oth_matrices(attach_vec_fields(n['load_synth_pref_matrices']()),params)
    posterior = n['apply_production_federal_on_evidence'](n['load_posterior_scenarios']())
    ideology = n['load_ideology_prior']()
    adjustments = n['load_lower_seat_adjustments']()
    return n,primary,matrices,params,posterior,ideology,adjustments


class ForecastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = calculator_fixture()

    def test_settings_validation(self):
        self.assertEqual(load_forecast_params()[0],defaults())
        for bad in ({'SIMULATIONS':1.5},{'SIMULATIONS':0},{'SEED':-1},
                    {'PREF_GENERIC_LOG_SD':float('nan')},{'TYPO':1}):
            with self.assertRaises(ValueError):
                validate(bad)

    def test_simplex_is_nonnegative_and_conserves(self):
        for x in ([25,30,10,25,5,5],[-100,120,2,3,4,5]):
            result = simplex(x)
            self.assertTrue((result>=0).all())
            self.assertAlmostEqual(result.sum(),100)

    def test_zero_uncertainty_matches_deployed_calculator(self):
        n,primary,matrices,params,posterior,ideology,adjustments = self.fixture
        targets = dict(ALP=24.6,LNP=29.1,GRN=13.3,ON=22,IND=5.5,OTH=5.5)
        expected,adjusted,_ = n['run_model'](primary,matrices,params,posterior,ideology,targets,adjustments)
        settings = defaults()
        for key in settings:
            if '_SD' in key:
                settings[key] = 0
        settings['SIMULATIONS'] = 2
        snapshot = fingerprint(primary,matrices,params,posterior,ideology,adjustments)
        actual = simulate(primary,matrices,params,posterior,ideology,targets,adjustments,settings)
        expected_counts = expected.winner.value_counts().reindex(PARTIES,fill_value=0).to_numpy()
        np.testing.assert_array_equal(actual['draws'][PARTIES].to_numpy(),np.tile(expected_counts,(2,1)))
        for _,row in actual['seats'].iterrows():
            winner = expected.set_index('district').loc[row.Seat,'winner']
            self.assertEqual(row[winner+' win (%)'],100)
        self.assertEqual(snapshot,fingerprint(primary,matrices,params,posterior,ideology,adjustments))
        local = perturb_local_primaries(adjusted,defaults(),np.random.default_rng(9))
        np.testing.assert_allclose(local[PARTIES].sum(axis=1),adjusted[PARTIES].sum(axis=1),atol=1e-9)
        np.testing.assert_allclose(local[PARTIES].sum(),adjusted[PARTIES].sum(),atol=1e-9)
        self.assertTrue((local[PARTIES].to_numpy()[adjusted[PARTIES].to_numpy()==0]==0).all())

    def test_reproducible_simulations_and_complete_events(self):
        _,primary,matrices,params,posterior,ideology,adjustments = self.fixture
        targets = dict(ALP=24.6,LNP=29.1,GRN=13.3,ON=22,IND=5.5,OTH=5.5)
        settings = defaults()|{'SIMULATIONS':3}
        a = simulate(primary,matrices,params,posterior,ideology,targets,adjustments,settings)
        b = simulate(primary,matrices,params,posterior,ideology,targets,adjustments,settings)
        for key in ('seats','parties','government','draws','primary_draws'):
            pd.testing.assert_frame_equal(a[key],b[key])
        np.testing.assert_allclose(a['primary_draws'].sum(axis=1),100)
        self.assertTrue(a['draws'][PARTIES].sum(axis=1).eq(88).all())
        np.testing.assert_allclose(a['seats'].filter(like='win (%)').sum(axis=1),100)
        self.assertAlmostEqual(a['government'].iloc[:7]['Probability (%)'].sum(),100)

    def test_wrapper_leaves_special_priors_unchanged_outside_forecasts(self):
        from SRC.preference_engine import diagnose_preference_weights, _diagnose_preference_weights_base
        _,_,matrices,params,posterior,ideology,_ = self.fixture
        snapshot = copy.deepcopy(params['on_special_scenario_priors'])
        matrix = next(iter(matrices.values()))['matrix']
        args = ('LNP',['ALP','ON'],matrix,'Inner Ring',params,posterior,ideology)
        self.assertEqual(diagnose_preference_weights(*args),_diagnose_preference_weights_base(*args))
        drawn = draw_model_params(params,{'ON':22,'ALP':78},defaults(),['Inner Ring'],np.random.default_rng(1))
        result = diagnose_preference_weights(*args[:4],drawn,posterior,ideology)
        self.assertAlmostEqual(sum(result['final_flows'].values()),1)
        self.assertEqual(params['on_special_scenario_priors'],snapshot)
        self.assertEqual(drawn['on_special_scenario_priors'],snapshot)
