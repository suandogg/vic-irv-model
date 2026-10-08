import unittest
from SRC.preference_engine import diagnose_preference_weights

class SingleBaselineTests(unittest.TestCase):
    def params(self):
        return {"scalar_params":{"TRIAL_SINGLE_ON_BASELINE":True,"TRIAL_NO_FLOOR":True,"MAJOR_PAIR_MAX":1,"THREE_WAY_MAX":1,"IND_OTH_MAX":1},"geography_adjustments":{"Rural":{"ON":.3}},"on_special_scenario_priors":{}}

    def test_single_matrix_not_posterior_or_geography(self):
        d=diagnose_preference_weights("OTH",["ALP","LNP","ON"],{"OTH":{"ALP":.2,"LNP":.5,"ON":.3}},"Regional",self.params(),{"OTH|ALP+LNP+ON":{"ALP":.9,"ON":.1}},{})
        self.assertEqual(d["basis"],"single synthetic ON baseline")
        self.assertAlmostEqual(d["final_flows"]["ON"],.3)
        self.assertFalse(any(s["stage"]=="final ON siphon" for s in d["stages"]))

    def test_special_locked_even_if_future_federal_record_matches(self):
        params=self.params(); params["on_special_scenario_priors"]={"ALP+ON|LNP|Regional":{"ALP":.21,"ON":.79}}
        post={"LNP|ALP+ON":{"ALP":1,"ON":0,"__federal_on_trial__":True,"__reliability__":1}}
        d=diagnose_preference_weights("LNP",["ALP","ON"],{"LNP":{"ALP":.8,"ON":.2}},"Regional",params,post,{})
        self.assertEqual(d["basis"],"ON special prior")
        self.assertAlmostEqual(d["final_flows"]["ON"],.79)

    def test_exact_federal_blend_retained(self):
        post={"OTH|ALP+LNP+ON":{"ALP":.4,"LNP":.4,"ON":.2,"__federal_on_trial__":True,"__reliability__":.5}}
        d=diagnose_preference_weights("OTH",["ALP","LNP","ON"],{"OTH":{"ALP":.2,"LNP":.5,"ON":.3}},"Regional",self.params(),post,{})
        self.assertEqual(d["basis"],"federal ON evidence trial")
        self.assertAlmostEqual(d["final_flows"]["ON"],.25)

    def test_non_on_round_unchanged(self):
        params=self.params(); plain=self.params(); plain["scalar_params"]["TRIAL_SINGLE_ON_BASELINE"]=False
        args=("OTH",["ALP","LNP"],{"OTH":{"ALP":.2,"LNP":.8}},"Regional")
        self.assertEqual(diagnose_preference_weights(*args,params)["final_flows"],diagnose_preference_weights(*args,plain)["final_flows"])

if __name__=="__main__": unittest.main()
