from __future__ import annotations

import pandas as pd

from SRC.loaders import read_csv_raw


def load_legacy_primary_inputs(
    filename: str = "LEGACY_PRIMARY_INPUTS.csv",
) -> pd.DataFrame:
    df = read_csv_raw(filename)

    numeric_columns = [
        "ALP_pvi",
        "LNP_pvi",
        "GRN_pvi",
        "IND_pvi",
        "OTH_pvi",
        "ON_strength",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="raise")

    for column in ["district", "region", "seat_type", "held_by"]:
        df[column] = df[column].astype(str).str.strip()

    return df
