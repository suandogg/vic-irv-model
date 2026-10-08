"""Existing labelled families only; paired held-out diagnostic, not fallback."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_candidate_subtype_pool import load_observations, pooled_share
from tools.validate_candidate_subtype_shrinkage import blend
from tools.validate_vec_conditional_flows import distance

KNOWN = {'LEFT', 'CENTRE_LEFT', 'CENTRE', 'CENTRE_RIGHT', 'RIGHT'}


def main():
    observations = load_observations()
    labelled = [r for r in observations if r['family'] in KNOWN]
    family_observations = [dict(r, subtype=r['category']+'|'+r['family']) for r in labelled]
    rows = []
    for target in labelled:
        subtype = pooled_share(observations, target, True, 1)
        family = pooled_share(family_observations, dict(target, subtype=target['category']+'|'+target['family']), True, 3)
        if subtype is None or family is None:
            continue
        errors = {'subtype_only': distance(subtype[0], target['shares'], target['field']), 'family_only': distance(family[0], target['shares'], target['field'])}
        for strength in (1, 3, 5, 10):
            errors[f'prior_{strength}'] = distance(blend(subtype[0], family[0], subtype[1], strength), target['shares'], target['field'])
        rows.append({'seat': target['seat'], 'candidate': target['candidate'], 'family': target['family'], 'subtype_seats': subtype[1], 'family_seats': family[1], 'errors': errors})
    summary = {}
    for label, subset in [('all', rows), ('sparse_1_or_2_seats', [r for r in rows if r['subtype_seats'] <= 2])]:
        summary[label] = {'parcels': len(subset), 'mean_errors_pp': {m: sum(r['errors'][m] for r in subset)/len(subset) for m in rows[0]['errors']}}
    (ROOT/'reports/preference_review_2026_10_08/candidate_family_prior.json').write_text(json.dumps({'method': 'Existing non-unknown labels; same broad origin category and exact continuing field; held-out seat excluded; family pool minimum3. No ON extrapolation.', 'summary': summary, 'parcels': rows}, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
