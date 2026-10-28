"""All-party concentration / preference pattern interaction stress test."""
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from Tests.test_forecast_engine import calculator_fixture
from SRC.forecast_engine import simulate,fingerprint,engine_source_hash
from SRC.forecast_subregions import load_subregions
from SRC.forecast_params import load_forecast_params
from SRC.constants import PARTIES


def main():
    _,p,m,params,post,i,a = calculator_fixture()
    mapping,source = load_subregions(list(p.district))
    groups = dict(zip(mapping.district,mapping.subregion))
    settings,_ = load_forecast_params()
    targets = dict(ALP=24.6,LNP=29.1,GRN=13.3,ON=22,IND=5.5,OTH=5.5)
    out = ROOT/'reports/all_party_patterns_2026_10_28'
    out.mkdir(exist_ok=True)
    prefs = {'preference_region_share':.25,'preference_local_share':.25}
    concentration = {'concentration_log_sd':.2}
    profiles = {'Current':{},'Concentration':concentration,'Regional preferences':prefs,
                'Both upper regions':concentration|prefs,
                'Both subregions':concentration|prefs|{'subregion_fraction':1.}}
    summary,pooled,parties,raw_draws,coefficients = [],[],[],[],[]
    for label,experiment in profiles.items():
        seat_frames,count_frames = [],[]
        for seed in [20261010,20261011,20261012]:
            r = simulate(p,m,params,post,i,targets,a,settings|{'SEED':seed,'SIMULATIONS':100},
                         experiment=experiment,subregions=groups)
            seat_frames.append(r['seats'].set_index('Seat').filter(like='win (%)'))
            count_frames.append(r['draws'][PARTIES])
            raw_draws.append(r['draws'].assign(Trial=label,Seed=seed))
            coefficients.append(r['concentration_draws'].assign(Trial=label,Seed=seed))
            summary.append(dict(Trial=label,Seed=seed,Seats_at_least_98=int(r['diagnostics']['At least 98%'].sum())))
            print(label,seed,'done',flush=True)
        probabilities = sum(seat_frames)/len(seat_frames)
        pooled.append(probabilities.reset_index().assign(Trial=label))
        counts = pd.concat(count_frames,ignore_index=True)
        for party in PARTIES:
            q = np.quantile(counts[party],[.05,.5,.95],method='nearest')
            parties.append(dict(Trial=label,Party=party,Lower=int(q[0]),Median=int(q[1]),Upper=int(q[2]),
                                Average=float(counts[party].mean())))
        print(label,'pooled >=98',int((probabilities.max(axis=1)>=98).sum()),
              'all wins',int((probabilities.max(axis=1)==100).sum()),flush=True)
    for name,table in [('summary',pd.DataFrame(summary)),('pooled_seats',pd.concat(pooled)),
                       ('party_ranges',pd.DataFrame(parties)),('draws',pd.concat(raw_draws)),
                       ('coefficients',pd.concat(coefficients))]:
        table.to_csv(out/(name+'.csv'),index=False)
    (out/'manifest.json').write_text(json.dumps(dict(source=source,subregions=groups,
        profiles=profiles,settings=settings,draws_per_seed=100,seeds=[20261010,20261011,20261012],
        targets=targets,input_mode='committed model/mapping snapshot, not current polling/live settings',
        preference_trial='vec_field_coverage',engine_hash=engine_source_hash(),
        input_hash=fingerprint(p,m,params,post,i,a,groups),
        caveat='Uncalibrated concentration SD 0.2; ON alpha uncertainty replaced, class-ON preference term retained.'),indent=2))


if __name__=='__main__':
    main()
