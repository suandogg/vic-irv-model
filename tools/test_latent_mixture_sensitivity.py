from __future__ import annotations

import pandas as pd

from compare_latent_ranking_shadow import (
    SCENARIOS,
    build_primaries,
    historical_metrics,
    seat_counts,
)
from SRC.baseline_loader import load_baseline_2cp
from SRC.federal_on_evidence_loader import apply_production_federal_on_evidence
from SRC.ideology_loader import load_ideology_prior
from SRC.latent_ranking import run_latent_ranking_all
from SRC.legacy_primary_loader import load_legacy_primary_inputs
from SRC.loaders import apply_seat_held_metadata, load_seat_held_metadata
from SRC.matrix_loader import load_synth_pref_matrices
from SRC.params_loader import load_params
from SRC.posterior_loader import load_posterior_scenarios
from SRC.seat_adjustments_loader import load_lower_seat_adjustments
from SRC.turnout_loader import (
    attach_turnout_weights,
    load_lower_turnout_weights,
    turnout_weighted_share,
)


def main():
    primary_inputs = apply_seat_held_metadata(
        load_legacy_primary_inputs(), load_seat_held_metadata()
    )
    matrices = load_synth_pref_matrices()
    params = load_params()
    posterior = apply_production_federal_on_evidence(load_posterior_scenarios())
    ideology = load_ideology_prior()
    turnout = load_lower_turnout_weights()
    baseline = load_baseline_2cp()
    adjustments = load_lower_seat_adjustments()
    rows = []
    for scenario, targets in SCENARIOS.items():
        primaries, scenario_params = build_primaries(
            primary_inputs,
            params,
            targets,
            adjustments if scenario == "Demos" else None,
        )
        for strength in [0.5, 1.0, 1.5]:
            for regularization in [0.01, 0.05, 0.15]:
                raw, fits = run_latent_ranking_all(
                    primaries,
                    matrices,
                    scenario_params,
                    posterior,
                    ideology,
                    mixture=True,
                    type_strength=strength,
                    regularization=regularization,
                )
                frame = attach_turnout_weights(pd.DataFrame(raw), turnout)
                row = {
                    "scenario": scenario,
                    "type_strength": strength,
                    "regularization": regularization,
                    "alp_2pp_weighted": turnout_weighted_share(frame, "ALP_2PP") * 100,
                    **seat_counts(frame),
                    "fit_rmse_pp": pd.DataFrame(fits)["pairwise_rmse"].mean() * 100,
                }
                if scenario == "2022 reconstruction":
                    row.update(historical_metrics(frame, baseline))
                rows.append(row)
    result = pd.DataFrame(rows)
    output = ROOT / "reports" / "latent_mixture_sensitivity.csv"
    result.to_csv(output, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[1]
    main()
