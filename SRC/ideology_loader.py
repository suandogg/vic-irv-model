from SRC.loaders import read_csv_raw, clean_percent


PARTIES = ["ALP", "LNP", "GRN", "ON", "IND", "OTH"]


def load_ideology_prior(filename="IDEOLOGY.csv"):
    raw = read_csv_raw(filename)

    raw.columns = [str(c).strip().upper() for c in raw.columns]

    elim_col = raw.columns[0]

    out = {}

    for _, row in raw.iterrows():
        eliminated = str(row[elim_col]).strip().upper()

        if eliminated not in PARTIES:
            continue

        out[eliminated] = {}

        for party in PARTIES:
            if party in raw.columns:
                out[eliminated][party] = clean_percent(row[party])

    return out