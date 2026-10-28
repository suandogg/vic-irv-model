"""Isolate party-specific dispersion widths; do not select for desired certainty."""
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from Tests.test_forecast_engine import calculator_fixture
from SRC.forecast_engine import simulate,fingerprint,engine_source_hash
from SRC.forecast_params import load_forecast_params
from SRC.constants import PARTIES


def main():
    _,p,m,params,post,i,a = calculator_fixture()
    settings,_ = load_forecast_params()
    targets = dict(ALP=24.6,LNP=29.1,GRN=13.3,ON=22,IND=5.5,OTH=5.5)
    out = ROOT/'reports/party_widths_2026_10_28'
    out.mkdir(exist_ok=True)
    profiles = {'Current':{}}
    for party in PARTIES:
        profiles[party+' only 0.20'] = {'concentration_by_party':{party:.2}}
    for width in [.1,.2,.3]:
        profiles[f'Uniform {width:.2f}'] = {'concentration_log_sd':width}
    profiles['Differentiated stress'] = {'concentration_by_party':dict(ALP=.1,LNP=.1,GRN=.15,ON=.3,IND=.2,OTH=.2)}
    pooled,parties,draws,coefficients,seed_summary = [],[],[],[],[]
    for label,experiment in profiles.items():
        seat_frames,count_frames = [],[]
        for seed in [20261010,20261011]:
            r = simulate(p,m,params,post,i,targets,a,settings|{'SEED':seed,'SIMULATIONS':100},experiment=experiment)
            seat_frames.append(r['seats'].set_index('Seat').filter(like='win (%)'))
            count_frames.append(r['draws'][PARTIES])
            draws.append(r['draws'].assign(Trial=label,Seed=seed))
            coefficients.append(r['concentration_draws'].assign(Trial=label,Seed=seed))
            seed_summary.append(dict(Trial=label,Seed=seed,Seats_at_least_98=int(r['diagnostics']['At least 98%'].sum())))
        probabilities = sum(seat_frames)/len(seat_frames)
        pooled.append(probabilities.reset_index().assign(Trial=label))
        counts = pd.concat(count_frames,ignore_index=True)
        for party in PARTIES:
            q = np.quantile(counts[party],[.05,.5,.95],method='nearest')
            parties.append(dict(Trial=label,Party=party,Lower=int(q[0]),Median=int(q[1]),Upper=int(q[2]),
                                Average=float(counts[party].mean())))
        print(label,'mean leader',round(probabilities.max(axis=1).mean(),3),
              '>=98',int((probabilities.max(axis=1)>=98).sum()),flush=True)
    all_seats = pd.concat(pooled,ignore_index=True)
    columns = [p+' win (%)' for p in PARTIES]
    baseline = all_seats[all_seats.Trial=='Current'].set_index('Seat')[columns].idxmax(axis=1)
    rows = []
    for label,g in all_seats.groupby('Trial',sort=False):
        g = g.set_index('Seat')
        leader = g[columns].max(axis=1)
        rows.append(dict(Trial=label,Average_leading_win=float(leader.mean()),
            Median_leading_win=float(leader.median()),Seats_at_least_98=int((leader>=98).sum()),
            Seats_all_draws=int((leader==100).sum()),
            Average_baseline_favourite_win=float(np.mean([g.loc[seat,baseline[seat]] for seat in g.index])),
            Changed_favourites=int((g[columns].idxmax(axis=1)!=baseline).sum())))
    for name,table in [('summary',pd.DataFrame(rows)),('seed_summary',pd.DataFrame(seed_summary)),
                       ('pooled_seats',all_seats),('party_ranges',pd.DataFrame(parties)),
                       ('draws',pd.concat(draws)),('coefficients',pd.concat(coefficients))]:
        table.to_csv(out/(name+'.csv'),index=False)
    (out/'manifest.json').write_text(json.dumps(dict(profiles=profiles,settings=settings,
        draws_per_seed=100,seeds=[20261010,20261011],targets=targets,
        input_mode='committed model snapshot, not current polling/live settings',
        preference_trial='vec_field_coverage',geography='upper-house regions; preference-pattern trial off',
        engine_hash=engine_source_hash(),input_hash=fingerprint(p,m,params,post,i,a),
        caveat='Exploratory widths, not calibration. Positive ON width replaces alpha SD; zero retains it.'),indent=2))


if __name__=='__main__':
    main()
