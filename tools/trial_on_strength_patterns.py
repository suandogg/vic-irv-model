"""Compare ON-strength persistence scenarios without assigning mixture weights."""
import copy
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from Tests.test_forecast_engine import calculator_fixture
from SRC.constants import PARTIES
from SRC.forecast_engine import simulate, forecast_counts, fingerprint
from SRC.forecast_params import load_forecast_params
from SRC.primary_pipeline import build_projected_primaries


def main():
    _,primary,matrices,params,posterior,ideology,adjustments = calculator_fixture()
    targets = dict(ALP=24.6,LNP=29.1,GRN=13.3,ON=22,IND=5.5,OTH=5.5)
    settings,_ = load_forecast_params()
    out = ROOT/'reports/on_strength_patterns_2026_10_28'
    out.mkdir(exist_ok=True)
    central_rows,probabilities,party_rows,summary = [],[],[],[]
    scenarios = [('Flatter',.4),('Current',.6),('Strength concentrated',1.)]
    for label,alpha in scenarios:
        scenario_params = copy.deepcopy(params)
        scenario_params['scalar_params']['ON alpha'] = alpha
        adjusted,_ = build_projected_primaries(primary,scenario_params,targets,adjustments)
        # Existing LNP precollapse can move ALP/LNP/IND totals after primary
        # calibration. Keep that production behaviour, rather than silently
        # recentering it for this experiment. ON statewide remains fixed.
        np.testing.assert_allclose(adjusted.ON.mean()*100,targets['ON'],atol=1e-7)
        np.testing.assert_allclose(adjusted[PARTIES].sum(axis=1),1.,atol=1e-9)
        counted = forecast_counts(adjusted,matrices,scenario_params,posterior,ideology).set_index('district')
        central = adjusted[['district','region','seat_type','ON_strength']+PARTIES].copy()
        for p in PARTIES:
            central[p] *= 100
        central['Winner'] = central.district.map(counted.winner)
        central['Winner margin above 50 (pp)'] = central.district.map(counted.margin)*100
        central_rows.append(central.assign(Pattern=label,Alpha=alpha))
        # Three seeds, 100 draws each, paired statewide/parameter/local shocks.
        seed_results = []
        for seed in [20261010,20261011,20261012]:
            result = simulate(primary,matrices,scenario_params,posterior,ideology,targets,adjustments,
                              settings|{'SEED':seed,'SIMULATIONS':100})
            probabilities.append(result['seats'].assign(Pattern=label,Seed=seed))
            seed_results.append(result['draws'][PARTIES])
            print(label,seed,'completed',flush=True)
        counts = pd.concat(seed_results,ignore_index=True)
        for p in PARTIES:
            q = np.quantile(counts[p],[.05,.5,.95],method='nearest')
            party_rows.append(dict(Pattern=label,Party=p,Lower=int(q[0]),Median=int(q[1]),Upper=int(q[2]),
                                   Average=float(counts[p].mean()),Central_seats=int((counted.winner==p).sum())))
        summary.append(dict(Pattern=label,Alpha=alpha,Min_ON=float(central.ON.min()),Max_ON=float(central.ON.max()),
                            Seat_SD_ON=float(central.ON.std()),Mean_ON=float(central.ON.mean()),
                            Donor_strength=params['scalar_params'].get('ON_PRIMARY_DONOR_STRENGTH')))
    central = pd.concat(central_rows,ignore_index=True)
    central.to_csv(out/'central_seats.csv',index=False)
    raw = pd.concat(probabilities,ignore_index=True)
    raw.to_csv(out/'probabilities_by_seed.csv',index=False)
    pooled = raw.groupby(['Pattern','Seat'],sort=False)[[p+' win (%)' for p in PARTIES]].mean().reset_index()
    pooled.to_csv(out/'pooled_probabilities.csv',index=False)
    pd.DataFrame(party_rows).to_csv(out/'party_ranges.csv',index=False)
    pd.DataFrame(summary).to_csv(out/'pattern_summary.csv',index=False)
    # Envelope: sensitivity across plausible-looking assumptions, NOT a probability interval.
    envelope = pooled.groupby('Seat')[[p+' win (%)' for p in PARTIES]].agg(['min','max'])
    envelope.columns = [' '.join(c) for c in envelope.columns]
    envelope.to_csv(out/'sensitivity_envelope.csv')
    (out/'manifest.json').write_text(json.dumps(dict(targets=targets,settings=settings,
        patterns=dict(scenarios),seeds=[20261010,20261011,20261012],draws_per_seed=100,
        input_hash=fingerprint(primary,matrices,params,posterior,ideology,adjustments),
        input_mode='committed snapshot; not current polling or live Sheets',
        preference_trial='vec_field_coverage',
        caveat='No mixture weights or default changes; alpha choices illustrative, not fitted.'),indent=2))
    print(pd.DataFrame(summary).to_string(index=False),flush=True)
    for pattern,rows in pooled.groupby('Pattern'):
        print(pattern,'seats >=98:',int((rows.filter(like='win (%)').max(axis=1)>=98).sum()),flush=True)


if __name__=='__main__':
    main()
