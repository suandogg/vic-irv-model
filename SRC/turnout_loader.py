from __future__ import annotations

import pandas as pd

from SRC.loaders import read_csv_raw


def load_lower_turnout_weights(
    filename: str = "LOWER_TURNOUT_WEIGHTS.csv",
) -> pd.DataFrame:
    """Load auditable 2022 formal-vote weights for all 88 districts."""
    df = read_csv_raw(filename)
    required = {"district", "formal_votes_2022"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Turnout weights missing columns: {missing}")

    out = df.copy()
    out["district"] = out["district"].astype(str).str.strip()
    out["formal_votes_2022"] = pd.to_numeric(
        out["formal_votes_2022"], errors="raise"
    )
    if out["district"].duplicated().any():
        duplicates = sorted(out.loc[out["district"].duplicated(), "district"].unique())
        raise ValueError(f"Duplicate turnout-weight districts: {duplicates}")
    if len(out) != 88:
        raise ValueError(f"Turnout weights must contain 88 districts; found {len(out)}")
    if (out["formal_votes_2022"] <= 0).any():
        raise ValueError("All turnout weights must be positive")
    return out.reset_index(drop=True)


def attach_turnout_weights(
    results: pd.DataFrame,
    turnout_weights: pd.DataFrame,
) -> pd.DataFrame:
    """Attach one formal-vote weight to every district result."""
    merged = results.merge(
        turnout_weights[["district", "formal_votes_2022"]],
        on="district",
        how="left",
        validate="one_to_one",
    )
    missing = merged.loc[merged["formal_votes_2022"].isna(), "district"].tolist()
    if missing:
        raise ValueError(f"Missing turnout weights for districts: {missing}")
    return merged


def turnout_weighted_share(results: pd.DataFrame, share_column: str) -> float:
    """Return a decimal statewide/region share weighted by formal votes."""
    weights = pd.to_numeric(results["formal_votes_2022"], errors="coerce")
    shares = pd.to_numeric(results[share_column], errors="coerce")
    valid = weights.notna() & shares.notna() & (weights > 0)
    denominator = float(weights[valid].sum())
    if denominator <= 0:
        raise ValueError("No positive turnout weights available for displayed share")
    return float((shares[valid] * weights[valid]).sum() / denominator)
