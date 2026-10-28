"""Describe independent historical lean changes, NOT fitted nowcast SDs."""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from SRC.constants import PARTIES
DATA=ROOT/'data/research/historical_primaries_2026_10_29'
OUT=ROOT/'reports/historical_lean_evidence_2026_10_29'


def main():
    candidates=pd.read_csv(DATA/'candidates.csv',keep_default_na=False)
    panel=pd.read_csv(DATA/'district_primaries.csv')
    old=panel.query('Year == 2014').set_index('District')
    new=panel.query('Year == 2018').set_index('District')
    if len(old)!=88 or set(old.index)!=set(new.index):
        raise ValueError('Historical district panel not aligned')
    new=new.loc[old.index]
    state=candidates.groupby(['Year','BroadCategory']).Votes.sum().unstack(fill_value=0)
    state=state.reindex(columns=PARTIES,fill_value=0)
    state=state.div(state.sum(axis=1),axis=0)
    rows=[]
    for seat in old.index:
        before=candidates[candidates.Year.eq(2014)&candidates.District.eq(seat)]
        after=candidates[candidates.Year.eq(2018)&candidates.District.eq(seat)]
        common_flags=dict(
            Both_elections_major_parties_present=all(
                before.BroadCategory.eq(p).any() and after.BroadCategory.eq(p).any()
                for p in ['ALP','LNP','GRN']),
            Multiple_coalition_candidates=bool(old.loc[seat,'CoalitionCandidateCount']>1 or new.loc[seat,'CoalitionCandidateCount']>1),
            Multiple_independents=bool(old.loc[seat,'IndependentCount']>1 or new.loc[seat,'IndependentCount']>1),
            Largest_independent_share=max(old.loc[seat,'LargestIndependentShare'],new.loc[seat,'LargestIndependentShare']))
        for party in PARTIES:
            b=before[before.BroadCategory.eq(party)]
            a=after[after.BroadCategory.eq(party)]
            names_before=set(b.Candidate.str.upper().str.replace(r'\W','',regex=True))
            names_after=set(a.Candidate.str.upper().str.replace(r'\W','',regex=True))
            lean_old=float(old.loc[seat,party]-state.loc[2014,party])
            lean_new=float(new.loc[seat,party]-state.loc[2018,party])
            rows.append(dict(District=seat,Party=party,Share_2014=old.loc[seat,party],Share_2018=new.loc[seat,party],
                Lean_2014_pp=100*lean_old,Lean_2018_pp=100*lean_new,
                Lean_change_pp=100*(lean_new-lean_old),
                Present_both=bool(len(a) and len(b)),Candidate_set_changed=names_before!=names_after,
                Candidate_names_2014=' | '.join(sorted(names_before)),
                Candidate_names_2018=' | '.join(sorted(names_after)),**common_flags))
    detail=pd.DataFrame(rows)
    detail['Major_field_context_subset']=(detail.Both_elections_major_parties_present
        &~detail.Multiple_coalition_candidates&detail.Largest_independent_share.lt(.1))
    # The 10% flag is a transparent descriptive split, not a calibrated cutoff.
    records=[]
    subsets={'All historical districts':detail,
        'Present both':detail[detail.Present_both],
        'Major field; single Coalition; no IND >=10%':detail[detail.Major_field_context_subset]}
    for label,table in subsets.items():
        for party in PARTIES:
            x=table.loc[table.Party.eq(party),'Lean_change_pp']
            records.append(dict(Subset=label,Party=party,Districts=len(x),
                Mean_pp=float(x.mean()) if len(x) else None,
                SD_pp=float(x.std(ddof=1)) if len(x)>1 else None,
                Median_absolute_pp=float(x.abs().median()) if len(x) else None,
                Minimum_pp=float(x.min()) if len(x) else None,
                Maximum_pp=float(x.max()) if len(x) else None,
                Use_for_ON_calibration=False))
    OUT.mkdir(exist_ok=True)
    detail.to_csv(OUT/'lean_changes.csv',index=False)
    pd.DataFrame(records).to_csv(OUT/'descriptive_summary.csv',index=False)
    for label,subset in [('all',detail),('major_field',detail[detail.Major_field_context_subset])]:
        matrix=subset.pivot(index='District',columns='Party',values='Lean_change_pp')
        matrix[['ALP','LNP','GRN']].corr().to_csv(OUT/(label+'_major_party_correlation.csv'))
    detail.assign(Absolute_change_pp=detail.Lean_change_pp.abs()).sort_values(
        'Absolute_change_pp',ascending=False).to_csv(OUT/'ranked_context_changes.csv',index=False)
    (OUT/'method.json').write_text(json.dumps(dict(
        definition='(2018 district share - 2018 statewide share) - (2014 district share - 2014 statewide share)',
        statewide_convention='Formal-vote weighted official statewide share; descriptive only, not a change to production equal-seat balancing',
        observation='One four-year historical electoral transition, 88 common-boundary districts',
        context_split='All three established parties present at both elections; no multiple Coalition candidates; no individual independent reaching 10% in either election. The 10% split is descriptive, not estimated.',
        classification='All official-label independents aggregated. Do not substitute for production principal-IND classification.',
        warning='Realised lean movement combines structural, regional, candidate and local effects. Do not apply each full SD independently to every forecast layer. ON absent, no ON calibration. No current boundary mapping inferred.'),indent=2))
    print(pd.DataFrame(records).to_string(index=False))
    print('\nLargest established-party lean changes:')
    print(detail[detail.Party.isin(['ALP','LNP','GRN'])].assign(
        Abs=lambda x:x.Lean_change_pp.abs()).nlargest(10,'Abs')[
            ['District','Party','Lean_change_pp','Candidate_set_changed','Largest_independent_share']].to_string(index=False))


if __name__=='__main__':
    main()
