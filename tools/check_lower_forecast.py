"""Reproducible prototype smoke run; no fitting, live sync or Sheet writes."""
import argparse
import json
from pathlib import Path
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from Tests.test_forecast_engine import calculator_fixture
from SRC.forecast_engine import simulate, fingerprint
from SRC.forecast_params import defaults


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--draws',type=int,default=200)
    args = parser.parse_args()
    _,primary,matrices,params,posterior,ideology,adjustments = calculator_fixture()
    targets = dict(ALP=24.6,LNP=29.1,GRN=13.3,ON=22,IND=5.5,OTH=5.5)
    settings = defaults()|{'SIMULATIONS':args.draws}
    start = time.monotonic()
    def progress(done,total):
        if done%50==0 or done==total:
            print(f'{done}/{total}: {time.monotonic()-start:.1f}s',flush=True)
    result = simulate(primary,matrices,params,posterior,ideology,targets,adjustments,settings,progress)
    out = ROOT/'reports/forecast_prototype_2026_10_10'
    out.mkdir(exist_ok=True)
    for key in ('seats','parties','government','draws','primary_draws'):
        result[key].to_csv(out/f'{key}.csv',index=False)
    manifest = {'settings':settings,'targets':targets,'input_mode':'committed CSV snapshot',
        'calibration':'none; engineering smoke run only','preference_trial':'vec_field_coverage',
        'signature':fingerprint(primary,matrices,params,posterior,ideology,targets,adjustments,settings),
        'runtime_seconds':time.monotonic()-start}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(result['parties'].to_string(index=False))
    print(result['government'].to_string(index=False))


if __name__=='__main__':
    main()
