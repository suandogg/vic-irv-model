import pandas as pd
from SRC.constants import PARTIES


def build_primary_vote_table(seat_helper_df: pd.DataFrame) -> pd.DataFrame:

    rows = []

    for _, row in seat_helper_df.iterrows():

        district = row["district"]
        region = row["region"]
        seat_type = row["seat_type"]
        held_by = row["held_by"]

        for party in PARTIES:

            vote = row[party]

            rows.append({
                "district": district,
                "region": region,
                "seat_type": seat_type,
                "held_by": held_by,
                "party": party,
                "primary_vote": vote
            })

    return pd.DataFrame(rows)