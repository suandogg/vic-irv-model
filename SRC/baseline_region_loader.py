from SRC.loaders import read_csv_raw


def load_baseline_region_summary(filename="BASELINE_REGION_SUMMARY.csv"):
    df = read_csv_raw(filename)

    df.columns = [
        str(col).strip().lower()
        for col in df.columns
    ]

    df["region"] = (
        df["region"]
        .astype(str)
        .str.strip()
    )

    return df