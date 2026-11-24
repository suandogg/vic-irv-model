import os,sys,unittest,json,tempfile
from pathlib import Path
from unittest.mock import patch,MagicMock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from SRC.params_loader import load_params
from SRC.release_defaults import LNP_ON_TARGETS,PREFERENCE_OFFSETS,target_flows,offset_flows,TARGET_KEY,OFFSET_KEY
from SRC.forecast_params import load_forecast_params,defaults,validate
from SRC.model_version import legacy_mode

class NativeV6Tests(unittest.TestCase):
 def test_native_defaults_and_special_prior(self):
  self.assertFalse(legacy_mode());p=load_params();self.assertEqual(p['scalar_params']['ON alpha'],.8)
  self.assertEqual(p[OFFSET_KEY]['by_donor'],PREFERENCE_OFFSETS)
  for cls in ('Inner Ring','Middle Ring','Outer Metro'):self.assertEqual(p['on_special_scenario_priors'][f'LNP+ON|ALP|{cls}']['ON'],.221)
  self.assertEqual(p['scalar_params']['AEC_ANCHOR_WHEN_MISS'],p['scalar_params']['AEC_ANCHOR_WHEN_MISSING'])
 def test_card_exceptions_and_context_targets(self):
  f={'ALP':.7,'ON':.2,'GRN':.1}
  for seat,factor in [('GREENVALE',0),('PRESTON',0),('BRUNSWICK',.5),('FOOTSCRAY',.5),('MELBOURNE',1)]:
   out=target_flows(f,'LNP','Inner Ring',{'__district__':seat},LNP_ON_TARGETS)
   self.assertAlmostEqual(out['ON'],.2+factor*(.511139-.2));self.assertAlmostEqual(out['ALP']/out['GRN'],7)
  self.assertEqual(target_flows(f,'LNP','Regional',{},LNP_ON_TARGETS),f)
 def test_regional_offsets_keep_other_recipient_ratios(self):
  p=load_params()
  for donor,delta in PREFERENCE_OFFSETS.items():
   f={'ON':.4,'ALP':.2,'LNP':.4};out=offset_flows(f,donor,'Peri-urban',p[OFFSET_KEY]);self.assertLess(out['ON'],.4);self.assertAlmostEqual(out['ALP']/out['LNP'],.5)
   self.assertEqual(offset_flows(f,donor,'Inner Ring',p[OFFSET_KEY]),f)
 def test_input_corrections(self):
  import pandas as pd
  from SRC.legacy_primary_loader import load_legacy_primary_inputs
  from SRC.seat_adjustments_loader import load_lower_seat_adjustments
  from SRC.candidate_field import load_field_config
  from SRC.lnp_precollapse_loader import load_lnp_precollapse_inputs
  # Read through the same validated native loaders; no Sheet writes.
  primary=load_legacy_primary_inputs().set_index('district');self.assertEqual(primary.loc['Ringwood','held_by'],'ALP');self.assertAlmostEqual(primary.loc['Narracan','ALP_pvi'],-.111432)
  text=(ROOT/'data/raw/LOWER_LNP_PRECOLLAPSE.csv').read_text();self.assertIn('4.9751%',text);self.assertIn('2.6789%',text)
  reviewed=pd.read_csv(ROOT/'data/development/candidate_field/REVIEWED_CANDIDATES.csv');row=reviewed[reviewed.iloc[:,0].eq('Hawthorn')].iloc[0];self.assertIn('17.183',row.astype(str).to_list())
 def test_native_uncertainty_and_draw_limit(self):
  settings,_=load_forecast_params();self.assertEqual(settings['STATEWIDE_SD_ALP_PP'],2.58324923279813);self.assertEqual(defaults()['STATEWIDE_SD_ON_PP'],2.134003178186207);self.assertEqual(validate(dict(settings,SIMULATIONS=50000))['SIMULATIONS'],50000)
 def test_registered_cards(self):
  from SRC.htv_deal import load_htv_deal_config
  from SRC.htv_review import load_htv_review_config
  d=load_htv_deal_config();self.assertEqual(d['exceptions'],[]);self.assertGreater(d['seat_liberal_shifts']['BRUNSWICK'],0)
  r=load_htv_review_config();self.assertTrue({'Eureka','Hawthorn','Morwell'}.issubset(r['greens_seats']));self.assertIn('Albert Park',r['labor_open_seats'])
 def test_sync_never_writes_protected_csv(self):
  import SRC.live_sheet_sync as s
  protected=json.loads((ROOT/'data/v6_protected_inputs.json').read_text())
  sheet=MagicMock();sheet.worksheets.return_value=[MagicMock(title='PARAMS')];client=MagicMock();client.open_by_key.return_value=sheet
  with patch.object(s,'resolve_credentials',return_value=object()),patch.object(s.gspread,'authorize',return_value=client),patch.object(s,'worksheet_to_dataframe') as read:
   result=s.sync_inputs_from_google_sheet(only_tabs={'PARAMS'});read.assert_not_called();self.assertEqual(result['synced'],0);self.assertIn('PARAMS',result['skipped'])
 def test_exact_1000_draw_receipt(self):
  r=json.loads((ROOT/'reports/v6_engine_port_2026-11-25/exact_match.json').read_text());self.assertTrue(r['passed']);self.assertEqual(r['different_seats'],[]);self.assertEqual(r['draws'],1000)
  import hashlib
  for name,checksum in r['native_source_and_input_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),checksum,name)

 def test_native_default_forecast_matches_explicit_profile(self):
  import sys
  sys.path.insert(0,str(ROOT/'reports/v6_engine_port_2026-11-25/reference'))
  from trial_adapter import load_trial
  from SRC.model_inputs import default_experiment
  from SRC.forecast_engine import simulate
  _,p,m,params,post,ideology,a=load_trial((ROOT/'app.py').read_text())
  e,g=default_experiment(p);settings,_=load_forecast_params();settings.update(SIMULATIONS=2,SEED=20261010)
  targets=json.loads((ROOT/'data/v6_targets.json').read_text())
  first=simulate(p,m,params,post,ideology,targets,a,settings)
  second=simulate(p,m,params,post,ideology,targets,a,settings,experiment=e,subregions=g)
  import pandas as pd
  pd.testing.assert_frame_equal(first['seats'],second['seats'],check_exact=True)
