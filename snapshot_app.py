"""Testing laboratory entrypoint, isolated from the reference spreadsheet."""
import runpy
import os
from pathlib import Path
import SRC.live_sheet_sync as sheet_sync
import streamlit as st

TEST_SHEET_ID = "1sLmANVOERsbV08BIZYUfT_fccTGw-mCvAwJSAD_4968"
# Explicit environment precedence prevents inherited reference-app secrets from
# accidentally reconnecting this deployment to the original spreadsheet.
os.environ["VIC_IRV_SHEET_ID"] = TEST_SHEET_ID
st.sidebar.caption("October testing · corrected exact-field VEC coverage default")
st.sidebar.link_button("Open testing spreadsheet", f"https://docs.google.com/spreadsheets/d/{TEST_SHEET_ID}/edit")

runpy.run_path(str(Path(__file__).with_name("app.py")), run_name="__main__")
