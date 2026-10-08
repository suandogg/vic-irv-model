"""Audit why comparable ALP-LNP 2CP swings vary substantially by seat."""

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
from SRC.legacy_primary_loader import load_legacy_primary_inputs
from SRC.legacy_primary_model import build_corrected_primary_table
from SRC.loaders import apply_seat_held_metadata, load_seat_held_metadata, read_csv_raw
from SRC.lnp_precollapse_loader import apply_lnp_precollapse
from SRC.matrix_loader import load_synth_pref_matrices
from SRC.params_loader import load_params
from SRC.posterior_loader import load_posterior_scenarios
from SRC.preference_engine import diagnose_preference_weights


TARGETS = {"ALP": 29.0, "LNP": 32.0, "GRN": 12.0, "ON": 18.0, "OTH": 4.5, "IND": 4.5}
REPORT_DIR = ROOT / "reports"


def scenario_params(params: dict) -> dict:
    out = dict(params)
    out["scalar_params"] = dict(params.get("scalar_params", {}))
    out["scalar_params"]["SCENARIO_ON_PRIMARY"] = TARGETS["ON"]
    return out


def trace_seat(district, votes, matrix, seat_type, params, posterior, ideology):
    working = {party: float(votes.get(party, 0.0)) for party in PARTIES}
    primary = dict(working)
    alive = [party for party in PARTIES if working[party] > 0]
    rounds = []
    round_number = 0
    while len(alive) > 2:
        round_number += 1
        eliminated = min(alive, key=lambda party: working[party])
        eliminated_votes = working[eliminated]
        alive = [party for party in alive if party != eliminated]
        diagnostic = diagnose_preference_weights(
            eliminated, alive, matrix, seat_type, params, posterior, ideology
        )
        flows = diagnostic["final_flows"]
        row = {
            "District": district, "SeatType": seat_type, "Round": round_number,
            "Eliminated": eliminated, "EliminatedVote": eliminated_votes,
            "AliveSet": "+".join(sorted(alive)), "Basis": diagnostic["basis"],
        }
        final_stage = diagnostic["stages"][-1]
        row.update({
            "EvidenceSeats": final_stage.get("evidence_seats"),
            "PosteriorReliability": final_stage.get("posterior_reliability"),
        })
        for recipient in PARTIES:
            flow = float(flows.get(recipient, 0.0))
            row[f"FlowTo{recipient}"] = flow
            row[f"VotesTo{recipient}"] = eliminated_votes * flow
        rounds.append(row)
        working[eliminated] = 0.0
        for recipient, flow in flows.items():
            working[recipient] += eliminated_votes * flow

    final = sorted(alive, key=lambda party: working[party], reverse=True)
    final_total = working[final[0]] + working[final[1]]
    result = {
        "District": district, "SeatType": seat_type,
        **{f"Primary{party}": primary[party] for party in PARTIES},
        "Winner": final[0], "RunnerUp": final[1],
        "WinnerPct": working[final[0]] / final_total,
        "RunnerUpPct": working[final[1]] / final_total,
        "ALPFinalShare": working["ALP"] / final_total if "ALP" in final else None,
        "LNPFinalShare": working["LNP"] / final_total if "LNP" in final else None,
        "EliminationOrder": ">".join(row["Eliminated"] for row in rounds),
        "UnsupportedRounds": sum(row["Basis"] not in {"federal ON evidence trial", "posterior"} for row in rounds),
        "ExactFederalRounds": sum(row["Basis"] == "federal ON evidence trial" for row in rounds),
    }
    return result, rounds


def main():
    inputs = apply_seat_held_metadata(load_legacy_primary_inputs(), load_seat_held_metadata())
    params = scenario_params(load_params())
    posterior = apply_production_federal_on_evidence(load_posterior_scenarios())
    ideology = load_ideology_prior()
    matrices = load_synth_pref_matrices()
    on_alpha = float(params["scalar_params"].get("ON alpha", 0.6))
    primaries = apply_lnp_precollapse(
        build_corrected_primary_table(inputs, TARGETS, on_alpha=on_alpha)
    )
    lookup = primaries.assign(key=primaries["district"].str.strip().str.upper()).set_index("key")
    baseline_frame = read_csv_raw("BASELINE_2CP.csv")
    baseline_frame["district_key"] = baseline_frame["district"].str.strip().str.upper()
    baseline = baseline_frame.set_index("district_key")
    results, rounds = [], []
    for district, matrix_obj in matrices.items():
        seat = lookup.loc[district.strip().upper()]
        votes = {party: float(seat[party]) for party in PARTIES}
        result, seat_rounds = trace_seat(
            district, votes, matrix_obj["matrix"], seat["seat_type"],
            params, posterior, ideology,
        )
        result["HeldBy"] = seat["held_by"]
        district_key = district.strip().upper()
        if district_key in baseline.index and result["HeldBy"] == "ALP":
            prior = clean_baseline_value(baseline.loc[district_key].get("ALP_2CP"))
            result["PriorHeld2CP"] = prior
            result["HeldPartySwingPct"] = (
                (result["ALPFinalShare"] - prior) * 100
                if prior is not None and result["ALPFinalShare"] is not None else None
            )
        results.append(result)
        rounds.extend(seat_rounds)

    results_df = pd.DataFrame(results)
    rounds_df = pd.DataFrame(rounds)
    comparable = results_df[
        (results_df["HeldBy"] == "ALP")
        & (results_df["Winner"].isin(["ALP", "LNP"]))
        & (results_df["RunnerUp"].isin(["ALP", "LNP"]))
    ].copy()
    comparable["SwingGapFromMedian"] = (
        comparable["HeldPartySwingPct"] - comparable["HeldPartySwingPct"].median()
    )
    comparable = comparable.sort_values("HeldPartySwingPct")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(REPORT_DIR / "alp_swing_audit_all_seats.csv", index=False)
    rounds_df.to_csv(REPORT_DIR / "alp_swing_audit_all_rounds.csv", index=False)
    comparable.to_csv(REPORT_DIR / "alp_swing_audit_comparable_alp_lnp.csv", index=False)
    focus = rounds_df[rounds_df["District"].str.upper().isin(["BASS", "ASHWOOD"])]
    focus.to_csv(REPORT_DIR / "alp_swing_audit_bass_ashwood_rounds.csv", index=False)
    print(results_df[results_df["District"].str.upper().isin(["BASS", "ASHWOOD"])].to_string(index=False))
    print("\nRound detail:\n", focus.to_string(index=False))


if __name__ == "__main__":
    main()
