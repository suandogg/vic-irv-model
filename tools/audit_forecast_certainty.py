"""Isolated uncertainty trials on frozen committed inputs; no Sheet writes."""
import json
from pathlib import Path
import sys
import time
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from Tests.test_forecast_engine import calculator_fixture
from SRC.constants import PARTIES
from SRC.forecast_engine import simulate, forecast_counts, fingerprint, engine_source_hash
from SRC.forecast_params import load_forecast_params
from SRC.primary_pipeline import build_projected_primaries
from SRC.irv import trace_irv_for_district, district_key


def main():
    _,primary,matrices,params,posterior,ideology,adjustments = calculator_fixture()
    targets = dict(ALP=24.6,LNP=29.1,GRN=13.3,ON=22,IND=5.5,OTH=5.5)
    settings,_ = load_forecast_params()
    out = ROOT/'reports/forecast_certainty_2026_10_28'
    out.mkdir(exist_ok=True)
    adjusted,_ = build_projected_primaries(primary,params,targets,adjustments)
    central = forecast_counts(adjusted,matrices,params,posterior,ideology).set_index('district')
    source_rows = []
    for row in adjusted.to_dict('records'):
        trace = trace_irv_for_district({p:row[p] for p in PARTIES},
            matrices[district_key(row['district'])]['matrix'],row['seat_type'],params,posterior,ideology)
        source_rows.extend(dict(Seat=row['district'],**r) for r in trace if r.get('basis'))
    sources = pd.DataFrame(source_rows)
    sources.to_csv(out/'central_preference_rounds.csv',index=False)
    # Isolate existing controls before introducing new distributions/assumptions.
    profiles = {'Current':settings,
        'Local SD 2.5':settings|{'SEAT_PRIMARY_SD_PP':2.5},
        'Local SD 3.0':settings|{'SEAT_PRIMARY_SD_PP':3.0},
        'Preference SDs x1.5':{k:v*1.5 if k.startswith('PREF_') else v for k,v in settings.items()},
        'Statewide SDs x1.5':{k:v*1.5 if k.startswith('STATEWIDE_SD_') else v for k,v in settings.items()},
        'Combined local 2.5 + preferences':{k:v*1.5 if k.startswith('PREF_') else
            2.5 if k=='SEAT_PRIMARY_SD_PP' else v for k,v in settings.items()}}
    summaries,diagnostics,parties,governments = [],[],[],[]
    for label,values in profiles.items():
        start = time.monotonic()
        result = simulate(primary,matrices,params,posterior,ideology,targets,adjustments,values)
        d = result['diagnostics'].copy()
        d['Central winner'] = d.Seat.map(central.winner)
        d['Central winning margin (pp above 50)'] = d.Seat.map(central.margin)*100
        # Holder-level labels only: does not claim all retained parcel origins use this basis.
        d['Central holder-level preference bases'] = d.Seat.map(
            sources.groupby('Seat').basis.agg(lambda x:'; '.join(sorted(set(x)))))
        diagnostics.append(d.assign(Trial=label))
        parties.append(result['parties'].assign(Trial=label))
        governments.append(result['government'].assign(Trial=label))
        summaries.append(dict(Trial=label,Seats_at_least_98=int(d['At least 98%'].sum()),
            Seats_all_draws=int((d['Leading win (%)']==100).sum()),
            Median_2PP_SD=float(d['ALP–LNP 2PP SD (pp)'].median()),
            Runtime_seconds=time.monotonic()-start))
        print(summaries[-1],flush=True)
    for name,frames in [('diagnostics',diagnostics),('parties',parties),('government',governments)]:
        pd.concat(frames,ignore_index=True).to_csv(out/(name+'.csv'),index=False)
    pd.DataFrame(summaries).to_csv(out/'summary.csv',index=False)
    (out/'manifest.json').write_text(json.dumps(dict(targets=targets,profiles=profiles,
        input_mode='committed CSV snapshot; not current live Sheet settings',
        preference_trial='vec_field_coverage',engine_hash=engine_source_hash(),
        signature=fingerprint(primary,matrices,params,posterior,ideology,adjustments,targets,profiles),
        calibration='none: sensitivity experiments, no fitted uncertainty or election-day drift'),indent=2))


if __name__=='__main__':
    main()
