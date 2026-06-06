from SRC.loaders import read_csv_raw


def load_baseline_2cp(filename="BASELINE_2CP.csv"):

    df = read_csv_raw(filename)

    df.columns = [str(c).strip() for c in df.columns]

    df["district"] = (
        df["district"]
        .astype(str)
        .str.strip()
    )

    return df