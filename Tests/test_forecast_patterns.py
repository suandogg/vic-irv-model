import unittest
import numpy as np
from SRC.forecast_patterns import (balance_primary_pattern,strength_contrast,
    centre_region_contrasts,tilt_preference_pattern)


class PatternTests(unittest.TestCase):
    def test_positive_mappings_and_local_matching(self):
        from SRC.forecast_patterns import concentration_pattern
        base = np.array([[.1,.4],[.2,.4],[.4,.4]])
        sd = np.log(base[:,0]).std()
        for form in ('positive_softplus','positive_bounded'):
            tilt,power = concentration_pattern(base,[-4*sd,0],form)
            self.assertTrue((power>0).all())
            self.assertLess(power[0],1)
            initial = base[:,0]*np.exp(tilt[:,0])
            self.assertTrue(np.all(np.diff(initial)>0))
            tilt,power = concentration_pattern(base,[0,0],form)
            np.testing.assert_array_equal(tilt,0)
            np.testing.assert_array_equal(power,1)
            _,power = concentration_pattern(base,[sd*1e-6,0],form)
            self.assertAlmostEqual((power[0]-1)/1e-6,1,places=5)
            x = balance_primary_pattern(base,concentration_pattern(base,[.3,0],form)[0])
            np.testing.assert_allclose(x.sum(axis=0),base.sum(axis=0),atol=1e-9)

    def test_positive_simulation_identity_and_constraints(self):
        from Tests.test_forecast_engine import calculator_fixture
        from SRC.forecast_engine import simulate
        from SRC.forecast_params import defaults
        import pandas as pd
        _,p,m,params,post,i,a = calculator_fixture()
        target = dict(ALP=24.6,LNP=29.1,GRN=13.3,ON=22,IND=5.5,OTH=5.5)
        settings = defaults()|{'SIMULATIONS':2}
        baseline = simulate(p,m,params,post,i,target,a,settings)
        for form in ('positive_softplus','positive_bounded'):
            off = simulate(p,m,params,post,i,target,a,settings,experiment={'concentration_form':form})
            pd.testing.assert_frame_equal(off['draws'],baseline['draws'])
            trial = simulate(p,m,params,post,i,target,a,settings,
                             experiment={'concentration_form':form,'concentration_log_sd':.3})
            self.assertTrue((trial['concentration_exponents']>0).all().all())
            if form=='positive_bounded':
                self.assertTrue((trial['concentration_exponents']<2).all().all())
            pd.testing.assert_frame_equal(trial['primary_draws'],baseline['primary_draws'])

    def test_concentration_exponent_diagnostic(self):
        from SRC.forecast_patterns import concentration_exponents
        base = np.array([[.1,.4],[.2,.4],[.4,.4]])
        sd = np.log(base[:,0]).std()
        np.testing.assert_allclose(concentration_exponents(base,[-2*sd,.5]),[-1,1])
        np.testing.assert_allclose(concentration_exponents(base,[0,0]),[1,1])
    def setUp(self):
        self.base = np.array([[.7,.3,0],[.4,.4,.2],[.2,.5,.3]])

    def test_zero_identity_and_immutable_inputs(self):
        original = self.base.copy()
        x = balance_primary_pattern(self.base,np.zeros_like(self.base))
        np.testing.assert_array_equal(x,self.base)
        x[0,0]=0
        np.testing.assert_array_equal(self.base,original)

    def test_combined_strength_and_regional_conservation(self):
        tilt = strength_contrast(self.base)*np.array([.3,-.2,.5])
        tilt += centre_region_contrasts(['A','A','B'],{'A':[.2,-.1,.4],'B':[-.4,.3,.1]})
        x = balance_primary_pattern(self.base,tilt)
        np.testing.assert_allclose(x.sum(axis=0),self.base.sum(axis=0),atol=1e-9)
        np.testing.assert_allclose(x.sum(axis=1),self.base.sum(axis=1),atol=1e-9)
        self.assertEqual(x[0,2],0)
        self.assertFalse(np.allclose(x,self.base))

    def test_region_weighting_is_by_seat(self):
        x = centre_region_contrasts(['A','A','B'],{'A':[1.,0.],'B':[-1.,2.]})
        np.testing.assert_allclose(x.mean(axis=0),0,atol=1e-15)

    def test_preference_rows_immutable_and_zero_preserved(self):
        row = {'ALP':.6,'LNP':.4,'ON':0.}
        changed = tilt_preference_pattern(row,{'ALP':.3,'ON':1.})
        self.assertAlmostEqual(sum(changed.values()),1)
        self.assertEqual(changed['ON'],0)
        self.assertGreater(changed['ALP'],row['ALP'])
        self.assertEqual(row,{'ALP':.6,'LNP':.4,'ON':0.})
        self.assertEqual(tilt_preference_pattern(row,{}),row)

    def test_invalid_inputs_fail(self):
        with self.assertRaises(ValueError):
            balance_primary_pattern(self.base,np.full_like(self.base,np.nan))
        with self.assertRaises(ValueError):
            tilt_preference_pattern({'ALP':1.},{'ON':.3})
        with self.assertRaises(ValueError):
            tilt_preference_pattern({'ALP':0.},{})

    def test_integrated_patterns_reproducible_and_paired(self):
        from Tests.test_forecast_engine import calculator_fixture
        from SRC.forecast_params import defaults
        from SRC.forecast_engine import simulate,fingerprint
        from SRC.constants import PARTIES
        import pandas as pd
        _,p,m,params,post,i,a = calculator_fixture()
        t = dict(ALP=24.6,LNP=29.1,GRN=13.3,ON=22,IND=5.5,OTH=5.5)
        s = defaults()|{'SIMULATIONS':2}
        before = fingerprint(p,m,params,post,i,a)
        baseline = simulate(p,m,params,post,i,t,a,s)
        e = {'concentration_log_sd':.2,'preference_region_share':.25,'preference_local_share':.25}
        x = simulate(p,m,params,post,i,t,a,s,experiment=e)
        y = simulate(p,m,params,post,i,t,a,s,experiment=e)
        pd.testing.assert_frame_equal(x['draws'],y['draws'])
        pd.testing.assert_frame_equal(x['primary_draws'],baseline['primary_draws'])
        self.assertEqual(before,fingerprint(p,m,params,post,i,a))
        self.assertTrue(x['draws'][PARTIES].sum(axis=1).eq(88).all())
        self.assertTrue(np.any(x['concentration_draws'].to_numpy()!=0))
        off = simulate(p,m,params,post,i,t,a,s,experiment={'concentration_log_sd':0})
        pd.testing.assert_frame_equal(off['draws'],baseline['draws'])
        with self.assertRaises(ValueError):
            simulate(p,m,params,post,i,t,a,s,experiment={'preference_region_share':.8,'preference_local_share':.3})
        with self.assertRaises(ValueError):
            simulate(p,m,params,post,i,t,a,s,experiment={'preference_region_share':.2,'local_preference_mode':'add'})

    def test_regional_flow_shocks_reused(self):
        import pandas as pd
        from SRC.forecast_engine import draw_preference_pattern
        from SRC.constants import PARTIES
        origin = {o:{p:0. for p in PARTIES} for o in PARTIES}
        seats = pd.DataFrame({'district':['A','B','C'],'region':['X','X','Y']})
        x = draw_preference_pattern({'origin':origin},seats,1.,0.,np.random.default_rng(3))
        np.testing.assert_array_equal(x['A'],x['B'])
        self.assertFalse(np.allclose(x['A'],x['C']))

    def test_party_specific_widths(self):
        from Tests.test_forecast_engine import calculator_fixture
        from SRC.forecast_params import defaults
        from SRC.forecast_engine import simulate
        from SRC.constants import PARTIES
        import pandas as pd
        _,p,m,params,post,i,a = calculator_fixture()
        t = dict(ALP=24.6,LNP=29.1,GRN=13.3,ON=22,IND=5.5,OTH=5.5)
        s = defaults()|{'SIMULATIONS':2}
        scalar = simulate(p,m,params,post,i,t,a,s,experiment={'concentration_log_sd':.2})
        vector = simulate(p,m,params,post,i,t,a,s,
                          experiment={'concentration_by_party':dict.fromkeys(PARTIES,.2)})
        pd.testing.assert_frame_equal(scalar['draws'],vector['draws'])
        pd.testing.assert_frame_equal(scalar['concentration_draws'],vector['concentration_draws'])
        one = simulate(p,m,params,post,i,t,a,s,experiment={'concentration_by_party':{'ALP':.2}})
        self.assertTrue((one['concentration_draws'].drop(columns='ALP')==0).all().all())
        self.assertTrue(one['draws'][PARTIES].sum(axis=1).eq(88).all())
        for override in ({'TYPO':.2},{'ON':float('nan')},{'GRN':-1}):
            with self.assertRaises(ValueError):
                simulate(p,m,params,post,i,t,a,s,experiment={'concentration_by_party':override})
