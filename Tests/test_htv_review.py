import unittest
from streamlit.testing.v1 import AppTest
from SRC.constants import PARTIES
from SRC.forecast_engine import simulate
from SRC.forecast_params import defaults
from SRC.htv_deal import apply_htv_deal, load_htv_deal_config, shift_flows
from SRC.htv_review import (GREENS_SEATS, apply_htv_review, load_htv_review_config, seat_rules,
                            validate_config)
from SRC.irv import distribute_parcel_holder, initialise_parcels, parcel_totals
from SRC.preference_engine import diagnose_preference_weights
from Tests.test_forecast_engine import calculator_fixture

TARGETS=dict(ALP=23.68,LNP=29.28,GRN=13.63,ON=22.49,IND=5.46,OTH=5.46)
CONFIG=load_htv_review_config()


class ReviewRuleTests(unittest.TestCase):
    def test_seat_rules(self):
        self.assertEqual(seat_rules('MELBOURNE','Inner Ring',CONFIG),{'ON':('ALP','GRN',.725,'share')})
        self.assertIn('ON',seat_rules('BOX HILL','Middle ring',CONFIG))
        self.assertNotIn('ON',seat_rules('WERRIBEE','Peri-urban',CONFIG))
        self.assertEqual(seat_rules('WERRIBEE','Peri-urban',CONFIG),{'GRN':('ALP','LNP',.03,'points')})
        self.assertEqual(len(GREENS_SEATS),15)
        self.assertEqual(seat_rules('CAULFIELD','Middle Ring',CONFIG)['ALP'][:2],('LNP','GRN'))
        self.assertAlmostEqual(CONFIG['labor_open_shift'],load_htv_deal_config()['prahran_shift'],places=12)
        self.assertNotIn('GRN',seat_rules('ALBERT PARK','Inner Ring',load_htv_review_config(greens_points=0)))

    def test_share_and_points_keep_pair_total_and_others(self):
        share={'__htv_shift__':{'ON':('ALP','GRN',.725,'share')}}
        flows=shift_flows({'ALP':.2,'GRN':.2,'LNP':.6},'ON',share)
        self.assertAlmostEqual(flows['ALP'],.29,places=12)
        self.assertAlmostEqual(flows['GRN'],.11,places=12)
        self.assertEqual(flows['LNP'],.6)
        points={'__htv_shift__':{'GRN':('ALP','LNP',.03,'points')}}
        flows=shift_flows({'ALP':.8,'LNP':.1,'ON':.1},'GRN',points)
        self.assertAlmostEqual(flows['ALP']/(flows['ALP']+flows['LNP']),8/9-.03,places=12)
        self.assertAlmostEqual(flows['ALP']+flows['LNP'],.9,places=12)
        self.assertEqual(flows['ON'],.1)
        self.assertEqual(shift_flows({'ALP':.7,'ON':.3},'GRN',points),{'ALP':.7,'ON':.3})

    def test_config_is_checked(self):
        for bad in (dict(CONFIG,on_target=.3),dict(CONFIG,greens_points=.5),dict(CONFIG,extra=1)):
            with self.assertRaises(ValueError):
                validate_config(bad)


class ReviewEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,cls.primary,cls.matrices,cls.params,cls.posterior,cls.ideology,cls.adjustments=calculator_fixture()
        cls.both=apply_htv_review(apply_htv_deal(cls.matrices,load_htv_deal_config()),CONFIG)

    def flows(self,matrices,seat,elim,alive):
        return diagnose_preference_weights(elim,alive,matrices[seat]['matrix'],matrices[seat]['seat_type'],
                                           self.params,self.posterior,self.ideology)['final_flows']

    def test_source_rows_unchanged_idempotent_and_order_free(self):
        reviewed=apply_htv_review(self.matrices,CONFIG)
        self.assertNotIn('__htv_shift__',self.matrices['MELBOURNE']['matrix'])
        again=apply_htv_review(reviewed,CONFIG)
        self.assertEqual(again['CAULFIELD']['matrix']['__htv_shift__'],reviewed['CAULFIELD']['matrix']['__htv_shift__'])
        other=apply_htv_deal(apply_htv_review(self.matrices,CONFIG),load_htv_deal_config())
        for seat in ('MELBOURNE','PRAHRAN','CAULFIELD','WERRIBEE'):
            self.assertEqual(other[seat]['matrix']['__htv_shift__'],self.both[seat]['matrix']['__htv_shift__'])
        self.assertEqual(set(self.both['MELBOURNE']['matrix']['__htv_shift__']),{'LNP','ON'})

    def test_one_nation_pair_share_is_target(self):
        for alive in (['ALP','GRN'],['ALP','GRN','LNP'],['ALP','GRN','LNP','OTH']):
            f=self.flows(self.both,'MELBOURNE','ON',alive)
            self.assertAlmostEqual(f['ALP']/(f['ALP']+f['GRN']),.725,places=9)
            self.assertAlmostEqual(sum(f.values()),1,places=9)
        self.assertEqual(self.flows(self.both,'WERRIBEE','ON',['ALP','GRN']),
                         self.flows(self.matrices,'WERRIBEE','ON',['ALP','GRN']))

    def test_one_nation_voters_final_split_equals_target(self):
        for seat,votes in (('MELBOURNE',dict(ALP=28,GRN=34,LNP=9,ON=14,IND=5,OTH=10)),
                           ('NORTHCOTE',dict(ALP=30,GRN=30,LNP=14,ON=11,IND=5,OTH=10))):
            item=self.both[seat]; parcels=initialise_parcels(votes); alive=list(PARTIES)
            while len(alive)>2:
                totals=parcel_totals(parcels); out=min(alive,key=lambda p:totals[p])
                alive=[p for p in alive if p!=out]
                distribute_parcel_holder(parcels,out,alive,item['matrix'],item['seat_type'],
                                         self.params,self.posterior,self.ideology)
            self.assertEqual(set(alive),{'ALP','GRN'})
            on=parcels['ALP']['ON']/(parcels['ALP']['ON']+parcels['GRN']['ON'])
            self.assertAlmostEqual(on,.725,places=9)

    def test_greens_open_card_only_against_coalition(self):
        before=self.flows(self.matrices,'ALBERT PARK','GRN',['ALP','LNP'])
        after=self.flows(self.both,'ALBERT PARK','GRN',['ALP','LNP'])
        self.assertAlmostEqual(after['ALP'],before['ALP']-.03,places=9)
        self.assertEqual(self.flows(self.both,'ALBERT PARK','GRN',['ALP','ON']),
                         self.flows(self.matrices,'ALBERT PARK','GRN',['ALP','ON']))
        self.assertEqual(self.flows(self.both,'MELBOURNE','GRN',['ALP','LNP']),
                         self.flows(self.matrices,'MELBOURNE','GRN',['ALP','LNP']))

    def test_caulfield_labor_flow_leans_less_to_greens(self):
        before=self.flows(self.matrices,'CAULFIELD','ALP',['GRN','LNP'])
        after=self.flows(self.both,'CAULFIELD','ALP',['GRN','LNP'])
        self.assertLess(after['GRN'],before['GRN'])

    def test_forecast_accepts_config_and_rejects_bad_one(self):
        settings=defaults()|{'SIMULATIONS':2}
        run=lambda e:simulate(self.primary,self.matrices,self.params,self.posterior,self.ideology,TARGETS,
                              self.adjustments,settings,experiment=e)
        self.assertEqual(run({'htv_review':CONFIG})['experiment']['htv_review'],CONFIG)
        with self.assertRaises(ValueError):
            run({'htv_review':dict(CONFIG,on_target=2)})


class ReviewSwitchTests(unittest.TestCase):
    def test_switch_defaults_off_and_runs_central_count(self):
        app=AppTest.from_file('app.py',default_timeout=120).run()
        self.assertEqual(len(app.exception),0)
        self.assertFalse(app.checkbox(key='htv_review_2026').value)
        app.checkbox(key='htv_review_2026').check().run()
        self.assertEqual(len(app.exception),0)
