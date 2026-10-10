"""Paired sensitivity runs on committed inputs, not historical calibration."""
import json
import sys
import time
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from Tests.test_forecast_engine import calculator_fixture
from SRC.forecast_engine import simulate, uncertainty_profile, engine_source_hash
from SRC.forecast_params import load_forecast_params

_,primary,matrices,params,posterior,ideology,adjustments = calculator_fixture()
targets = dict(ALP=24.6,LNP=29.1,GRN=13.3,ON=22,IND=5.5,OTH=5.5)
settings,_ = load_forecast_params()
out = ROOT/'reports/forecast_uncertainty_2026_10_10'
out.mkdir(exist_ok=True)
results = {}
runtimes = {}
for label,multiplier in [('Narrower',.5),('Current',1),('Wider',1.5)]:
    start = time.monotonic()
    result = simulate(primary,matrices,params,posterior,ideology,targets,adjustments,
                      uncertainty_profile(settings,multiplier))
    runtimes[label] = time.monotonic()-start
    results[label] = result
    result['draws'].to_csv(out/(label.lower()+'_draws.csv'),index=False)
    print(label,round(runtimes[label],2),flush=True)
for key in ('parties','government','seats'):
    table = pd.concat([result[key].assign(Assumptions=label) for label,result in results.items()],ignore_index=True)
    table.to_csv(out/(key+'.csv'),index=False)
    if key!='seats':
        print(table.to_string(index=False),flush=True)
(out/'manifest.json').write_text(json.dumps(dict(settings=settings,targets=targets,
    multipliers=dict(Narrower=.5,Current=1,Wider=1.5),runtime_seconds=runtimes,
    source='committed CSV inputs; FORECAST PARAMS verified against live Sheet 10 October',
    preference_trial='vec_field_coverage',engine_hash=engine_source_hash(),
    caveat='Sensitivity only; SD assumptions not calibrated'),indent=2))
