"""Independent endpoint diagnostic, not a calibration or clean held-out score.

Replays proportional primary-origin transport from AEC aggregate rounds and
compares actual final-pair endpoints with Antony Green's compilation of AEC flows.
Only Victorian divisions and exact finalist candidates are compared.
"""
from pathlib import Path
import sys
import json
import hashlib
import importlib.util
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('/Users/callumrees/Desktop/federal_irv_model')
OUT = ROOT / 'reports/federal_endpoint_audit_2026_10_10'


def replay(rounds):
    base = rounds[rounds.CountNumber.eq(0)].copy()
    primary = base.set_index('CandidateID').PrimaryVotes.astype(float).to_dict()
    holdings = {cid: {origin: value if cid == origin else 0.0
                      for origin, value in primary.items()} for cid in primary}
    for count in sorted(rounds.loc[rounds.CountNumber.gt(0), 'CountNumber'].unique()):
        group = rounds[rounds.CountNumber.eq(count)]
        excluded = group[group.IsExcludedThisCount.astype(str).str.lower().eq('true')]
        if len(excluded) != 1:
            raise ValueError('Expected one excluded candidate')
        row = excluded.iloc[0]
        cid, tally = int(row.CandidateID), float(row.PreferenceCountBefore)
        if abs(sum(holdings[cid].values()) - tally) > 1e-5:
            raise ValueError('Mixed-pile reconstruction does not reconcile')
        recipients = group[group.TransferCount.gt(0)]
        if abs(recipients.TransferCount.sum() - tally) > 1e-5:
            raise ValueError('Round transfers do not reconcile')
        for recipient in recipients.itertuples():
            share = float(recipient.TransferCount) / tally
            for origin, votes in holdings[cid].items():
                holdings[int(recipient.CandidateID)][origin] += votes * share
        holdings[cid] = {origin: 0.0 for origin in primary}
    finalists = [cid for cid, origins in holdings.items() if sum(origins.values()) > 1e-6]
    if len(finalists) != 2:
        raise ValueError(f'Expected two actual finalists, found {finalists}')
    for origin, votes in primary.items():
        if abs(sum(holdings[cid][origin] for cid in finalists) - votes) > 1e-5:
            raise ValueError('Primary-origin mass lost')
    return base, finalists, holdings


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('aec_report_parser', SOURCE/'build_candidate_classification.py')
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    report = parser.parse_preference_flow_report(SOURCE/'FED2025_PreferenceFlowReport.pdf')
    report = report[report.State.eq('VIC') & ~report.IsTwoPartyTable].copy()
    rounds = pd.read_csv(SOURCE/'data/derived/AEC_CANDIDATE_ROUNDS_LONG.csv')
    rounds = rounds[rounds.State.eq('VIC')]
    # Verify the derived count values against the official source, not just totals.
    raw = pd.read_csv(SOURCE/'HouseDopByDivisionDownload-31496.csv', skiprows=1)
    raw = raw[raw.StateAb.eq('VIC') & raw.CalculationType.eq('Preference Count')]
    checked = rounds.merge(raw[['CandidateID','CountNumber','CalculationValue']],
                           on=['CandidateID','CountNumber'],validate='one_to_one')
    if len(checked) != len(rounds) or not np.allclose(checked.PreferenceCountAfter, checked.CalculationValue, atol=0, rtol=0):
        raise ValueError('Derived rounds differ from official AEC counts')
    results, skipped = [], []
    for seat, group in rounds.groupby('Electorate'):
        base, finalists, holdings = replay(group)
        positions = base.set_index('BallotPosition').CandidateID.astype(int).to_dict()
        names = base.set_index('CandidateID').CandidateName.to_dict()
        categories = base.set_index('CandidateID').ModelCategory.to_dict()
        for row in report[report.Electorate.eq(seat)].itertuples():
            a, b = positions[row.FinalAPosition], positions[row.FinalBPosition]
            origin = positions[row.BallotPosition]
            if set(finalists) != {a,b}:
                skipped.append(dict(Seat=seat, CandidateID=origin, Reason='Report pair differs from actual DOP finalists'))
                continue
            if origin in finalists:
                continue
            primary = float(base.loc[base.CandidateID.eq(origin),'PrimaryVotes'].iloc[0])
            if row.ToAVotes + row.ToBVotes != row.FlowVotes or primary != row.FlowVotes:
                raise ValueError(f'Official origin denominator mismatch: {seat}/{origin}')
            actual = row.ToAVotes / row.FlowVotes
            predicted = holdings[a][origin] / primary
            results.append(dict(Seat=seat,CandidateID=origin,Candidate=names[origin],
                Category=categories[origin],PrimaryVotes=primary,FinalA=names[a],FinalB=names[b],
                OfficialShareA=actual,ReconstructedShareA=predicted,
                ErrorPP=100*(predicted-actual),AbsoluteErrorPP=100*abs(predicted-actual),
                SourcePage=row.SourceFlowPage))
    result = pd.DataFrame(results)
    if result.empty:
        raise ValueError('No comparable official endpoints')
    result.sort_values('AbsoluteErrorPP',ascending=False).to_csv(OUT/'candidate_endpoints.csv',index=False)
    imported = pd.read_csv(ROOT/'data/development/FEDERAL_VIC_ON_SEAT_FLOWS.csv')
    endpoint_rows = []
    for (seat, origin, alive), group in imported.groupby(['Seat','Eliminated','AliveSet']):
        candidates = result[result.Seat.eq(seat) & result.Category.eq(origin)]
        if candidates.empty or len(str(alive).split('+')) != 2:
            continue
        seat_base = rounds[rounds.Electorate.eq(seat) & rounds.CountNumber.eq(0)]
        names_to_category = seat_base.set_index('CandidateName').ModelCategory.to_dict()
        a = names_to_category[candidates.iloc[0].FinalA]
        b = names_to_category[candidates.iloc[0].FinalB]
        if set(str(alive).split('+')) != {a,b} or a == b:
            continue
        expected_n = int(seat_base.ModelCategory.eq(origin).sum())
        if len(candidates) != expected_n:
            raise ValueError('Incomplete category endpoint benchmark')
        actual = np.average(candidates.OfficialShareA,weights=candidates.PrimaryVotes)
        predicted = float(group.loc[group.Recipient.eq(a),'Share'].iloc[0])
        endpoint_rows.append(dict(Seat=seat,Origin=origin,AliveSet=alive,Recipient=a,
            OfficialShare=actual,ImportedShare=predicted,ErrorPP=100*(predicted-actual),
            AbsoluteErrorPP=100*abs(predicted-actual),Candidates=len(candidates)))
    endpoints = pd.DataFrame(endpoint_rows)
    endpoints.to_csv(OUT/'imported_exact_pair_endpoints.csv',index=False)
    pd.DataFrame(skipped).to_csv(OUT/'excluded_pairs.csv',index=False)
    summary = result.groupby('Category').apply(lambda g: pd.Series(dict(
        Candidates=len(g),Seats=g.Seat.nunique(),MeanAbsErrorPP=g.AbsoluteErrorPP.mean(),
        VoteWeightedAbsErrorPP=np.average(g.AbsoluteErrorPP,weights=g.PrimaryVotes),
        MaxAbsErrorPP=g.AbsoluteErrorPP.max())), include_groups=False).reset_index()
    summary.to_csv(OUT/'category_summary.csv',index=False)
    # The endpoint PDF was already used in candidate classification, not directly
    # by the proportional transport algorithm. This is not untouched holdout data.
    manifest = {str(p.relative_to(SOURCE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [
        SOURCE/'FED2025_PreferenceFlowReport.pdf',SOURCE/'build_candidate_classification.py',
        SOURCE/'build_shadow_category_flows.py',SOURCE/'HouseDopByDivisionDownload-31496.csv',
        SOURCE/'data/derived/AEC_CANDIDATE_ROUNDS_LONG.csv']}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    notes = f'''# Federal endpoint reconstruction audit

{len(result)} non-finalist candidate endpoints in {result.Seat.nunique()} Victorian federal divisions.
Actual final-pair candidates matched exactly. Derived preference counts were
checked cell-for-cell against the official AEC DOP download. All reconstructed
primary-origin amounts reconcile. Endpoint counts come from Antony Green's
February 2026 compilation of AEC flows. Endpoint fractions use integer counts,
not rounded percentages. Worst discrepancies are in candidate_endpoints.csv.

The PDF had already supplied TPP/TCP metadata and suggested ideology profiles in
candidate classification. The category reconstruction itself uses aggregate DOP
rounds and proportional mixed-pile transport, not those endpoint counts. Therefore
this is an independent endpoint measurement check of that reconstruction assumption,
NOT a pristine held-out forecasting test. Category definitions may have been
influenced by report-based profiles or subjective review. No parameters were fitted.

Individual-candidate errors isolate the mixed-pile approximation before grouping.
Category averages must not be interpreted as new ON-versus-ALP or ON-versus-IND
evidence when those candidates were not the actual finalists. No state preference
rules or federal evidence weights were changed by this audit.
'''
    (OUT/'README.md').write_text(notes)
    print(notes)
    print(summary.to_string(index=False))
    print('Imported exact-pair endpoint checks:')
    print(endpoints.to_string(index=False))
    print(result.nlargest(8,'AbsoluteErrorPP')[['Seat','Candidate','Category','AbsoluteErrorPP']].to_string(index=False))


if __name__ == '__main__':
    main()
