import os,unittest
from SRC.model_version import legacy_mode
@unittest.skipIf(legacy_mode(),'Final defaults deliberately bypassed in legacy mode')
class V7Defaults(unittest.TestCase):
 def test_approved_profile_and_retention(self):
  from SRC.params_loader import load_params
  from SRC.candidate_field import load_field_config
  from SRC.final_profile import KEY,PROFILE_ID,CONFIG
  self.assertEqual(load_params()[KEY],PROFILE_ID)
  self.assertEqual(load_field_config()['residual_retention'],1.)
  self.assertEqual(len(CONFIG['groups']),7)
  self.assertEqual(CONFIG['groups'][6]['applied_strength'],.5)
 def test_Werribee_has_five_separate_minor_nominees(self):
  from SRC.final_profile import allocation
  rows=allocation().rosters['Werribee'];self.assertEqual(len(rows),5)
  self.assertTrue(all(r['candidate']!='OTH' for r in rows))
 def test_named_candidate_source_matches_frozen_v6_inputs(self):
  import json,hashlib
  from pathlib import Path
  root=Path(__file__).resolve().parents[1]
  original=json.loads((root/'reports/v6_engine_port_2026-11-25/exact_match.json').read_text())['native_source_and_input_sha256']
  for name,sha in original.items():
   if name.startswith(('data/raw/','data/development/')):
    self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),sha,name)
