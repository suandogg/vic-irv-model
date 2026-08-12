import os

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials


SHEET_ID = "1avkQZ0A8tlVI1tR0UakEriNKuq9N7dwRUFJzecb26Ro"

CREDENTIALS_FILE = os.path.join(
    os.path.dirname(__file__),
    "credentials.json"
)

DATA_DIR = os.path.join(
    os.path.dirname(__file__),
    "data",
    "raw"
)

FILES = {
    # Lower house files
    "LOWER_PRIMARY_INPUTS": "LEGACY_PRIMARY_INPUTS.csv",
    "SEAT HELPER": "SEAT HELPER.csv",
    "PARAMS": "PARAMS.csv",
    "SYNTH PREF MATRIX": "SYNTH PREF MATRIX.csv",
    "BASELINE_2CP": "BASELINE_2CP.csv",
    "BASELINE_REGION_SUMMARY": "BASELINE_REGION_SUMMARY.csv",
    "IDEOLOGY": "IDEOLOGY.csv",
    "LOWER_ON_PREF_EVIDENCE": "FEDERAL_VIC_ON_SCENARIOS.csv",
    "LOWER_ON_PREF_CONFIG": "LOWER_ON_PREF_CONFIG.csv",
    "LOWER_LNP_PRECOLLAPSE": "LOWER_LNP_PRECOLLAPSE.csv",
    "LOWER_SEAT_ADJUSTMENTS": "LOWER_SEAT_ADJUSTMENTS.csv",
    "LOWER_POLL_SCENARIOS": "LOWER_POLL_SCENARIOS.csv",

    # Upper house files
    "UPPER_REGION_BASELINE": "UPPER_REGION_BASELINE.csv",
    "UPPER_PREF_PARAMS": "UPPER_PREF_PARAMS.csv",
    "UPPER_PARTY_RELATIONSHIPS": "UPPER_PARTY_RELATIONSHIPS.csv",
    "UPPER_INCUMBENTS": "UPPER_INCUMBENTS.csv",
    "2022_GVTs": "2022_GVTs.csv",
    "UPPER_PARTY_INPUTS_NAMED": "UPPER_PARTY_INPUTS_NAMED.csv",
    "UPPER_CANDIDATES": "UPPER_CANDIDATES.csv",
    "UPPER_2022_CANDIDATES": "UPPER_2022_CANDIDATES.csv",
    "UPPER_REGION_PVI_NAMED": "UPPER_REGION_PVI_NAMED.csv",
    "UPPER_PREFERENCE_EVIDENCE": "UPPER_PREFERENCE_EVIDENCE.csv",
    "UPPER_PREFERENCE_PRIORS": "UPPER_PREFERENCE_PRIORS.csv",
    "UPPER_BALLOT_BEHAVIOUR": "UPPER_BALLOT_BEHAVIOUR.csv",
    "UPPER_OVERRIDES": "UPPER_OVERRIDES.csv",
    "UPPER_MODEL_PARAMS": "UPPER_MODEL_PARAMS.csv",
    "UPPER_PARTY_CLASSES": "UPPER_PARTY_CLASSES.csv",
}


RAW_GRID_TABS = {
    "PARAMS",
    "SYNTH PREF MATRIX",
}


def worksheet_to_dataframe(worksheet, tab_name):
    if tab_name in RAW_GRID_TABS:
        values = worksheet.get_all_values()

        if not values:
            return pd.DataFrame()

        return pd.DataFrame(values)

    data = worksheet.get_all_records()

    if not data:
        return pd.DataFrame()

    return pd.DataFrame(data)


def sync_sheet():
    creds = Credentials.from_service_account_file(
        CREDENTIALS_FILE,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )

    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)

    os.makedirs(DATA_DIR, exist_ok=True)

    print(f"\nSyncing from Google Sheet: {sh.title}\n")
    available_tabs = [worksheet.title for worksheet in sh.worksheets()]

    for tab_name, csv_filename in FILES.items():
        try:
            worksheet = sh.worksheet(tab_name)
            df = worksheet_to_dataframe(worksheet, tab_name)

            if df.empty:
                print(f"  ⚠  {tab_name} — sheet is empty, skipping")
                continue

            out_path = os.path.join(DATA_DIR, csv_filename)

            if tab_name in RAW_GRID_TABS:
                df.to_csv(out_path, index=False, header=False)
            else:
                df.to_csv(out_path, index=False)

            print(
                f"  ✓  {tab_name} → data/raw/{csv_filename} "
                f"({len(df)} rows)"
            )

        except gspread.exceptions.WorksheetNotFound:
            print(f"  ✗  {tab_name} — tab not found in sheet, skipping")
            print(f"     Available tabs: {', '.join(available_tabs)}")

        except Exception as e:
            print(f"  ✗  {tab_name} — error: {e}")

    print("\nSync complete. Restart Streamlit to pick up changes.\n")


if __name__ == "__main__":
    sync_sheet()
