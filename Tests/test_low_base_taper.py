import unittest
import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest
from SRC.constants import PARTIES
from SRC.forecast_engine import perturb_local_primaries,simulate
from SRC.forecast_params import defaults
from SRC.legacy_primary_model import build_corrected_primary_table,build_legacy_primary_table
from SRC.low_base_taper import ALP_BASE_SHARE,error_scale,load_taper_config,tapered_primary,validate_config
from SRC.nowcast_uncertainty import perturb_district_leans
from Tests.test_forecast_engine import calculator_fixture
from SRC.primary_pipeline import build_projected_primaries

TARGETS=dict(ALP=23.68,LNP=29.28,GRN=13.63,ON=22.49,IND=5.46,OTH=5.46)
CONFIG=load_taper_config()


def nowcast(primary):
    return dict(local_sd_pp={'ALP':3.5,'LNP':3.2},region_sd_pp={'ALP':1.3},class_sd_pp={},
                correlation=np.eye(len(PARTIES)).tolist(),contexts={},transport_log_sd={},provenance='test')


class TaperFormulaTests(unittest.TestCase):
    def test_lowest_seat_stays_positive_and_high_seats_stay_additive(self):
        self.assertAlmostEqual(tapered_primary(-.24,.2368,CONFIG),.0733,places=3)
        self.assertAlmostEqual(tapered_primary(.10,.2368,CONFIG),.3368,places=12)

    def test_taper_is_continuous_at_k(self):
        pvi=CONFIG['k']-ALP_BASE_SHARE
        self.assertAlmostEqual(tapered_primary(pvi-1e-9,.2368,CONFIG),.2368+pvi,places=7)

    def test_config_is_checked(self):
        with self.assertRaises(ValueError):
            validate_config(dict(CONFIG,party='LNP'))
        with self.assertRaises(ValueError):
            load_taper_config(0)


class TaperPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,cls.primary,cls.matrices,cls.params,cls.posterior,cls.ideology,cls.adjustments=calculator_fixture()

    def build(self,params,targets=TARGETS):
        return build_projected_primaries(self.primary,params,targets,self.adjustments,collect_diagnostics=False)[0]

    def test_absent_config_keeps_additive_table(self):
        pd.testing.assert_frame_equal(build_legacy_primary_table(self.primary,TARGETS),
                                      build_legacy_primary_table(self.primary,TARGETS,low_base_taper=None))

    def test_taper_lifts_clipped_seats_and_keeps_totals(self):
        off=self.build(self.params)
        on=self.build(dict(self.params,low_base_taper=CONFIG))
        shepparton=on.district.eq('Shepparton')
        self.assertLess(off.loc[shepparton,'ALP'].iloc[0],1e-6)
        self.assertGreater(on.loc[shepparton,'ALP'].iloc[0],.03)
        np.testing.assert_allclose(on[PARTIES].sum(axis=1),1,atol=1e-12)
        np.testing.assert_allclose(on[PARTIES].mean(),off[PARTIES].mean(),atol=2e-4)

    def test_calibration_hits_targets_and_zero_target_stays_zero(self):
        table=build_corrected_primary_table(self.primary,TARGETS,low_base_taper=CONFIG)
        self.assertAlmostEqual(table.ALP.mean(),.2368,places=10)
        absent=dict(TARGETS,OTH=0)
        self.assertEqual(build_corrected_primary_table(self.primary,absent,low_base_taper=CONFIG).OTH.max(),0)

    def test_error_taper_scales_only_alp_and_keeps_stream(self):
        table=self.build(dict(self.params,low_base_taper=CONFIG))
        config=nowcast(self.primary)
        _,plain=perturb_district_leans(table,config,np.random.default_rng(3))
        result,tapered=perturb_district_leans(table,config,np.random.default_rng(3),low_base_taper=CONFIG)
        column=PARTIES.index('ALP')
        np.testing.assert_allclose(tapered[:,column],plain[:,column]*error_scale(table.ALP.to_numpy(),CONFIG))
        others=[i for i in range(len(PARTIES)) if i!=column]
        np.testing.assert_array_equal(tapered[:,others],plain[:,others])
        self.assertGreater(result.ALP.min(),1e-4)
        np.testing.assert_allclose(result[PARTIES].sum(axis=1),1,atol=1e-9)

    def test_local_noise_path_uses_the_taper(self):
        table=self.build(dict(self.params,low_base_taper=CONFIG))
        tapered=perturb_local_primaries(table,defaults(),np.random.default_rng(4),low_base_taper=CONFIG)
        self.assertGreater(tapered.ALP.min(),1e-4)

    def run_forecast(self,experiment):
        settings=defaults()|{'SIMULATIONS':2}
        return simulate(self.primary,self.matrices,self.params,self.posterior,self.ideology,TARGETS,
                        self.adjustments,settings,experiment=experiment)

    def test_forecast_accepts_taper_and_rejects_bad_config(self):
        result=self.run_forecast({'low_base_taper':CONFIG})
        self.assertEqual(result['experiment']['low_base_taper'],CONFIG)
        self.assertGreater(result['primary_extremes']['ALP min (%)'].min(),.01)
        with self.assertRaises(ValueError):
            self.run_forecast({'low_base_taper':dict(CONFIG,k=2)})


class TaperSwitchTests(unittest.TestCase):
    def test_switch_defaults_off_and_runs_central_count(self):
        app=AppTest.from_file('app.py',default_timeout=120).run()
        self.assertEqual(len(app.exception),0)
        self.assertFalse(app.checkbox(key='alp_low_base_taper').value)
        app.checkbox(key='alp_low_base_taper').check().run()
        self.assertEqual(len(app.exception),0)
        self.assertEqual(len(app.error),0)
