"""Replay recorded transfers; no preference extrapolation or ON insertion."""
import json
import re
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]


def key(value):
    return re.sub(r'\s+', ' ', str(value).strip()).upper()


def resolve(value, names):
    name = key(value)
    if name in names:
        return name
    surname, given = name.split(',', 1)
    matches = [n for n in names if n.split(',', 1)[0] == surname and n.split(',', 1)[1].strip().startswith(given.strip()[:1])]
    if len(matches) != 1:
        raise ValueError(f'Unresolved candidate {value}')
    return matches[0]


def main():
    candidates = pd.read_csv(ROOT/'data/development/VEC_2022_CANDIDATE_CLASSIFICATION.csv')
    flows = pd.read_csv(ROOT/'data/development/VEC_2022_DISTRIBUTIONS_LONG.csv')
    results = []
    for seat, group in candidates.groupby('Electorate'):
        metadata = {key(r.CandidateName): r.BroadCategory for r in group.itertuples()}
        totals = {key(r.CandidateName): float(r.PrimaryVotes) for r in group.itertuples()}
        active = set(totals)
        formal = sum(totals.values())
        rounds = []
        for number, transfer in flows[flows.Electorate == seat].groupby('Round', sort=True):
            eliminated = resolve(transfer.EliminatedCandidate.iloc[0], metadata)
            parcel = float(transfer.TransferParcel.iloc[0])
            if eliminated not in active or abs(totals[eliminated]-parcel) > max(25, .005*parcel):
                raise ValueError(f'Invalid recorded parcel {seat}/{number}')
            if abs(transfer.VotesTransferred.sum()-parcel) > 1:
                raise ValueError(f'Transfers do not conserve votes {seat}/{number}')
            active.remove(eliminated)
            totals[eliminated] = 0
            for row in transfer.itertuples():
                if not row.VotesTransferred:
                    continue
                recipient = resolve(row.RecipientCandidate, metadata)
                if row.VotesTransferred and recipient not in active:
                    raise ValueError(f'Transfer to inactive candidate {seat}/{number}')
                totals[recipient] += float(row.VotesTransferred)
            assert abs(sum(totals.values())-formal) < 1e-6
            categories = {p: sum(totals[n] for n in active if metadata[n] == p)/formal*100 for p in set(metadata.values())}
            rounds.append({'round': int(number), 'eliminated': eliminated, 'category': metadata[eliminated], 'remaining_candidates': len(active), 'category_totals_pct': categories})
        final = sorted(active, key=lambda n: totals[n], reverse=True)
        results.append({'seat': seat, 'candidate_count': len(metadata), 'OTH_candidate_count': sum(p == 'OTH' for p in metadata.values()),
                        'final_candidates': final, 'final_categories': [metadata[n] for n in final], 'final_shares_pct': [totals[n]/formal*100 for n in final], 'rounds': rounds})
    (ROOT/'reports/preference_review_2026_10_08/vec_candidate_replay.json').write_text(json.dumps(results, indent=2)+'\n')
    print('Conserved vote totals across', len(results), 'recorded seat replays')
    for r in results:
        if r['seat'] in ('Laverton', 'Kororoit'):
            print(json.dumps(r, indent=2))


if __name__ == '__main__':
    main()
