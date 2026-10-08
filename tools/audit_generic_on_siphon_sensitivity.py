"""Measure outcome reliance on unsupported generic ON siphoning."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from SRC.constants import PARTIES
from SRC.federal_on_evidence_loader import apply_production_federal_on_evidence
from SRC.ideology_loader import load_ideology_prior
from SRC.irv import run_irv_for_district
from SRC.legacy_primary_loader import load_legacy_primary_inputs
from SRC.legacy_primary_model import build_corrected_primary_table
from SRC.matrix_loader import load_synth_pref_matrices
from SRC.params_loader import load_params
from SRC.posterior_loader import load_posterior_scenarios


BASELINE = {"ALP": 36.66, "LNP": 34.48, "GRN": 11.50, "ON": 0.28, "IND": 5.55, "OTH": 11.53}
ON_LEVELS = [10.0, 18.0, 20.0, 24.4]
REPORT_DIR = ROOT / "reports"


def targets_for_on(level):
    residual = sum(BASELINE[p] for p in PARTIES if p != "ON")
    return {p: level if p == "ON" else BASELINE[p] * (100 - level) / residual for p in PARTIES}


def params_for_level(params, level, siphon_enabled=True):
    out = dict(params)
    out["scalar_params"] = dict(params.get("scalar_params", {}))
    out["scalar_params"]["SCENARIO_ON_PRIMARY"] = level
    if not siphon_enabled:
        out["scalar_params"]["SIPHON_STRENGTH_ON"] = 0.0
    return out


def main():
    inputs = load_legacy_primary_inputs()
    matrices = load_synth_pref_matrices()
    params = load_params()
    posterior = apply_production_federal_on_evidence(load_posterior_scenarios())
    ideology = load_ideology_prior()
    on_alpha = float(params["scalar_params"].get("ON alpha", 0.6))
    rows = []
    for level in ON_LEVELS:
        primaries = build_corrected_primary_table(inputs, targets_for_on(level), on_alpha=on_alpha)
        lookup = primaries.assign(key=primaries["district"].str.upper()).set_index("key")
        current_params = params_for_level(params, level, True)
        no_siphon_params = params_for_level(params, level, False)
        for district, matrix_obj in matrices.items():
            seat = lookup.loc[district.upper()]
            votes = {party: float(seat[party]) for party in PARTIES}
            current = run_irv_for_district(votes, matrix_obj["matrix"], seat["seat_type"], current_params, posterior, ideology)
            no_siphon = run_irv_for_district(votes, matrix_obj["matrix"], seat["seat_type"], no_siphon_params, posterior, ideology)
            rows.append({
                "ONLevel": level, "District": district, "SeatType": seat["seat_type"],
                "CurrentWinner": current["winner"], "CurrentRunnerUp": current["runner_up"],
                "CurrentWinnerPct": current["winner_pct"],
                "NoSiphonWinner": no_siphon["winner"], "NoSiphonRunnerUp": no_siphon["runner_up"],
                "NoSiphonWinnerPct": no_siphon["winner_pct"],
                "WinnerChanged": current["winner"] != no_siphon["winner"],
                "PairChanged": current["matchup"] != no_siphon["matchup"],
                "WinnerPctChange": no_siphon["winner_pct"] - current["winner_pct"],
            })
    detail = pd.DataFrame(rows)
    summary = detail.groupby("ONLevel", as_index=False).agg(
        WinnerChanges=("WinnerChanged", "sum"), PairChanges=("PairChanged", "sum"),
        MeanAbsoluteWinnerPctChange=("WinnerPctChange", lambda x: x.abs().mean()),
        MaximumAbsoluteWinnerPctChange=("WinnerPctChange", lambda x: x.abs().max()),
    )
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    detail.to_csv(REPORT_DIR / "generic_on_siphon_sensitivity_all_seats.csv", index=False)
    detail[detail["WinnerChanged"] | detail["PairChanged"]].to_csv(
        REPORT_DIR / "generic_on_siphon_sensitivity_changed_seats.csv", index=False
    )
    summary.to_csv(REPORT_DIR / "generic_on_siphon_sensitivity_summary.csv", index=False)
    print(summary.to_string(index=False))
    print("\nChanged seats:\n", detail[detail["WinnerChanged"] | detail["PairChanged"]].to_string(index=False))


if __name__ == "__main__":
    main()
