"""Seat-count sensitivity only: not an estimate of unobserved heterogeneity."""
from pathlib import Path
import copy
import pandas as pd
from SRC.posterior_loader import norm_alive_set

ROOT=Path(__file__).resolve().parents[1]

def seat_count_trial(posterior, prior_seats):
    raw=pd.read_csv(ROOT/"data/raw/SCENARIO_STATS.csv")
    raw["key"]=raw.Eliminated.str.upper()+"|"+raw.AliveSet.map(norm_alive_set)
    out=copy.deepcopy(posterior)
    for key,group in raw.groupby("key"):
        if key not in out or out[key].get("__federal_on_trial__"): continue
        counts=group.Seats.dropna().unique()
        if len(counts)!=1: raise ValueError(f"Inconsistent scenario seat count: {key}")
        seats=float(counts[0])
        if seats<1: raise ValueError(f"Invalid evidence seats: {key}")
        out[key]["__trial_reliability_override__"]=seats/(seats+prior_seats)
        out[key]["__evidence_seats__"]=seats
    return out
