import copy
import unittest
from SRC.matrix_loader import load_synth_pref_matrices
from SRC.params_loader import load_params
from tools.trial_oth_matrix_rebuild import rebuild_oth_matrices


class OTHRebuildTests(unittest.TestCase):
    def test_only_eighty_oth_rows_change_and_inputs_untouched(self):
        matrices = load_synth_pref_matrices()
        params = load_params()
        before, settings = copy.deepcopy(matrices), copy.deepcopy(params)
        trial = rebuild_oth_matrices(matrices, params)
        changed = 0
        for seat, record in matrices.items():
            for origin, row in record["matrix"].items():
                if trial[seat]["matrix"][origin] != row:
                    self.assertEqual(origin, "OTH")
                    changed += 1
        self.assertEqual(changed, 80)
        self.assertEqual(matrices, before)
        self.assertEqual(params, settings)
        self.assertAlmostEqual(trial["PAKENHAM"]["matrix"]["OTH"]["ON"], .5)
        self.assertEqual(trial["MORWELL"], matrices["MORWELL"])
        self.assertEqual(trial["NARRACAN"], matrices["NARRACAN"])


if __name__ == "__main__":
    unittest.main()
