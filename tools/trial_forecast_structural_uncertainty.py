"""Offline structural trials; no new production controls or Sheet mutations."""
from pathlib import Path
import sys
import json
import time
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from Tests.test_forecast_engine import calculator_fixture
from SRC.forecast_engine import simulate, engine_source_hash, fingerprint, government_events, STRUCTURAL_EXPERIMENTS
from SRC.forecast_params import load_forecast_params
from SRC.constants import PARTIES


def main():
    _,p,m,params,post,i,a = calculator_fixture()
    targets = dict(ALP=24.6,LNP=29.1,GRN=13.3,ON=22,IND=5.5,OTH=5.5)
    settings,_ = load_forecast_params()
    out = ROOT/'reports/forecast_structural_2026_10_28'
    out.mkdir(exist_ok=True)
    # The structured nowcast needs its own explicit Sheet-controlled configuration.
    experiments = {k:v for k,v in STRUCTURAL_EXPERIMENTS.items() if 'structured_nowcast' not in v}
    seeds = [20261010,20261011,20261012]
    summaries,raw_seats,raw_counts,parties,events = [],[],[],[],[]
    for label,experiment in experiments.items():
        frames,seat_frames = [],[]
        for seed in seeds:
            start = time.monotonic()
            result = simulate(p,m,params,post,i,targets,a,settings|{'SEED':seed,'SIMULATIONS':100},experiment=experiment)
            frames.append(result['draws'][PARTIES])
            seat_frames.append(result['seats'].set_index('Seat').filter(like='win (%)'))
            raw_seats.append(result['seats'].assign(Trial=label,Seed=seed))
            raw_counts.append(result['draws'].assign(Trial=label,Seed=seed))
            d = result['diagnostics']
            summaries.append(dict(Trial=label,Seed=seed,Seats_at_least_98=int(d['At least 98%'].sum()),
                                  Seats_all_draws=int((d['Leading win (%)']==100).sum()),
                                  Runtime_seconds=time.monotonic()-start))
            print(summaries[-1],flush=True)
        counts = pd.concat(frames,ignore_index=True)
        probabilities = sum(seat_frames)/len(seeds)
        probabilities.reset_index().assign(Trial=label).to_csv(out/(label.replace(' ','_')+'_pooled_seats.csv'),index=False)
        print(label,'pooled seats >=98:',int((probabilities.max(axis=1)>=98).sum()),flush=True)
        for party in PARTIES:
            q = np.quantile(counts[party],[.05,.5,.95],method='nearest')
            parties.append(dict(Trial=label,Party=party,Lower=int(q[0]),Median=int(q[1]),Upper=int(q[2]),
                                Average=float(counts[party].mean())))
        for event,mask in government_events(counts).items():
            events.append(dict(Trial=label,Event=event,Probability=100*float(mask.mean())))
    for name,table in [('summary',pd.DataFrame(summaries)),('seats_by_seed',pd.concat(raw_seats)),
                       ('draws',pd.concat(raw_counts)),('parties',pd.DataFrame(parties)),('events',pd.DataFrame(events))]:
        table.to_csv(out/(name+'.csv'),index=False)
    (out/'manifest.json').write_text(json.dumps(dict(settings=settings,draws_per_seed=100,seeds=seeds,
        targets=targets,experiments=experiments,input_mode='committed snapshot, not live Sheet',
        preference_trial='vec_field_coverage',engine_hash=engine_source_hash(),
        input_hash=fingerprint(p,m,params,post,i,a,targets),
        caveat='Uncalibrated paired sensitivity trials; same marginal variance pre-balancing for t5; '
               'split preserves origin-recipient marginal variance, add increases it'),indent=2))


if __name__=='__main__':
    main()
