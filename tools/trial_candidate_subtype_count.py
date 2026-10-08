"""Strict seat-held-out candidate count with exact broad-field subtype pools."""
import json
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.audit_vec_candidate_replay import key
from tools.validate_candidate_subtype_pool import load_observations, pooled_share
from tools.trial_candidate_endogenous_count import count_candidates


def main():
    observations = load_observations()
    candidates = pd.read_csv(ROOT/'data/development/VEC_2022_CANDIDATE_CLASSIFICATION.csv')
    actual = {r['seat']: r for r in json.loads((ROOT/'reports/preference_review_2026_10_08/vec_candidate_replay.json').read_text())}
    results = []
    for seat, group in candidates.groupby('Electorate'):
        metadata = {key(r.CandidateName): r for r in group.itertuples()}
        categories = {n: r.BroadCategory for n, r in metadata.items()}
        primaries = {n: float(r.PrimaryVotes) for n, r in metadata.items()}
        def fallback(eliminated, remaining):
            field = sorted({categories[n] for n in remaining})
            if categories[eliminated] == 'ON' or 'ON' in field:
                return None  # This test does not invent native/synthetic ON flows.
            target = {'seat': seat, 'category': categories[eliminated], 'subtype': str(metadata[eliminated].CandidateSubtype), 'field': field}
            pool = pooled_share(observations, target, True, 3)
            if pool is None:
                return None
            return {'field': sorted(remaining), 'shares': pool[0], 'training_seats': pool[1], 'method': 'subtype exact broad-field pool; proportional recipients'}
        result = count_candidates(primaries, categories, {}, prefer_exact=True, fallback=fallback)
        if result['status'] == 'complete':
            result['winner_correct'] = result['final_candidates'][0] == actual[seat]['final_candidates'][0]
            result['pair_correct'] = set(result['final_candidates']) == set(actual[seat]['final_candidates'])
        results.append(dict(seat=seat, **result))
    complete = [r for r in results if r['status'] == 'complete']
    summary = {'seats': len(results), 'complete': len(complete), 'unresolved': len(results)-len(complete), 'correct_winners_among_complete': sum(r['winner_correct'] for r in complete), 'correct_pairs_among_complete': sum(r['pair_correct'] for r in complete)}
    (ROOT/'reports/preference_review_2026_10_08/candidate_subtype_count.json').write_text(json.dumps({'summary': summary, 'seats': results}, indent=2)+'\n')
    print(json.dumps(summary))
    print([(r['seat'], r['status'], r.get('final_categories'), r.get('next_eliminated')) for r in results if r['seat'] in ('Laverton', 'Kororoit', 'Pakenham', 'Morwell', 'Pascoe Vale', 'Ashwood', 'Yan Yean')])


if __name__ == '__main__':
    main()
