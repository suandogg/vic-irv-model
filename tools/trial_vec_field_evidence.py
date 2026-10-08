"""Attach field-keyed evidence without replacing general-purpose matrix rows."""
import copy
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def attach_vec_fields(matrices):
    result = copy.deepcopy(matrices)
    flows = pd.read_csv(ROOT / "data/development/VEC_2022_CATEGORY_FLOWS_LONG.csv")
    for (seat, origin), group in flows.groupby(["Electorate", "EliminatedCategory"]):
        field = set(group.AliveSetAfter.iloc[0].split("+"))
        if group.AliveSetAfter.nunique() != 1 or origin in field:
            raise ValueError(f"Invalid extracted field: {seat}/{origin}")
        # Native ON cases are a separate evidence comparison, not this trial.
        if origin == "ON" or "ON" in field:
            continue
        shares = dict(zip(group.RecipientCategory, group.Share))
        if abs(sum(shares.values())-1) > 1e-8 or not set(shares).issubset(field):
            raise ValueError(f"Invalid extracted shares: {seat}/{origin}")
        key = seat.upper()
        if key not in result:
            raise ValueError(f"Unknown extracted seat: {seat}")
        result[key]["matrix"].setdefault("__vec_field_rows__", {})[origin] = {
            "field": sorted(field), "shares": shares,
            "round": int(group.CategoryExitRound.iloc[0]),
            "primary_votes": int(group.CategoryPrimaryVotes.iloc[0]),
            "method": str(group.Method.iloc[0]),
        }
    return result
