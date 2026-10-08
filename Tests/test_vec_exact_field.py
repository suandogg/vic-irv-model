import copy
import unittest
from SRC.preference_engine import diagnose_preference_weights
from tools.preference_review_trials import variant
from tools.trial_vec_field_evidence import attach_vec_fields
from SRC.matrix_loader import load_synth_pref_matrices
from tools.validate_vec_field_holdout import pool_fields


class VECExactFieldTests(unittest.TestCase):
    def params(self):
        return {"scalar_params": {"SIPHON_STRENGTH_ON": 0, "TRIAL_NO_FLOOR": True, "THREE_WAY_MAX": 1, "MAJOR_PAIR_MAX": 1}, "on_special_scenario_priors": {}}

    def matrix(self):
        return {"OTH": {"ALP": .1, "LNP": .5, "ON": .4}, "__vec_field_rows__": {"OTH": {"field": ["ALP", "LNP"], "shares": {"ALP": .75, "LNP": .25}, "method": "CANDIDATE_ORIGIN_PASS_THROUGH"}}}

    def test_exact_field_preserves_on_insertion(self):
        matrix = self.matrix()
        before = copy.deepcopy(matrix)
        d = diagnose_preference_weights("OTH", ["ALP", "LNP", "ON"], matrix, "Regional", variant(self.params(), "vec_exact_field"))
        self.assertAlmostEqual(d["final_flows"]["ON"], .4)
        self.assertAlmostEqual(d["final_flows"]["ALP"], .45)
        self.assertTrue(d["stages"][0]["vec_exact_field_matched"])
        self.assertEqual(matrix, before)

    def test_unmatched_field_unchanged(self):
        args = ("OTH", ["ALP", "LNP", "GRN", "ON"], self.matrix(), "Regional")
        p = self.params()
        self.assertEqual(diagnose_preference_weights(*args, p)["final_flows"], diagnose_preference_weights(*args, variant(p, "vec_exact_field"))["final_flows"])

    def test_special_unchanged(self):
        p = self.params()
        p["on_special_scenario_priors"] = {"ALP+ON|OTH|Regional": {"ALP": .53, "ON": .47}}
        m = self.matrix()
        m["__vec_field_rows__"]["OTH"]["field"] = ["ALP"]
        args = ("OTH", ["ALP", "ON"], m, "Regional")
        self.assertEqual(diagnose_preference_weights(*args, p)["final_flows"], diagnose_preference_weights(*args, variant(p, "vec_exact_field"))["final_flows"])

    def test_native_on_fields_excluded_and_original_unchanged(self):
        matrices = load_synth_pref_matrices()
        before = copy.deepcopy(matrices)
        trial = attach_vec_fields(matrices)
        records = [row for m in trial.values() for row in m["matrix"].get("__vec_field_rows__", {}).values()]
        self.assertTrue(records)
        self.assertTrue(all("ON" not in row["field"] for row in records))
        self.assertEqual(matrices, before)

    def test_pool_excludes_held_out_seat(self):
        evidence = {seat: {"matrix": self.matrix()} for seat in ["HELD", "TRAIN"]}
        evidence["HELD"]["matrix"]["__vec_field_rows__"]["OTH"]["shares"] = {"ALP": 0, "LNP": 1}
        row = pool_fields(evidence, "HELD")["OTH"]["ALP+LNP"]
        self.assertEqual(row["training_seats"], ["TRAIN"])
        self.assertEqual(row["shares"], {"ALP": .75, "LNP": .25})

    def test_pool_selected_by_exact_field(self):
        matrix = self.matrix()
        matrix.pop("__vec_field_rows__")
        matrix["__vec_pooled_fields__"] = {"OTH": {"ALP+LNP": {
            "field": ["ALP", "LNP"], "shares": {"ALP": .75, "LNP": .25}, "method": "pool"}}}
        d = diagnose_preference_weights("OTH", ["ALP", "LNP", "ON"], matrix, "Regional", variant(self.params(), "vec_exact_field"))
        self.assertTrue(d["stages"][0]["vec_exact_field_matched"])
        self.assertAlmostEqual(d["final_flows"]["ON"], .4)


if __name__ == "__main__":
    unittest.main()
