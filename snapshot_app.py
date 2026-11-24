"""Testing laboratory entrypoint, isolated from the reference spreadsheet."""
import runpy
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
if "--legacy" in sys.argv: os.environ["PRISM_MODEL_VERSION"]="legacy"
else: os.environ.setdefault("PRISM_MODEL_VERSION","v6")
from SRC.model_version import legacy_mode
import SRC.live_sheet_sync as sheet_sync
import streamlit as st

TEST_SHEET_ID = "1sLmANVOERsbV08BIZYUfT_fccTGw-mCvAwJSAD_4968"
# Explicit environment precedence prevents inherited reference-app secrets from
# accidentally reconnecting this deployment to the original spreadsheet.
os.environ["VIC_IRV_SHEET_ID"] = TEST_SHEET_ID
st.sidebar.caption('October testing · legacy 14 November' if legacy_mode() else 'October testing · frozen v6 defaults (legacy: -- --legacy)')
st.sidebar.link_button("Open testing spreadsheet", f"https://docs.google.com/spreadsheets/d/{TEST_SHEET_ID}/edit")

runpy.run_path(str(Path(__file__).with_name("app.py")), run_name="__main__")
