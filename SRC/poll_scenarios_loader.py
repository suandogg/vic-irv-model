from __future__ import annotations

import pandas as pd

from SRC.constants import PARTIES
from SRC.loaders import DATA_DIR, read_csv_raw


def load_poll_scenarios(filename: str = "LOWER_POLL_SCENARIOS.csv") -> pd.DataFrame:
    if not (DATA_DIR / filename).exists():
        return pd.DataFrame(columns=["scenario", *PARTIES, "notes"])
    frame = read_csv_raw(filename)
    required = ["scenario", *PARTIES]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Lower poll scenarios missing columns: {missing}")
    frame = frame.copy()
    frame["scenario"] = frame["scenario"].astype(str).str.strip()
    for party in PARTIES:
        frame[party] = pd.to_numeric(frame[party], errors="raise")
    if "notes" not in frame:
        frame["notes"] = ""
    return frame
