"""Strict seat-held-out, equal-seat pooled exact-field evidence diagnostic.

No posterior/federal aggregates; no held-out preference observations. Both
arms retain the same held-out primary votes and synthetic ON assumptions.
"""
import copy
import json
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.trial_vec_field_evidence import attach_vec_fields
from tools.preference_review_trials import variant
from tools.validate_leave_one_out import mean_matrix, actual_result
from SRC.matrix_loader import load_synth_pref_matrices
from SRC.params_loader import load_params
from SRC.ideology_loader import load_ideology_prior
from SRC.constants import PARTIES
from SRC.irv import run_irv_for_district
from SRC.lnp_precollapse_loader import apply_lnp_precollapse


def pool_fields(evidence, held_out):
    groups = {}
    for seat, item in evidence.items():
        if seat == held_out:
            continue
        for origin, record in item['matrix'].get('__vec_field_rows__', {}).items():
            key = (origin, '+'.join(record['field']))
            groups.setdefault(key, []).append((seat, record))
    pooled = {}
    for (origin, field), records in groups.items():
        parties = field.split('+')
        pooled.setdefault(origin, {})[field] = {
            'field': parties,
            'shares': {p: sum(r['shares'].get(p, 0) for _, r in records)/len(records) for p in parties},
            'method': 'equal-seat exact-field pool; held-out seat excluded',
            'training_seats': [s for s, _ in records],
        }
    return pooled


def main():
    matrices = load_synth_pref_matrices()
    evidence = attach_vec_fields(matrices)
    params = load_params()
    ideology = load_ideology_prior()
    candidates = pd.read_csv(ROOT/'data/development/VEC_2022_CANDIDATE_CLASSIFICATION.csv')
    votes = candidates.groupby(['Electorate', 'BroadCategory']).PrimaryVotes.sum().unstack(fill_value=0).reindex(columns=PARTIES, fill_value=0)
    votes = votes.div(votes.sum(axis=1), axis=0).reset_index().rename(columns={'Electorate': 'district'})
    votes = apply_lnp_precollapse(votes)
    votes.index = votes.district.str.upper()
    baseline = pd.read_csv(ROOT/'data/raw/BASELINE_2CP.csv')
    baseline.index = baseline.district.str.upper()
    rows = []
    for seat, item in matrices.items():
        training = [v for k, v in matrices.items() if k != seat and v['seat_type'] == item['seat_type']]
        matrix = mean_matrix(training or [v for k, v in matrices.items() if k != seat])
        pooled = pool_fields(evidence, seat)
        assert all(seat not in r['training_seats'] for fields in pooled.values() for r in fields.values())
        trial = copy.deepcopy(matrix)
        trial['__vec_pooled_fields__'] = pooled
        primary = {p: float(votes.loc[seat, p]) for p in PARTIES}
        settings = copy.deepcopy(params)
        settings['scalar_params']['SCENARIO_ON_PRIMARY'] = primary['ON']*100
        winner, runner, actual = actual_result(baseline.loc[seat])
        for name, current in [('reference', matrix), ('vec_exact_field', trial)]:
            result = run_irv_for_district(primary, current, item['seat_type'], variant(settings, name), {}, ideology)
            same_pair = {result['winner'], result['runner_up']} == {winner, runner}
            predicted = result['winner_pct'] if result['winner'] == winner else result['runner_up_pct']
            rows.append({'seat': seat, 'variant': name, 'winner_correct': result['winner'] == winner,
                         'pair_correct': same_pair, 'error_pp': (predicted-actual[winner])*100 if same_pair else None})
    common = {r['seat'] for r in rows if r['variant'] == 'reference' and r['pair_correct']} & {r['seat'] for r in rows if r['variant'] == 'vec_exact_field' and r['pair_correct']}
    summary = {}
    for name in ['reference', 'vec_exact_field']:
        selected = [r for r in rows if r['variant'] == name]
        paired = [r['error_pp'] for r in selected if r['seat'] in common]
        summary[name] = {'seats': len(selected), 'correct_winners': sum(r['winner_correct'] for r in selected),
                         'correct_final_pairs': sum(r['pair_correct'] for r in selected), 'common_pairs': len(paired),
                         'common_pair_MAE_pp': sum(abs(e) for e in paired)/len(paired),
                         'common_pair_mean_error_pp': sum(paired)/len(paired)}
    payload = {'method': 'Equal-seat pooled exact fields across all classes, excluding held-out seat; same-class legacy fallback; no posterior or federal aggregate.', 'summary': summary, 'seats': rows}
    target = ROOT/'reports/preference_review_2026_10_08/vec_field_holdout.json'
    target.write_text(json.dumps(payload, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
