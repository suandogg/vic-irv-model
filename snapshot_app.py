"""Frozen-input backup entrypoint: use committed CSVs even with Sheet credentials."""
import runpy
from pathlib import Path
import SRC.live_sheet_sync as sheet_sync

def frozen_inputs(*args, **kwargs):
    return {"synced": 0, "errors": [], "message": "Frozen model snapshot — 8 October 2026"}

sheet_sync.sync_inputs_from_google_sheet = frozen_inputs
runpy.run_path(str(Path(__file__).with_name("app.py")), run_name="__main__")
