"""Positive persistence vs linear: paired tail-shape comparison, not calibration."""
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
    profiles = {'Current':{}}
    for form in ['linear','positive_softplus','positive_bounded']:
        for width in [.2,.3]:
            profiles[f'{form} {width:.2f}'] = {'concentration_log_sd':width,'concentration_form':form}
    out = ROOT/'reports/positive_persistence_2026_10_28'
    out.mkdir(exist_ok=True)
    pooled,draws,parties,powers,extremes,summary = [],[],[],[],[],[]
    for label,experiment in profiles.items():
        seats,counts,exponents,primaries = [],[],[],[]
        for seed in [20261010,20261011]:
            r = simulate(p,m,params,post,i,targets,a,settings|{'SEED':seed,'SIMULATIONS':100},experiment=experiment)
            seats.append(r['seats'].set_index('Seat').filter(like='win (%)'))
            counts.append(r['draws'][PARTIES])
            draws.append(r['draws'].assign(Trial=label,Seed=seed))
            exponents.append(r['concentration_exponents'])
            primaries.append(r['primary_extremes'])
            powers.append(r['concentration_exponents'].assign(Trial=label,Seed=seed))
            extremes.append(r['primary_extremes'].assign(Trial=label,Seed=seed))
        probabilities = sum(seats)/len(seats)
        pooled.append(probabilities.reset_index().assign(Trial=label))
        c = pd.concat(counts,ignore_index=True)
        e = pd.concat(exponents,ignore_index=True)
        v = pd.concat(primaries,ignore_index=True)
        summary.append(dict(Trial=label,Average_leading_win=float(probabilities.max(axis=1).mean()),
            Seats_at_least_98=int((probabilities.max(axis=1)>=98).sum()),
            Seats_all_draws=int((probabilities.max(axis=1)==100).sum()),
            Zero_GRN_draws=int((c.GRN==0).sum()),GRN_min=int(c.GRN.min()),GRN_max=int(c.GRN.max()),
            GRN_negative_powers=int((e.GRN<0).sum()),GRN_power_mean=float(e.GRN.mean()),
            GRN_power_p05=float(e.GRN.quantile(.05)),GRN_power_p50=float(e.GRN.quantile(.5)),
            GRN_power_p95=float(e.GRN.quantile(.95)),
            GRN_local_max_p95=float(v['GRN max (%)'].quantile(.95)),
            GRN_local_max=float(v['GRN max (%)'].max())))
        for party in PARTIES:
            q = np.quantile(c[party],[.05,.5,.95],method='nearest')
            parties.append(dict(Trial=label,Party=party,Lower=int(q[0]),Median=int(q[1]),Upper=int(q[2]),
                                Average=float(c[party].mean())))
        print(summary[-1],flush=True)
    for name,table in [('summary',pd.DataFrame(summary)),('pooled_seats',pd.concat(pooled)),
                       ('party_ranges',pd.DataFrame(parties)),('draws',pd.concat(draws)),
                       ('powers',pd.concat(powers)),('primary_extremes',pd.concat(extremes))]:
        table.to_csv(out/(name+'.csv'),index=False)
    (out/'manifest.json').write_text(json.dumps(dict(profiles=profiles,settings=settings,
        draws_per_seed=100,seeds=[20261010,20261011],targets=targets,
        input_mode='committed snapshot, not live polling or Sheet settings',
        preference_trial='vec_field_coverage',geography='upper-house regions; regional preference trial off',
        engine_hash=engine_source_hash(),input_hash=fingerprint(p,m,params,post,i,a),
        caveat='Forms match zero and local derivative, not global variance. Positive bounded power (0,2) is an explicit research prior.'),indent=2))


if __name__=='__main__':
    main()
