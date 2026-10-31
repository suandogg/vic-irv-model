from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw"
CREDENTIALS_FILE = ROOT / "credentials.json"
DEFAULT_SHEET_ID = "1sLmANVOERsbV08BIZYUfT_fccTGw-mCvAwJSAD_4968"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

FILES = {
    "DISPLAY PARAMS": "DISPLAY PARAMS.csv",
    "FORECAST PARAMS": "FORECAST PARAMS.csv",
    "NOWCAST BUDGET": "NOWCAST BUDGET.csv",
    "NOWCAST CORRELATION": "NOWCAST CORRELATION.csv",
    "NOWCAST CONTEXTS": "NOWCAST CONTEXTS.csv",
    "SUB-REGIONS": "SUB-REGIONS.csv",
    "LOWER_PRIMARY_INPUTS": "LEGACY_PRIMARY_INPUTS.csv",
    "LOWER_TURNOUT_WEIGHTS": "LOWER_TURNOUT_WEIGHTS.csv",
    "SEAT HELPER": "SEAT HELPER.csv",
    "PARAMS": "PARAMS.csv",
    "SYNTH PREF MATRIX": "SYNTH PREF MATRIX.csv",
    "BASELINE_2CP": "BASELINE_2CP.csv",
    "BASELINE_REGION_SUMMARY": "BASELINE_REGION_SUMMARY.csv",
    "IDEOLOGY": "IDEOLOGY.csv",
    "LOWER_ON_PREF_EVIDENCE": "FEDERAL_VIC_ON_SCENARIOS.csv",
    "LOWER_ON_PREF_CONFIG": "LOWER_ON_PREF_CONFIG.csv",
    "LOWER_LNP_PRECOLLAPSE": "LOWER_LNP_PRECOLLAPSE.csv",
    "LOWER_SEAT_ADJUSTMENTS": "LOWER_SEAT_ADJUSTMENTS.csv",
    "LOWER_CANDIDATE_EFFECTS": "LOWER_CANDIDATE_EFFECTS.csv",
    "LOWER_CANDIDATE_FIELD": "LOWER_CANDIDATE_FIELD.csv",
    "LOWER_CANDIDATE_PREFS": "LOWER_CANDIDATE_PREFS.csv",
    "LOWER_POLL_SCENARIOS": "LOWER_POLL_SCENARIOS.csv",
    "UPPER_REGION_BASELINE": "UPPER_REGION_BASELINE.csv",
    "UPPER_PREF_PARAMS": "UPPER_PREF_PARAMS.csv",
    "UPPER_PARTY_RELATIONSHIPS": "UPPER_PARTY_RELATIONSHIPS.csv",
    "UPPER_INCUMBENTS": "UPPER_INCUMBENTS.csv",
    "2022_GVTs": "2022_GVTs.csv",
    "UPPER_PARTY_INPUTS_NAMED": "UPPER_PARTY_INPUTS_NAMED.csv",
    "UPPER_CANDIDATES": "UPPER_CANDIDATES.csv",
    "UPPER_2022_CANDIDATES": "UPPER_2022_CANDIDATES.csv",
    "UPPER_REGION_PVI_NAMED": "UPPER_REGION_PVI_NAMED.csv",
    "UPPER_PREFERENCE_EVIDENCE": "UPPER_PREFERENCE_EVIDENCE.csv",
    "UPPER_PREFERENCE_PRIORS": "UPPER_PREFERENCE_PRIORS.csv",
    "UPPER_BALLOT_BEHAVIOUR": "UPPER_BALLOT_BEHAVIOUR.csv",
    "UPPER_OVERRIDES": "UPPER_OVERRIDES.csv",
    "UPPER_MODEL_PARAMS": "UPPER_MODEL_PARAMS.csv",
    "UPPER_PARTY_CLASSES": "UPPER_PARTY_CLASSES.csv",
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
    if tab_name.startswith('LOWER_CANDIDATE_'):
        values = worksheet.get_all_values()
        if not values or not values[0] or len(set(values[0])) != len(values[0]):
            raise ValueError('Candidate tab requires unique column headings')
        return pd.DataFrame(values[1:], columns=values[0])
    if tab_name in RAW_GRID_TABS:
        return pd.DataFrame(worksheet.get_all_values())
    return pd.DataFrame(worksheet.get_all_records())


def safe_sync_error(exc: Exception) -> str:
    """Public app diagnostics must never echo arbitrary credential/API payloads."""
    response = getattr(exc, "response", None)
    code = getattr(response, "status_code", None)
    if code == 429:
        return "Google read-request quota/rate limit reached (HTTP 429)."
    if code in (401, 403):
        return f"Google authentication or spreadsheet permission error (HTTP {code})."
    if code == 404:
        return "Google could not find the spreadsheet or tab (HTTP 404)."
    if isinstance(code, int) and code >= 500:
        return f"Google service temporarily unavailable (HTTP {code})."
    message = str(exc).lower()
    if "header" in message and ("duplicate" in message or "unique" in message):
        return "Duplicate column headings: the tab could not be imported as named columns."
    if "timeout" in message or "timed out" in message:
        return "The Google Sheet request timed out."
    if isinstance(exc, OSError):
        return "Network or local saved-input access failed."
    if isinstance(exc, (ValueError, TypeError)):
        return "The tab could not be converted to the expected input table."
    return "Sheet import failed; exception type: " + type(exc).__name__ + "."


def input_diagnostic(tab_name: str, filename: str, status: str, reason: str = "") -> dict:
    path = DATA_DIR / filename
    try:
        available = path.is_file() and path.stat().st_size > 0
        modified = (datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
                    if available else None)
    except OSError:
        available, modified = None, None
    return {"tab":tab_name,"file":filename,"status":status,"reason":reason,
            "saved_csv_available":available,"saved_csv_modified_utc":modified}


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
            "diagnostics": [],
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
            "message": "Google Sheet connection failed: " + safe_sync_error(exc),
            "diagnostics": [{"tab":"Spreadsheet connection","status":"error",
                "reason":safe_sync_error(exc),"file":"","saved_csv_available":None}],
        }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    synced = 0
    skipped = []
    errors = []
    diagnostics = []

    for tab_name, csv_filename in FILES.items():
        if only_tabs and tab_name not in only_tabs and csv_filename not in only_tabs:
            continue
        if tab_name not in available_tabs:
            skipped.append(tab_name)
            diagnostics.append(input_diagnostic(tab_name,csv_filename,"skipped","Tab not found in workbook."))
            continue

        try:
            dataframe = worksheet_to_dataframe(sheet.worksheet(tab_name), tab_name)
            if dataframe.empty and not tab_name.startswith('LOWER_CANDIDATE_'):
                skipped.append(tab_name)
                diagnostics.append(input_diagnostic(tab_name,csv_filename,"skipped","Tab has no data rows."))
                continue

            output_path = DATA_DIR / csv_filename
            dataframe.to_csv(
                output_path,
                index=False,
                header=tab_name not in RAW_GRID_TABS,
            )
            synced += 1
            diagnostics.append(input_diagnostic(tab_name,csv_filename,"synced"))
        except Exception as exc:
            errors.append(f"{tab_name}: {exc}")
            diagnostics.append(input_diagnostic(tab_name,csv_filename,"error",safe_sync_error(exc)))

    return {
        "ok": not errors,
        "synced": synced,
        "skipped": skipped,
        "errors": errors,
        "message": f"Synced {synced} Google Sheet tabs",
        "diagnostics": diagnostics,
    }
