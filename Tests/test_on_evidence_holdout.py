import unittest
import pandas as pd
from tools.audit_on_evidence_holdout import validate_source, predict

class HoldoutTests(unittest.TestCase):
    def sample(self):
        return pd.DataFrame([dict(Seat=seat,State="VIC",Eliminated="OTH",AliveSet="ALP+ON",Recipient=p,Share=share,Votes=share*100,ScenarioTotal=100,Method="test",VoteBasis="test",Source="test") for seat,alp in (("A",.2),("B",.8),("C",.6)) for p,share in (("ALP",alp),("ON",1-alp))])

    def test_heldout_values_cannot_affect_training_pool(self):
        raw=self.sample(); validate_source(raw)
        training=raw.loc[~raw.Seat.eq("A")]
        self.assertAlmostEqual(predict(training,["ALP","ON"],"equal_pool")["ALP"],.7)
        raw.loc[raw.Seat.eq("A"),"Share"]=.999
        self.assertAlmostEqual(predict(raw.loc[~raw.Seat.eq("A")],["ALP","ON"],"equal_pool")["ALP"],.7)

    def test_duplicate_or_missing_destinations_rejected(self):
        raw=self.sample()
        with self.assertRaises(ValueError): validate_source(pd.concat([raw,raw.iloc[:1]]))
        with self.assertRaises(ValueError): validate_source(raw.iloc[1:])

    def test_predictors_conserve_probability(self):
        for method in ("uniform","equal_pool","vote_pool","equal_pool_shrunk_uniform_20"):
            result=predict(self.sample(),["ALP","ON"],method)
            self.assertAlmostEqual(sum(result.values()),1)
            self.assertTrue(all(0<=v<=1 for v in result.values()))

if __name__=="__main__": unittest.main()
