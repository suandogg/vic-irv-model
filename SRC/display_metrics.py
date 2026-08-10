from __future__ import annotations

import pandas as pd

from SRC.loaders import normalise_held_party


def clean_baseline_value(value):
    if pd.isna(value):
        return None
    value = float(value)
    return value / 100 if value > 1.5 else value


def held_party_2cp_swing(row, baseline_lookup):
    """Return swing from the perspective of the party that held the seat.

    A changed opponent is valid as long as the held party remains in the new
    final two. If the held party misses the final two, there is no comparable
    current 2CP share and the displayed swing is blank.
    """
    district = str(row["district"]).strip()
    held = normalise_held_party(row["held_by"])
    winner = normalise_held_party(row["winner"])
    runner_up = normalise_held_party(row["runner_up"])

    if district not in baseline_lookup.index:
        return None
    if held == winner:
        current_held_share = float(row["winner_pct"])
    elif held == runner_up:
        current_held_share = float(row["runner_up_pct"])
    else:
        return None

    held_column = f"{held}_2CP"
    baseline_row = baseline_lookup.loc[district]
    if held_column not in baseline_row.index:
        return None
    baseline_held_share = clean_baseline_value(baseline_row[held_column])
    if baseline_held_share is None:
        return None
    return (current_held_share - baseline_held_share) * 100
