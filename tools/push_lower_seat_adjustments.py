"""Publish the editable lower-house seat adjustment register and defaults."""

from __future__ import annotations

from pathlib import Path

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials


ROOT = Path(__file__).resolve().parents[1]
SHEET_ID = "1avkQZ0A8tlVI1tR0UakEriNKuq9N7dwRUFJzecb26Ro"
TAB_NAME = "LOWER_SEAT_ADJUSTMENTS"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
PARAM_ROWS = [
    (
        "RETIRING_INCUMBENT_PENALTY_PP", 1.0,
        "Default primary-vote penalty when the incumbent member retires; editable by seat in LOWER_SEAT_ADJUSTMENTS.",
    ),
    (
        "SOPHOMORE_SURGE_BONUS_PP", 1.0,
        "Default primary-vote bonus for a member contesting their first re-election; editable by seat in LOWER_SEAT_ADJUSTMENTS.",
    ),
]


def main() -> None:
    client = gspread.authorize(Credentials.from_service_account_file(
        ROOT / "credentials.json", scopes=SCOPES
    ))
    spreadsheet = client.open_by_key(SHEET_ID)
    source = pd.read_csv(ROOT / "data/raw/LEGACY_PRIMARY_INPUTS.csv")
    frame = source[["district", "held_by"]].rename(columns={"held_by": "party"})
    frame["retiring_incumbent"] = False
    frame["first_re_election"] = False
    frame["retirement_penalty_pp"] = ""
    frame["sophomore_bonus_pp"] = ""
    frame["candidate_strength_pp"] = ""
    frame["manual_adjustment_pp"] = ""
    frame["enabled"] = True
    frame["notes"] = ""
    frame = frame.sort_values("district").reset_index(drop=True)

    worksheets = {worksheet.title: worksheet for worksheet in spreadsheet.worksheets()}
    if TAB_NAME in worksheets:
        worksheet = worksheets[TAB_NAME]
        existing = pd.DataFrame(worksheet.get_all_records())
        if not existing.empty and "district" in existing:
            preserved = existing.set_index("district")
            for column in frame.columns[2:]:
                if column in preserved:
                    frame[column] = frame["district"].map(preserved[column]).fillna(frame[column])
        worksheet.clear()
        worksheet.resize(rows=max(100, len(frame) + 1), cols=len(frame.columns))
    else:
        worksheet = spreadsheet.add_worksheet(
            title=TAB_NAME, rows=max(100, len(frame) + 1), cols=len(frame.columns)
        )
    worksheet.update([frame.columns.tolist(), *frame.astype(object).values.tolist()], "A1")
    worksheet.freeze(rows=1)
    worksheet.set_basic_filter(f"A1:J{len(frame) + 1}")
    worksheet.format("A1:J1", {
        "backgroundColor": {"red": 0.20, "green": 0.36, "blue": 0.62},
        "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
    })

    params = spreadsheet.worksheet("PARAMS")
    for key, value, description in PARAM_ROWS:
        values = params.get_all_values()
        keys = [row[0] if row else "" for row in values]
        if key in keys:
            row_no = keys.index(key) + 1
        else:
            row_no = keys.index("Optional for later") + 1
            params.insert_row([], index=row_no)
        params.update(
            values=[[key, value, description]], range_name=f"A{row_no}:C{row_no}",
            value_input_option="USER_ENTERED",
        )
        verified = params.get(f"A{row_no}:C{row_no}")[0]
        if verified[0] != key or abs(float(verified[1]) - value) > 1e-12:
            raise RuntimeError(f"PARAMS verification failed: {verified!r}")
    print(f"Verified {TAB_NAME}: {len(frame)} seats and {len(PARAM_ROWS)} defaults")


if __name__ == "__main__":
    main()
