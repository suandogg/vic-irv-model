import pandas as pd

from SRC.loaders import read_csv_raw, clean_percent


PARTIES = ["ALP", "LNP", "GRN", "ON", "IND", "OTH"]


def clean_district_name(value):

    if pd.isna(value):
        return None

    text = str(value)

    # Remove region line
    text = text.split("\n")[0]

    text = text.strip()
    text = text.replace('"', "")

    return text


def load_synth_pref_matrices(filename="SYNTH PREF MATRIX.csv"):

    raw = read_csv_raw(filename, header=None)

    matrices = {}

    row = 0

    while row < len(raw):

        district = clean_district_name(raw.iloc[row, 0])

        if not district:
            row += 1
            continue

        seat_type = str(raw.iloc[row + 1, 0]).strip()

        matrix = {}

        # synthetic matrix rows
        # rows row+3 to row+8
        for r in range(row + 3, row + 9):

            from_party = raw.iloc[r, 8]

            if pd.isna(from_party):
                continue

            from_party = str(from_party).strip().upper()

            if from_party not in PARTIES:
                continue

            matrix[from_party] = {}

            for i, to_party in enumerate(PARTIES):

                value = raw.iloc[r, 9 + i]

                matrix[from_party][to_party] = clean_percent(value)

        # keep only real seats
        if len(matrix) > 0:

            matrices[district] = {
                "seat_type": seat_type,
                "matrix": matrix
            }

        row += 10

        matrices = dict(list(matrices.items())[:88])

    return matrices