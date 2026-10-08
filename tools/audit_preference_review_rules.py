"""Trace actual parcel flows, rule selection and elimination survival gaps."""
from pathlib import Path
import sys
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.preference_review_trials import SCENARIOS, variant
from tools.compare_latent_ranking_shadow import build_primaries
from SRC.constants import PARTIES
from SRC.irv import initialise_parcels, parcel_totals, distribute_parcel_holder
from SRC.params_loader import load_params
from SRC.legacy_primary_loader import load_legacy_primary_inputs
from SRC.matrix_loader import load_synth_pref_matrices
from SRC.posterior_loader import load_posterior_scenarios
from SRC.federal_on_evidence_loader import apply_production_federal_on_evidence
from SRC.ideology_loader import load_ideology_prior
from SRC.seat_adjustments_loader import load_lower_seat_adjustments
from SRC.preference_engine import diagnose_preference_weights, get_on_special_prior

def main():
    out=ROOT/"reports/preference_review_2026_10_08"
    params=load_params(); inputs=load_legacy_primary_inputs(); matrices=load_synth_pref_matrices()
    posterior=apply_production_federal_on_evidence(load_posterior_scenarios()); ideology=load_ideology_prior()
    adjustments=load_lower_seat_adjustments(); rows=[]; parcels_out=[]
    for scenario,targets in SCENARIOS.items():
        primary,p=build_primaries(inputs,params,targets,adjustments)
        for name in ("reference","no_geography","no_synthetic_priority","simplified"):
            settings=variant(p,name)
            for district,group in primary.groupby("district"):
                matrix=matrices[district.upper()]["matrix"]; seat_type=group.iloc[0]["seat_type"]
                # Long-form primaries use party/vote columns.
                votes={row["party"]:float(row["primary_vote"]) for _,row in group.iterrows()}
                parcels=initialise_parcels(votes); alive=[party for party in PARTIES if votes.get(party,0)>0]; number=0
                while len(alive)>2:
                    totals=parcel_totals(parcels); ordered=sorted(alive,key=lambda party:totals[party])
                    holder=ordered[0]; continuing=[party for party in alive if party!=holder]; number+=1
                    diag,effective,origin_rows=distribute_parcel_holder(parcels,holder,continuing,matrix,seat_type,settings,posterior,ideology)
                    special=get_on_special_prior(holder,continuing,seat_type,settings) is not None
                    rows.append(dict(Scenario=scenario,Variant=name,District=district,Round=number,Eliminated=holder,AliveSet="+".join(sorted(continuing)),Basis=diag["basis"],SpecialAvailable=special,SpecialSelected=diag["basis"]=="ON special prior",EliminatedVote=totals[holder],SurvivalGap=totals[ordered[1]]-totals[holder],ONInField="ON" in alive,ONTransfer=effective.get("ON",0),Coverage=diag.get("aec_coverage")))
                    for origin in origin_rows:
                        origin_diag=diag if origin["origin"]==holder or diag["basis"]=="ON special prior" else diagnose_preference_weights(origin["origin"],continuing,matrix,seat_type,settings,posterior,ideology)
                        stages=origin_diag["stages"]
                        for i,stage in enumerate(stages):
                            if i==0 or stage.get("stage") not in ("final geography adjustment","final ON siphon","final minimum support floor","final share caps"): continue
                            before=stages[i-1]; on_change=float(stage.get("ON",0) or 0)-float(before.get("ON",0) or 0)
                            parcels_out.append(dict(Scenario=scenario,Variant=name,District=district,Round=number,Holder=holder,Origin=origin["origin"],ParcelVotes=origin["votes"],Basis=origin["basis"],Stage=stage["stage"],ONShareChange=on_change,ONVoteChange=on_change*origin["votes"]))
                    alive=continuing
    rounds=pd.DataFrame(rows); stages=pd.DataFrame(parcels_out)
    rounds.to_csv(out/"round_rule_audit.csv",index=False); stages.to_csv(out/"parcel_stage_audit.csv",index=False)
    summary=rounds.groupby(["Scenario","Variant","Basis"],as_index=False).agg(Rounds=("Round","size"),SpecialAvailable=("SpecialAvailable","sum"),SpecialSelected=("SpecialSelected","sum"))
    summary.to_csv(out/"rule_use_summary.csv",index=False)
    print(summary[summary.Variant.eq("reference")].to_string(index=False))
    print("Primary columns",primary.columns.tolist())

if __name__=="__main__": main()
