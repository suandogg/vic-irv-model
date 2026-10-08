"""Separate scenario movement from pre-existing 2022 reconstruction error."""

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
SCENARIO = {"ALP": 29.0, "LNP": 32.0, "GRN": 12.0, "ON": 18.0, "IND": 4.5, "OTH": 4.5}
REPORT_DIR = ROOT / "reports"


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
    base_primaries = build_corrected_primary_table(inputs, BASELINE, on_alpha=on_alpha)
    scenario_primaries = build_corrected_primary_table(inputs, SCENARIO, on_alpha=on_alpha)
    base_lookup = base_primaries.assign(key=base_primaries["district"].str.upper()).set_index("key")
    scenario_lookup = scenario_primaries.assign(key=scenario_primaries["district"].str.upper()).set_index("key")
    baseline = read_csv_raw("BASELINE_2CP.csv")
    baseline["key"] = baseline["district"].str.upper()
    baseline = baseline.set_index("key")
    rows = []

    for district, matrix_obj in matrices.items():
        key = district.upper()
        base_seat, scenario_seat = base_lookup.loc[key], scenario_lookup.loc[key]
        held = base_seat["held_by"]
        actual_held = clean_baseline_value(baseline.loc[key].get(f"{held}_2CP"))
        actual_pair = [
            party for party in PARTIES
            if pd.notna(baseline.loc[key].get(f"{party}_2CP"))
        ]
        base_result = run_irv_for_district(
            {p: float(base_seat[p]) for p in PARTIES}, matrix_obj["matrix"],
            base_seat["seat_type"], params_for(params, BASELINE), posterior, ideology,
        )
        scenario_result = run_irv_for_district(
            {p: float(scenario_seat[p]) for p in PARTIES}, matrix_obj["matrix"],
            scenario_seat["seat_type"], params_for(params, SCENARIO), posterior, ideology,
        )
        model_base_held = party_share(base_result, held)
        scenario_held = party_share(scenario_result, held)
        residual = (
            model_base_held - actual_held
            if model_base_held is not None and actual_held is not None else None
        )
        displayed_swing = (
            scenario_held - actual_held
            if scenario_held is not None and actual_held is not None else None
        )
        scenario_only_change = (
            scenario_held - model_base_held
            if scenario_held is not None and model_base_held is not None else None
        )
        same_pair = (
            len(actual_pair) == 2
            and {scenario_result["winner"], scenario_result["runner_up"]} == set(actual_pair)
        )
        calibrated_held = (
            actual_held + scenario_only_change
            if same_pair and actual_held is not None and scenario_only_change is not None else None
        )
        calibrated_winner = None
        if calibrated_held is not None:
            calibrated_winner = held if calibrated_held >= 0.5 else next(
                party for party in actual_pair if party != held
            )
        rows.append({
            "District": district, "SeatType": base_seat["seat_type"], "HeldBy": held,
            "ActualBaselineHeldShare": actual_held,
            "ActualBaselinePair": "+".join(sorted(actual_pair)),
            "ModelBaselineWinner": base_result["winner"], "ModelBaselineRunnerUp": base_result["runner_up"],
            "ModelBaselineHeldShare": model_base_held,
            "BaselineReconstructionResidual": residual,
            "ScenarioWinner": scenario_result["winner"], "ScenarioRunnerUp": scenario_result["runner_up"],
            "ScenarioHeldShare": scenario_held,
            "DisplayedSwingFromActual": displayed_swing,
            "ScenarioChangeFromModelBaseline": scenario_only_change,
            "SameFinalPairAsBaseline": same_pair,
            "CalibratedHeldShare": calibrated_held,
            "CalibratedWinner": calibrated_winner,
            "CalibrationChangesWinner": (
                calibrated_winner != scenario_result["winner"]
                if calibrated_winner is not None else False
            ),
            "ResidualShareOfDisplayedSwing": (
                residual / displayed_swing if residual is not None and displayed_swing not in {None, 0} else None
            ),
        })

    detail = pd.DataFrame(rows)
    comparable = detail.dropna(subset=["BaselineReconstructionResidual"])
    summary = pd.DataFrame([{
        "ComparableSeats": len(comparable),
        "MeanResidual": comparable["BaselineReconstructionResidual"].mean(),
        "MeanAbsoluteResidual": comparable["BaselineReconstructionResidual"].abs().mean(),
        "MaximumAbsoluteResidual": comparable["BaselineReconstructionResidual"].abs().max(),
        "SeatsResidualOver2pp": int((comparable["BaselineReconstructionResidual"].abs() > 0.02).sum()),
        "SeatsResidualOver5pp": int((comparable["BaselineReconstructionResidual"].abs() > 0.05).sum()),
        "SamePairCalibrationSeats": int(detail["SameFinalPairAsBaseline"].sum()),
        "CalibrationWinnerChanges": int(detail["CalibrationChangesWinner"].sum()),
    }])
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    detail.to_csv(REPORT_DIR / "baseline_reconstruction_audit.csv", index=False)
    summary.to_csv(REPORT_DIR / "baseline_reconstruction_summary.csv", index=False)
    print(summary.to_string(index=False))
    print("\nLargest residuals:\n", comparable.reindex(comparable.BaselineReconstructionResidual.abs().sort_values(ascending=False).index).head(25).to_string(index=False))
    print("\nBass/Ashwood:\n", detail[detail.District.str.upper().isin(["BASS", "ASHWOOD"])].to_string(index=False))


if __name__ == "__main__":
    main()
