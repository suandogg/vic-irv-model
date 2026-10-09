import copy
import unittest

from SRC.matrix_loader import load_synth_pref_matrices
from SRC.params_loader import load_params
from SRC.oth_matrix_builder import rebuild_oth_matrices


class OthMatrixBuilderTests(unittest.TestCase):
    def test_repair_is_scoped_normalized_and_idempotent(self):
        original = load_synth_pref_matrices()
        snapshot = copy.deepcopy(original)
        params = load_params()
        params_snapshot = copy.deepcopy(params)
        repaired = rebuild_oth_matrices(original, params)
        changed = [s for s in original if original[s] != repaired[s]]
        self.assertEqual(len(changed), 80)
        for seat in changed:
            self.assertAlmostEqual(sum(repaired[seat]['matrix']['OTH'].values()), 1)
            for party in original[seat]['matrix']:
                if party != 'OTH':
                    self.assertEqual(original[seat]['matrix'][party], repaired[seat]['matrix'][party])
        narracan = next(s for s in original if s.casefold() == 'narracan')
        self.assertEqual(original[narracan], repaired[narracan])
        self.assertEqual(original, snapshot)
        self.assertEqual(params, params_snapshot)
        self.assertEqual(rebuild_oth_matrices(repaired, params), repaired)

    def test_invalid_prior_rejected(self):
        params = load_params()
        params['on_column_prior']['OTH']['Inner Ring'] = 1.1
        with self.assertRaises(ValueError):
            rebuild_oth_matrices(load_synth_pref_matrices(), params)
