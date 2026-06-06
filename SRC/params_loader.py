import pandas as pd

from SRC.loaders import read_csv_raw, clean_percent


def clean_value(value):
    if pd.isna(value):
        return None

    if isinstance(value, str):
        value = value.strip()

        if value == "":
            return None

        if value.endswith("%"):
            return float(value.replace("%", "")) / 100

        try:
            return float(value)
        except ValueError:
            return value

    return value


def load_params(filename="PARAMS.csv"):
    raw = read_csv_raw(filename, header=None)

    params = {
        "on_vote_source_matrix": {},
        "on_column_prior": {},
        "on_row_prior": {},
        "geography_adjustments": {},
        "scalar_params": {},
        "on_special_scenario_priors": {},
    }

    # ON vote source matrix
    # Rows 2:7 in the sheet export, columns 0:5
    for i in range(2, 8):
        seat_type = raw.iloc[i, 0]
        if pd.isna(seat_type):
            continue

        params["on_vote_source_matrix"][str(seat_type).strip()] = {
            "ALP": clean_value(raw.iloc[i, 1]),
            "LNP": clean_value(raw.iloc[i, 2]),
            "GRN": clean_value(raw.iloc[i, 3]),
            "IND": clean_value(raw.iloc[i, 4]),
            "OTH": clean_value(raw.iloc[i, 5]),
        }

    # ON-column prior table: preference TO ON
    seat_types = [
        clean_value(raw.iloc[9, c])
        for c in range(1, 7)
    ]

    for i in range(10, 15):
        party = clean_value(raw.iloc[i, 0])
        if party is None:
            continue

        params["on_column_prior"][party] = {}

        for c, seat_type in enumerate(seat_types, start=1):
            params["on_column_prior"][party][seat_type] = clean_value(raw.iloc[i, c])

    # ON-row prior table: preference FROM ON
    for i in range(18, 24):
        seat_type = clean_value(raw.iloc[i, 0])
        if seat_type is None:
            continue

        params["on_row_prior"][seat_type] = {
            "ALP": clean_value(raw.iloc[i, 1]),
            "LNP": clean_value(raw.iloc[i, 2]),
            "GRN": clean_value(raw.iloc[i, 3]),
            "IND": clean_value(raw.iloc[i, 4]),
            "OTH": clean_value(raw.iloc[i, 5]),
        }

    # Geography adjustments
    for i in range(27, 31):
        geography = clean_value(raw.iloc[i, 0])
        if geography is None:
            continue

        params["geography_adjustments"][geography] = {
            "ALP": clean_value(raw.iloc[i, 1]),
            "LNP": clean_value(raw.iloc[i, 2]),
            "GRN": clean_value(raw.iloc[i, 3]),
            "ON": clean_value(raw.iloc[i, 4]),
            "IND": clean_value(raw.iloc[i, 5]),
            "OTH": clean_value(raw.iloc[i, 6]),
        }

    # Scalar params: rows with param name in col A and value in col B
    for i in range(len(raw)):
        key = clean_value(raw.iloc[i, 0])
        value = clean_value(raw.iloc[i, 1])

        if isinstance(key, str) and value is not None:
            if key.isupper() or key.startswith("ON ") or key.endswith("alpha"):
                params["scalar_params"][key] = value

    # ON special scenario priors
    for i in range(78, len(raw)):
        alive_set = clean_value(raw.iloc[i, 0])
        eliminated = clean_value(raw.iloc[i, 1])
        seat_type = clean_value(raw.iloc[i, 2])

        if alive_set is None or eliminated is None or seat_type is None:
            continue

        key = f"{alive_set}|{eliminated}|{seat_type}"

        params["on_special_scenario_priors"][key] = {
            "ALP": clean_value(raw.iloc[i, 3]),
            "LNP": clean_value(raw.iloc[i, 4]),
            "ON": clean_value(raw.iloc[i, 5]),
        }

    return params