"""Development-only sensitivity for non-ON preference geography strength.

The ON recipient adjustment is always retained at its current value. Only
ALP/LNP/GRN/IND/OTH geography adjustments are scaled.
"""

from __future__ import annotations

from copy import deepcopy
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
USER_SCENARIO = {"ALP": 29.0, "LNP": 32.0, "GRN": 12.0, "ON": 18.0, "IND": 4.5, "OTH": 4.5}
STANDARD_ON_LEVELS = [10.0, 20.0, 24.4]
NON_ON_STRENGTHS = [0.0, 0.25, 0.50, 0.75]
REPORT_DIR = ROOT / "reports"


def targets_for_on(level):
    residual = sum(BASELINE[p] for p in PARTIES if p != "ON")
    return {p: level if p == "ON" else BASELINE[p] * (100 - level) / residual for p in PARTIES}


def scaled_params(params, targets, strength):
    out = deepcopy(params)
    total = sum(targets.values())
    out["scalar_params"]["SCENARIO_ON_PRIMARY"] = targets["ON"] / total * 100
    for seat_class, adjustments in out.get("geography_adjustments", {}).items():
        original_on = adjustments.get("ON")
        out["geography_adjustments"][seat_class] = {
            party: (value if party == "ON" else float(value or 0.0) * strength)
            for party, value in adjustments.items()
        }
        if out["geography_adjustments"][seat_class].get("ON") != original_on:
            raise AssertionError("ON geography adjustment must remain unchanged")
    return out


def main():
    inputs = load_legacy_primary_inputs()
    matrices = load_synth_pref_matrices()
    params = load_params()
    posterior = apply_production_federal_on_evidence(load_posterior_scenarios())
    ideology = load_ideology_prior()
    on_alpha = float(params["scalar_params"].get("ON alpha", 0.6))
    scenarios = [("User scenario", USER_SCENARIO)] + [
        (f"ON {level:g}", targets_for_on(level)) for level in STANDARD_ON_LEVELS
    ]
    rows = []
    for scenario_name, targets in scenarios:
        primaries = build_corrected_primary_table(inputs, targets, on_alpha=on_alpha)
        lookup = primaries.assign(key=primaries["district"].str.upper()).set_index("key")
        current_params = scaled_params(params, targets, 1.0)
        for district, matrix_obj in matrices.items():
            seat = lookup.loc[district.upper()]
            votes = {party: float(seat[party]) for party in PARTIES}
            current = run_irv_for_district(votes, matrix_obj["matrix"], seat["seat_type"], current_params, posterior, ideology)
            for strength in NON_ON_STRENGTHS:
                trial = run_irv_for_district(
                    votes, matrix_obj["matrix"], seat["seat_type"],
                    scaled_params(params, targets, strength), posterior, ideology,
                )
                rows.append({
                    "Scenario": scenario_name, "NonONGeographyStrength": strength,
                    "District": district, "SeatType": seat["seat_type"],
                    "CurrentWinner": current["winner"], "CurrentRunnerUp": current["runner_up"],
                    "CurrentWinnerPct": current["winner_pct"],
                    "TrialWinner": trial["winner"], "TrialRunnerUp": trial["runner_up"],
                    "TrialWinnerPct": trial["winner_pct"],
                    "WinnerChanged": current["winner"] != trial["winner"],
                    "PairChanged": current["matchup"] != trial["matchup"],
                    "WinnerPctChange": trial["winner_pct"] - current["winner_pct"],
                })
    detail = pd.DataFrame(rows)
    summary = detail.groupby(["Scenario", "NonONGeographyStrength"], as_index=False).agg(
        WinnerChanges=("WinnerChanged", "sum"), PairChanges=("PairChanged", "sum"),
        MeanAbsoluteWinnerPctChange=("WinnerPctChange", lambda x: x.abs().mean()),
        MaximumAbsoluteWinnerPctChange=("WinnerPctChange", lambda x: x.abs().max()),
    )
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    detail.to_csv(REPORT_DIR / "non_on_geography_sensitivity_all_seats.csv", index=False)
    detail[detail["WinnerChanged"] | detail["PairChanged"]].to_csv(
        REPORT_DIR / "non_on_geography_sensitivity_changed_seats.csv", index=False
    )
    summary.to_csv(REPORT_DIR / "non_on_geography_sensitivity_summary.csv", index=False)
    print(summary.to_string(index=False))
    print("\nChanged seats:\n", detail[detail["WinnerChanged"] | detail["PairChanged"]].to_string(index=False))


if __name__ == "__main__":
    main()
