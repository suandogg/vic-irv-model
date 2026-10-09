import copy
import unittest

from SRC.matrix_loader import load_synth_pref_matrices
from SRC.params_loader import load_params
from SRC.oth_matrix_builder import rebuild_oth_matrices
from SRC.vec_field_evidence import attach_vec_fields
from SRC.preference_engine import diagnose_preference_weights


class MainRepairsTest(unittest.TestCase):
    def setUp(self):
        self.original = load_synth_pref_matrices()
        self.params = load_params()
        self.repaired = attach_vec_fields(rebuild_oth_matrices(self.original, self.params))

    def test_only_oth_stored_rows_change(self):
        for seat in self.original:
            for origin, row in self.original[seat]['matrix'].items():
                if origin != 'OTH':
                    self.assertEqual(row, self.repaired[seat]['matrix'][origin])
            row = self.repaired[seat]['matrix']['OTH']
            if sum(row.values()):
                self.assertAlmostEqual(sum(row.values()), 1, delta=0.001)

    def test_exact_field_coverage_and_unmatched_fields(self):
        matched = 0
        for seat, entry in self.repaired.items():
            matrix = entry['matrix']
            for origin, record in matrix.get('__vec_field_rows__', {}).items():
                field = record['field']
                diagnostic = diagnose_preference_weights(origin, field, matrix, 'Inner Ring', self.params)
                raw_stage = next(s for s in diagnostic['stages'] if s['stage'] == 'raw AEC row')
                self.assertTrue(raw_stage['vec_exact_field_matched'])
                self.assertEqual(raw_stage['aec_coverage'], 1)
                other_field = sorted(set(field) ^ {'IND'})
                if other_field and origin not in other_field:
                    other = diagnose_preference_weights(origin, other_field, matrix, 'Inner Ring', self.params)
                    other_raw = next(s for s in other['stages'] if s['stage'] == 'raw AEC row')
                    self.assertFalse(other_raw['vec_exact_field_matched'])
                matched += 1
        self.assertGreater(matched, 100)

    def test_special_priors_unchanged_for_every_seat(self):
        for seat in self.original:
            for origin in ['LNP', 'GRN', 'IND', 'OTH']:
                args = (origin, ['ALP', 'ON'])
                old = diagnose_preference_weights(*args, self.original[seat]['matrix'], 'Inner Ring', self.params)
                new = diagnose_preference_weights(*args, self.repaired[seat]['matrix'], 'Inner Ring', self.params)
                self.assertEqual(old['final_flows'], new['final_flows'])

    def test_inputs_not_mutated(self):
        snapshot = copy.deepcopy(self.original)
        rebuild_oth_matrices(self.original, self.params)
        self.assertEqual(self.original, snapshot)
