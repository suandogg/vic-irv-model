"""Isolate proportional recipients using recorded category transfers/order.

Not a forecast: follows known eliminations and category shares, replacing only
the split among candidates within a recipient category. No ON insertion.
"""
import json
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.audit_vec_candidate_replay import key, resolve
from SRC.candidate_shadow import allocate_category_flow


def main():
    candidates = pd.read_csv(ROOT/'data/development/VEC_2022_CANDIDATE_CLASSIFICATION.csv')
    flows = pd.read_csv(ROOT/'data/development/VEC_2022_DISTRIBUTIONS_LONG.csv')
    records = []
    for seat, group in candidates.groupby('Electorate'):
        categories = {key(r.CandidateName): r.BroadCategory for r in group.itertuples()}
        actual = {key(r.CandidateName): float(r.PrimaryVotes) for r in group.itertuples()}
        shadow = actual.copy()
        active = set(actual)
        formal = sum(actual.values())
        different_lowest_rounds = []
        for number, transfer in flows[flows.Electorate == seat].groupby('Round', sort=True):
            eliminated = resolve(transfer.EliminatedCandidate.iloc[0], categories)
            if min(active, key=lambda n: (shadow[n], n)) != eliminated:
                different_lowest_rounds.append(int(number))
            active.remove(eliminated)
            shares = {}
            parcel = float(transfer.TransferParcel.iloc[0])
            for row in transfer.itertuples():
                if not row.VotesTransferred:
                    continue
                recipient = resolve(row.RecipientCandidate, categories)
                actual[recipient] += row.VotesTransferred
                category = categories[recipient]
                shares[category] = shares.get(category, 0)+row.VotesTransferred/parcel
            recipients = {n: {'category': categories[n], 'tally': shadow[n]} for n in active}
            movement = allocate_category_flow(shadow[eliminated], shares, recipients)
            shadow[eliminated] = actual[eliminated] = 0
            for recipient, amount in movement.items():
                shadow[recipient] += amount
            assert abs(sum(shadow.values())-formal) < 1e-6
        ordered = sorted(active, key=lambda n: shadow[n], reverse=True)
        actual_winner = max(active, key=lambda n: actual[n])
        records.append({'seat': seat, 'order_divergence_rounds': different_lowest_rounds,
                        'winner_correct_on_forced_order': ordered[0] == actual_winner,
                        'actual_winner_share_pct': actual[actual_winner]/formal*100,
                        'shadow_actual_winner_share_pct': shadow[actual_winner]/formal*100})
    target = ROOT/'reports/preference_review_2026_10_08/candidate_recipient_allocation.json'
    target.write_text(json.dumps(records, indent=2)+'\n')
    print('Seats:', len(records), 'with different lowest candidate:', sum(bool(r['order_divergence_rounds']) for r in records))
    print([r for r in records if r['seat'] in ('Laverton', 'Kororoit')])


if __name__ == '__main__':
    main()
