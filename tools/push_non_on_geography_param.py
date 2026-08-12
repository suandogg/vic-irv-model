"""Add or update the lower-house non-ON geography multiplier in PARAMS."""

from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials


ROOT = Path(__file__).resolve().parents[1]
SHEET_ID = "1avkQZ0A8tlVI1tR0UakEriNKuq9N7dwRUFJzecb26Ro"
KEY = "NON_ON_GEOGRAPHY_STRENGTH"
VALUE = 0.75
DESCRIPTION = (
    "Multiplier applied to ALP, LNP, GRN, IND and OTH preference-geography "
    "adjustments; ON adjustments remain at full strength."
)


def main() -> None:
    credentials = Credentials.from_service_account_file(
        ROOT / "credentials.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    worksheet = gspread.authorize(credentials).open_by_key(SHEET_ID).worksheet("PARAMS")
    values = worksheet.get_all_values()
    column_a = [row[0] if row else "" for row in values]

    if KEY in column_a:
        target_row = column_a.index(KEY) + 1
    else:
        class_row = column_a.index("CLASS_SMOOTH_K") + 1
        target_row = class_row + 1
        existing = worksheet.cell(target_row, 1).value
        if existing:
            worksheet.insert_row([], index=target_row)

    worksheet.update(
        values=[[KEY, VALUE, DESCRIPTION]],
        range_name=f"A{target_row}:C{target_row}",
        value_input_option="USER_ENTERED",
    )
    verified = worksheet.get(f"A{target_row}:C{target_row}")[0]
    if verified[0] != KEY or abs(float(verified[1]) - VALUE) > 1e-12:
        raise RuntimeError(f"PARAMS verification failed: {verified!r}")
    print(f"Verified PARAMS row {target_row}: {verified}")


if __name__ == "__main__":
    main()
