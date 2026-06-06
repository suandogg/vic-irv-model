from pathlib import Path
import pandas as pd

from loaders import read_csv_raw
from export_results import main as export_python_results


PROJECT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_DIR / "outputs"

TOLERANCE = 0.001


def clean_party(value):
    text = str(value).strip().upper()

    if "LABOR" in text or text == "ALP":
        return "ALP"
    if "LIBERAL" in text or "NATIONAL" in text or text == "LNP":
        return "LNP"
    if "GREENS" in text or text == "GRN":
        return "GRN"
    if "ONE" in text or text in ["ON", "ONP"]:
        return "ON"
    if "IND" in text:
        return "IND"
    if "OTH" in text or "OTHER" in text:
        return "OTH"

    return text


def normalise_matchup(value):
    parties = str(value).strip().upper().replace("ONP", "ON").split("-")
    parties = [p.strip() for p in parties if p.strip()]
    return "-".join(sorted(parties))


def matchup_parties(value):
    parties = str(value).strip().upper().replace("ONP", "ON").split("-")
    return [p.strip() for p in parties if p.strip()]


def to_decimal(value):
    if pd.isna(value):
        return None

    text = str(value).strip()

    if text == "":
        return None

    if text.endswith("%"):
        return float(text.replace("%", "")) / 100

    num = float(text)
    return num / 100 if num > 1 else num


def load_sheet_results():
    raw = read_csv_raw("PRIMARY ELECTION CALC DETAILED (IRV).csv", header=None)

    cols = [
        16, 50, 53, 54,
        42, 43, 44, 45, 46, 47
    ]

    df = raw.iloc[124:212, cols].copy()

    df.columns = [
        "district",
        "sheet_result",
        "sheet_matchup",
        "sheet_margin",
        "sheet_ALP_2cp",
        "sheet_LNP_2cp",
        "sheet_GRN_2cp",
        "sheet_ON_2cp",
        "sheet_IND_2cp",
        "sheet_OTH_2cp",
    ]

    df["district"] = df["district"].astype(str).str.strip()
    df["sheet_winner"] = df["sheet_result"].apply(clean_party)
    df["sheet_matchup_norm"] = df["sheet_matchup"].apply(normalise_matchup)

    for col in [
        "sheet_ALP_2cp",
        "sheet_LNP_2cp",
        "sheet_GRN_2cp",
        "sheet_ON_2cp",
        "sheet_IND_2cp",
        "sheet_OTH_2cp",
    ]:
        df[col] = df[col].apply(to_decimal)

    return df.reset_index(drop=True)


def add_python_party_2cp_columns(py):
    for party in ["ALP", "LNP", "GRN", "ON", "IND", "OTH"]:
        py[f"python_{party}_2cp"] = None

    for idx, row in py.iterrows():
        winner = row["winner"]
        runner_up = row["runner_up"]

        py.at[idx, f"python_{winner}_2cp"] = row["winner_pct"]
        py.at[idx, f"python_{runner_up}_2cp"] = row["runner_up_pct"]

    return py


def add_final_party_comparisons(df):
    party1 = []
    party2 = []

    for matchup in df["sheet_matchup"]:
        parts = matchup_parties(matchup)

        party1.append(parts[0] if len(parts) > 0 else None)
        party2.append(parts[1] if len(parts) > 1 else None)

    df["sheet_final_party_1"] = party1
    df["sheet_final_party_2"] = party2

    for n in [1, 2]:
        df[f"sheet_party_{n}_2cp"] = df.apply(
            lambda r: r.get(f"sheet_{r[f'sheet_final_party_{n}']}_2cp")
            if r[f"sheet_final_party_{n}"] else None,
            axis=1
        )

        df[f"python_party_{n}_2cp"] = df.apply(
            lambda r: r.get(f"python_{r[f'sheet_final_party_{n}']}_2cp")
            if r[f"sheet_final_party_{n}"] else None,
            axis=1
        )

        df[f"party_{n}_2cp_diff"] = (
            df[f"python_party_{n}_2cp"] - df[f"sheet_party_{n}_2cp"]
        )

        df[f"party_{n}_2cp_diff_pp"] = df[f"party_{n}_2cp_diff"] * 100

        df[f"party_{n}_2cp_match"] = (
            df[f"party_{n}_2cp_diff"].abs() <= TOLERANCE
        )

    df["max_2cp_diff_pp"] = df[
        ["party_1_2cp_diff_pp", "party_2_2cp_diff_pp"]
    ].abs().max(axis=1)

    df["final_2cp_match"] = (
        df["party_1_2cp_match"] & df["party_2_2cp_match"]
    )

    return df


def main():
    export_python_results()

    py = pd.read_csv(OUTPUT_DIR / "python_irv_results.csv")
    py["python_matchup_norm"] = py["matchup"].apply(normalise_matchup)
    py = add_python_party_2cp_columns(py)

    sheet = load_sheet_results()

    merged = sheet.merge(py, on="district", how="left")

    merged["winner_match"] = merged["sheet_winner"] == merged["winner"]

    merged["matchup_match"] = (
        merged["sheet_matchup_norm"] == merged["python_matchup_norm"]
    )

    merged = add_final_party_comparisons(merged)

    comparison_path = OUTPUT_DIR / "validation_comparison.csv"
    merged.to_csv(comparison_path, index=False)

    print()
    print("VALIDATION COMPLETE")
    print("Rows compared:", len(merged))

    print()
    print("Winner matches:")
    print(merged["winner_match"].value_counts(dropna=False))

    print()
    print("Matchup matches:")
    print(merged["matchup_match"].value_counts(dropna=False))

    print()
    print("Final 2CP matches:")
    print(merged["final_2cp_match"].value_counts(dropna=False))

    print()
    print("2CP difference summary, percentage points:")
    print(merged["max_2cp_diff_pp"].describe())

    print()
    print("Largest 2CP differences:")
    print(
        merged[
            [
                "district",
                "sheet_matchup",
                "matchup",
                "winner_match",
                "matchup_match",
                "max_2cp_diff_pp",
                "party_1_2cp_diff_pp",
                "party_2_2cp_diff_pp",
            ]
        ]
        .sort_values("max_2cp_diff_pp", ascending=False)
        .head(15)
    )

    print()
    print("Saved validation file to:")
    print(comparison_path)


if __name__ == "__main__":
    main()