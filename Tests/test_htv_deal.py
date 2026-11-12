import math
import unittest
from streamlit.testing.v1 import AppTest
from SRC.constants import PARTIES
from SRC.forecast_engine import simulate
from SRC.forecast_params import defaults
from SRC.htv_deal import apply_htv_deal,liberal_shift_from_evidence,load_htv_deal_config,seat_shifts,shift_flows,validate_config
from SRC.preference_engine import diagnose_preference_weights
from Tests.test_forecast_engine import calculator_fixture

TARGETS=dict(ALP=23.68,LNP=29.28,GRN=13.63,ON=22.49,IND=5.46,OTH=5.46)
CONFIG=load_htv_deal_config()
LIBERAL_SHIFT=liberal_shift_from_evidence()
logit=lambda p:math.log(p/(1-p))


class DealRuleTests(unittest.TestCase):
    def test_seat_rules(self):
        self.assertEqual(seat_shifts('MELBOURNE',CONFIG)['LNP'][:2],('ALP','GRN'))
        self.assertNotIn('LNP',seat_shifts('FOOTSCRAY',CONFIG))
        self.assertNotIn('LNP',seat_shifts('Brunswick',CONFIG))
        self.assertEqual(seat_shifts('PRAHRAN',CONFIG)['ALP'][:2],('LNP','GRN'))
        self.assertNotIn('ALP',seat_shifts('RICHMOND',CONFIG))

    def test_shift_keeps_pair_total_and_other_shares(self):
        matrix={'__htv_shift__':{'LNP':('ALP','GRN',LIBERAL_SHIFT)}}
        flows=shift_flows({'ALP':.30,'GRN':.60,'ON':.10},'LNP',matrix)
        self.assertAlmostEqual(flows['ALP']+flows['GRN'],.90,places=12)
        self.assertEqual(flows['ON'],.10)
        self.assertAlmostEqual(logit(flows['ALP']/.9)-logit(1/3),LIBERAL_SHIFT,places=9)
        self.assertEqual(shift_flows({'ALP':.7,'ON':.3},'LNP',matrix),{'ALP':.7,'ON':.3})

    def test_shift_comes_from_clean_vec_pairs_only(self):
        import pandas as pd
        from SRC.htv_deal import EVIDENCE
        rows=pd.read_csv(EVIDENCE)
        clean=rows[rows.origin.eq('LNP')&rows.method.eq('distribution')]
        self.assertEqual(sorted(clean.District),['Brunswick','Melbourne','Northcote'])
        self.assertAlmostEqual(LIBERAL_SHIFT,clean.logit_change.mean(),places=12)
        self.assertAlmostEqual(LIBERAL_SHIFT,.9006,places=3)
        self.assertAlmostEqual(CONFIG['prahran_shift'],LIBERAL_SHIFT/2,places=12)

    def test_seat_specific_shifts(self):
        seats=CONFIG['seat_liberal_shifts']
        self.assertAlmostEqual(seats['MELBOURNE'],.938819,places=6)
        import pandas as pd
        from SRC.htv_deal import EVIDENCE
        rows=pd.read_csv(EVIDENCE).set_index('District')
        for seat in ('Pascoe Vale','Preston'):
            own=rows.loc[seat,'logit_change']
            self.assertAlmostEqual(seats[seat.upper()],(own+LIBERAL_SHIFT)/2,places=6)
            self.assertGreater(seats[seat.upper()],LIBERAL_SHIFT)
        self.assertEqual(seat_shifts('RICHMOND',CONFIG)['LNP'][2],LIBERAL_SHIFT)
        self.assertEqual(seat_shifts('PRESTON',CONFIG)['LNP'][2],seats['PRESTON'])
        flat=load_htv_deal_config(seat_specific=False)
        self.assertEqual(seat_shifts('PRESTON',flat)['LNP'][2],LIBERAL_SHIFT)

    def test_config_is_checked(self):
        with self.assertRaises(ValueError):
            validate_config(dict(CONFIG,liberal_shift=-1))
        with self.assertRaises(ValueError):
            validate_config(dict(CONFIG,extra=1))


class DealEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,cls.primary,cls.matrices,cls.params,cls.posterior,cls.ideology,cls.adjustments=calculator_fixture()

    def flows(self,matrices,seat,elim,alive):
        return diagnose_preference_weights(elim,alive,matrices[seat]['matrix'],'Inner Ring',
                                           self.params,self.posterior,self.ideology)['final_flows']

    def test_source_rows_unchanged_and_idempotent(self):
        dealt=apply_htv_deal(self.matrices,CONFIG)
        self.assertNotIn('__htv_shift__',self.matrices['MELBOURNE']['matrix'])
        self.assertEqual(dealt['MELBOURNE']['matrix']['LNP'],self.matrices['MELBOURNE']['matrix']['LNP'])
        again=apply_htv_deal(dealt,CONFIG)
        self.assertEqual(again['MELBOURNE']['matrix']['__htv_shift__'],dealt['MELBOURNE']['matrix']['__htv_shift__'])

    def test_engine_moves_liberal_flow_to_labor_except_brunswick(self):
        dealt=apply_htv_deal(self.matrices,CONFIG)
        before=self.flows(self.matrices,'MELBOURNE','LNP',['ALP','GRN'])
        after=self.flows(dealt,'MELBOURNE','LNP',['ALP','GRN'])
        self.assertGreater(after['ALP'],before['ALP']+.15)
        self.assertAlmostEqual(sum(after.values()),1,places=12)
        self.assertEqual(self.flows(dealt,'BRUNSWICK','LNP',['ALP','GRN']),
                         self.flows(self.matrices,'BRUNSWICK','LNP',['ALP','GRN']))

    def test_prahran_labor_flow_leans_less_to_greens(self):
        dealt=apply_htv_deal(self.matrices,CONFIG)
        before=self.flows(self.matrices,'PRAHRAN','ALP',['GRN','LNP'])
        after=self.flows(dealt,'PRAHRAN','ALP',['GRN','LNP'])
        self.assertLess(after['GRN'],before['GRN'])

    def run_forecast(self,experiment):
        settings=defaults()|{'SIMULATIONS':2}
        return simulate(self.primary,self.matrices,self.params,self.posterior,self.ideology,TARGETS,
                        self.adjustments,settings,experiment=experiment)

    def test_forecast_accepts_config_and_rejects_bad_one(self):
        result=self.run_forecast({'htv_deal':CONFIG})
        self.assertEqual(result['experiment']['htv_deal'],CONFIG)
        with self.assertRaises(ValueError):
            self.run_forecast({'htv_deal':dict(CONFIG,liberal_shift=9)})


class DealSwitchTests(unittest.TestCase):
    def test_switch_defaults_off_and_runs_central_count(self):
        app=AppTest.from_file('app.py',default_timeout=120).run()
        self.assertEqual(len(app.exception),0)
        self.assertFalse(app.checkbox(key='htv_deal_2026').value)
        app.checkbox(key='htv_deal_2026').check().run()
        self.assertEqual(len(app.exception),0)
        self.assertEqual(len(app.error),0)
