"""Paired all-seat uncertainty comparison; no live or production writes."""
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from Tests.test_forecast_engine import calculator_fixture
from SRC.forecast_engine import simulate,engine_source_hash,fingerprint
from SRC.forecast_params import validate
from SRC.params_loader import load_params
from SRC.seat_adjustments_loader import load_lower_seat_adjustments
from SRC.lnp_precollapse_loader import load_lnp_precollapse_inputs
from SRC.nowcast_loader import load_nowcast_inputs
from SRC.oth_matrix_builder import rebuild_oth_matrices
from tools.trial_vec_field_evidence import attach_vec_fields
from tools.preference_review_trials import variant
from SRC.constants import PARTIES


def frame(values,header=True):
    width=max(map(len,values))
    padded=[row+[None]*(width-len(row)) for row in values]
    return (pd.DataFrame(padded[1:],columns=padded[0]).replace('',np.nan)
            if header else pd.DataFrame(padded).replace('',np.nan))


def main():
    snapshot=json.loads((ROOT/'reports/nowcast_architecture_live_snapshot_2026_10_28.json').read_text())
    def sheet(name,header=True):
        return frame(snapshot['sheets'][name]['values'],header)
    n,_,_,_,post,ideology,_=calculator_fixture()
    primary=sheet('LOWER_PRIMARY_INPUTS')
    for col in ['ALP_pvi','LNP_pvi','GRN_pvi','IND_pvi','OTH_pvi','ON_strength']:
        primary[col]=pd.to_numeric(primary[col])
    with patch('SRC.params_loader.read_csv_raw',return_value=sheet('PARAMS',False)):
        params=variant(load_params(),'vec_field_coverage')
    with patch('SRC.seat_adjustments_loader.read_csv_raw',return_value=sheet('LOWER_SEAT_ADJUSTMENTS')):
        adjustments=load_lower_seat_adjustments()
    with patch('SRC.lnp_precollapse_loader.read_csv_raw',return_value=sheet('LOWER_LNP_PRECOLLAPSE')):
        precollapse=load_lnp_precollapse_inputs()
    settings=validate(dict(zip(sheet('FORECAST PARAMS').Parameter,sheet('FORECAST PARAMS').Value)))
    groups=dict(zip(sheet('SUB-REGIONS').District,sheet('SUB-REGIONS')['Proposed sub-region']))
    matrices=rebuild_oth_matrices(attach_vec_fields(n['load_synth_pref_matrices']()),params)
    config,_=load_nowcast_inputs(list(primary.district))
    # Freeze the initial zero-transport proposal for attribution, even after the
    # development Sheet adopts nonzero applicability assumptions.
    config=config|{'transport_log_sd':dict(vec=0,federal=0,special=0,generic=0)}
    targets=dict(ALP=24.2,LNP=30.2,GRN=14.7,ON=21.9,IND=4.5,OTH=4.5)
    transport_config=config|{'transport_log_sd':dict(vec=.15,federal=.25,special=.35,generic=.35),
        'provenance':config['provenance']+' Additional source applicability SDs are explicit judgment-based 2026 sensitivity assumptions, not fitted evidence.'}
    variants={'Current default':{},
        'Previous concentration trial':dict(concentration_log_sd=.3,concentration_form='positive_bounded',subregion_fraction=.5),
        'Structured nowcast':dict(structured_nowcast=config),
        'Combined concentration and leans':dict(structured_nowcast=config,
            concentration_log_sd=.3,concentration_form='positive_bounded',subregion_fraction=.5),
        'Combined plus source applicability':dict(structured_nowcast=transport_config,
            concentration_log_sd=.3,concentration_form='positive_bounded',subregion_fraction=.5)}
    out=ROOT/'reports/combined_nowcast_comparison_2026_10_29'
    out.mkdir(exist_ok=True)
    summaries=[]
    for index,(label,experiment) in enumerate(variants.items()):
        start=time.monotonic()
        def progress(done,total):
            if done%100==0 or done==total:
                print(f'{label}: {done}/{total} ({time.monotonic()-start:.1f}s)',flush=True)
        with patch('SRC.forecast_engine.load_lnp_precollapse_inputs',return_value=precollapse):
            result=simulate(primary,matrices,params,post,ideology,targets,adjustments,settings,
                progress=progress,experiment=experiment,subregions=groups)
        folder=out/str(index)
        folder.mkdir(exist_ok=True)
        for key,value in result.items():
            if isinstance(value,pd.DataFrame):
                value.to_csv(folder/(key+'.csv'),index=False)
        rates=result['seats'][[p+' win (%)' for p in PARTIES]].to_numpy()
        top=rates.max(axis=1)
        ranked=np.sort(rates,axis=1)
        summaries.append({'Mode':label,'Average leading win (%)':float(top.mean()),
            'Seats above 90%':int((top>90).sum()),'Seats above 98%':int((top>98).sum()),
            'Seats at least 90%':int((top>=90).sum()),'Seats at least 98%':int((top>=98).sum()),
            'Seats 100%':int((top==100).sum()),
            'Average top two combined (%)':float(ranked[:,-2:].sum(axis=1).mean()),
            'Mean district 2PP SD (pp)':float(result['diagnostics']['ALP–LNP 2PP SD (pp)'].mean())})
        print(json.dumps(summaries[-1]),flush=True)
    pd.DataFrame(summaries).to_csv(out/'summary.csv',index=False)
    (out/'manifest.json').write_text(json.dumps({'targets':targets,'settings':settings,
        'experiments':variants,'engine_hash':engine_source_hash(),
        'input_hash':fingerprint(primary,matrices,params,post,ideology,adjustments,precollapse,groups),
        'sources':'Matched 28 October live core snapshot, committed preference evidence and 29 October nowcast seed configuration. Not an exact capture of hosted inputs today.',
        'thresholds':'Above uses strict >; at least uses >=. Average leading probability is the mean across 88 district maxima.'},indent=2))
    print(pd.DataFrame(summaries).to_string(index=False),flush=True)


if __name__=='__main__':
    main()
