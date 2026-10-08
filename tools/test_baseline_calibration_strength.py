"""Development-only sensitivity for unchanged-final-pair baseline calibration."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from SRC.constants import PARTIES
from SRC.display_metrics import clean_baseline_value
from SRC.federal_on_evidence_loader import apply_production_federal_on_evidence
from SRC.ideology_loader import load_ideology_prior
from SRC.irv import run_irv_for_district
from SRC.legacy_primary_loader import load_legacy_primary_inputs
from SRC.legacy_primary_model import build_corrected_primary_table
from SRC.loaders import apply_seat_held_metadata, load_seat_held_metadata, read_csv_raw
from SRC.matrix_loader import load_synth_pref_matrices
from SRC.params_loader import load_params
from SRC.posterior_loader import load_posterior_scenarios


BASELINE = {"ALP": 36.66, "LNP": 34.48, "GRN": 11.50, "ON": 0.28, "IND": 5.55, "OTH": 11.53}
USER_SCENARIO = {"ALP": 29.0, "LNP": 32.0, "GRN": 12.0, "ON": 18.0, "IND": 4.5, "OTH": 4.5}
STRENGTHS = [0.0, 0.25, 0.50, 0.75, 1.0]
REPORT_DIR = ROOT / "reports"


def targets_for_on(level):
    residual = sum(BASELINE[p] for p in PARTIES if p != "ON")
    return {p: level if p == "ON" else BASELINE[p] * (100 - level) / residual for p in PARTIES}


def params_for(params, targets):
    out = dict(params)
    out["scalar_params"] = dict(params.get("scalar_params", {}))
    out["scalar_params"]["SCENARIO_ON_PRIMARY"] = targets["ON"] / sum(targets.values()) * 100
    return out


def party_share(result, party):
    if result["winner"] == party:
        return result["winner_pct"]
    if result["runner_up"] == party:
        return result["runner_up_pct"]
    return None


def main():
    inputs = apply_seat_held_metadata(load_legacy_primary_inputs(), load_seat_held_metadata())
    matrices = load_synth_pref_matrices()
    params = load_params()
    posterior = apply_production_federal_on_evidence(load_posterior_scenarios())
    ideology = load_ideology_prior()
    on_alpha = float(params["scalar_params"].get("ON alpha", 0.6))
    baseline_primaries = build_corrected_primary_table(inputs, BASELINE, on_alpha=on_alpha)
    baseline_lookup = baseline_primaries.assign(key=baseline_primaries["district"].str.upper()).set_index("key")
    recorded = read_csv_raw("BASELINE_2CP.csv")
    recorded["key"] = recorded["district"].str.upper()
    recorded = recorded.set_index("key")

    reconstruction = {}
    for district, matrix_obj in matrices.items():
        key = district.upper()
        seat = baseline_lookup.loc[key]
        held = seat["held_by"]
        actual_share = clean_baseline_value(recorded.loc[key].get(f"{held}_2CP"))
        actual_pair = [party for party in PARTIES if pd.notna(recorded.loc[key].get(f"{party}_2CP"))]
        result = run_irv_for_district(
            {p: float(seat[p]) for p in PARTIES}, matrix_obj["matrix"], seat["seat_type"],
            params_for(params, BASELINE), posterior, ideology,
        )
        model_share = party_share(result, held)
        reconstruction[key] = {
            "held": held, "actual_share": actual_share, "actual_pair": actual_pair,
            "residual": model_share - actual_share if model_share is not None and actual_share is not None else None,
        }

    scenarios = [("User scenario", USER_SCENARIO)] + [
        (f"ON {level:g}", targets_for_on(level)) for level in [10.0, 20.0, 24.4]
    ]
    rows = []
    for scenario_name, targets in scenarios:
        primaries = build_corrected_primary_table(inputs, targets, on_alpha=on_alpha)
        lookup = primaries.assign(key=primaries["district"].str.upper()).set_index("key")
        for district, matrix_obj in matrices.items():
            key = district.upper()
            seat = lookup.loc[key]
            info = reconstruction[key]
            result = run_irv_for_district(
                {p: float(seat[p]) for p in PARTIES}, matrix_obj["matrix"], seat["seat_type"],
                params_for(params, targets), posterior, ideology,
            )
            pair = {result["winner"], result["runner_up"]}
            eligible = len(info["actual_pair"]) == 2 and pair == set(info["actual_pair"])
            held_share = party_share(result, info["held"])
            for strength in STRENGTHS:
                calibrated_held = (
                    max(0.0, min(1.0, held_share - strength * info["residual"]))
                    if eligible and held_share is not None and info["residual"] is not None
                    else held_share
                )
                if eligible:
                    opponent = next(p for p in info["actual_pair"] if p != info["held"])
                    winner = info["held"] if calibrated_held >= 0.5 else opponent
                    runner = opponent if winner == info["held"] else info["held"]
                    winner_pct = calibrated_held if winner == info["held"] else 1 - calibrated_held
                else:
                    winner, runner, winner_pct = result["winner"], result["runner_up"], result["winner_pct"]
                rows.append({
                    "Scenario": scenario_name, "CalibrationStrength": strength,
                    "District": district, "SeatType": seat["seat_type"], "HeldBy": info["held"],
                    "Eligible": eligible, "BaselineResidual": info["residual"],
                    "RawWinner": result["winner"], "RawRunnerUp": result["runner_up"],
                    "RawWinnerPct": result["winner_pct"], "RawHeldShare": held_share,
                    "CalibratedHeldShare": calibrated_held,
                    "CalibratedWinner": winner, "CalibratedRunnerUp": runner,
                    "CalibratedWinnerPct": winner_pct,
                    "WinnerChanged": winner != result["winner"],
                    "HeldShareChange": calibrated_held - held_share if calibrated_held is not None and held_share is not None else None,
                })

    detail = pd.DataFrame(rows)
    seat_counts = detail.groupby(["Scenario", "CalibrationStrength", "CalibratedWinner"]).size().unstack(fill_value=0)
    for party in PARTIES:
        if party not in seat_counts:
            seat_counts[party] = 0
    seat_counts = seat_counts[PARTIES].reset_index().rename(columns={p: f"{p}Seats" for p in PARTIES})
    summary = detail.groupby(["Scenario", "CalibrationStrength"], as_index=False).agg(
        EligibleSeats=("Eligible", "sum"), WinnerChanges=("WinnerChanged", "sum"),
        MeanAbsoluteHeldShareChange=("HeldShareChange", lambda x: x.abs().mean()),
        MaximumAbsoluteHeldShareChange=("HeldShareChange", lambda x: x.abs().max()),
    ).merge(seat_counts, on=["Scenario", "CalibrationStrength"], how="left")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    detail.to_csv(REPORT_DIR / "baseline_calibration_sensitivity_all_seats.csv", index=False)
    detail[detail["WinnerChanged"]].to_csv(
        REPORT_DIR / "baseline_calibration_sensitivity_changed_seats.csv", index=False
    )
    summary.to_csv(REPORT_DIR / "baseline_calibration_sensitivity_summary.csv", index=False)
    print(summary.to_string(index=False))
    print("\nUser-scenario winner changes:\n", detail[(detail.Scenario == "User scenario") & detail.WinnerChanged].to_string(index=False))


if __name__ == "__main__":
    main()
