import copy
import unittest
from SRC.preference_engine import enforce_floor, posterior_reliability
from tools.preference_review_trials import variant
from tools.trial_posterior_reliability import seat_count_trial

class PreferenceReviewTests(unittest.TestCase):
    def test_geography_isolation_preserves_other_inputs(self):
        original={"scalar_params":{"NON_ON_GEOGRAPHY_STRENGTH":.75},"geography_adjustments":{"Rural":{"ALP":-.03,"ON":.04}},"on_special_scenario_priors":{"unchanged":True}}
        on=variant(original,"no_on_recipient_geography")
        other=variant(original,"no_non_on_recipient_geography")
        self.assertEqual(on["geography_adjustments"]["Rural"],{"ALP":-.03,"ON":0})
        self.assertEqual(other["scalar_params"]["NON_ON_GEOGRAPHY_STRENGTH"],0)
        self.assertEqual(other["geography_adjustments"],original["geography_adjustments"])
        self.assertEqual(original["geography_adjustments"]["Rural"]["ON"],.04)

    def test_zero_floor_trial_preserves_zero_destination(self):
        vec=[1.,0.,0.,0.,0.,0.]
        result=enforce_floor(vec,["ALP","LNP"],{"TRIAL_NO_FLOOR":True})
        self.assertEqual(result[1],0.)
        self.assertEqual(sum(result),1.)

    def test_trials_do_not_mutate_special_priors_or_reference(self):
        original={"scalar_params":{},"on_special_scenario_priors":{"ALP+ON|LNP|Regional":{"ALP":.21,"ON":.79}},"geography_adjustments":{"RURAL":{"ON":.04}}}
        saved=copy.deepcopy(original)
        for name in ("no_siphon","no_geography","no_constraints","no_synthetic_priority","simplified"):
            trial=variant(original,name)
            self.assertEqual(trial["on_special_scenario_priors"],saved["on_special_scenario_priors"])
        self.assertEqual(original,saved)

    def test_seat_count_trial_keeps_federal_evidence_and_uses_independent_seats(self):
        source={"ALP|GRN+LNP":{"GRN":.8,"LNP":.2},"ON|ALP+LNP":{"ALP":.2,"LNP":.8,"__federal_on_trial__":True}}
        result=seat_count_trial(source,10)
        self.assertAlmostEqual(posterior_reliability(result["ALP|GRN+LNP"]),2/12)
        self.assertEqual(result["ON|ALP+LNP"],source["ON|ALP+LNP"])
        self.assertNotIn("__trial_reliability_override__",source["ALP|GRN+LNP"])

if __name__=="__main__": unittest.main()
