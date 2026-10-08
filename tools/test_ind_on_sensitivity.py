"""Test unsupported IND-to-ON preference assumptions without changing production.

Victorian federal IND evidence contains no eliminations with ON continuing.
This tool therefore labels the ON share as an assumption, uses Victorian-only
federal evidence solely for the residual ALP/LNP/GRN split, and shrinks the
constructed vector 75% toward the complete current Victorian flow.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FEDERAL_FLOWS = Path(
    "/Users/callumrees/Desktop/federal_irv_model/data/raw/"
    "CATEGORY_PREF_FLOWS_LONG.csv"
)
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
ASSUMED_IND_TO_ON = [0.0, 0.05, 0.10, 0.15]
MAXIMUM_TRIAL_WEIGHT = 0.25
PRIOR_EQUIVALENT_SEATS = 20.0
VARIANCE_PENALTY = 10.0
REPORT_DIR = ROOT / "reports"


def targets_for_on(on_level: float) -> dict[str, float]:
    non_on_total = sum(BASELINE[p] for p in PARTIES if p != "ON")
    return {
        p: on_level if p == "ON" else BASELINE[p] * (100 - on_level) / non_on_total
        for p in PARTIES
    }


def load_victorian_ind_pools() -> dict[str, dict]:
    flows = pd.read_csv(FEDERAL_FLOWS)
    flows = flows[
        flows["State"].eq("VIC") & flows["Eliminated"].eq("IND")
    ].copy()
    pools = {}
    for alive, group in flows.groupby("AliveSet"):
        by_seat = group.pivot_table(
            index="Seat", columns="Recipient", values="Share", fill_value=0.0
        )
        shares = by_seat.mean().to_dict()
        total = sum(shares.values())
        pools[alive] = {
            "shares": {p: value / total for p, value in shares.items()},
            "seats": int(len(by_seat)),
            "scenario_total": float(
                group.groupby("Seat")["ScenarioTotal"].first().sum()
            ),
            "mean_variance": float(by_seat.var(ddof=1).fillna(0.0).mean()),
        }
    return pools


def choose_pool(alive: list[str], pools: dict[str, dict]) -> tuple[str, dict]:
    alive_set = set(alive) - {"ON"}
    eligible = []
    for key, value in pools.items():
        observed = set(key.split("+"))
        overlap = observed & alive_set
        if len(overlap) >= 2:
            eligible.append((key, value, len(overlap), len(observed - alive_set)))
    if not eligible:
        raise ValueError(f"No Victorian IND residual pool for {sorted(alive_set)}")
    selected = max(
        eligible,
        key=lambda item: (item[2], -item[3], item[1]["seats"]),
    )
    return selected[0], selected[1]


def sensitivity_flow(
    district: str,
    eliminated: str,
    alive: list[str],
    matrix: dict,
    seat_type: str,
    params: dict,
    posterior: dict,
    ideology: dict,
    pools: dict[str, dict],
    assumed_on: float,
) -> tuple[dict[str, float], dict | None]:
    diagnostic = diagnose_preference_weights(
        eliminated, alive, matrix, seat_type, params, posterior, ideology
    )
    current = diagnostic["final_flows"]
    if eliminated != "IND" or "ON" not in alive:
        return current, None

    try:
        pool_key, pool = choose_pool(alive, pools)
    except ValueError:
        return current, None
    supported = [p for p in pool["shares"] if p in alive]
    unsupported = [p for p in alive if p not in supported and p != "ON"]
    non_on_current = max(1e-12, 1.0 - current.get("ON", 0.0))
    residual = 1.0 - assumed_on
    unsupported_shares = {
        p: residual * current.get(p, 0.0) / non_on_current
        for p in unsupported
    }
    supported_mass = max(0.0, residual - sum(unsupported_shares.values()))
    pool_total = sum(pool["shares"][p] for p in supported)
    constructed = {p: 0.0 for p in alive}
    constructed["ON"] = assumed_on
    for p in unsupported:
        constructed[p] = unsupported_shares[p]
    for p in supported:
        constructed[p] = supported_mass * pool["shares"][p] / pool_total

    sample_weight = pool["seats"] / (
        pool["seats"] + PRIOR_EQUIVALENT_SEATS
    )
    heterogeneity_weight = 1.0 / (
        1.0 + VARIANCE_PENALTY * pool["mean_variance"]
    )
    trial_weight = min(
        MAXIMUM_TRIAL_WEIGHT, sample_weight * heterogeneity_weight
    )
    trial = {
        p: (1 - trial_weight) * current.get(p, 0.0)
        + trial_weight * constructed.get(p, 0.0)
        for p in alive
    }
    total = sum(trial.values())
    trial = {p: value / total for p, value in trial.items()}
    metadata = {
        "District": district,
        "Eliminated": eliminated,
        "AliveSet": "+".join(sorted(alive)),
        "CurrentBasis": diagnostic["basis"],
        "FederalResidualPool": pool_key,
        "FederalSeats": pool["seats"],
        "FederalScenarioTotal": pool["scenario_total"],
        "AssumedINDtoON": assumed_on,
        "TrialWeight": trial_weight,
        "CurrentONFlow": current.get("ON", 0.0),
        "ConstructedONFlow": constructed.get("ON", 0.0),
        "TrialONFlow": trial.get("ON", 0.0),
        "ONFlowChange": trial.get("ON", 0.0) - current.get("ON", 0.0),
        "UnsupportedRecipientsPreserved": "+".join(sorted(unsupported)),
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
    pools: dict[str, dict],
    assumed_on: float,
) -> tuple[dict, list[dict]]:
    working = {p: float(votes.get(p, 0.0)) for p in PARTIES}
    alive = [p for p in PARTIES if working[p] > 0]
    order = []
    activations = []
    while len(alive) > 2:
        eliminated = min(alive, key=lambda p: working[p])
        eliminated_votes = working[eliminated]
        alive = [p for p in alive if p != eliminated]
        flow, metadata = sensitivity_flow(
            district, eliminated, alive, matrix, seat_type, params,
            posterior, ideology, pools, assumed_on,
        )
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
    pools = load_victorian_ind_pools()
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
            for assumed in ASSUMED_IND_TO_ON:
                trial, used = run_trial_for_district(
                    district, votes, matrix_obj["matrix"], seat["seat_type"],
                    params, posterior, ideology, pools, assumed,
                )
                outcomes.append({
                    "ONLevel": level,
                    "AssumedINDtoON": assumed,
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
    outcomes.to_csv(REPORT_DIR / "ind_on_sensitivity_all_seats.csv", index=False)
    outcomes[
        outcomes["WinnerChanged"] | outcomes["PairChanged"]
    ].to_csv(REPORT_DIR / "ind_on_sensitivity_changed_seats.csv", index=False)
    activations.to_csv(REPORT_DIR / "ind_on_sensitivity_activations.csv", index=False)
    summary = outcomes.groupby(["ONLevel", "AssumedINDtoON"], as_index=False).agg(
        ActivatedSeats=("TrialActivated", "sum"),
        WinnerChanges=("WinnerChanged", "sum"),
        PairChanges=("PairChanged", "sum"),
        MeanAbsoluteWinnerPctChange=("WinnerPctChange", lambda x: x.abs().mean()),
        MaximumAbsoluteWinnerPctChange=("WinnerPctChange", lambda x: x.abs().max()),
    )
    summary.to_csv(REPORT_DIR / "ind_on_sensitivity_summary.csv", index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
