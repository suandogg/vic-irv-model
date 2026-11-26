"""Independent fixed-seed website control versus native engine; writes only this report."""
import argparse,os,sys,json,time
from pathlib import Path
from types import SimpleNamespace
p=argparse.ArgumentParser();p.add_argument('mode',choices=['reference','native']);p.add_argument('--draws',type=int,default=1000);a=p.parse_args()
ROOT=Path(__file__).resolve().parents[1];REPORT=ROOT/'reports/v7_engine_port_2026-11-26';REF=ROOT/'reports/v6_engine_port_2026-11-25/reference'
model=Path('/private/tmp/prism-v6-control') if a.mode=='reference' else ROOT
os.chdir(model);sys.path.insert(0,str(model));sys.path.insert(0,str(REF));sys.path.insert(0,str(ROOT.parent/'election-website/scripts'));sys.dont_write_bytecode=True
from trial_adapter import load_trial
import numpy as np
import pandas as pd
import SRC.forecast_engine as engine
from SRC.forecast_params import load_forecast_params
from SRC.nowcast_loader import load_nowcast_inputs
from SRC.forecast_subregions import load_subregions
from SRC.candidate_field import load_field_config
from SRC.low_base_taper import load_taper_config
from SRC.oth_scaling import load_oth_scaling_config
from SRC import htv_deal,htv_review,candidate_count
n,primary,matrices,params,posterior,ideology,adjustments=load_trial((model/'app.py').read_text())
if a.mode=='reference':
 import website_release_profile as base
 import website_final_runtime as w
 params,_=w.parameters_for_run(params,new_candidate=True);w.install_preference_runtime();matrices=base.prepare_matrices(matrices,params)
 n['run_model']=w.wrap_central(n['run_model'])
settings,_=load_forecast_params();settings.update(SIMULATIONS=a.draws,SEED=20261010)
config,_=load_nowcast_inputs(list(primary.district));mapping,_=load_subregions(list(primary.district));groups=dict(zip(mapping.district,mapping.subregion))
experiment=dict(structured_nowcast=config,concentration_log_sd=.3,concentration_form='positive_bounded',subregion_fraction=.5,candidate_field=load_field_config(),low_base_taper=load_taper_config(),oth_scaling=load_oth_scaling_config())
if a.mode=='reference':
 deal,review=base.corrected_htv_configs(base.V6_INPUT_CORRECTIONS,htv_deal.load_htv_deal_config,htv_review.load_htv_review_config,{'greens_seats':htv_review.GREENS_SEATS,'labor_open_seats':htv_review.LABOR_OPEN_SEATS})
 settings,experiment=w.apply_uncertainty_profile(settings,experiment,w.profile_metadata())
else:deal,review=htv_deal.load_htv_deal_config(),htv_review.load_htv_review_config()
experiment.update(htv_deal=deal,htv_review=review);matrices=htv_review.apply_htv_review(htv_deal.apply_htv_deal(matrices,deal),review)
targets=json.loads((ROOT/'data/v7_targets.json').read_text())
n['st']=SimpleNamespace(session_state=dict(candidate_field_version_b=True,alp_low_base_taper=True,oth_proportional=True))
from SRC.candidate_effects import load_candidate_effects
n['load_candidate_effects']=load_candidate_effects
central,projected,_=n['run_model'](primary,matrices,params,posterior,ideology,targets,adjustments)
out=REPORT/a.mode;out.mkdir(parents=True,exist_ok=True)
central.to_csv(out/'central.csv',index=False);projected.to_csv(out/'primaries.csv',index=False)
scenario={'ALP':20,'LNP':31,'GRN':13,'ON':25,'IND':4,'OTH':7}
second,second_primary,_=n['run_model'](primary,matrices,params,posterior,ideology,scenario,adjustments)
second.to_csv(out/'scenario-b-central.csv',index=False);second_primary.to_csv(out/'scenario-b-primaries.csv',index=False)
(out/'configuration.json').write_text(json.dumps({'settings':settings,'experiment':experiment,'targets':targets},sort_keys=True,default=str,indent=2)+'\n')
# Observe actual per-draw primaries and named final pairs without altering calculations.
original=engine.forecast_counts;primary_rows=[];count_rows=[];pairs=[];named=candidate_count.result_from_context

def observe_named(*args,**kwargs):
 result=named(*args,**kwargs)
 if result is not None:pairs.append({k:result.get(k) for k in ('winner','runner_up','margin','ALP_2PP','winner_candidate','runner_up_candidate')})
 return result
candidate_count.result_from_context=observe_named
ordinary=engine.run_irv_for_district
def observe_ordinary(*args,**kwargs):
 result=ordinary(*args,**kwargs);pairs.append({k:result.get(k) for k in ('winner','runner_up','margin')});return result
engine.run_irv_for_district=observe_ordinary

def observe(adjusted,*args,**kwargs):
 primary_rows.append(adjusted.set_index('district').loc[list(primary.district),engine.PARTIES].to_numpy())
 r=original(adjusted,*args,**kwargs);count_rows.append(r);return r
engine.forecast_counts=observe
start=time.monotonic()
r=engine.simulate(primary,matrices,params,posterior,ideology,targets,adjustments,settings,lambda done,total:print(f'{a.mode} {done}/{total} {time.monotonic()-start:.1f}s',flush=True) if done%250==0 else None,experiment=experiment,subregions=groups)
for key in ('seats','parties','draws','government','primary_draws'):r[key].to_csv(out/(key+'.csv'),index=False)
np.savez_compressed(out/'per_draw.npz',primary=np.asarray(primary_rows),winner=np.asarray([x.winner.to_list() for x in count_rows]),margin=np.asarray([x.margin.to_list() for x in count_rows]),alp_2pp=np.asarray([x.ALP_2PP.to_list() for x in count_rows]))
pd.DataFrame(pairs).to_csv(out/'final_pairs.csv',index=False)
print('DONE',a.mode,len(pairs),time.monotonic()-start,flush=True)
