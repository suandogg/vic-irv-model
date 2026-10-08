import copy
import unittest
from SRC.preference_engine import diagnose_preference_weights
from tools.preference_review_trials import variant


class IncompleteAnchorTests(unittest.TestCase):
    def params(self):
        return {"scalar_params": {"SIPHON_STRENGTH_ON": 0, "TRIAL_NO_FLOOR": True, "THREE_WAY_MAX": 1, "MAJOR_PAIR_MAX": 1}, "on_special_scenario_priors": {}}

    def test_incomplete_row_retains_existing_fallback_without_anchor(self):
        p = self.params()
        args = ("OTH", ["ALP", "LNP", "IND"], {"OTH": {"ALP": .3, "LNP": .7}}, "Regional")
        ideology = {"OTH": {"ALP": .2, "LNP": .3, "IND": .5}}
        ref = diagnose_preference_weights(*args, p, {}, ideology)
        trial = diagnose_preference_weights(*args, variant(p, "no_incomplete_matrix_anchor"), {}, ideology)
        self.assertEqual(trial["basis"], ref["basis"])
        self.assertAlmostEqual(trial["final_flows"]["IND"], .5)
        self.assertLess(ref["final_flows"]["IND"], .5)
        self.assertFalse(any(s["stage"] == "AEC anchor blend" for s in trial["stages"]))

    def test_complete_row_unchanged(self):
        p = self.params()
        args = ("OTH", ["ALP", "LNP"], {"OTH": {"ALP": .3, "LNP": .7}}, "Regional")
        self.assertEqual(diagnose_preference_weights(*args, p)["final_flows"], diagnose_preference_weights(*args, variant(p, "no_incomplete_matrix_anchor"))["final_flows"])

    def test_special_unchanged(self):
        p = self.params()
        p["on_special_scenario_priors"] = {"ALP+ON|LNP|Regional": {"ALP": .21, "ON": .79}}
        saved = copy.deepcopy(p)
        args = ("LNP", ["ALP", "ON"], {"LNP": {"ALP": 1}}, "Regional")
        self.assertEqual(diagnose_preference_weights(*args, p)["final_flows"], diagnose_preference_weights(*args, variant(p, "no_incomplete_matrix_anchor"))["final_flows"])
        self.assertEqual(p, saved)


if __name__ == "__main__":
    unittest.main()
