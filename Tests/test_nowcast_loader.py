import copy
import unittest
import pandas as pd
from SRC.constants import PARTIES
from SRC.nowcast_loader import RAW,FILES,load_nowcast_inputs,parse_inputs,scale_config


class NowcastLoaderTests(unittest.TestCase):
    def setUp(self):
        self.districts=list(pd.read_csv(RAW/'LEGACY_PRIMARY_INPUTS.csv').district)
        self.tables={k:pd.read_csv(RAW/v,dtype=str,keep_default_na=False) for k,v in FILES.items()}

    def parse(self,tables=None):
        t=self.tables if tables is None else tables
        return parse_inputs(t['budget'],t['correlation'],t['contexts'],self.districts)

    def test_seed_and_complete_roster(self):
        config,review=self.parse()
        self.assertEqual(review['unreviewed_contexts'],88)
        self.assertEqual(review['enabled_contexts'],0)
        self.assertEqual(config['contexts'],{})
        self.assertGreater(config['region_sd_pp']['ALP'],.75)
        self.assertEqual(config['transport_log_sd'],dict(vec=.15,federal=.25,special=.35,generic=.35))
        source_rows=review['budget'].query("Component == 'transport_log_sd'")
        self.assertTrue(source_rows['Evidence status'].eq('JUDGMENT_2026').all())
        actual,_=load_nowcast_inputs(self.districts)
        self.assertEqual(actual,config)

    def test_missing_and_duplicate_inputs_rejected(self):
        for key in self.tables:
            t=copy.deepcopy(self.tables)
            t[key]=t[key].iloc[:-1]
            with self.assertRaises(ValueError):
                self.parse(t)
        t=copy.deepcopy(self.tables)
        t['budget']=pd.concat([t['budget'],t['budget'].iloc[:1]])
        with self.assertRaises(ValueError):
            self.parse(t)

    def test_reviewed_context_required(self):
        self.tables['contexts'].loc[0,'Enabled']='TRUE'
        with self.assertRaises(ValueError):
            self.parse()
        self.tables['contexts'].loc[0,'ReviewStatus']='REVIEWED'
        self.tables['contexts'].loc[0,'Notes']='Known candidate, illustrative strength uncertainty'
        self.tables['contexts'].loc[0,'IND_SD_pp']='5'
        config,review=self.parse()
        self.assertEqual(review['enabled_contexts'],1)
        self.assertEqual(config['contexts'][self.tables['contexts'].loc[0,'District']]['candidate_sd_pp']['IND'],5)

    def test_complete_scaling(self):
        config,_=self.parse()
        config['contexts']={'Example':{'local_multiplier':{p:2 for p in PARTIES},
            'candidate_sd_pp':{p:3 for p in PARTIES},'note':'test'}}
        config['transport_log_sd']['special']=.2
        before=copy.deepcopy(config)
        scaled=scale_config(config,1.5)
        self.assertEqual(config,before)
        self.assertEqual(scaled['contexts']['Example']['candidate_sd_pp']['ALP'],4.5)
        self.assertEqual(scaled['contexts']['Example']['local_multiplier']['ALP'],2)
        self.assertEqual(scaled['correlation'],config['correlation'])
        self.assertAlmostEqual(scaled['transport_log_sd']['special'],.3)
        self.assertAlmostEqual(scaled['local_sd_pp']['ALP'],1.5*config['local_sd_pp']['ALP'])


if __name__=='__main__':
    unittest.main()
