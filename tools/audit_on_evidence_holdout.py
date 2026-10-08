"""Seat-blocked tests of reconstructed Victorian federal category flows.

No production settings or source tables are written. All pooling excludes the
held-out seat before estimating means, votes or variance. This is not a test
against observed full ballot rankings or state-election outcomes.
"""
from pathlib import Path
import sys
import json
import math
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from SRC.matrix_loader import load_synth_pref_matrices
from SRC.federal_on_evidence_loader import load_federal_on_config

SOURCE = ROOT / "data/development/FEDERAL_VIC_ON_SEAT_FLOWS.csv"
OUT = ROOT / "reports/preference_review_2026_10_08/federal_holdout.json"

def validate_source(raw):
    required = {"Seat", "State", "Eliminated", "AliveSet", "Recipient", "Share", "Votes", "ScenarioTotal", "Method", "VoteBasis", "Source"}
    if not required.issubset(raw.columns):
        raise ValueError(f"Missing columns: {sorted(required-set(raw.columns))}")
    if not raw.State.eq("VIC").all():
        raise ValueError("Non-Victorian records")
    if raw.duplicated(["Seat", "Eliminated", "AliveSet", "Recipient"]).any():
        raise ValueError("Duplicate seat-scenario-recipient records")
    for key, group in raw.groupby(["Seat", "Eliminated", "AliveSet"]):
        if set(group.Recipient) != set(key[2].split("+")):
            raise ValueError(f"Incomplete destination set: {key}")
        if group.ScenarioTotal.nunique()!=1 or group.ScenarioTotal.iloc[0]<=0:
            raise ValueError(f"Conflicting denominator: {key}")
        if not math.isclose(group.Share.sum(),1,abs_tol=1e-8):
            raise ValueError(f"Shares do not sum to one: {key}")
        for row in group.itertuples():
            if not 0 <= row.Share <= 1 or not math.isclose(row.Votes/row.ScenarioTotal,row.Share,abs_tol=1e-8):
                raise ValueError(f"Inconsistent share: {key}")

def predict(training, recipients, method):
    if training.empty:
        return None
    n = training.Seat.nunique()
    if method=="uniform":
        return {p:1/len(recipients) for p in recipients}
    if method=="vote_pool":
        totals=training.groupby("Seat").ScenarioTotal.first().sum()
        return {p:float(training.loc[training.Recipient.eq(p),"Votes"].sum()/totals) for p in recipients}
    means=training.groupby("Recipient").Share.mean()
    weight=n/(n+20) if method=="equal_pool_shrunk_uniform_20" else 1
    return {p:weight*float(means[p])+(1-weight)/len(recipients) for p in recipients}

def main():
    raw=pd.read_csv(SOURCE); validate_source(raw)
    predictions=[]; fields=[]
    for (elim,alive), group in raw.groupby(["Eliminated","AliveSet"]):
        seats=sorted(group.Seat.unique()); recipients=alive.split("+")
        fields.append(dict(Eliminated=elim,AliveSet=alive,Seats=len(seats),Testable=len(seats)>=2,ProductionMinimumAfterHoldout=len(seats)-1>=2))
        if len(seats)<2:
            continue
        for seat in seats:
            train=group.loc[~group.Seat.eq(seat)]
            actual=group.loc[group.Seat.eq(seat)].set_index("Recipient").Share
            assert seat not in set(train.Seat)
            for method in ("uniform","equal_pool","vote_pool","equal_pool_shrunk_uniform_20"):
                pred=predict(train,recipients,method)
                errors=[pred[p]-float(actual[p]) for p in recipients]
                predictions.append(dict(Seat=seat,Eliminated=elim,AliveSet=alive,Method=method,TrainingSeats=train.Seat.nunique(),MeanAbsErrorPP=100*sum(abs(e) for e in errors)/len(errors),MeanSquaredErrorPP2=10000*sum(e*e for e in errors)/len(errors),ONErrorPP=100*(pred["ON"]-float(actual["ON"])) if "ON" in recipients else None,Prediction=pred,Actual={p:float(actual[p]) for p in recipients}))
    summaries=[]
    for method in sorted({r["Method"] for r in predictions}):
        for scope in ("all_testable","production_eligible_after_holdout"):
            selected=[r for r in predictions if r["Method"]==method and (scope=="all_testable" or r["TrainingSeats"]>=2)]
            if not selected: continue
            byseat={seat:[r for r in selected if r["Seat"]==seat] for seat in sorted({r["Seat"] for r in selected})}
            seat_mae=[sum(r["MeanAbsErrorPP"] for r in rows)/len(rows) for rows in byseat.values()]
            on=[r["ONErrorPP"] for r in selected if r["ONErrorPP"] is not None]
            summaries.append(dict(Method=method,Scope=scope,Seats=len(byseat),SeatScenarios=len(selected),SeatBalancedMAEPP=sum(seat_mae)/len(seat_mae),ScenarioBalancedMAEPP=sum(r["MeanAbsErrorPP"] for r in selected)/len(selected),ONRecipientMAEPP=sum(abs(e) for e in on)/len(on) if on else None,ONRecipientBiasPP=sum(on)/len(on) if on else None))
    matrices=load_synth_pref_matrices()
    positive_to_on=sum(float(row.get("ON",0) or 0)>0 for obj in matrices.values() for origin,row in obj["matrix"].items() if origin!="ON")
    inventory=dict(SourceFile=SOURCE.name,Rows=len(raw),Seats=raw.Seat.nunique(),SeatScenarios=len(raw.groupby(["Seat","Eliminated","AliveSet"])),Fields=len(fields),SingletonFields=sum(f["Seats"]==1 for f in fields),Methods=sorted(raw.Method.unique()),VoteBasis=sorted(raw.VoteBasis.unique()),Sources=sorted(raw.Source.unique()),SyntheticMatrixSeats=len(matrices),NonONRowsWithPositiveON=positive_to_on,FederalConfig=load_federal_on_config())
    OUT.write_text(json.dumps(dict(Inventory=inventory,Fields=fields,Summary=summaries,Predictions=predictions),indent=2)+"\n")
    print(json.dumps(dict(Inventory=inventory,Summary=summaries),indent=2))

if __name__=="__main__": main()
