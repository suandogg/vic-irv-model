from __future__ import annotations

from pathlib import Path

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials


ROOT = Path(__file__).resolve().parents[1]
SHEET_ID = "1avkQZ0A8tlVI1tR0UakEriNKuq9N7dwRUFJzecb26Ro"
TAB_NAME = "LOWER_PRIMARY_INPUTS"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def main() -> None:
    credentials = Credentials.from_service_account_file(
        ROOT / "credentials.json",
        scopes=SCOPES,
    )
    spreadsheet = gspread.authorize(credentials).open_by_key(SHEET_ID)

    if TAB_NAME in {worksheet.title for worksheet in spreadsheet.worksheets()}:
        raise RuntimeError(
            f"{TAB_NAME} already exists; refusing to overwrite it automatically"
        )

    frame = pd.read_csv(ROOT / "data" / "raw" / "LEGACY_PRIMARY_INPUTS.csv")
    values = [frame.columns.tolist(), *frame.astype(object).values.tolist()]

    worksheet = spreadsheet.add_worksheet(
        title=TAB_NAME,
        rows=max(100, len(values)),
        cols=len(frame.columns),
    )
    worksheet.update(values, "A1")
    worksheet.freeze(rows=1)
    worksheet.format(
        "A1:J1",
        {
            "backgroundColor": {"red": 0.20, "green": 0.36, "blue": 0.62},
            "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
        },
    )
    worksheet.format("E2:J89", {"numberFormat": {"type": "NUMBER", "pattern": "0.000000"}})
    worksheet.set_basic_filter("A1:J89")

    print(f"Created {TAB_NAME} with {len(frame)} districts")


if __name__ == "__main__":
    main()
