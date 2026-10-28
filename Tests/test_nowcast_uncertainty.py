import copy
import unittest
import numpy as np
import pandas as pd
from SRC.constants import PARTIES
from SRC.nowcast_uncertainty import validate_config,draw_vectors,perturb_district_leans,draw_transport


class NowcastUncertaintyTests(unittest.TestCase):
    def setUp(self):
        self.table = pd.DataFrame({
            'district':['A','B','C','D'], 'region':['R1','R1','R2','R2'],
            'seat_type':['Inner','Outer','Inner','Outer']})
        self.table[PARTIES] = np.array([[.4,.3,.1,.1,.1,0],[.2,.3,.2,.1,.1,.1],
                                       [.1,.2,.2,.2,.2,.1],[.3,.1,.1,.3,.1,.1]])
        self.config = {'provenance':'Explicit unit-test assumptions, not calibration'}

    def test_configuration_validation(self):
        for config in [{},{'provenance':'x','local_sd_pp':{'BAD':2}},
                       {'provenance':'x','local_sd_pp':{'ALP':float('nan')}},
                       {'provenance':'x','tail_df':2},
                       {'provenance':'x','contexts':{'Unknown':{}}},
                       {'provenance':'x','transport_log_sd':{'bad':.1}},
                       {'provenance':'x','contexts':{'A':{'candidate_sd_pp':{'ALP':2}}}}]:
            with self.assertRaises(ValueError):
                validate_config(config,list(self.table.district))

    def test_covariance_validation(self):
        for matrix in [np.eye(5),np.ones((6,6))*2,np.full((6,6),-1)]:
            with self.assertRaises(ValueError):
                validate_config(self.config|{'correlation':matrix.tolist()},list(self.table.district))
        singular = np.ones((6,6))
        valid = validate_config(self.config|{'correlation':singular.tolist()},list(self.table.district))
        x = draw_vectors(np.random.default_rng(3),100,np.array(valid['correlation']))
        np.testing.assert_allclose(x[:,0],x[:,1],atol=1e-7)

    def test_correlated_party_draws(self):
        correlation = np.eye(6)
        correlation[1,3] = correlation[3,1] = -.6
        for df in [None,5]:
            x = draw_vectors(np.random.default_rng(5),50000,correlation,df)
            self.assertAlmostEqual(np.corrcoef(x.T)[1,3],-.6,delta=.03)
            np.testing.assert_allclose(x.var(axis=0),1,atol=.07)

    def test_zero_identity(self):
        before = self.table.copy(deep=True)
        result,error = perturb_district_leans(self.table,self.config,np.random.default_rng(1))
        pd.testing.assert_frame_equal(result,before,check_exact=True)
        np.testing.assert_array_equal(error,0)

    def test_geographic_and_context_conservation(self):
        config = self.config|{'local_sd_pp':{p:5 for p in PARTIES},
            'region_sd_pp':{'ALP':3,'GRN':4},'class_sd_pp':{'LNP':2},'tail_df':5,
            'contexts':{'A':{'local_multiplier':{'ALP':2},'candidate_sd_pp':{'IND':7},
                             'note':'A known candidate-strength uncertainty, unit test'}}}
        before = copy.deepcopy(config)
        groups = dict(A='S1',B='S2',C='S1',D='S2')
        x,errors = perturb_district_leans(self.table,config,np.random.default_rng(8),groups,.5)
        again,_ = perturb_district_leans(self.table,config,np.random.default_rng(8),groups,.5)
        pd.testing.assert_frame_equal(x,again)
        self.assertEqual(config,before)
        self.assertTrue((x[PARTIES]>=0).all().all())
        self.assertEqual(x.loc[0,'OTH'],0)
        np.testing.assert_allclose(x[PARTIES].sum(),self.table[PARTIES].sum(),atol=1e-9)
        np.testing.assert_allclose(x[PARTIES].sum(axis=1),1,atol=1e-12)
        self.assertTrue(np.any(errors))
        with self.assertRaises(ValueError):
            perturb_district_leans(self.table,config,np.random.default_rng(8),{'A':'S1'},.5)

    def test_transport_source_separation_and_source_immutability(self):
        from SRC.forecast_engine import perturb_preference_flows
        settings = {k:0 for k in ['PREF_GENERIC_LOG_SD','PREF_FEDERAL_LOG_SD',
            'PREF_VEC_LOG_SD','PREF_SPECIAL_LOG_SD','PREF_CLASS_ON_LOG_SD']}
        config = validate_config(self.config|{'transport_log_sd':{'special':.4}},['A'])
        transport = draw_transport(config,np.random.default_rng(9))
        shocks = {'settings':settings,'origin':{},'class_on':{},'transport':transport}
        prior = {'ALP':.6,'ON':.4}
        diag = {'basis':'ON special prior','final_flows':prior,'stages':[]}
        before = copy.deepcopy(diag)
        one = perturb_preference_flows(diag,'LNP','Regional',shocks)
        two = perturb_preference_flows(diag,'LNP','Inner Ring',shocks)
        self.assertEqual(one,two)
        self.assertNotEqual(one,prior)
        self.assertAlmostEqual(sum(one.values()),1)
        generic = diag|{'basis':'ideology prior'}
        self.assertEqual(perturb_preference_flows(generic,'LNP','Regional',shocks),prior)
        self.assertEqual(diag,before)

    def test_simulation_gate_reproducibility_and_paired_targets(self):
        from Tests.test_forecast_engine import calculator_fixture
        from SRC.forecast_engine import simulate
        from SRC.forecast_params import defaults
        _,p,m,params,post,i,a = calculator_fixture()
        target = dict(ALP=24.6,LNP=29.1,GRN=13.3,ON=22,IND=5.5,OTH=5.5)
        settings = defaults()|{'SIMULATIONS':3}
        args=(p,m,params,post,i,target,a,settings)
        ordinary=simulate(*args)
        config=self.config|{'local_sd_pp':{p:3 for p in PARTIES},
                            'transport_log_sd':{'generic':.1,'special':.2}}
        trial=simulate(*args,experiment={'structured_nowcast':config})
        again=simulate(*args,experiment={'structured_nowcast':config})
        pd.testing.assert_frame_equal(trial['draws'],again['draws'])
        pd.testing.assert_frame_equal(trial['primary_draws'],ordinary['primary_draws'])
        self.assertTrue(trial['draws'][PARTIES].sum(axis=1).eq(88).all())
        self.assertEqual(params.get('_forecast_preference_shocks'),None)
        combined=dict(structured_nowcast=config,concentration_log_sd=.3,
                      concentration_form='positive_bounded')
        combined_run=simulate(*args,experiment=combined)
        pd.testing.assert_frame_equal(combined_run['primary_draws'],ordinary['primary_draws'])
        self.assertTrue(combined_run['draws'][PARTIES].sum(axis=1).eq(88).all())
        self.assertTrue((combined_run['concentration_exponents'].to_numpy()>0).all())
        self.assertTrue((combined_run['concentration_exponents'].to_numpy()<2).all())
        pd.testing.assert_frame_equal(combined_run['draws'],simulate(*args,experiment=combined)['draws'])
        # A zero structured budget recovers the same concentration draw with
        # ordinary residual scales disabled, proving no duplicate residual layer.
        no_residual=settings|{'REGION_PRIMARY_SD_PP':0,'SEAT_PRIMARY_SD_PP':0}
        concentration=dict(concentration_log_sd=.3,concentration_form='positive_bounded')
        only=simulate(p,m,params,post,i,target,a,no_residual,experiment=concentration)
        both=simulate(p,m,params,post,i,target,a,no_residual,
                      experiment=concentration|{'structured_nowcast':self.config})
        pd.testing.assert_frame_equal(only['seats'],both['seats'],check_exact=True)
        with self.assertRaises(ValueError):
            simulate(*args,experiment={'structured_nowcast':config,'local_primary_t_df':5})
        # No stochastic scales returns the original deterministic calculator.
        zero={k:0 if '_SD' in k else v for k,v in settings.items()}
        baseline=simulate(p,m,params,post,i,target,a,zero)
        off=simulate(p,m,params,post,i,target,a,zero,experiment={'structured_nowcast':self.config})
        pd.testing.assert_frame_equal(off['seats'],baseline['seats'],check_exact=True)

    def test_transport_works_when_existing_preference_sd_is_zero(self):
        from Tests.test_forecast_engine import calculator_fixture
        from SRC.forecast_engine import simulate
        from SRC.forecast_params import defaults
        _,p,m,params,post,i,a = calculator_fixture()
        target=dict(ALP=24.6,LNP=29.1,GRN=13.3,ON=22,IND=5.5,OTH=5.5)
        settings={k:0 if '_SD' in k else v for k,v in defaults().items()}|{'SIMULATIONS':2}
        r=simulate(p,m,params,post,i,target,a,settings,experiment={
            'structured_nowcast':self.config|{'transport_log_sd':{'special':.5}}})
        self.assertTrue(r['draws'][PARTIES].sum(axis=1).eq(88).all())


if __name__=='__main__':
    unittest.main()
