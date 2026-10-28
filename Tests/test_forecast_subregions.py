import unittest
import numpy as np
import pandas as pd
from SRC.forecast_subregions import validate_subregions,load_subregions
from SRC.forecast_engine import perturb_local_primaries,simulate
from SRC.forecast_params import defaults
from SRC.constants import PARTIES
from Tests.test_forecast_engine import calculator_fixture
from SRC.primary_pipeline import build_projected_primaries


class SubregionTests(unittest.TestCase):
    def test_mapping_validation(self):
        raw = pd.DataFrame({'District':[' A ','b'],'Proposed sub-region':['X','Y']})
        x = validate_subregions(raw,['A','B'])
        self.assertEqual(x.district.tolist(),['A','B'])
        self.assertEqual(x.subregion.tolist(),['X','Y'])
        for bad in (raw.iloc[:1],pd.concat([raw,raw.iloc[:1]]),
                    raw.assign(**{'Proposed sub-region':['X','']})):
            with self.assertRaises(ValueError):
                validate_subregions(bad,['A','B'])

    def test_live_schema_and_snapshot_coverage(self):
        p = pd.read_csv('data/raw/LEGACY_PRIMARY_INPUTS.csv')
        mapping,_ = load_subregions(list(p.district))
        self.assertEqual(len(mapping),88)
        self.assertEqual(mapping.subregion.nunique(),25)

    def test_crossed_groups_balance_and_pair(self):
        _,p,m,params,post,i,a = calculator_fixture()
        targets = dict(ALP=24.6,LNP=29.1,GRN=13.3,ON=22,IND=5.5,OTH=5.5)
        mapping,_ = load_subregions(list(p.district))
        groups = dict(zip(mapping.district,mapping.subregion))
        base,_ = build_projected_primaries(p,params,targets,a)
        for fraction in (.5,1.):
            x = perturb_local_primaries(base,defaults(),np.random.default_rng(1),
                subregions=groups,subregion_fraction=fraction,subregion_rng=np.random.default_rng(2))
            np.testing.assert_allclose(x[PARTIES].sum(),base[PARTIES].sum(),atol=1e-9)
            np.testing.assert_allclose(x[PARTIES].sum(axis=1),base[PARTIES].sum(axis=1),atol=1e-9)
            self.assertTrue((x[PARTIES].to_numpy()[base[PARTIES].to_numpy()==0]==0).all())
        s = defaults()|{'SIMULATIONS':2}
        baseline = simulate(p,m,params,post,i,targets,a,s)
        trial = simulate(p,m,params,post,i,targets,a,s,
                         experiment={'subregion_fraction':.5},subregions=groups)
        repeat = simulate(p,m,params,post,i,targets,a,s,
                          experiment={'subregion_fraction':.5},subregions=groups)
        pd.testing.assert_frame_equal(trial['draws'],repeat['draws'])
        pd.testing.assert_frame_equal(trial['primary_draws'],baseline['primary_draws'])
        zero = {k:0 if '_SD' in k else v for k,v in s.items()}
        x = simulate(p,m,params,post,i,targets,a,zero)
        y = simulate(p,m,params,post,i,targets,a,zero,
                     experiment={'subregion_fraction':1.},subregions=groups)
        pd.testing.assert_frame_equal(x['draws'],y['draws'])
        with self.assertRaises(ValueError):
            simulate(p,m,params,post,i,targets,a,s,experiment={'subregion_fraction':1.})
