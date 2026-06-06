import os
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials


LOWER_SHEET_ID = "1avkQZ0A8tlVI1tR0UakEriNKuq9N7dwRUFJzecb26Ro"
UPPER_SHEET_ID = "1sewCPOaxNNhewbhfJCCH_Pw2Kp5pUceXHxeYJKIAhJ8"

CREDENTIALS_FILE = os.path.join(
    os.path.dirname(__file__),
    "credentials.json"
)

DATA_DIR = os.path.join(
    os.path.dirname(__file__),
    "data",
    "raw"
)

LOWER_FILES = {
    "SEAT HELPER": "SEAT HELPER.csv",
    "BASELINE_2CP": "BASELINE_2CP.csv",
    "BASELINE_REGION_SUMMARY": "BASELINE_REGION_SUMMARY.csv",
    "IDEOLOGY": "IDEOLOGY.csv",
}

UPPER_FILES = {
    "UPPER_REGION_BASELINE": "UPPER_REGION_BASELINE.csv",
    "UPPER_PREF_PARAMS": "UPPER_PREF_PARAMS.csv",
    "UPPER_PARTY_RELATIONSHIPS": "UPPER_PARTY_RELATIONSHIPS.csv",
    "UPPER_INCUMBENTS": "UPPER_INCUMBENTS.csv",
    "2022_GVTs": "2022_GVTs.csv",
}


def sync_sheet(gc, sheet_id, files):
    sh = gc.open_by_key(sheet_id)

    print(f"\nSyncing from Google Sheet: {sh.title}\n")

    for tab_name, csv_filename in files.items():
        try:
            worksheet = sh.worksheet(tab_name)
            data = worksheet.get_all_records()

            if not data:
                print(f"  ⚠  {tab_name} — sheet is empty, skipping")
                continue

            df = pd.DataFrame(data)

            out_path = os.path.join(DATA_DIR, csv_filename)
            df.to_csv(out_path, index=False)

            print(
                f"  ✓  {tab_name} → data/raw/{csv_filename} "
                f"({len(df)} rows)"
            )

        except gspread.exceptions.WorksheetNotFound:
            print(f"  ✗  {tab_name} — tab not found in sheet, skipping")

        except Exception as e:
            print(f"  ✗  {tab_name} — error: {e}")


creds = Credentials.from_service_account_file(
    CREDENTIALS_FILE,
    scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
)

gc = gspread.authorize(creds)

sync_sheet(gc, LOWER_SHEET_ID, LOWER_FILES)
sync_sheet(gc, UPPER_SHEET_ID, UPPER_FILES)

print("\nSync complete. Restart Streamlit to pick up changes.\n")