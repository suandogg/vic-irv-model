"""Startup-only legacy selection; never switch input generations mid-run."""
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def legacy_mode():return os.environ.get('PRISM_MODEL_VERSION','v6')=='legacy'
def data_root():return ROOT/'data'/'legacy_20261114' if legacy_mode() else ROOT/'data'
