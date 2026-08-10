from pathlib import Path
import pandas as pd


RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


VALID_REGIONS = [
    "North-Eastern Metro",
    "Northern Metro",
    "Western Metro",
    "South-Eastern Metro",
    "Eastern Victoria",
    "Northern Victoria",
    "Western Victoria",
    "Southern Metro",
]


def read_csv_raw(filename: str, header=0) -> pd.DataFrame:
    path = RAW_DIR / filename
    return pd.read_csv(path, header=header)


def clean_percent(value):
    if pd.isna(value):
        return None

    if isinstance(value, str):
        value = value.strip()

        if value == "":
            return None

        if value.startswith("#"):
            return None

        if value.endswith("%"):
            return float(value.replace("%", "")) / 100

    return float(value)


def load_seat_helper(filename="SEAT HELPER.csv") -> pd.DataFrame:
    df = read_csv_raw(filename)

    print()
    print("Original columns:")
    print(df.columns.tolist())
    print()

    # Remove rows without a seat name
    df = df[df.iloc[:, 0].notna()].copy()

    # Rename key columns into Python-friendly names
    rename_map = {
        "Seat Name": "district",
        "Region": "region",
        "Seat Type": "seat_type",
        "Held by": "held_by",
        "ALP_adj": "ALP",
        "LNP_adj": "LNP",
        "GRN_adj": "GRN",
        "ON_adj": "ON",
        "IND_adj": "IND",
        "OTH_adj": "OTH",
    }

    existing_renames = {
        old_name: new_name
        for old_name, new_name in rename_map.items()
        if old_name in df.columns
    }

    df = df.rename(columns=existing_renames)

    # Keep only real Victorian lower-house regions
    df["region"] = df["region"].astype(str).str.strip()
    df = df[df["region"].isin(VALID_REGIONS)].copy()

    # Keep only the 88 actual districts, excluding regional summaries/helper duplicates
    df = df.head(88).copy()

    # Clean district names and text fields
    df["district"] = df["district"].astype(str).str.strip()
    df["seat_type"] = df["seat_type"].astype(str).str.strip()
    df["held_by"] = df["held_by"].astype(str).str.strip()

    # Convert adjusted vote columns into decimals
    percent_columns = ["ALP", "LNP", "GRN", "ON", "IND", "OTH"]

    for col in percent_columns:
        if col in df.columns:
            df[col] = df[col].apply(clean_percent)

    keep_columns = [
        "district",
        "region",
        "seat_type",
        "held_by",
        "ALP",
        "LNP",
        "GRN",
        "ON",
        "IND",
        "OTH",
    ]

    keep_columns = [col for col in keep_columns if col in df.columns]

    return df[keep_columns].reset_index(drop=True)


HELD_PARTY_ALIASES = {
    "LABOR": "ALP",
    "LIBERAL": "LNP",
    "NATIONAL": "LNP",
    "NATIONALS": "LNP",
    "GREENS": "GRN",
    "INDEPENDENT": "IND",
    "OTHER": "OTH",
    "ONE NATION": "ON",
}


def normalise_held_party(value: str) -> str:
    party = str(value).strip().upper()
    return HELD_PARTY_ALIASES.get(party, party)


def load_seat_held_metadata(filename="SEAT HELPER.csv") -> pd.DataFrame:
    """Load only district and held-party metadata from SEAT HELPER.

    No vote, preference, weight, or adjusted-result column is read into the
    returned frame, keeping SEAT HELPER outside the calculation pipeline.
    """
    raw = read_csv_raw(filename)
    required = {"Seat Name", "Region", "Held by"}
    missing = sorted(required.difference(raw.columns))
    if missing:
        raise ValueError(f"SEAT HELPER metadata missing columns: {missing}")

    metadata = raw.loc[:, ["Seat Name", "Region", "Held by"]].copy()
    metadata.columns = ["district", "region", "held_by"]
    metadata = metadata.dropna(subset=["district", "region", "held_by"])
    metadata["region"] = metadata["region"].astype(str).str.strip()
    metadata = metadata[metadata["region"].isin(VALID_REGIONS)].copy()
    metadata["district"] = metadata["district"].astype(str).str.strip()
    metadata["held_by"] = metadata["held_by"].apply(normalise_held_party)
    metadata = metadata.drop_duplicates(subset="district", keep="first")

    if len(metadata) != 88:
        raise ValueError(
            f"SEAT HELPER must provide held-party metadata for 88 districts; "
            f"found {len(metadata)}"
        )
    invalid = sorted(set(metadata["held_by"]) - {"ALP", "LNP", "GRN", "ON", "IND", "OTH"})
    if invalid:
        raise ValueError(f"Invalid held-party values in SEAT HELPER: {invalid}")
    return metadata[["district", "held_by"]].reset_index(drop=True)


def apply_seat_held_metadata(
    primary_inputs: pd.DataFrame,
    held_metadata: pd.DataFrame,
) -> pd.DataFrame:
    """Overlay authoritative held-party metadata without touching vote inputs."""
    lookup = held_metadata.set_index("district")["held_by"]
    missing = sorted(set(primary_inputs["district"]) - set(lookup.index))
    if missing:
        raise ValueError(f"SEAT HELPER held-party metadata missing districts: {missing}")
    out = primary_inputs.copy()
    out["held_by"] = out["district"].map(lookup)
    return out
