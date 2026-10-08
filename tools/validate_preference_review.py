"""Actual-primary reconstruction and strict matrix leave-one-seat-out checks.

Pooled SCENARIO_STATS is excluded because its loader lacks seat membership.
This prevents a held-out seat leaking through an aggregate posterior.
"""
from pathlib import Path
import sys
import copy
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.preference_review_trials import variant
from tools.validate_leave_one_out import mean_matrix, actual_result
from SRC.params_loader import load_params
from SRC.matrix_loader import load_synth_pref_matrices
from SRC.ideology_loader import load_ideology_prior
from SRC.constants import PARTIES
from SRC.irv import run_irv_for_district
from SRC.lnp_precollapse_loader import apply_lnp_precollapse
from tools.trial_oth_matrix_rebuild import rebuild_oth_matrices

NAMES=("reference","no_incomplete_matrix_anchor","oth_params_rebuild","single_on_baseline","no_on_recipient_geography","no_non_on_recipient_geography","no_siphon","no_geography","no_constraints","no_synthetic_priority","simplified")

def main():
    out=ROOT/"reports"/"preference_review_2026_10_08"
    source=ROOT/"data/development/VEC_2022_CANDIDATE_CLASSIFICATION.csv"
    candidates=pd.read_csv(source)
    raw=candidates.groupby(["Electorate","BroadCategory"])["PrimaryVotes"].sum().unstack(fill_value=0).reindex(columns=PARTIES,fill_value=0)
    raw=raw.div(raw.sum(axis=1),axis=0).reset_index().rename(columns={"Electorate":"district"})
    raw=apply_lnp_precollapse(raw)
    raw["key"]=raw.district.str.upper()
    raw=raw.set_index("key")
    matrices=load_synth_pref_matrices(); params=load_params(); ideology=load_ideology_prior()
    rebuilt = rebuild_oth_matrices(matrices, params)
    baseline=pd.read_csv(ROOT/"data/raw/BASELINE_2CP.csv")
    baseline["key"]=baseline.district.str.upper(); baseline=baseline.set_index("key")
    rows=[]
    for district, own in matrices.items():
        key=district.upper()
        if key not in raw.index or key not in baseline.index: raise ValueError(f"Missing historical seat {district}")
        actual=actual_result(baseline.loc[key])
        if actual is None: raise ValueError(f"Missing final pair {district}")
        winner,runner,shares=actual
        others=[v for k,v in matrices.items() if k!=district]
        same=[v for k,v in matrices.items() if k!=district and v["seat_type"]==own["seat_type"]]
        votes={p:float(raw.loc[key,p]) for p in PARTIES}
        p=copy.deepcopy(params); p["scalar_params"]["SCENARIO_ON_PRIMARY"]=votes["ON"]*100
        for mode,matrix in (("own_matrix_reconstruction",own["matrix"]),("strict_loo_seat_class",mean_matrix(same or others))):
            for name in NAMES:
                trial_matrix = matrix
                if name == "oth_params_rebuild":
                    if mode == "own_matrix_reconstruction":
                        trial_matrix = rebuilt[district]["matrix"]
                    else:
                        training = [v for k,v in rebuilt.items() if k != district and v["seat_type"] == own["seat_type"]]
                        trial_matrix = mean_matrix(training or [v for k,v in rebuilt.items() if k != district])
                result=run_irv_for_district(votes,trial_matrix,own["seat_type"],variant(p,name),{},ideology)
                pair={result["winner"],result["runner_up"]}=={winner,runner}
                predicted=result["winner_pct"] if result["winner"]==winner else result["runner_up_pct"] if result["runner_up"]==winner else None
                rows.append(dict(District=district,Mode=mode,Variant=name,SeatType=own["seat_type"],WinnerCorrect=result["winner"]==winner,FinalPairCorrect=pair,PredictedWinner=result["winner"],ActualWinner=winner,Error=predicted-shares[winner] if pair else None))
    detail=pd.DataFrame(rows)
    # Report final-contest share errors in percentage points, not fractions.
    detail["Error"]=detail["Error"]*100
    summary=detail.groupby(["Mode","Variant"],as_index=False).agg(Seats=("District","size"),WinnerAccuracy=("WinnerCorrect","mean"),FinalPairAccuracy=("FinalPairCorrect","mean"),ComparablePairs=("Error","count"),MeanError=("Error","mean"),MAE=("Error",lambda s:s.abs().mean()),RMSE=("Error",lambda s:(s.pow(2).mean())**.5))
    detail.to_csv(out/"historical_validation_seats.csv",index=False)
    summary.to_csv(out/"historical_validation_summary.csv",index=False)
    print(summary.to_string(index=False))

if __name__=="__main__": main()
