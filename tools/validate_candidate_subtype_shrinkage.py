"""Paired seat-held-out subtype shrinkage diagnostic; no live fallback."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_candidate_subtype_pool import load_observations, pooled_share
from tools.validate_vec_conditional_flows import distance


def blend(subtype, broad, seats, strength):
    weight = seats/(seats+strength)
    return {p: weight*subtype.get(p, 0)+(1-weight)*broad.get(p, 0) for p in set(subtype) | set(broad)}


def main():
    observations = load_observations()
    rows = []
    for target in observations:
        subtype = pooled_share(observations, target, True, 1)
        broad = pooled_share(observations, target, False, 1)
        if subtype is None or broad is None:
            continue
        errors = {'subtype_only': distance(subtype[0], target['shares'], target['field']),
                  'broad_only': distance(broad[0], target['shares'], target['field'])}
        for strength in (1, 3, 5, 10):
            errors[f'prior_{strength}'] = distance(blend(subtype[0], broad[0], subtype[1], strength), target['shares'], target['field'])
        rows.append({'seat': target['seat'], 'candidate': target['candidate'], 'subtype_seats': subtype[1],
                     'same_category_alive': target['category'] in target['field'], 'errors': errors})
    summary = {}
    filters = {'all': lambda r: True, 'sparse_1_or_2_seats': lambda r: r['subtype_seats'] <= 2,
               'same_category_alive': lambda r: r['same_category_alive']}
    for label, predicate in filters.items():
        selected = [r for r in rows if predicate(r)]
        summary[label] = {'parcels': len(selected), 'mean_errors_pp': {method: sum(r['errors'][method] for r in selected)/len(selected) for method in rows[0]['errors']}}
    (ROOT/'reports/preference_review_2026_10_08/candidate_subtype_shrinkage.json').write_text(json.dumps({'method': 'weight=n/(n+k), equal-seat pools; held-out seat excluded. Broad pool includes same-subtype evidence so estimates are correlated. Diagnostic strengths not tuned out of sample.', 'summary': summary, 'parcels': rows}, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
