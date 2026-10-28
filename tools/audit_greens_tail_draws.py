"""Replay archived extreme draws, with paired mechanism counterfactuals."""
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
from SRC.forecast_params import validate
from SRC.forecast_engine import draw_targets,draw_model_params,perturb_local_primaries,fingerprint
from SRC.forecast_patterns import strength_contrast,balance_primary_pattern
from SRC.primary_pipeline import build_projected_primaries
from SRC.irv import run_irv_for_district,trace_irv_for_district,district_key


def count(adjusted,matrices,params,posterior,ideology):
    result = []
    for row in adjusted.to_dict('records'):
        outcome = run_irv_for_district({p:row[p] for p in PARTIES},
            matrices[district_key(row['district'])]['matrix'],row['seat_type'],params,posterior,ideology)
        result.append(dict(Seat=row['district'],**outcome))
    return pd.DataFrame(result).set_index('Seat')


def main():
    _,primary,matrices,params,posterior,ideology,adjustments = calculator_fixture()
    archive = ROOT/'reports/party_widths_2026_10_28'
    manifest = json.loads((archive/'manifest.json').read_text())
    settings = validate(manifest['settings'])
    targets = manifest['targets']
    draws = pd.read_csv(archive/'draws.csv')
    draws = draws[draws.Trial=='Uniform 0.30']
    selected = draws[(draws.GRN==0)|(draws.GRN>=9)]
    out = ROOT/'reports/greens_tail_audit_2026_10_28'
    out.mkdir(exist_ok=True)
    summaries,seat_rows,counterfactuals,traces = [],[],[],[]
    core = {'Brunswick','Melbourne','Prahran','Richmond','Northcote','Pascoe Vale','Preston'}
    for seed in sorted(draws.Seed.unique()):
        rng = np.random.default_rng(seed)
        wanted = set(selected[selected.Seed==seed].Draw)
        for index in range(int(draws[draws.Seed==seed].Draw.max())):
            target = draw_targets(targets,settings,rng)
            model_params = draw_model_params(params,target,settings,primary.seat_type,rng)
            model_params['scalar_params']['ON alpha'] = float(params['scalar_params'].get('ON alpha',.6))
            base,_ = build_projected_primaries(primary,model_params,target,adjustments)
            coefficients = np.random.default_rng(np.random.SeedSequence([int(seed),index,505])).normal(size=len(PARTIES))*.3
            pattern = base.copy()
            pattern[PARTIES] = balance_primary_pattern(base[PARTIES].to_numpy(),strength_contrast(base[PARTIES])*coefficients)
            local_state = copy.deepcopy(rng.bit_generator.state)
            actual = perturb_local_primaries(pattern,settings,rng)
            if index+1 not in wanted:
                continue
            outcome = count(actual,matrices,model_params,posterior,ideology)
            expected = draws[(draws.Seed==seed)&(draws.Draw==index+1)].iloc[0]
            for party in PARTIES:
                assert int((outcome.winner==party).sum())==int(expected[party]),(seed,index+1,party)
            g_winners = outcome.index[outcome.winner=='GRN'].tolist()
            grn_log_sd = float(np.log(base.loc[base.GRN>0,'GRN']).std(ddof=0))
            summaries.append(dict(Seed=int(seed),Draw=index+1,GRN_seats=len(g_winners),
                GRN_target=target['GRN'],GRN_coefficient=coefficients[PARTIES.index('GRN')],
                GRN_base_log_SD=grn_log_sd,
                GRN_effective_exponent=1+coefficients[PARTIES.index('GRN')]/grn_log_sd,
                GRN_mean=float(actual.GRN.mean()*100),GRN_max=float(actual.GRN.max()*100),
                GRN_winning_seats='; '.join(g_winners),
                **{'coefficient_'+p:coefficients[j] for j,p in enumerate(PARTIES)}))
            for row in actual.to_dict('records'):
                seat = row['district']; r = outcome.loc[seat]
                seat_rows.append(dict(Seed=int(seed),Draw=index+1,Seat=seat,
                    **{p:100*row[p] for p in PARTIES},Winner=r.winner,Runner_up=r.runner_up,
                    Winner_pct=100*r.winner_pct,Margin_above_50=100*r.margin,Matchup=r.matchup,
                    Elimination_order='; '.join(r.elimination_order) if isinstance(r.elimination_order,list) else str(r.elimination_order)))
                if seat in core or r.winner=='GRN':
                    trace = trace_irv_for_district({p:row[p] for p in PARTIES},
                        matrices[district_key(seat)]['matrix'],row['seat_type'],model_params,posterior,ideology)
                    traces.extend(dict(Seed=int(seed),Draw=index+1,Seat=seat,**r) for r in trace)
            for label,cf_coefficients in [('GRN factor off',coefficients.copy()),('All concentration off',np.zeros(len(PARTIES)))]:
                if label=='GRN factor off':
                    cf_coefficients[PARTIES.index('GRN')] = 0
                cf = base.copy()
                cf[PARTIES] = balance_primary_pattern(base[PARTIES].to_numpy(),strength_contrast(base[PARTIES])*cf_coefficients)
                cf_rng = np.random.default_rng(); cf_rng.bit_generator.state = copy.deepcopy(local_state)
                cf = perturb_local_primaries(cf,settings,cf_rng)
                cf_outcome = count(cf,matrices,model_params,posterior,ideology)
                counterfactuals.append(dict(Seed=int(seed),Draw=index+1,Variant=label,
                    GRN_seats=int((cf_outcome.winner=='GRN').sum())))
            no_pref = copy.deepcopy(model_params)
            no_pref.pop('_forecast_preference_shocks',None)
            cf_outcome = count(actual,matrices,no_pref,posterior,ideology)
            counterfactuals.append(dict(Seed=int(seed),Draw=index+1,Variant='Preference shocks off',
                GRN_seats=int((cf_outcome.winner=='GRN').sum())))
            print(int(seed),index+1,'GRN',len(g_winners),'primary',round(target['GRN'],2),flush=True)
    for name,table in [('draw_summary',pd.DataFrame(summaries)),('seats',pd.DataFrame(seat_rows)),
                       ('counterfactuals',pd.DataFrame(counterfactuals)),('preference_rounds',pd.DataFrame(traces))]:
        table.to_csv(out/(name+'.csv'),index=False)
    (out/'manifest.json').write_text(json.dumps(dict(source='Uniform 0.30 archived trial',
        selection='All GRN=0 and GRN>=9 draws; selected tail audit, not new random sample',
        replay_verified=True,targets=targets,settings=settings,input_hash=fingerprint(primary,matrices,params,posterior,ideology,adjustments),
        caveat='Counterfactuals retain same target/parameter/local errors and fixed central ON alpha; all-concentration-off is not a full ordinary forecast baseline.'),indent=2))


if __name__=='__main__':
    main()
