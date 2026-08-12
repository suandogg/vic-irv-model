"""Load editable named-party upper-house inputs."""

from __future__ import annotations

import pandas as pd

from SRC.loaders import read_csv_raw


def load_upper_named_inputs() -> dict[str, pd.DataFrame]:
    return {
        "party_inputs": read_csv_raw("UPPER_PARTY_INPUTS_NAMED.csv"),
        "candidates": read_csv_raw("UPPER_CANDIDATES.csv"),
        "historical": read_csv_raw("UPPER_2022_CANDIDATES.csv"),
        "region_pvi": read_csv_raw("UPPER_REGION_PVI_NAMED.csv"),
        "evidence": read_csv_raw("UPPER_PREFERENCE_EVIDENCE.csv"),
        "classes": read_csv_raw("UPPER_PARTY_CLASSES.csv"),
        "behaviour": read_csv_raw("UPPER_BALLOT_BEHAVIOUR.csv"),
        "params": read_csv_raw("UPPER_MODEL_PARAMS.csv"),
        "overrides": read_csv_raw("UPPER_OVERRIDES.csv"),
    }
