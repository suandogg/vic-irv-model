import unittest
import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest
from SRC.constants import PARTIES
from SRC.forecast_engine import simulate
from SRC.forecast_params import defaults
from SRC.legacy_primary_model import build_corrected_primary_table,build_legacy_primary_table
from SRC.oth_scaling import OTH_BASE_SHARE,load_oth_scaling_config,scaled_primary,validate_config
from SRC.primary_pipeline import build_projected_primaries
from Tests.test_forecast_engine import calculator_fixture

TARGETS=dict(ALP=23.68,LNP=29.28,GRN=13.63,ON=22.49,IND=5.46,OTH=5.46)
CONFIG=load_oth_scaling_config()


class OthScalingFormulaTests(unittest.TestCase):
    def test_scales_relative_strength(self):
        self.assertAlmostEqual(scaled_primary(0,.0546,CONFIG),.0546,places=12)
        self.assertAlmostEqual(scaled_primary(-OTH_BASE_SHARE/2,.0546,CONFIG),.0273,places=12)
        self.assertAlmostEqual(scaled_primary(-.069144,.0546,CONFIG),.0546*(OTH_BASE_SHARE-.069144)/OTH_BASE_SHARE,places=12)

    def test_config_is_checked(self):
        with self.assertRaises(ValueError):
            validate_config(dict(CONFIG,party='ALP'))
        with self.assertRaises(ValueError):
            validate_config(dict(CONFIG,base_share=0))


class OthScalingPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,cls.primary,cls.matrices,cls.params,cls.posterior,cls.ideology,cls.adjustments=calculator_fixture()

    def build(self,params):
        return build_projected_primaries(self.primary,params,TARGETS,self.adjustments,collect_diagnostics=False)[0]

    def test_absent_config_keeps_additive_table(self):
        pd.testing.assert_frame_equal(build_legacy_primary_table(self.primary,TARGETS),
                                      build_legacy_primary_table(self.primary,TARGETS,oth_scaling=None))

    def test_no_seat_clips_to_zero_and_totals_hold(self):
        off=self.build(self.params)
        on=self.build(dict(self.params,oth_scaling=CONFIG))
        for seat in ('Ashwood','Narracan'):
            mask=on.district.eq(seat)
            self.assertLess(off.loc[mask,'OTH'].iloc[0],1e-6)
            self.assertGreater(on.loc[mask,'OTH'].iloc[0],.005)
        self.assertGreater(on.OTH.min(),.005)
        np.testing.assert_allclose(on[PARTIES].sum(axis=1),1,atol=1e-12)
        np.testing.assert_allclose(on[PARTIES].mean(),off[PARTIES].mean(),atol=2e-4)

    def test_calibration_hits_target_and_zero_target_stays_zero(self):
        table=build_corrected_primary_table(self.primary,TARGETS,oth_scaling=CONFIG)
        self.assertAlmostEqual(table.OTH.mean(),.0546,places=10)
        absent=dict(TARGETS,OTH=0)
        self.assertEqual(build_corrected_primary_table(self.primary,absent,oth_scaling=CONFIG).OTH.max(),0)

    def run_forecast(self,experiment):
        settings=defaults()|{'SIMULATIONS':2}
        return simulate(self.primary,self.matrices,self.params,self.posterior,self.ideology,TARGETS,
                        self.adjustments,settings,experiment=experiment)

    def test_forecast_accepts_config_and_rejects_bad_one(self):
        result=self.run_forecast({'oth_scaling':CONFIG})
        self.assertEqual(result['experiment']['oth_scaling'],CONFIG)
        with self.assertRaises(ValueError):
            self.run_forecast({'oth_scaling':dict(CONFIG,base_share=2)})


class OthScalingSwitchTests(unittest.TestCase):
    def test_switch_defaults_off_and_runs_central_count(self):
        app=AppTest.from_file('app.py',default_timeout=120).run()
        self.assertEqual(len(app.exception),0)
        self.assertFalse(app.checkbox(key='oth_proportional').value)
        app.checkbox(key='oth_proportional').check().run()
        self.assertEqual(len(app.exception),0)
        self.assertEqual(len(app.error),0)
