"""Build the field ballot from a candidate roster. Rerun with the final VEC list.

Usage: python tools/build_candidate_field_ballot.py ROSTER.json STATUS
Second and later independents in a seat follow the existing classification
policy: the principal independent is IND and additional independents are OTH.
Principal independents come from REVIEWED_CANDIDATES.csv where reviewed.
"""
import json
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT/'data/development/candidate_field'
GROUPS = {'Australian Labor Party': 'ALP', 'Liberal': 'LNP', 'The Nationals': 'LNP',
          'The Greens': 'GRN', 'One Nation': 'ON', 'Independent': 'IND'}


def main(path, status):
    seats = json.loads(Path(path).read_text())['seats']
    reviewed = pd.read_csv(FOLDER/'REVIEWED_CANDIDATES.csv', keep_default_na=False)
    rows = []
    for seat in seats:
        principal = set(reviewed[reviewed.district.eq(seat['Electorate'])&reviewed.model_group.eq('IND')].candidate_name)
        independents = sorted(r['CandidateName'] for r in seat['Rows'] if r['OfficialParty'] == 'Independent')
        lead = next(iter(principal), independents[0] if independents else '')
        for row in seat['Rows']:
            group = GROUPS.get(row['OfficialParty'], 'OTH')
            if group == 'IND' and row['CandidateName'] != lead:
                group = 'OTH'
            rows.append(dict(district=seat['Electorate'], candidate_name=row['CandidateName'],
                             affiliation=row['OfficialParty'], model_group=group, roster_status=status))
    frame = pd.DataFrame(rows).sort_values(['district', 'candidate_name'])
    if frame.district.nunique() != 88:
        raise ValueError('Ballot must cover 88 districts')
    frame.to_csv(FOLDER/'BALLOT.csv', index=False)


if __name__ == '__main__':
    main(*sys.argv[1:3])
