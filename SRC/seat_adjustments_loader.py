from __future__ import annotations

from pathlib import Path

import pandas as pd

from SRC.loaders import RAW_DIR, read_csv_raw


COLUMNS = [
    "district",
    "party",
    "retiring_incumbent",
    "first_re_election",
    "retirement_penalty_pp",
    "sophomore_bonus_pp",
    "candidate_strength_pp",
    "manual_adjustment_pp",
    "enabled",
    "notes",
]


def _as_bool(value, default=False) -> bool:
    if pd.isna(value) or str(value).strip() == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def load_lower_seat_adjustments(
    filename: str = "LOWER_SEAT_ADJUSTMENTS.csv",
) -> pd.DataFrame:
    """Load editable lower-house incumbency and seat adjustments.

    A missing file is treated as no adjustments so older committed CSV
    deployments remain backwards compatible.
    """
    if not (RAW_DIR / filename).exists():
        return pd.DataFrame(columns=COLUMNS)

    df = read_csv_raw(filename)
    missing = [column for column in COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Lower seat adjustments missing columns: {missing}")

    out = df[COLUMNS].copy()
    out["district"] = out["district"].astype(str).str.strip()
    out["party"] = out["party"].astype(str).str.strip().str.upper()
    for column in ["retiring_incumbent", "first_re_election"]:
        out[column] = out[column].map(_as_bool)
    out["enabled"] = out["enabled"].map(lambda value: _as_bool(value, True))
    for column in [
        "retirement_penalty_pp",
        "sophomore_bonus_pp",
        "candidate_strength_pp",
        "manual_adjustment_pp",
    ]:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    out["notes"] = out["notes"].fillna("").astype(str)
    return out
