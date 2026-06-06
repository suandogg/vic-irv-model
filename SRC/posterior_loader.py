from SRC.loaders import read_csv_raw, clean_percent


PARTIES = ["ALP", "LNP", "GRN", "IND", "OTH"]


def norm_party(value):
    return str(value).strip().upper()


def norm_alive_set(value):
    parts = (
        str(value)
        .strip()
        .upper()
        .replace("|", "+")
        .replace("/", "+")
        .replace(",", "+")
        .split("+")
    )

    parts = [p.strip() for p in parts if p.strip()]
    parts = sorted(parts)

    return "+".join(parts)


def load_posterior_scenarios(filename="SCENARIO_STATS.csv"):
    raw = read_csv_raw(filename)

    raw.columns = [
        str(c).strip().lower().replace(" ", "_")
        for c in raw.columns
    ]

    col_map = {
        "eliminated": None,
        "alive_set": None,
        "recipient": None,
        "share": None,
    }

    for col in raw.columns:

        if col in ["eliminated", "elim", "from"]:
            col_map["eliminated"] = col

        elif col in ["alive_set", "aliveset", "alive"]:
            col_map["alive_set"] = col

        elif col in ["recipient", "to", "party", "target"]:
            col_map["recipient"] = col

        elif col in ["share", "pct", "percent", "percentage", "prob", "weight"]:
            col_map["share"] = col

    missing = [k for k, v in col_map.items() if v is None]

    if missing:
        raise ValueError(
            f"SCENARIO_STATS missing columns: {missing}. "
            f"Saw {list(raw.columns)}"
        )

    out = {}

    for _, row in raw.iterrows():

        elim = norm_party(row[col_map["eliminated"]])
        alive = norm_alive_set(row[col_map["alive_set"]])
        recipient = norm_party(row[col_map["recipient"]])

        if elim not in PARTIES:
            continue

        if recipient not in PARTIES:
            continue

        share = clean_percent(row[col_map["share"]])

        if share is None or share <= 0:
            continue

        key = f"{elim}|{alive}"

        if key not in out:
            out[key] = {}

        out[key][recipient] = share

    return out