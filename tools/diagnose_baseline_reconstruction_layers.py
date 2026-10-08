"""Attribute 2022 baseline reconstruction error to model layers."""

from __future__ import annotations

from copy import deepcopy
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
from SRC.lnp_precollapse_loader import apply_lnp_precollapse
from SRC.matrix_loader import load_synth_pref_matrices
from SRC.params_loader import load_params
from SRC.posterior_loader import load_posterior_scenarios


BASELINE = {"ALP": 36.66, "LNP": 34.48, "GRN": 11.50, "ON": 0.28, "IND": 5.55, "OTH": 11.53}
REPORT_DIR = ROOT / "reports"


def variant_params(params, geography=True, siphon=True):
    out = deepcopy(params)
    out["scalar_params"]["SCENARIO_ON_PRIMARY"] = BASELINE["ON"]
    if not geography:
        for seat_class in out["geography_adjustments"]:
            out["geography_adjustments"][seat_class] = {party: 0.0 for party in PARTIES}
    if not siphon:
        out["scalar_params"]["SIPHON_STRENGTH_ON"] = 0.0
    return out


def held_share(result, held):
    if result["winner"] == held:
        return result["winner_pct"]
    if result["runner_up"] == held:
        return result["runner_up_pct"]
    return None


def raw_matrix_irv(votes, matrix):
    working = dict(votes)
    alive = [party for party in PARTIES if working[party] > 0]
    while len(alive) > 2:
        eliminated = min(alive, key=lambda party: working[party])
        parcel = working[eliminated]
        alive = [party for party in alive if party != eliminated]
        raw = {party: float(matrix.get(eliminated, {}).get(party, 0.0) or 0.0) for party in alive}
        total = sum(raw.values())
        flows = ({party: value / total for party, value in raw.items()} if total > 0
                 else {party: 1 / len(alive) for party in alive})
        working[eliminated] = 0.0
        for party, flow in flows.items():
            working[party] += parcel * flow
    final = sorted(alive, key=lambda party: working[party], reverse=True)
    total = working[final[0]] + working[final[1]]
    return {"winner": final[0], "runner_up": final[1],
            "winner_pct": working[final[0]] / total, "runner_up_pct": working[final[1]] / total}


def main():
    inputs = apply_seat_held_metadata(load_legacy_primary_inputs(), load_seat_held_metadata())
    matrices = load_synth_pref_matrices()
    params = load_params()
    posterior = apply_production_federal_on_evidence(load_posterior_scenarios())
    ideology = load_ideology_prior()
    primaries = apply_lnp_precollapse(
        build_corrected_primary_table(
            inputs,
            BASELINE,
            on_alpha=float(params["scalar_params"].get("ON alpha", 0.6)),
        )
    )
    lookup = primaries.assign(key=primaries["district"].str.upper()).set_index("key")
    baseline = read_csv_raw("BASELINE_2CP.csv")
    baseline["key"] = baseline["district"].str.upper()
    baseline = baseline.set_index("key")
    rows = []
    for district, matrix_obj in matrices.items():
        seat = lookup.loc[district.upper()]
        held = seat["held_by"]
        actual = clean_baseline_value(baseline.loc[district.upper()].get(f"{held}_2CP"))
        votes = {party: float(seat[party]) for party in PARTIES}
        variants = {
            "current": run_irv_for_district(votes, matrix_obj["matrix"], seat["seat_type"], variant_params(params), posterior, ideology),
            "no_geography": run_irv_for_district(votes, matrix_obj["matrix"], seat["seat_type"], variant_params(params, geography=False), posterior, ideology),
            "no_geography_or_siphon": run_irv_for_district(votes, matrix_obj["matrix"], seat["seat_type"], variant_params(params, geography=False, siphon=False), posterior, ideology),
            "no_posterior_no_geography": run_irv_for_district(votes, matrix_obj["matrix"], seat["seat_type"], variant_params(params, geography=False), {}, ideology),
            "raw_matrix": raw_matrix_irv(votes, matrix_obj["matrix"]),
        }
        for name, result in variants.items():
            predicted = held_share(result, held)
            rows.append({
                "District": district, "SeatType": seat["seat_type"], "HeldBy": held,
                "Variant": name, "ActualHeldShare": actual,
                "PredictedWinner": result["winner"], "PredictedRunnerUp": result["runner_up"],
                "PredictedHeldShare": predicted,
                "Residual": predicted - actual if predicted is not None and actual is not None else None,
            })
    detail = pd.DataFrame(rows)
    summary = detail.groupby("Variant", as_index=False).agg(
        ComparableSeats=("Residual", "count"), MeanResidual=("Residual", "mean"),
        MeanAbsoluteResidual=("Residual", lambda x: x.abs().mean()),
        MaximumAbsoluteResidual=("Residual", lambda x: x.abs().max()),
        ResidualsOver2pp=("Residual", lambda x: (x.abs() > 0.02).sum()),
        ResidualsOver5pp=("Residual", lambda x: (x.abs() > 0.05).sum()),
    )
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    detail.to_csv(REPORT_DIR / "baseline_reconstruction_layers_detail.csv", index=False)
    summary.to_csv(REPORT_DIR / "baseline_reconstruction_layers_summary.csv", index=False)
    print(summary.to_string(index=False))
    print("\nBass/Ashwood:\n", detail[detail.District.str.upper().isin(["BASS", "ASHWOOD"])].to_string(index=False))


if __name__ == "__main__":
    main()
