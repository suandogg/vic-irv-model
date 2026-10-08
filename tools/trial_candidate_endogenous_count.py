"""Strict exact-candidate-field endogenous shadow; stop on missing evidence.

Uses held-in recorded category transfers and approved proportional recipients.
This is a coverage/aggregation diagnostic, not independent forecast validation.
"""
import json
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.audit_vec_candidate_replay import key, resolve
from SRC.candidate_shadow import allocate_category_flow


def count_candidates(primaries, categories, evidence, prefer_exact=False):
    totals = primaries.copy()
    formal = sum(totals.values())
    active = set(totals)
    rounds = []
    while len(active) > 2:
        eliminated = min(active, key=lambda n: (totals[n], n))
        remaining = active - {eliminated}
        record = evidence.get(eliminated)
        if record is None or set(record['field']) != remaining:
            return {'status': 'unresolved', 'rounds': rounds, 'next_eliminated': eliminated,
                    'category': categories[eliminated], 'same_category_remaining': any(categories[n] == categories[eliminated] for n in remaining),
                    'remaining_candidates': sorted(remaining), 'reason': 'No exact continuing-candidate-field evidence'}
        recipients = {n: {'category': categories[n], 'tally': totals[n]} for n in remaining}
        exact = record.get('candidate_shares') if prefer_exact else None
        if exact is not None:
            if not set(exact).issubset(remaining) or abs(sum(exact.values())-1) > 1e-8 or any(v < 0 for v in exact.values()):
                raise ValueError('Invalid exact candidate shares')
            movement = {n: totals[eliminated]*exact.get(n, 0) for n in remaining}
        else:
            movement = allocate_category_flow(totals[eliminated], record['shares'], recipients)
        parcel = totals[eliminated]
        totals[eliminated] = 0
        for n, amount in movement.items():
            totals[n] += amount
        if abs(sum(totals.values())-formal) > 1e-6:
            raise ValueError('Vote conservation failure')
        rounds.append({'eliminated': eliminated, 'category': categories[eliminated], 'parcel': parcel,
                       'recipient_method': 'exact candidate evidence' if exact is not None else 'proportional candidate fallback'})
        active = remaining
    ordered = sorted(active, key=lambda n: (-totals[n], n))
    return {'status': 'complete', 'rounds': rounds, 'final_candidates': ordered,
            'final_categories': [categories[n] for n in ordered], 'final_shares_pct': [totals[n]/formal*100 for n in ordered]}


def main():
    candidates = pd.read_csv(ROOT/'data/development/VEC_2022_CANDIDATE_CLASSIFICATION.csv')
    flows = pd.read_csv(ROOT/'data/development/VEC_2022_DISTRIBUTIONS_LONG.csv')
    results = []
    for seat, group in candidates.groupby('Electorate'):
        categories = {key(r.CandidateName): r.BroadCategory for r in group.itertuples()}
        primary = {key(r.CandidateName): float(r.PrimaryVotes) for r in group.itertuples()}
        active = set(primary)
        evidence = {}
        for _, transfer in flows[flows.Electorate == seat].groupby('Round', sort=True):
            eliminated = resolve(transfer.EliminatedCandidate.iloc[0], categories)
            active.remove(eliminated)
            shares, candidate_shares = {}, {}
            parcel = float(transfer.TransferParcel.iloc[0])
            for row in transfer.itertuples():
                if not row.VotesTransferred:
                    continue
                recipient = resolve(row.RecipientCandidate, categories)
                category = categories[recipient]
                shares[category] = shares.get(category, 0)+row.VotesTransferred/parcel
                candidate_shares[recipient] = candidate_shares.get(recipient, 0)+row.VotesTransferred/parcel
            evidence[eliminated] = {'field': sorted(active), 'shares': shares, 'candidate_shares': candidate_shares}
        results.append(dict(seat=seat, **count_candidates(primary, categories, evidence, prefer_exact=True)))
    (ROOT/'reports/preference_review_2026_10_08/candidate_exact_precedence.json').write_text(json.dumps(results, indent=2)+'\n')
    complete = [r for r in results if r['status'] == 'complete']
    print('Complete:', len(complete), 'Unresolved:', len(results)-len(complete))
    print('Unresolved with same category continuing:', sum(r.get('same_category_remaining', False) for r in results))
    print([r for r in results if r['seat'] in ('Laverton', 'Kororoit', 'Pakenham', 'Morwell', 'Pascoe Vale', 'Ashwood', 'Yan Yean')])


if __name__ == '__main__':
    main()
