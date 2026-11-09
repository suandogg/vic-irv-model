"""Build the field ballot and default independent strengths from a candidate roster.

Usage: python tools/build_candidate_field_ballot.py ROSTER.csv STATUS
ROSTER.csv has district, candidate_name and affiliation columns. Independents
have the affiliation 'No registered party'. Second and later independents in a
seat follow the classification policy: the principal independent is IND and the
rest are OTH. The principal is the reviewed candidate where one exists, otherwise
the candidate with the strongest default.

An unreviewed principal independent never inherits the old IND surface. Their
default strength comes from VEC 2014-2022 history: a same-seat 2022 independent
keeps 0.86 of their share (10-90%: 0.37-1.62, n=19); anyone else gets the
first-time independent distribution (median 2.2%, 10-90%: 0.5-9.4%, n=176).
"""
import re
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT/'data/development/candidate_field'
GROUPS = {'Australian Labor Party - Victorian Branch': 'ALP',
          'Liberal Party of Australia - Victorian Division': 'LNP',
          'National Party of Australia - Victoria': 'LNP',
          'Australian Greens Victoria': 'GRN', 'One Nation Victoria': 'ON',
          'No registered party': 'IND'}
RETENTION = (0.372, 0.86, 1.623)
FIRST_TIME_PP = (0.49, 2.17, 9.43)


def name_key(name):
    """'BRIFFA, Tony' and 'Tony Briffa' give the same key."""
    name = str(name).strip().upper()
    if ',' in name:
        surname, _, given = name.partition(',')
    else:
        parts = name.split()
        surname, given = (parts[-1], parts[0]) if parts else ('', '')
    given = given.strip().split(' ')[0] if given.strip() else ''
    return re.sub(r'\W', '', surname)+'|'+re.sub(r'\W', '', given)[:4]


def history_2022():
    frame = pd.read_csv(ROOT/'data/development/VEC_2022_CANDIDATE_CLASSIFICATION.csv')
    frame = frame[frame.OfficialParty.isna()]
    return {(r.Electorate, name_key(r.CandidateName)): float(r.PrimaryShare) for r in frame.itertuples()}


def default_strength(district, name, history):
    previous = history.get((district, name_key(name)))
    if previous:
        low, mid, high = (100*previous*x for x in RETENTION)
        return dict(median_pp=round(mid, 3), p10_pp=round(low, 3), p90_pp=round(min(high, 60), 3),
                    prior_vote_pp=round(100*previous, 3),
                    basis=f'Default: same-seat 2022 independent at {100*previous:.2f}% times retention 0.86')
    low, mid, high = FIRST_TIME_PP
    return dict(median_pp=mid, p10_pp=low, p90_pp=high, prior_vote_pp='',
                basis='Default: first-time independent distribution, VEC 2018-2022')


def main(path, status):
    roster = pd.read_csv(path, keep_default_na=False)
    reviewed = pd.read_csv(FOLDER/'REVIEWED_CANDIDATES.csv', keep_default_na=False)
    history = history_2022()
    rows, defaults = [], []
    for district, seat in roster.groupby('district', sort=True):
        independents = seat[seat.affiliation.eq('No registered party')].candidate_name.tolist()
        chosen = reviewed[reviewed.district.eq(district)&reviewed.model_group.eq('IND')]
        keys = {name_key(n) for n in chosen.candidate_name}
        lead = next((n for n in independents if name_key(n) in keys), None)
        if chosen.shape[0] and lead is None:
            raise ValueError(f'{district}: reviewed independent is not on the roster')
        if lead is None and independents:
            lead = max(independents, key=lambda n: (default_strength(district, n, history)['median_pp'], n))
            slug = re.sub(r'\W+', '_', f'{district}_{lead}'.lower()).strip('_')
            defaults.append(dict(district=district, candidate_id=slug, candidate_name=lead, kind='entrant',
                                 model_group='IND', brand='', brand_share='',
                                 **default_strength(district, lead, history)))
        for row in seat.itertuples():
            group = GROUPS.get(row.affiliation, 'OTH')
            if group == 'IND' and row.candidate_name != lead:
                group = 'OTH'
            rows.append(dict(district=district, candidate_name=row.candidate_name,
                             affiliation=row.affiliation, model_group=group, roster_status=status))
    frame = pd.DataFrame(rows).sort_values(['district', 'candidate_name'])
    if frame.district.nunique() != 88:
        raise ValueError('Ballot must cover 88 districts')
    frame.to_csv(FOLDER/'BALLOT.csv', index=False)
    columns = ['district', 'candidate_id', 'candidate_name', 'kind', 'model_group', 'median_pp', 'p10_pp',
               'p90_pp', 'brand', 'brand_share', 'prior_vote_pp', 'basis']
    pd.DataFrame(defaults, columns=columns).to_csv(FOLDER/'DEFAULT_IND_STRENGTHS.csv', index=False)


if __name__ == '__main__':
    main(*sys.argv[1:3])
