from __future__ import annotations

from pathlib import Path

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials


ROOT = Path(__file__).resolve().parents[1]
SHEET_ID = "1avkQZ0A8tlVI1tR0UakEriNKuq9N7dwRUFJzecb26Ro"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
INPUTS = {
    "LOWER_ON_PREF_EVIDENCE": ROOT / "data" / "development" / "FEDERAL_VIC_ON_SCENARIOS.csv",
    "LOWER_ON_PREF_CONFIG": ROOT / "data" / "raw" / "LOWER_ON_PREF_CONFIG.csv",
}


def replace_tab(spreadsheet, title: str, frame: pd.DataFrame) -> None:
    worksheets = {worksheet.title: worksheet for worksheet in spreadsheet.worksheets()}
    if title in worksheets:
        worksheet = worksheets[title]
        worksheet.clear()
        worksheet.resize(rows=max(100, len(frame) + 1), cols=len(frame.columns))
    else:
        worksheet = spreadsheet.add_worksheet(
            title=title, rows=max(100, len(frame) + 1), cols=len(frame.columns)
        )
    values = [frame.columns.tolist(), *frame.fillna("").astype(object).values.tolist()]
    worksheet.update(values, "A1")
    worksheet.freeze(rows=1)
    worksheet.format(
        f"A1:{gspread.utils.rowcol_to_a1(1, len(frame.columns))}",
        {
            "backgroundColor": {"red": 0.20, "green": 0.36, "blue": 0.62},
            "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
        },
    )


def main() -> None:
    credentials = Credentials.from_service_account_file(
        ROOT / "credentials.json", scopes=SCOPES
    )
    spreadsheet = gspread.authorize(credentials).open_by_key(SHEET_ID)
    for title, path in INPUTS.items():
        frame = pd.read_csv(path)
        replace_tab(spreadsheet, title, frame)
        print(f"Updated {title}: {len(frame)} rows")


if __name__ == "__main__":
    main()
