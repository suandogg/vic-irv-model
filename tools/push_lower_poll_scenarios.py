"""Create or update the editable lower-house polling scenario library."""

from pathlib import Path

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials


ROOT = Path(__file__).resolve().parents[1]
SHEET_ID = "1avkQZ0A8tlVI1tR0UakEriNKuq9N7dwRUFJzecb26Ro"
TAB_NAME = "LOWER_POLL_SCENARIOS"


def main() -> None:
    client = gspread.authorize(Credentials.from_service_account_file(
        ROOT / "credentials.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    ))
    spreadsheet = client.open_by_key(SHEET_ID)
    worksheets = {worksheet.title: worksheet for worksheet in spreadsheet.worksheets()}
    seed = pd.read_csv(ROOT / "data/raw/LOWER_POLL_SCENARIOS.csv")
    if TAB_NAME in worksheets:
        worksheet = worksheets[TAB_NAME]
        existing = pd.DataFrame(worksheet.get_all_records())
        frame = existing if not existing.empty else seed
        worksheet.clear()
        worksheet.resize(rows=max(50, len(frame) + 1), cols=len(seed.columns))
    else:
        worksheet = spreadsheet.add_worksheet(
            title=TAB_NAME, rows=50, cols=len(seed.columns)
        )
        frame = seed
    worksheet.update([frame.columns.tolist(), *frame.astype(object).values.tolist()], "A1")
    worksheet.freeze(rows=1)
    worksheet.set_basic_filter(f"A1:H{len(frame) + 1}")
    worksheet.format("A1:H1", {
        "backgroundColor": {"red": 0.20, "green": 0.36, "blue": 0.62},
        "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
    })
    print(f"Verified {TAB_NAME}: {len(frame)} saved scenarios")


if __name__ == "__main__":
    main()
