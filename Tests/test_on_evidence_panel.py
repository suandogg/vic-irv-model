import copy
import unittest
from SRC.on_evidence_panel import current_on_evidence_rows
from SRC.irv import run_irv_for_district

class EvidencePanelTests(unittest.TestCase):
    def test_audit_is_read_only_and_reports_exact_weight(self):
        votes = {'ALP': .45, 'LNP': .45, 'ON': .1}
        matrix = {p: {q: .5 for q in ['ALP','LNP'] if q != p}
                  for p in ['ALP','LNP','ON']}
        params = {'scalar_params': {}, 'geography_adjustments': {}}
        post = {'ON|ALP+LNP': {'ALP': .2, 'LNP': .8,
            '__federal_on_trial__': True, '__reliability__': .125,
            '__evidence_seats__': 3}}
        inputs = (votes, matrix, 'Regional', params, post, {})
        saved = copy.deepcopy(inputs)
        before = run_irv_for_district(*inputs)
        rows = current_on_evidence_rows(*inputs)
        self.assertEqual(inputs, saved)
        self.assertEqual(run_irv_for_district(*inputs), before)
        self.assertEqual(rows[0]['Federal evidence seats'], 3)
        self.assertEqual(rows[0]['Federal blend weight (%)'], 12.5)

    def test_no_on_calls_returns_empty(self):
        self.assertEqual(current_on_evidence_rows({'ALP': .6, 'LNP': .4}, {},
            'Regional', {'scalar_params': {}}, {}, {}), [])
