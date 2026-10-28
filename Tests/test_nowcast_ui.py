import unittest
from streamlit.testing.v1 import AppTest


SOURCE='''
import pandas as pd
import streamlit as st
from unittest.mock import patch
from Tests.test_forecast_engine import calculator_fixture
from SRC.forecast_ui import render_forecast
from SRC.forecast_params import defaults
from SRC.primary_pipeline import build_projected_primaries,params_for_scenario
from SRC.forecast_engine import forecast_counts
@st.cache_resource
def fixture():
    return calculator_fixture()
_,p,m,params,post,ideology,adjustments=fixture()
targets=dict(ALP=24.2,LNP=30.2,GRN=14.7,ON=21.9,IND=4.5,OTH=4.5)
def central(p,m,params,post,ideology,targets,adjustments,weights):
    adjusted,_=build_projected_primaries(p,params,targets,adjustments)
    return forecast_counts(adjusted,m,params_for_scenario(params,targets),post,ideology),None,None
with patch('SRC.forecast_ui.load_forecast_params',return_value=(defaults()|{'SIMULATIONS':2},'Test settings')):
    render_forecast(p,m,params,post,ideology,targets,adjustments,'Test preference method',
                    {'message':'Local test; no Sheet sync'},central,None)
'''


class NowcastUITests(unittest.TestCase):
    def test_selection_run_and_sensitivity_metadata(self):
        app=AppTest.from_string(SOURCE,default_timeout=30).run()
        self.assertEqual(len(app.exception),0)
        self.assertEqual(app.selectbox(key='forecast_structural_trial').value,'Current')
        app.selectbox(key='forecast_structural_trial').set_value('Structured nowcast (development)').run()
        self.assertEqual(len(app.exception),0)
        self.assertTrue(any('88 unreviewed' in c.value for c in app.caption))
        app.button(key='run_lower_forecast').click().run()
        self.assertEqual(len(app.exception),0)
        self.assertEqual(len(app.error),0)
        stored=app.session_state['lower_forecast_run']
        config=stored['result']['experiment']['structured_nowcast']
        self.assertGreater(config['region_sd_pp']['ALP'],1)
        app.button(key='compare_forecast_uncertainty').click().run()
        self.assertEqual(len(app.exception),0)
        self.assertEqual(len(app.error),0)
        _,comparison=app.session_state['forecast_uncertainty_comparison']
        wider=comparison['Wider (1.5× SD)']['experiment']['structured_nowcast']
        self.assertAlmostEqual(wider['local_sd_pp']['ALP'],config['local_sd_pp']['ALP']*1.5)
        app.selectbox(key='forecast_geographic_trial').set_value('Blend upper-house and sub-regions').run()
        self.assertEqual(len(app.exception),0)
        self.assertTrue(any('changed' in str(x.value).lower() for x in app.info))


if __name__=='__main__':
    unittest.main()
