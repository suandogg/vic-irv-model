"""Update only the lower-house OTH donor-depletion settings in PARAMS."""

from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials


ROOT = Path(__file__).resolve().parents[1]
SHEET_ID = "1avkQZ0A8tlVI1tR0UakEriNKuq9N7dwRUFJzecb26Ro"
VALUES = [
    [
        "OTH_ON_DONOR_DEPLETION_STRENGTH", "0.5",
        "Reduces only the generic OTH-to-ON siphon as ON rises; 0 disables and 1 removes the full siphon by the reference ON vote.",
    ],
    [
        "OTH_ON_DEPLETION_BASELINE", "0.28",
        "Historical statewide ON primary used as the zero-depletion anchor.",
    ],
    [
        "OTH_ON_DEPLETION_REFERENCE", "24.4",
        "Statewide ON primary at which the full configured depletion strength applies.",
    ],
]


def main() -> None:
    credentials = Credentials.from_service_account_file(
        ROOT / "credentials.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    worksheet = gspread.authorize(credentials).open_by_key(SHEET_ID).worksheet("PARAMS")
    column_a = worksheet.col_values(1)
    geography_rows = [
        row for row, value in enumerate(column_a, start=1)
        if value == "Geography"
    ]
    if not geography_rows:
        raise RuntimeError("Could not find the Geography parameter section")
    geography_row = max(geography_rows)
    desired_rows = list(range(geography_row - 3, geography_row))

    for values, desired_row in zip(VALUES, desired_rows):
        key = values[0]
        if key in column_a:
            row = column_a.index(key) + 1
        else:
            row = desired_row
            existing = worksheet.cell(row, 1).value
            if existing:
                raise RuntimeError(
                    f"Refusing to overwrite PARAMS row {row}: {existing!r}"
                )
        worksheet.update(values=[values], range_name=f"A{row}:C{row}")
        print(f"Updated PARAMS row {row}: {key}={values[1]}")


if __name__ == "__main__":
    main()
