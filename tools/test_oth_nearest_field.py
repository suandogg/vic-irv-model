"""Test tightly constrained OTH nearest-field projections.

Only Victorian-federal OTH evidence is used. A projection is permitted only
when the target continuing field can be obtained by removing exactly one
party from an observed field. The projected evidence receives an additional
50% reliability penalty and is blended toward the current Victorian rule
with generic ON siphoning disabled for that round.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from SRC.constants import PARTIES
from SRC.federal_on_evidence_loader import (
    apply_production_federal_on_evidence,
    conservative_reliability,
    load_federal_on_config,
    load_federal_on_evidence,
)
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
PROJECTION_RELIABILITY_MULTIPLIER = 0.5
MAXIMUM_PROJECTED_WEIGHT = 0.25
REPORT_DIR = ROOT / "reports"


def targets_for_on(on_level: float) -> dict[str, float]:
    non_on_total = sum(BASELINE[p] for p in PARTIES if p != "ON")
    return {
        p: on_level if p == "ON" else BASELINE[p] * (100 - on_level) / non_on_total
        for p in PARTIES
    }


def oth_parent_scenarios() -> dict[str, dict]:
    return {
        key.split("|", 1)[1]: value
        for key, value in load_federal_on_evidence().items()
        if key.startswith("OTH|")
    }


def find_one_removal_parent(
    target_alive: list[str],
    parents: dict[str, dict],
) -> tuple[str, dict, str] | None:
    target = set(target_alive)
    candidates = []
    for parent_key, scenario in parents.items():
        parent = set(parent_key.split("+"))
        removed = parent - target
        if target.issubset(parent) and len(removed) == 1:
            candidates.append((parent_key, scenario, next(iter(removed))))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[1]["seats"])


def projected_oth_flow(
    district: str,
    alive: list[str],
    matrix: dict,
    seat_type: str,
    params: dict,
    posterior: dict,
    ideology: dict,
    parents: dict[str, dict],
    config: dict,
) -> tuple[dict[str, float], dict | None]:
    current_diag = diagnose_preference_weights(
        "OTH", alive, matrix, seat_type, params, posterior, ideology
    )
    current = current_diag["final_flows"]
    if current_diag["basis"] in {"federal ON evidence trial", "ON special prior"}:
        return current, None

    parent = find_one_removal_parent(alive, parents)
    if parent is None:
        return current, None
    parent_key, evidence, removed_party = parent

    projected = {
        party: evidence["shares"].get(party, 0.0)
        for party in alive
    }
    projected_total = sum(projected.values())
    if projected_total <= 0:
        return current, None
    projected = {
        party: value / projected_total for party, value in projected.items()
    }

    no_siphon_params = dict(params)
    no_siphon_params["scalar_params"] = dict(params.get("scalar_params", {}))
    no_siphon_params["scalar_params"]["SIPHON_STRENGTH_ON"] = 0.0
    no_siphon_diag = diagnose_preference_weights(
        "OTH", alive, matrix, seat_type, no_siphon_params,
        posterior, ideology,
    )
    no_siphon = no_siphon_diag["final_flows"]
    weight = min(
        MAXIMUM_PROJECTED_WEIGHT,
        conservative_reliability(evidence, config=config)
        * PROJECTION_RELIABILITY_MULTIPLIER,
    )
    trial = {
        party: (1 - weight) * no_siphon.get(party, 0.0)
        + weight * projected.get(party, 0.0)
        for party in alive
    }
    total = sum(trial.values())
    trial = {party: value / total for party, value in trial.items()}
    metadata = {
        "District": district,
        "Eliminated": "OTH",
        "AliveSet": "+".join(sorted(alive)),
        "CurrentBasis": current_diag["basis"],
        "ParentAliveSet": parent_key,
        "RemovedParty": removed_party,
        "FederalSeats": evidence["seats"],
        "FederalScenarioTotal": evidence["scenario_total"],
        "ProjectionWeight": weight,
        "CurrentONFlow": current.get("ON", 0.0),
        "NoSiphonONFlow": no_siphon.get("ON", 0.0),
        "ProjectedONFlow": projected.get("ON", 0.0),
        "TrialONFlow": trial.get("ON", 0.0),
        "ONFlowChangeFromCurrent": trial.get("ON", 0.0) - current.get("ON", 0.0),
    }
    return trial, metadata


def run_trial_for_district(
    district: str,
    votes: dict[str, float],
    matrix: dict,
    seat_type: str,
    params: dict,
    posterior: dict,
    ideology: dict,
    parents: dict[str, dict],
    config: dict,
) -> tuple[dict, list[dict]]:
    working = {p: float(votes.get(p, 0.0)) for p in PARTIES}
    alive = [p for p in PARTIES if working[p] > 0]
    order = []
    activations = []
    while len(alive) > 2:
        eliminated = min(alive, key=lambda p: working[p])
        eliminated_votes = working[eliminated]
        alive = [p for p in alive if p != eliminated]
        if eliminated == "OTH" and "ON" in alive:
            flow, metadata = projected_oth_flow(
                district, alive, matrix, seat_type, params, posterior,
                ideology, parents, config,
            )
        else:
            diagnostic = diagnose_preference_weights(
                eliminated, alive, matrix, seat_type, params,
                posterior, ideology,
            )
            flow, metadata = diagnostic["final_flows"], None
        if metadata:
            metadata["EliminatedVoteShare"] = eliminated_votes
            activations.append(metadata)
        working[eliminated] = 0.0
        for party, share in flow.items():
            working[party] += eliminated_votes * share
        order.append(eliminated)
    final = sorted(alive, key=lambda p: working[p], reverse=True)
    total = working[final[0]] + working[final[1]]
    return {
        "winner": final[0],
        "runner_up": final[1],
        "winner_pct": working[final[0]] / total if total else 0.0,
        "matchup": f"{final[0]}-{final[1]}",
        "elimination_order": ">".join(order),
    }, activations


def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    inputs = load_legacy_primary_inputs()
    matrices = load_synth_pref_matrices()
    params = load_params()
    posterior = apply_production_federal_on_evidence(load_posterior_scenarios())
    ideology = load_ideology_prior()
    parents = oth_parent_scenarios()
    config = load_federal_on_config()
    on_alpha = float(params["scalar_params"].get("ON alpha", 0.6))
    outcomes = []
    activations = []

    for level in ON_LEVELS:
        wide = build_corrected_primary_table(
            inputs, targets_for_on(level), on_alpha=on_alpha
        )
        lookup = wide.assign(
            district_key=wide["district"].astype(str).str.strip().str.upper()
        ).set_index("district_key")
        for district, matrix_obj in matrices.items():
            seat = lookup.loc[str(district).strip().upper()]
            votes = {p: float(seat[p]) for p in PARTIES}
            current = run_irv_for_district(
                votes, matrix_obj["matrix"], seat["seat_type"],
                params, posterior, ideology,
            )
            trial, used = run_trial_for_district(
                district, votes, matrix_obj["matrix"], seat["seat_type"],
                params, posterior, ideology, parents, config,
            )
            outcomes.append({
                "ONLevel": level,
                "District": district,
                "SeatType": seat["seat_type"],
                "CurrentWinner": current["winner"],
                "CurrentRunnerUp": current["runner_up"],
                "CurrentWinnerPct": current["winner_pct"],
                "TrialWinner": trial["winner"],
                "TrialRunnerUp": trial["runner_up"],
                "TrialWinnerPct": trial["winner_pct"],
                "WinnerChanged": current["winner"] != trial["winner"],
                "PairChanged": current["matchup"] != trial["matchup"],
                "WinnerPctChange": trial["winner_pct"] - current["winner_pct"],
                "TrialActivated": bool(used),
            })
            for row in used:
                activations.append({"ONLevel": level, **row})
    return pd.DataFrame(outcomes), pd.DataFrame(activations)


def main() -> None:
    outcomes, activations = run()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    outcomes.to_csv(REPORT_DIR / "oth_nearest_field_all_seats.csv", index=False)
    outcomes[
        outcomes["WinnerChanged"] | outcomes["PairChanged"]
    ].to_csv(REPORT_DIR / "oth_nearest_field_changed_seats.csv", index=False)
    activations.to_csv(REPORT_DIR / "oth_nearest_field_activations.csv", index=False)
    summary = outcomes.groupby("ONLevel", as_index=False).agg(
        ActivatedSeats=("TrialActivated", "sum"),
        WinnerChanges=("WinnerChanged", "sum"),
        PairChanges=("PairChanged", "sum"),
        MeanAbsoluteWinnerPctChange=("WinnerPctChange", lambda x: x.abs().mean()),
        MaximumAbsoluteWinnerPctChange=("WinnerPctChange", lambda x: x.abs().max()),
    )
    summary.to_csv(REPORT_DIR / "oth_nearest_field_summary.csv", index=False)
    evidence = load_federal_on_evidence()
    parent = evidence["OTH|ALP+GRN+IND+LNP+ON"]["shares"]
    actual = evidence["OTH|ALP+GRN+LNP+ON"]["shares"]
    projected = {p: value for p, value in parent.items() if p != "IND"}
    projected_total = sum(projected.values())
    projected = {p: value / projected_total for p, value in projected.items()}
    total_variation = 0.5 * sum(
        abs(projected[p] - actual[p]) for p in actual
    )
    validation = pd.DataFrame([
        {
            "ParentAliveSet": "ALP+GRN+IND+LNP+ON",
            "RemovedParty": "IND",
            "TargetAliveSet": "ALP+GRN+LNP+ON",
            "Recipient": party,
            "ProjectedShare": projected[party],
            "ObservedShare": actual[party],
            "Error": projected[party] - actual[party],
            "AbsoluteError": abs(projected[party] - actual[party]),
            "TotalVariationDistance": total_variation,
            "ParentSeats": evidence["OTH|ALP+GRN+IND+LNP+ON"]["seats"],
            "TargetSeats": evidence["OTH|ALP+GRN+LNP+ON"]["seats"],
        }
        for party in actual
    ])
    validation.to_csv(
        REPORT_DIR / "oth_nearest_field_validation.csv", index=False
    )
    print(summary.to_string(index=False))
    print(f"Validation total variation distance: {total_variation:.3%}")


if __name__ == "__main__":
    main()
