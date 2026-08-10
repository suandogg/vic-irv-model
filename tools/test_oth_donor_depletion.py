"""Development-only sensitivity test for depletion of OTH voters friendly to ON."""

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
from SRC.preference_engine import diagnose_preference_weights


BASELINE = {
    "ALP": 36.66, "LNP": 34.48, "GRN": 11.50,
    "ON": 0.28, "IND": 5.55, "OTH": 11.53,
}
ON_LEVELS = [10.0, 20.0, 24.4]
DEPLETION_STRENGTHS = [0.25, 0.50, 0.75, 1.00]
REFERENCE_ON_LEVEL = 24.4
REPORT_DIR = ROOT / "reports"


def targets_for_on(on_level: float) -> dict[str, float]:
    non_on_total = sum(BASELINE[p] for p in PARTIES if p != "ON")
    return {
        p: on_level if p == "ON" else BASELINE[p] * (100 - on_level) / non_on_total
        for p in PARTIES
    }


def siphon_retention(on_level: float, depletion_strength: float) -> float:
    progress = max(0.0, min(
        1.0,
        (on_level - BASELINE["ON"]) / (REFERENCE_ON_LEVEL - BASELINE["ON"]),
    ))
    return 1.0 - depletion_strength * progress


def trial_irv(district, votes, matrix, seat_type, params, posterior, ideology,
              on_level, depletion_strength):
    working = {p: float(votes.get(p, 0.0)) for p in PARTIES}
    alive = [p for p in PARTIES if working[p] > 0]
    activations = []
    retention = siphon_retention(on_level, depletion_strength)
    base_strength = float(params["scalar_params"].get("SIPHON_STRENGTH_ON", 0.25))

    while len(alive) > 2:
        eliminated = min(alive, key=lambda p: working[p])
        eliminated_votes = working[eliminated]
        alive = [p for p in alive if p != eliminated]
        use_params = params
        if eliminated == "OTH" and "ON" in alive:
            use_params = dict(params)
            use_params["scalar_params"] = dict(params["scalar_params"])
            use_params["scalar_params"]["SIPHON_STRENGTH_ON"] = base_strength * retention
        diagnostic = diagnose_preference_weights(
            eliminated, alive, matrix, seat_type, use_params, posterior, ideology
        )
        flow = diagnostic["final_flows"]
        if eliminated == "OTH" and "ON" in alive and diagnostic["basis"] != "federal ON evidence trial":
            current_diagnostic = diagnose_preference_weights(
                eliminated, alive, matrix, seat_type, params, posterior, ideology
            )
            current_on_flow = current_diagnostic["final_flows"].get("ON", 0.0)
            activations.append({
                "ONLevel": on_level,
                "DepletionStrength": depletion_strength,
                "District": district,
                "SeatType": seat_type,
                "AliveSet": "+".join(sorted(alive)),
                "Basis": diagnostic["basis"],
                "OTHVoteShareAtElimination": eliminated_votes,
                "SiphonRetention": retention,
                "EffectiveSiphonStrength": base_strength * retention,
                "CurrentOTHToONFlow": current_on_flow,
                "TrialOTHToONFlow": flow.get("ON", 0.0),
                "OTHToONFlowChange": flow.get("ON", 0.0) - current_on_flow,
            })
        working[eliminated] = 0.0
        for party, share in flow.items():
            working[party] += eliminated_votes * share

    final = sorted(alive, key=lambda p: working[p], reverse=True)
    total = working[final[0]] + working[final[1]]
    return {
        "winner": final[0], "runner_up": final[1],
        "matchup": f"{final[0]}-{final[1]}",
        "winner_pct": working[final[0]] / total if total else 0.0,
    }, activations


def main() -> None:
    inputs = load_legacy_primary_inputs()
    matrices = load_synth_pref_matrices()
    params = load_params()
    posterior = apply_production_federal_on_evidence(load_posterior_scenarios())
    ideology = load_ideology_prior()
    on_alpha = float(params["scalar_params"].get("ON alpha", 0.6))
    rows, activation_rows = [], []

    for level in ON_LEVELS:
        wide = build_corrected_primary_table(inputs, targets_for_on(level), on_alpha=on_alpha)
        lookup = wide.assign(district_key=wide["district"].str.strip().str.upper()).set_index("district_key")
        for district, matrix_obj in matrices.items():
            seat = lookup.loc[str(district).strip().upper()]
            votes = {p: float(seat[p]) for p in PARTIES}
            current = run_irv_for_district(
                votes, matrix_obj["matrix"], seat["seat_type"], params, posterior, ideology
            )
            for strength in DEPLETION_STRENGTHS:
                trial, activations = trial_irv(
                    district, votes, matrix_obj["matrix"], seat["seat_type"], params,
                    posterior, ideology, level, strength,
                )
                rows.append({
                    "ONLevel": level, "DepletionStrength": strength,
                    "SiphonRetention": siphon_retention(level, strength),
                    "District": district, "SeatType": seat["seat_type"],
                    "CurrentWinner": current["winner"], "CurrentRunnerUp": current["runner_up"],
                    "CurrentWinnerPct": current["winner_pct"],
                    "TrialWinner": trial["winner"], "TrialRunnerUp": trial["runner_up"],
                    "TrialWinnerPct": trial["winner_pct"],
                    "WinnerChanged": current["winner"] != trial["winner"],
                    "PairChanged": current["matchup"] != trial["matchup"],
                    "WinnerPctChange": trial["winner_pct"] - current["winner_pct"],
                    "TrialActivated": bool(activations),
                })
                activation_rows.extend(activations)

    outcomes = pd.DataFrame(rows)
    activations = pd.DataFrame(activation_rows)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    outcomes.to_csv(REPORT_DIR / "oth_donor_depletion_all_seats.csv", index=False)
    outcomes[outcomes["WinnerChanged"] | outcomes["PairChanged"]].to_csv(
        REPORT_DIR / "oth_donor_depletion_changed_seats.csv", index=False
    )
    activations.to_csv(REPORT_DIR / "oth_donor_depletion_activations.csv", index=False)
    summary = outcomes.groupby(["ONLevel", "DepletionStrength", "SiphonRetention"], as_index=False).agg(
        ActivatedSeats=("TrialActivated", "sum"),
        WinnerChanges=("WinnerChanged", "sum"), PairChanges=("PairChanged", "sum"),
        MeanAbsoluteWinnerPctChange=("WinnerPctChange", lambda x: x.abs().mean()),
        MaximumAbsoluteWinnerPctChange=("WinnerPctChange", lambda x: x.abs().max()),
    )
    summary.to_csv(REPORT_DIR / "oth_donor_depletion_summary.csv", index=False)
    flow_summary = activations.groupby(
        ["ONLevel", "DepletionStrength", "SiphonRetention"], as_index=False
    ).agg(
        ActivatedRounds=("District", "size"),
        MeanCurrentOTHToONFlow=("CurrentOTHToONFlow", "mean"),
        MeanTrialOTHToONFlow=("TrialOTHToONFlow", "mean"),
        MeanOTHToONFlowChange=("OTHToONFlowChange", "mean"),
    )
    flow_summary.to_csv(REPORT_DIR / "oth_donor_depletion_flow_summary.csv", index=False)
    print(summary.to_string(index=False))
    print(flow_summary.to_string(index=False))


if __name__ == "__main__":
    main()
