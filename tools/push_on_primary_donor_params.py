"""Update only the lower-house explicit ON primary donor settings in PARAMS."""

from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

ROOT = Path(__file__).resolve().parents[1]
SHEET_ID = "1avkQZ0A8tlVI1tR0UakEriNKuq9N7dwRUFJzecb26Ro"
ROWS = [
    ("ON_PRIMARY_DONOR_STRENGTH", 0.35,
     "Blends primary geography toward explicit ON vote sourcing from the seat-class source matrix; 0 is legacy proportional geography and 1 is full matrix sourcing."),
    ("ON_PRIMARY_OTH_DEPLETION_STRENGTH", 0.75,
     "Maximum fraction of OTH's primary donor weight reallocated as ON rises; released weight moves one-third to ALP and two-thirds to LNP."),
    ("ON_PRIMARY_OTH_DEPLETION_START", 10,
     "Statewide ON primary at which primary-source OTH depletion begins."),
    ("ON_PRIMARY_OTH_DEPLETION_FULL", 30,
     "Statewide ON primary at which maximum primary-source OTH depletion applies."),
]


def main():
    credentials = Credentials.from_service_account_file(
        ROOT / "credentials.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    ws = gspread.authorize(credentials).open_by_key(SHEET_ID).worksheet("PARAMS")
    values = ws.get_all_values()
    keys = [row[0] if row else "" for row in values]
    insert_at = keys.index("Optional for later") + 1
    for key, value, description in ROWS:
        values = ws.get_all_values()
        keys = [row[0] if row else "" for row in values]
        if key in keys:
            row = keys.index(key) + 1
        else:
            row = insert_at
            ws.insert_row([], index=row)
            insert_at += 1
        ws.update(values=[[key, value, description]], range_name=f"A{row}:C{row}",
                  value_input_option="USER_ENTERED")
        verified = ws.get(f"A{row}:C{row}")[0]
        if verified[0] != key or abs(float(verified[1]) - float(value)) > 1e-12:
            raise RuntimeError(f"PARAMS verification failed: {verified!r}")
        print(f"Verified PARAMS row {row}: {verified}")


if __name__ == "__main__":
    main()
