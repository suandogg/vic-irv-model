import pandas as pd

from SRC.loaders import read_csv_raw, clean_percent


UPPER_PARTIES = ["ALP", "LNP", "GRN", "ON", "OTH_L", "OTH_R"]


PARTY_NORMALISER = {
    "ALP": "ALP",
    "LNP": "LNP",
    "GRN": "GRN",
    "ON": "ON",
    "OTH LEFT": "OTH_L",
    "OTH_L": "OTH_L",
    "OTHL": "OTH_L",
    "OTH RIGHT": "OTH_R",
    "OTH_R": "OTH_R",
    "OTHR": "OTH_R",
}


def norm_party(value):
    return PARTY_NORMALISER.get(
        str(value).strip().upper(),
        str(value).strip().upper()
    )


def load_upper_region_baseline(filename="UPPER_REGION_BASELINE.csv"):
    df = read_csv_raw(filename)

    df.columns = [
        str(col).strip().lower()
        for col in df.columns
    ]

    df = df.rename(columns={
        "region": "region",
        "party": "party",
        "uh_2022_vote": "uh_2022_vote",
        "lh_2022_vote": "lh_2022_vote",
    })

    df["region"] = df["region"].astype(str).str.strip()
    df["party"] = df["party"].apply(norm_party)

    df["uh_2022_vote"] = df["uh_2022_vote"].apply(clean_percent)

    if "lh_2022_vote" in df.columns:
        df["lh_2022_vote"] = df["lh_2022_vote"].apply(clean_percent)
    else:
        df["lh_2022_vote"] = None

    df = df[df["party"].isin(UPPER_PARTIES)].copy()

    return df.reset_index(drop=True)


def load_upper_pref_params(filename="UPPER_PREF_PARAMS.csv"):
    df = read_csv_raw(filename)

    df.columns = [
        str(col).strip().lower()
        for col in df.columns
    ]

    out = {}

    for _, row in df.iterrows():
        key = str(row["parameter"]).strip().upper()

        if not key or key == "NAN":
            continue

        value = row["value"]

        try:
            value = clean_percent(value)
        except Exception:
            value = float(value)

        out[key] = value

    return out


def load_upper_party_relationships(filename="UPPER_PARTY_RELATIONSHIPS.csv"):
    df = read_csv_raw(filename)

    df.columns = [
        str(col).strip().upper().replace(" ", "_")
        for col in df.columns
    ]

    from_col = df.columns[0]

    relationships = {}

    for _, row in df.iterrows():
        from_party = norm_party(row[from_col])

        if from_party not in UPPER_PARTIES:
            continue

        relationships[from_party] = {}

        for party in UPPER_PARTIES:
            value = row.get(party, 0)

            if pd.isna(value):
                value = 0

            relationships[from_party][party] = float(value)

        total = sum(relationships[from_party].values())

        if total > 0:
            relationships[from_party] = {
                party: value / total
                for party, value in relationships[from_party].items()
            }

    return relationships