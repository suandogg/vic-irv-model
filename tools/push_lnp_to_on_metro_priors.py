"""Update only metropolitan LNP elimination priors in ALP-ON final twos."""

from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials


ROOT = Path(__file__).resolve().parents[1]
SHEET_ID = "1avkQZ0A8tlVI1tR0UakEriNKuq9N7dwRUFJzecb26Ro"
UPDATES = {
    ("ALP+ON", "LNP", "Inner Ring"): (0.50, 0.50),
    ("ALP+ON", "LNP", "Middle Ring"): (0.44, 0.56),
    ("ALP+ON", "LNP", "Outer Metro"): (0.37, 0.63),
}


def main() -> None:
    credentials = Credentials.from_service_account_file(
        ROOT / "credentials.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    worksheet = gspread.authorize(credentials).open_by_key(SHEET_ID).worksheet("PARAMS")
    values = worksheet.get_all_values()
    matched = {}
    for row_number, row in enumerate(values, start=1):
        padded = row + [""] * (6 - len(row))
        key = tuple(cell.strip() for cell in padded[:3])
        if key in UPDATES:
            if key in matched:
                raise RuntimeError(f"Duplicate PARAMS special prior: {key}")
            matched[key] = row_number
    missing = set(UPDATES) - set(matched)
    if missing:
        raise RuntimeError(f"Missing PARAMS special priors: {sorted(missing)}")

    for key, (alp_share, on_share) in UPDATES.items():
        row_number = matched[key]
        worksheet.update(
            values=[[alp_share, "", on_share]],
            range_name=f"D{row_number}:F{row_number}",
            value_input_option="USER_ENTERED",
        )

    verified = worksheet.get_all_values()
    for key, (alp_share, on_share) in UPDATES.items():
        row = verified[matched[key] - 1] + [""] * 6
        actual = (float(row[3]), float(row[5]))
        if any(abs(a - b) > 1e-12 for a, b in zip(actual, (alp_share, on_share))):
            raise RuntimeError(f"Verification failed for {key}: {actual}")
        print(f"Verified PARAMS row {matched[key]} {key}: ALP={actual[0]}, ON={actual[1]}")


if __name__ == "__main__":
    main()
