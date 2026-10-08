from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from SRC.baseline_loader import load_baseline_2cp
from SRC.federal_on_evidence_loader import apply_production_federal_on_evidence
from SRC.ideology_loader import load_ideology_prior
from SRC.irv import run_irv_all
from SRC.latent_ranking import run_latent_ranking_all
from SRC.legacy_primary_loader import load_legacy_primary_inputs
from SRC.legacy_primary_model import (
    apply_seat_primary_adjustments,
    apply_on_primary_donor_geography,
    build_corrected_primary_table,
    deplete_on_primary_source_matrix,
)
from SRC.lnp_precollapse_loader import apply_lnp_precollapse
from SRC.loaders import apply_seat_held_metadata, load_seat_held_metadata
from SRC.matrix_loader import load_synth_pref_matrices
from SRC.params_loader import load_params
from SRC.posterior_loader import load_posterior_scenarios
from SRC.transform import build_primary_vote_table
from SRC.seat_adjustments_loader import load_lower_seat_adjustments
from SRC.turnout_loader import (
    attach_turnout_weights,
    load_lower_turnout_weights,
    turnout_weighted_share,
)


SCENARIOS = {
    "Demos": {"ALP": 25, "LNP": 30, "GRN": 14, "ON": 20, "IND": 5.5, "OTH": 5.5},
    "2022 reconstruction": {
        "ALP": 36.66, "LNP": 34.48, "GRN": 11.50,
        "ON": 0.28, "IND": 5.55, "OTH": 11.53,
    },
}


def build_primaries(primary_inputs, params, targets, seat_adjustments=None):
    scenario_params = copy.deepcopy(params)
    scenario_params["scalar_params"]["SCENARIO_ON_PRIMARY"] = targets["ON"]
    on_alpha = float(scenario_params["scalar_params"].get("ON alpha", 0.6) or 0.6)
    grn_persistence = float(
        scenario_params["scalar_params"].get("GRN_PVI_PERSISTENCE", 1.0) or 1.0
    )
    adjusted = build_corrected_primary_table(
        primary_inputs, targets, on_alpha, {"GRN": grn_persistence}
    )
    source_matrix = scenario_params.get("on_vote_source_matrix", {})
    depletion = float(
        scenario_params["scalar_params"].get(
            "ON_PRIMARY_OTH_DEPLETION_STRENGTH", 0.0
        ) or 0.0
    )
    if depletion > 0:
        source_matrix = deplete_on_primary_source_matrix(
            source_matrix,
            on_level=targets["ON"],
            max_depletion=depletion,
            start_level=float(scenario_params["scalar_params"].get(
                "ON_PRIMARY_OTH_DEPLETION_START", 10.0
            )),
            full_level=float(scenario_params["scalar_params"].get(
                "ON_PRIMARY_OTH_DEPLETION_FULL", 30.0
            )),
        )
    adjusted = apply_on_primary_donor_geography(
        primary_inputs=primary_inputs,
        current=adjusted,
        targets=targets,
        source_matrix=source_matrix,
        strength=float(scenario_params["scalar_params"].get(
            "ON_PRIMARY_DONOR_STRENGTH", 0.0
        ) or 0.0),
        on_alpha=on_alpha,
    )
    if seat_adjustments is not None:
        adjusted, _ = apply_seat_primary_adjustments(
            current=adjusted,
            adjustments=seat_adjustments,
            targets=targets,
            retirement_penalty_pp=float(scenario_params["scalar_params"].get(
                "RETIRING_INCUMBENT_PENALTY_PP", 1.0
            )),
            sophomore_bonus_pp=float(scenario_params["scalar_params"].get(
                "SOPHOMORE_SURGE_BONUS_PP", 1.0
            )),
        )
    return build_primary_vote_table(apply_lnp_precollapse(adjusted)), scenario_params


def seat_counts(frame):
    counts = frame["winner"].value_counts()
    return {party: int(counts.get(party, 0)) for party in ["ALP", "LNP", "GRN", "ON", "IND", "OTH"]}


def historical_metrics(frame, baseline):
    joined = frame.merge(baseline, on="district", how="left")
    valid = joined["ALP_2CP"].notna() & joined["LNP_2CP"].notna()
    observed = joined.loc[valid, "ALP_2CP"].astype(float)
    predicted = joined.loc[valid, "ALP_2PP"].astype(float)
    errors = predicted - observed
    observed_winner = observed.ge(0.5).map({True: "ALP", False: "LNP"})
    predicted_winner = predicted.ge(0.5).map({True: "ALP", False: "LNP"})
    return {
        "historical_seats": int(valid.sum()),
        "mae_pp": float(errors.abs().mean() * 100),
        "rmse_pp": float((errors.pow(2).mean() ** 0.5) * 100),
        "winner_accuracy_pct": float((observed_winner == predicted_winner).mean() * 100),
    }


def main():
    primary_inputs = apply_seat_held_metadata(
        load_legacy_primary_inputs(), load_seat_held_metadata()
    )
    matrices = load_synth_pref_matrices()
    params = load_params()
    posterior = apply_production_federal_on_evidence(load_posterior_scenarios())
    ideology = load_ideology_prior()
    weights = load_lower_turnout_weights()
    baseline = load_baseline_2cp()
    seat_adjustments = load_lower_seat_adjustments()
    summary_rows, changed_rows, fit_rows = [], [], []

    for scenario_name, targets in SCENARIOS.items():
        primary_votes, scenario_params = build_primaries(
            primary_inputs,
            params,
            targets,
            seat_adjustments if scenario_name == "Demos" else None,
        )
        parcel_params = copy.deepcopy(scenario_params)
        parcel_params["scalar_params"]["PARCEL_ORIGIN_RETENTION"] = 0.75
        parcel = attach_turnout_weights(
            pd.DataFrame(run_irv_all(
                primary_votes, matrices, parcel_params, posterior, ideology
            )), weights
        )
        latent_raw, single_fits = run_latent_ranking_all(
            primary_votes, matrices, scenario_params, posterior, ideology
        )
        latent = attach_turnout_weights(pd.DataFrame(latent_raw), weights)
        mixture_raw, mixture_fits = run_latent_ranking_all(
            primary_votes,
            matrices,
            scenario_params,
            posterior,
            ideology,
            mixture=True,
        )
        mixture = attach_turnout_weights(pd.DataFrame(mixture_raw), weights)

        engines = [
            ("parcel_75", parcel),
            ("latent_single", latent),
            ("latent_mixture_5type", mixture),
        ]
        for engine_name, frame in engines:
            row = {
                "scenario": scenario_name,
                "engine": engine_name,
                "alp_2pp_weighted": turnout_weighted_share(frame, "ALP_2PP") * 100,
                "alp_2pp_unweighted": float(frame["ALP_2PP"].mean() * 100),
                **seat_counts(frame),
            }
            if scenario_name == "2022 reconstruction":
                row.update(historical_metrics(frame, baseline))
            summary_rows.append(row)

        for engine_name, frame in engines[1:]:
            compared = parcel[["district", "winner", "ALP_2PP"]].merge(
                frame[["district", "winner", "ALP_2PP"]],
                on="district",
                suffixes=("_parcel75", "_shadow"),
            )
            compared["scenario"] = scenario_name
            compared["shadow_engine"] = engine_name
            compared["alp_2pp_change_pp"] = (
                compared["ALP_2PP_shadow"] - compared["ALP_2PP_parcel75"]
            ) * 100
            changed_rows.extend(
                compared.loc[
                    compared["winner_parcel75"] != compared["winner_shadow"]
                ].to_dict("records")
            )
        for engine_name, fits in [
            ("latent_single", single_fits),
            ("latent_mixture_5type", mixture_fits),
        ]:
            for fit in fits:
                fit_rows.append({
                    "scenario": scenario_name,
                    "engine": engine_name,
                    **fit,
                })

    report_dir = ROOT / "reports"
    report_dir.mkdir(exist_ok=True)
    summary = pd.DataFrame(summary_rows)
    changed = pd.DataFrame(changed_rows)
    fit_frame = pd.DataFrame(fit_rows)
    if not fit_frame.empty:
        fit_frame["basis_counts"] = fit_frame["basis_counts"].map(json.dumps)
        fit_frame["mixture_weights"] = fit_frame["mixture_weights"].map(
            lambda value: json.dumps(value) if isinstance(value, dict) else ""
        )
    summary.to_csv(report_dir / "latent_ranking_shadow_summary.csv", index=False)
    changed.to_csv(report_dir / "latent_ranking_shadow_changed_seats.csv", index=False)
    fit_frame.to_csv(report_dir / "latent_ranking_shadow_pairwise_fit.csv", index=False)
    print(summary.to_string(index=False))
    print(f"\nChanged winners: {len(changed)}")
    if len(changed):
        print(changed.to_string(index=False))
    print("\nPairwise fit:")
    print(fit_frame.groupby(["scenario", "engine"])[["pairwise_rmse", "max_pairwise_error"]].agg(["mean", "max"]))


if __name__ == "__main__":
    main()
