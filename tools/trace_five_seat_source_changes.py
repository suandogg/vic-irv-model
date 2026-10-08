"""Compare sources on identical reference-path fields and parcels.

Counterfactual flows are evaluated before distribution, holding each reference
parcel fixed. This isolates flow changes before changing the elimination path.
"""
from pathlib import Path
import sys
import copy
import json

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.preference_review_trials import SCENARIOS, variant
from tools.compare_latent_ranking_shadow import build_primaries
from SRC.trial_seat_panel import SEATS
from SRC.irv import initialise_parcels, parcel_totals, distribute_parcel_holder, trace_irv_for_district
from SRC.constants import PARTIES
from SRC.params_loader import load_params
from SRC.legacy_primary_loader import load_legacy_primary_inputs
from SRC.matrix_loader import load_synth_pref_matrices
from SRC.posterior_loader import load_posterior_scenarios
from SRC.federal_on_evidence_loader import apply_production_federal_on_evidence
from SRC.ideology_loader import load_ideology_prior
from SRC.seat_adjustments_loader import load_lower_seat_adjustments
from SRC.preference_engine import diagnose_preference_weights

def sources(diag):
    return list(dict.fromkeys(s.get("basis") for s in diag["stages"] if s.get("stage") in ("basis selected","single ON baseline trial","federal ON evidence trial")))

def main():
    params=load_params(); matrices=load_synth_pref_matrices()
    posterior=apply_production_federal_on_evidence(load_posterior_scenarios())
    ideology=load_ideology_prior()
    primary,p=build_primaries(load_legacy_primary_inputs(),params,SCENARIOS["ON18"],load_lower_seat_adjustments())
    trial=variant(p,"matrix_source_only"); records=[]; paths={}
    for seat in SEATS:
        group=primary.loc[primary.district.eq(seat)]
        votes={r.party:float(r.primary_vote) for r in group.itertuples()}
        obj=matrices[seat.upper()]; matrix=obj["matrix"]; cls=obj["seat_type"]
        paths[seat]={name:trace_irv_for_district(votes,matrix,cls,settings,posterior,ideology) for name,settings in (("reference",p),("source_only",trial))}
        parcels=initialise_parcels(votes); alive=[party for party in PARTIES if votes.get(party,0)>0]; number=0
        while len(alive)>2:
            totals=parcel_totals(parcels); holder=min(alive,key=lambda party:totals[party]); continuing=[party for party in alive if party!=holder]; number+=1
            original=copy.deepcopy(parcels)
            refdiag,refflow,origins=distribute_parcel_holder(parcels,holder,continuing,matrix,cls,p,posterior,ideology)
            trialdiag,trialflow,_=distribute_parcel_holder(copy.deepcopy(original),holder,continuing,matrix,cls,trial,posterior,ideology)
            parcel_records=[]
            for origin in origins:
                party=origin["origin"]
                rd=refdiag if party==holder or refdiag["basis"]=="ON special prior" else diagnose_preference_weights(party,continuing,matrix,cls,p,posterior,ideology)
                td=trialdiag if party==holder or trialdiag["basis"]=="ON special prior" else diagnose_preference_weights(party,continuing,matrix,cls,trial,posterior,ideology)
                parcel_records.append(dict(Origin=party,Votes=origin["votes"],ReferenceSources=sources(rd),TrialSources=sources(td),ReferenceFlows=rd["final_flows"],TrialFlows=td["final_flows"]))
            change={party:100*(trialflow.get(party,0)-refflow.get(party,0)) for party in continuing}
            vote_change={party:value*totals[holder] for party,value in change.items()}
            records.append(dict(Seat=seat,SeatType=cls,Round=number,Holder=holder,AliveSet="+".join(sorted(continuing)),EliminatedSeatVote=totals[holder],ReferenceBasis=refdiag["basis"],TrialBasis=trialdiag["basis"],ReferenceEffectiveFlow=refflow,TrialEffectiveFlow=trialflow,ChangePP=change,SeatVoteChangePP=vote_change,Changed=any(abs(v)>1e-8 for v in change.values()),Material=any(abs(v)>1e-5 for v in vote_change.values()),Parcels=parcel_records))
            alive=continuing
    out=ROOT/"reports/preference_review_2026_10_08/five_seat_source_trace.json"
    out.write_text(json.dumps(dict(Scenario="ON18",Method="Counterfactual on fixed reference-path parcels; not alternate-path attribution",Rounds=records,ActualPaths=paths),indent=2)+"\n")
    for seat in SEATS:
        changed=[r for r in records if r["Seat"]==seat and r["Material"]]
        first=changed[0] if changed else None
        print(json.dumps(dict(Seat=seat,FirstChangedRound=first),indent=2))

if __name__=="__main__": main()
