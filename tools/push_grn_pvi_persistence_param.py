"""Add or update the lower-house Greens PVI persistence setting in PARAMS."""

from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

ROOT = Path(__file__).resolve().parents[1]
SHEET_ID = "1avkQZ0A8tlVI1tR0UakEriNKuq9N7dwRUFJzecb26Ro"
KEY = "GRN_PVI_PERSISTENCE"
VALUE = 1.0
DESCRIPTION = (
    "Multiplier applied to the Greens' 2022 district PVI before statewide "
    "primary calibration; 1 retains the current geography and lower values flatten it."
)


def main():
    credentials = Credentials.from_service_account_file(
        ROOT / "credentials.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    worksheet = gspread.authorize(credentials).open_by_key(SHEET_ID).worksheet("PARAMS")
    values = worksheet.get_all_values()
    keys = [row[0] if row else "" for row in values]
    if KEY in keys:
        row = keys.index(KEY) + 1
    else:
        row = keys.index("Optional for later") + 1
        if worksheet.cell(row, 1).value:
            worksheet.insert_row([], index=row)
    worksheet.update(
        values=[[KEY, VALUE, DESCRIPTION]], range_name=f"A{row}:C{row}",
        value_input_option="USER_ENTERED",
    )
    verified = worksheet.get(f"A{row}:C{row}")[0]
    if verified[0] != KEY or abs(float(verified[1]) - VALUE) > 1e-12:
        raise RuntimeError(f"PARAMS verification failed: {verified!r}")
    print(f"Verified PARAMS row {row}: {verified}")


if __name__ == "__main__":
    main()
