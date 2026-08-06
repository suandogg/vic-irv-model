from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw"
CREDENTIALS_FILE = ROOT / "credentials.json"
DEFAULT_SHEET_ID = "1avkQZ0A8tlVI1tR0UakEriNKuq9N7dwRUFJzecb26Ro"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

FILES = {
    "LOWER_PRIMARY_INPUTS": "LEGACY_PRIMARY_INPUTS.csv",
    "PARAMS": "PARAMS.csv",
    "SYNTH PREF MATRIX": "SYNTH PREF MATRIX.csv",
    "BASELINE_2CP": "BASELINE_2CP.csv",
    "BASELINE_REGION_SUMMARY": "BASELINE_REGION_SUMMARY.csv",
    "IDEOLOGY": "IDEOLOGY.csv",
    "UPPER_REGION_BASELINE": "UPPER_REGION_BASELINE.csv",
    "UPPER_PREF_PARAMS": "UPPER_PREF_PARAMS.csv",
    "UPPER_PARTY_RELATIONSHIPS": "UPPER_PARTY_RELATIONSHIPS.csv",
    "UPPER_INCUMBENTS": "UPPER_INCUMBENTS.csv",
    "2022_GVTs": "2022_GVTs.csv",
}

RAW_GRID_TABS = {
    "PARAMS",
    "SYNTH PREF MATRIX",
}


def _secret_get(
    secrets: Mapping[str, Any] | None,
    key: str,
    default: Any = None,
) -> Any:
    if secrets is None:
        return default
    try:
        return secrets.get(key, default)
    except Exception:
        try:
            return secrets[key]
        except Exception:
            return default


def _as_dict(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return dict(value)
    try:
        return dict(value)
    except Exception:
        return None


def resolve_sheet_id(secrets: Mapping[str, Any] | None = None) -> str:
    for key in [
        "VIC_IRV_SHEET_ID",
        "vic_irv_sheet_id",
        "google_sheet_id",
        "sheet_id",
    ]:
        value = os.environ.get(key) or _secret_get(secrets, key)
        if value:
            return str(value).strip()
    return DEFAULT_SHEET_ID


def resolve_credentials(
    secrets: Mapping[str, Any] | None = None,
) -> Credentials | None:
    raw_json = os.environ.get("VIC_IRV_GOOGLE_CREDENTIALS_JSON")
    if raw_json:
        return Credentials.from_service_account_info(
            json.loads(raw_json),
            scopes=SCOPES,
        )

    for key in [
        "gcp_service_account",
        "google_service_account",
        "service_account",
    ]:
        info = _as_dict(_secret_get(secrets, key))
        if info:
            return Credentials.from_service_account_info(info, scopes=SCOPES)

    top_level = _as_dict(secrets)
    if top_level and {"client_email", "private_key"}.issubset(top_level):
        return Credentials.from_service_account_info(top_level, scopes=SCOPES)

    if CREDENTIALS_FILE.exists():
        return Credentials.from_service_account_file(
            CREDENTIALS_FILE,
            scopes=SCOPES,
        )

    return None


def worksheet_to_dataframe(worksheet, tab_name: str) -> pd.DataFrame:
    if tab_name in RAW_GRID_TABS:
        return pd.DataFrame(worksheet.get_all_values())
    return pd.DataFrame(worksheet.get_all_records())


def sync_inputs_from_google_sheet(
    secrets: Mapping[str, Any] | None = None,
    only_tabs: set[str] | None = None,
) -> dict[str, Any]:
    credentials = resolve_credentials(secrets)
    if credentials is None:
        return {
            "ok": False,
            "synced": 0,
            "skipped": [],
            "errors": [],
            "message": "Missing Google service-account credentials",
        }

    try:
        client = gspread.authorize(credentials)
        sheet = client.open_by_key(resolve_sheet_id(secrets))
        available_tabs = {worksheet.title for worksheet in sheet.worksheets()}
    except Exception as exc:
        return {
            "ok": False,
            "synced": 0,
            "skipped": [],
            "errors": [str(exc)],
            "message": f"Google Sheet connection failed: {exc}",
        }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    synced = 0
    skipped = []
    errors = []

    for tab_name, csv_filename in FILES.items():
        if only_tabs and tab_name not in only_tabs and csv_filename not in only_tabs:
            continue
        if tab_name not in available_tabs:
            skipped.append(tab_name)
            continue

        try:
            dataframe = worksheet_to_dataframe(sheet.worksheet(tab_name), tab_name)
            if dataframe.empty:
                skipped.append(tab_name)
                continue

            output_path = DATA_DIR / csv_filename
            dataframe.to_csv(
                output_path,
                index=False,
                header=tab_name not in RAW_GRID_TABS,
            )
            synced += 1
        except Exception as exc:
            errors.append(f"{tab_name}: {exc}")

    return {
        "ok": not errors,
        "synced": synced,
        "skipped": skipped,
        "errors": errors,
        "message": f"Synced {synced} Google Sheet tabs",
    }
