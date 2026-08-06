from __future__ import annotations

import os
from pathlib import Path

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials


ROOT = Path(__file__).resolve().parents[1]
SHEET_ID = "1oScZouRTL46hXtnVmhUg_TYueOdCjbWz6F06ALq5_KQ"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def client() -> gspread.Client:
    credentials_path = Path(
        os.environ.get("VIC_IRV_CREDENTIALS", ROOT / "credentials.json")
    )
    credentials = Credentials.from_service_account_file(
        credentials_path,
        scopes=SCOPES,
    )
    return gspread.authorize(credentials)


def main() -> None:
    spreadsheet = client().open_by_key(SHEET_ID)

    swing = spreadsheet.worksheet("SWING CALC").get(
        "A5:BH92",
        value_render_option="UNFORMATTED_VALUE",
    )
    helper = spreadsheet.worksheet("SEAT HELPER").get(
        "A5:AA92",
        value_render_option="UNFORMATTED_VALUE",
    )
    targets_row = spreadsheet.worksheet("PRIMARY ELECTION CALC (IRV)").get(
        "X8:AC8",
        value_render_option="UNFORMATTED_VALUE",
    )[0]

    swing_by_district = {str(row[0]).strip(): row for row in swing}

    input_rows = []
    expected_rows = []
    for helper_row in helper:
        district = str(helper_row[0]).strip()
        swing_row = swing_by_district[district]

        input_rows.append(
            {
                "district": district,
                "region": helper_row[1],
                "seat_type": helper_row[2],
                "held_by": helper_row[26],
                "ALP_pvi": swing_row[7],
                "LNP_pvi": swing_row[18],
                "GRN_pvi": swing_row[29],
                "IND_pvi": swing_row[39],
                "OTH_pvi": swing_row[49],
                "ON_strength": swing_row[59],
            }
        )
        expected_rows.append(
            {
                "district": district,
                "ALP": helper_row[18],
                "LNP": helper_row[19],
                "GRN": helper_row[20],
                "ON": helper_row[21],
                "IND": helper_row[22],
                "OTH": helper_row[23],
            }
        )

    targets = {
        "GRN": targets_row[0] * 100,
        "ALP": targets_row[1] * 100,
        "OTH": targets_row[2] * 100,
        "IND": targets_row[3] * 100,
        "LNP": targets_row[4] * 100,
        "ON": targets_row[5] * 100,
    }

    raw_dir = ROOT / "data" / "raw"
    fixture_dir = ROOT / "tests" / "fixtures"
    raw_dir.mkdir(parents=True, exist_ok=True)
    fixture_dir.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(input_rows).to_csv(
        raw_dir / "LEGACY_PRIMARY_INPUTS.csv",
        index=False,
    )
    pd.DataFrame(expected_rows).to_csv(
        fixture_dir / "LEGACY_PRIMARY_EXPECTED.csv",
        index=False,
    )
    pd.DataFrame([targets]).to_csv(
        fixture_dir / "LEGACY_PRIMARY_TARGETS.csv",
        index=False,
    )

    print(f"Exported {len(input_rows)} districts")
    print(f"Targets: {targets}")


if __name__ == "__main__":
    main()
