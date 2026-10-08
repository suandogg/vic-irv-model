"""Approximate 2022 leave-one-seat-out validation of preference methodology."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from SRC.constants import PARTIES
from SRC.ideology_loader import load_ideology_prior
from SRC.irv import run_irv_for_district
from SRC.legacy_primary_loader import load_legacy_primary_inputs
from SRC.legacy_primary_model import build_corrected_primary_table
from SRC.loaders import read_csv_raw
from SRC.matrix_loader import load_synth_pref_matrices
from SRC.params_loader import load_params
from SRC.posterior_loader import load_posterior_scenarios


TARGETS_2022_NO_ON = {
    "ALP": 36.66, "LNP": 34.48, "GRN": 11.50,
    "ON": 0.0, "IND": 5.55, "OTH": 11.53,
}
REPORT_DIR = ROOT / "reports"


def mean_matrix(items):
    items = list(items)
    return {
        source: {
            recipient: sum(
                float(item["matrix"].get(source, {}).get(recipient, 0.0) or 0.0)
                for item in items
            ) / len(items)
            for recipient in PARTIES
        }
        for source in PARTIES
    }


def scale_geography(params, strength):
    out = deepcopy(params)
    for seat_type in out.get("geography_adjustments", {}):
        out["geography_adjustments"][seat_type] = {
            party: float(value or 0.0) * strength
            for party, value in out["geography_adjustments"][seat_type].items()
        }
    return out


def actual_result(row):
    shares = {
        party: row.get(f"{party}_2CP") for party in PARTIES
        if pd.notna(row.get(f"{party}_2CP"))
    }
    if len(shares) != 2:
        return None
    shares = {party: float(value) for party, value in shares.items()}
    final = sorted(shares, key=shares.get, reverse=True)
    return final[0], final[1], shares


def main():
    inputs = load_legacy_primary_inputs()
    matrices = load_synth_pref_matrices()
    params = load_params()
    params["scalar_params"]["SCENARIO_ON_PRIMARY"] = 0.0
    geography_variants = {
        strength: scale_geography(params, strength)
        for strength in [0.0, 0.25, 0.50, 0.75, 1.0]
    }
    posterior = load_posterior_scenarios()
    ideology = load_ideology_prior()
    on_alpha = float(params["scalar_params"].get("ON alpha", 0.6))
    primaries = build_corrected_primary_table(inputs, TARGETS_2022_NO_ON, on_alpha=on_alpha)
    primary_lookup = primaries.assign(key=primaries["district"].str.upper()).set_index("key")
    baseline = read_csv_raw("BASELINE_2CP.csv")
    baseline["key"] = baseline["district"].str.upper()
    baseline = baseline.set_index("key")
    rows = []

    for district, own in matrices.items():
        key = district.upper()
        if key not in baseline.index or key not in primary_lookup.index:
            continue
        actual = actual_result(baseline.loc[key])
        if actual is None:
            continue
        actual_winner, actual_runner, actual_shares = actual
        seat = primary_lookup.loc[key]
        votes = {party: float(seat[party]) for party in PARTIES}
        others = [value for name, value in matrices.items() if name != district]
        same_class = [
            value for name, value in matrices.items()
            if name != district and value["seat_type"] == own["seat_type"]
        ]
        variants = {
            "own_matrix": (own["matrix"], params),
            "loo_statewide": (mean_matrix(others), params),
            **{
                f"loo_seat_class_geo_{strength:.2f}": (
                    mean_matrix(same_class or others), variant_params
                )
                for strength, variant_params in geography_variants.items()
            },
        }
        for variant, (matrix, variant_params) in variants.items():
            result = run_irv_for_district(
                votes, matrix, seat["seat_type"], variant_params, posterior, ideology
            )
            actual_winner_share = actual_shares[actual_winner]
            predicted_actual_winner_share = (
                result["winner_pct"] if result["winner"] == actual_winner
                else result["runner_up_pct"] if result["runner_up"] == actual_winner
                else None
            )
            rows.append({
                "District": district, "SeatType": seat["seat_type"], "Variant": variant,
                "ActualWinner": actual_winner, "ActualRunnerUp": actual_runner,
                "ActualWinnerShare": actual_winner_share,
                "PredictedWinner": result["winner"], "PredictedRunnerUp": result["runner_up"],
                "PredictedWinnerShare": result["winner_pct"],
                "WinnerCorrect": result["winner"] == actual_winner,
                "FinalPairCorrect": {result["winner"], result["runner_up"]} == {actual_winner, actual_runner},
                "PredictedActualWinnerShare": predicted_actual_winner_share,
                "ActualWinnerShareError": (
                    predicted_actual_winner_share - actual_winner_share
                    if predicted_actual_winner_share is not None else None
                ),
            })

    detail = pd.DataFrame(rows)
    summary = detail.groupby("Variant", as_index=False).agg(
        Seats=("District", "size"), WinnerAccuracy=("WinnerCorrect", "mean"),
        FinalPairAccuracy=("FinalPairCorrect", "mean"),
        ComparableMargins=("ActualWinnerShareError", "count"),
        MeanError=("ActualWinnerShareError", "mean"),
        MeanAbsoluteError=("ActualWinnerShareError", lambda x: x.abs().mean()),
        RootMeanSquaredError=("ActualWinnerShareError", lambda x: (x.pow(2).mean()) ** 0.5),
    )
    by_class = detail.groupby(["Variant", "SeatType"], as_index=False).agg(
        Seats=("District", "size"), WinnerAccuracy=("WinnerCorrect", "mean"),
        FinalPairAccuracy=("FinalPairCorrect", "mean"),
        MeanError=("ActualWinnerShareError", "mean"),
        MeanAbsoluteError=("ActualWinnerShareError", lambda x: x.abs().mean()),
    )
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    detail.to_csv(REPORT_DIR / "leave_one_out_validation_detail.csv", index=False)
    summary.to_csv(REPORT_DIR / "leave_one_out_validation_summary.csv", index=False)
    by_class.to_csv(REPORT_DIR / "leave_one_out_validation_by_seat_class.csv", index=False)
    print(summary.to_string(index=False))
    print("\nSeat-class comparison:\n", by_class.to_string(index=False))


if __name__ == "__main__":
    main()
