"""Held-out candidate-parcel category shares on exact broad fields only."""
import json
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.audit_vec_candidate_replay import key, resolve
from tools.validate_vec_conditional_flows import distance


def pooled_share(observations, target, subtype, minimum):
    matches = [r for r in observations if r['seat'] != target['seat'] and r['field'] == target['field']
               and (r['subtype'] == target['subtype'] if subtype else r['category'] == target['category'])]
    seats = {}
    for row in matches:
        seats.setdefault(row['seat'], []).append(row)
    if len(seats) < minimum:
        return None
    field = target['field']
    shares = {p: sum(sum(r['shares'].get(p, 0) for r in records)/len(records) for records in seats.values())/len(seats) for p in field}
    return shares, len(seats)


def load_observations():
    candidates = pd.read_csv(ROOT/'data/development/VEC_2022_CANDIDATE_CLASSIFICATION.csv')
    transfers = pd.read_csv(ROOT/'data/development/VEC_2022_DISTRIBUTIONS_LONG.csv')
    observations = []
    for seat, group in candidates.groupby('Electorate'):
        meta = {key(r.CandidateName): r for r in group.itertuples()}
        active = set(meta)
        for _, transfer in transfers[transfers.Electorate == seat].groupby('Round', sort=True):
            eliminated = resolve(transfer.EliminatedCandidate.iloc[0], meta)
            active.remove(eliminated)
            field = sorted({meta[n].BroadCategory for n in active})
            # No inference about synthetic ON from this historic test.
            if meta[eliminated].BroadCategory == 'ON' or 'ON' in field or len(field) < 2:
                continue
            shares = {}
            parcel = float(transfer.TransferParcel.iloc[0])
            for row in transfer.itertuples():
                if not row.VotesTransferred:
                    continue
                recipient = resolve(row.RecipientCandidate, meta)
                p = meta[recipient].BroadCategory
                shares[p] = shares.get(p, 0)+float(row.VotesTransferred)/parcel
            observations.append({'seat': seat, 'candidate': eliminated, 'category': meta[eliminated].BroadCategory,
                                 'subtype': str(meta[eliminated].CandidateSubtype), 'field': field, 'shares': shares})
    return observations


def main():
    observations = load_observations()
    summaries, detail = {}, []
    for minimum in (1, 3, 5):
        rows = []
        for target in observations:
            subtype = pooled_share(observations, target, True, minimum)
            broad = pooled_share(observations, target, False, minimum)
            if subtype is None or broad is None:
                continue
            row = {'seat': target['seat'], 'candidate': target['candidate'], 'subtype': target['subtype'], 'field': target['field'],
                   'same_category_alive': target['category'] in target['field'], 'minimum_seats': minimum,
                   'subtype_training_seats': subtype[1], 'subtype_error_pp': distance(subtype[0], target['shares'], target['field']),
                   'broad_error_pp': distance(broad[0], target['shares'], target['field'])}
            rows.append(row)
        summaries[str(minimum)] = {'eligible_parcels': len(observations), 'matched_parcels': len(rows),
                                  'subtype_error_pp': sum(r['subtype_error_pp'] for r in rows)/len(rows),
                                  'broad_error_pp': sum(r['broad_error_pp'] for r in rows)/len(rows),
                                  'same_category_alive_matched': sum(r['same_category_alive'] for r in rows)}
        detail.extend(rows)
    (ROOT/'reports/preference_review_2026_10_08/candidate_subtype_holdout.json').write_text(json.dumps({'summary': summaries, 'parcels': detail}, indent=2)+'\n')
    print(json.dumps(summaries, indent=2))


if __name__ == '__main__':
    main()
