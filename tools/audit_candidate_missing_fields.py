"""Inventory first unresolved field per held-out seat; no extrapolation."""
import json
import sys
from collections import Counter
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.audit_vec_candidate_replay import key
from tools.validate_candidate_subtype_pool import load_observations


def main():
    report = ROOT/'reports/preference_review_2026_10_08'
    count = json.loads((report/'candidate_subtype_count.json').read_text())
    candidates = pd.read_csv(ROOT/'data/development/VEC_2022_CANDIDATE_CLASSIFICATION.csv')
    observations = load_observations()
    rows = []
    for row in count['seats']:
        if row['status'] != 'unresolved':
            continue
        meta = {key(r.CandidateName): r for r in candidates[candidates.Electorate == row['seat']].itertuples()}
        subtype = str(meta[row['next_eliminated']].CandidateSubtype)
        field = sorted({meta[n].BroadCategory for n in row['remaining_candidates']})
        exact = [r for r in observations if r['seat'] != row['seat'] and r['field'] == field and r['subtype'] == subtype]
        broad = [r for r in observations if r['seat'] != row['seat'] and r['field'] == field and r['category'] == row['category']]
        n = len({r['seat'] for r in exact})
        reason = 'ON excluded from this diagnostic' if 'ON' in field or row['category'] == 'ON' else 'subtype field unobserved elsewhere' if n == 0 else 'only one training seat' if n == 1 else 'only two training seats' if n == 2 else 'unexpected unresolved case'
        rows.append({'seat': row['seat'], 'subtype': subtype, 'category': row['category'], 'field': field,
                     'same_category_alive': row['same_category_remaining'], 'matching_subtype_seats': n,
                     'matching_broad_seats': len({r['seat'] for r in broad}), 'reason': reason})
    summary = dict(Counter(r['reason'] for r in rows))
    combinations = Counter((r['subtype'], '+'.join(r['field'])) for r in rows)
    payload = {'summary': summary, 'first_missing_fields': rows, 'combinations': [{'subtype': k[0], 'field': k[1], 'seats_stopped': v} for k, v in combinations.most_common()]}
    (report/'candidate_missing_fields.json').write_text(json.dumps(payload, indent=2)+'\n')
    print(json.dumps(summary))
    print(combinations.most_common(10))


if __name__ == '__main__':
    main()
