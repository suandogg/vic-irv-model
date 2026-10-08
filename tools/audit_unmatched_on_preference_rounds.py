"""Audit actual ON-related rounds not covered by production federal evidence."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from SRC.constants import PARTIES
from SRC.federal_on_evidence_loader import apply_production_federal_on_evidence
from SRC.ideology_loader import load_ideology_prior
from SRC.irv import trace_preference_diagnostics_for_district
from SRC.legacy_primary_loader import load_legacy_primary_inputs
from SRC.legacy_primary_model import build_corrected_primary_table
from SRC.matrix_loader import load_synth_pref_matrices
from SRC.params_loader import load_params
from SRC.posterior_loader import load_posterior_scenarios


BASELINE = {"ALP": 36.66, "LNP": 34.48, "GRN": 11.50, "ON": 0.28, "IND": 5.55, "OTH": 11.53}
ON_LEVELS = [10.0, 18.0, 20.0, 24.4]
OUTPUT = ROOT / "reports" / "unmatched_on_preference_rounds.csv"
SUMMARY = ROOT / "reports" / "unmatched_on_preference_summary.csv"


def targets_for_on(on_level: float) -> dict[str, float]:
    non_on_total = sum(BASELINE[p] for p in PARTIES if p != "ON")
    return {
        p: on_level if p == "ON" else BASELINE[p] * (100 - on_level) / non_on_total
        for p in PARTIES
    }


def stage_vector(stage: dict) -> dict[str, float]:
    return {
        p: 0.0 if pd.isna(stage.get(p)) else float(stage.get(p) or 0)
        for p in PARTIES
    }


def total_variation(a: dict[str, float], b: dict[str, float]) -> float:
    return 0.5 * sum(abs(a[p] - b[p]) for p in PARTIES)


def audit() -> pd.DataFrame:
    inputs = load_legacy_primary_inputs()
    matrices = load_synth_pref_matrices()
    params = load_params()
    posterior = apply_production_federal_on_evidence(load_posterior_scenarios())
    ideology = load_ideology_prior()
    on_alpha = float(params["scalar_params"].get("ON alpha", 0.6))
    rows = []

    for level in ON_LEVELS:
        scenario_params = dict(params)
        scenario_params["scalar_params"] = dict(params.get("scalar_params", {}))
        scenario_params["scalar_params"]["SCENARIO_ON_PRIMARY"] = level
        wide = build_corrected_primary_table(inputs, targets_for_on(level), on_alpha=on_alpha)
        lookup = wide.assign(
            district_key=wide["district"].astype(str).str.strip().str.upper()
        ).set_index("district_key")
        for district, matrix_obj in matrices.items():
            seat = lookup.loc[str(district).strip().upper()]
            votes = {p: float(seat[p]) for p in PARTIES}
            trace = trace_preference_diagnostics_for_district(
                votes, matrix_obj["matrix"], seat["seat_type"], scenario_params, posterior, ideology
            )
            frame = pd.DataFrame(trace)
            for round_name, stages in frame.groupby("round", sort=False):
                first = stages.iloc[0]
                eliminated = str(first["eliminated"])
                alive = str(first["alive"]).split(">")
                if eliminated != "ON" and "ON" not in alive:
                    continue
                evidence_stage = stages[stages["stage"].eq("federal ON evidence trial")]
                selected = stages[stages["stage"].eq("basis selected")]
                siphon = stages[stages["stage"].eq("final ON siphon")]
                siphon_effect = 0.0
                if not siphon.empty:
                    siphon_index = siphon.index[0]
                    prior_rows = stages.loc[stages.index < siphon_index]
                    if not prior_rows.empty:
                        siphon_effect = total_variation(
                            stage_vector(prior_rows.iloc[-1]), stage_vector(siphon.iloc[0])
                        )
                basis = (
                    "federal ON evidence trial"
                    if not evidence_stage.empty
                    else str(selected.iloc[-1].get("basis", "unknown")) if not selected.empty
                    else "unknown"
                )
                rows.append({
                    "ONLevel": level,
                    "District": district,
                    "SeatType": seat["seat_type"],
                    "Round": round_name,
                    "EliminatedVoteShare": float(first["eliminated_vote"]),
                    "Eliminated": eliminated,
                    "AliveSet": "+".join(sorted(alive)),
                    "EvidenceBacked": not evidence_stage.empty,
                    "Basis": basis,
                    "GenericSiphonApplied": siphon_effect > 1e-12,
                    "GenericSiphonTVD": siphon_effect,
                    "SiphonVoteMass": float(first["eliminated_vote"]) * siphon_effect,
                    "MissingExactEvidence": evidence_stage.empty,
                })
    return pd.DataFrame(rows)


def main() -> None:
    rows = audit()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rows.to_csv(OUTPUT, index=False)
    summary = (
        rows.groupby(["ONLevel", "EvidenceBacked", "Basis", "Eliminated", "AliveSet"], as_index=False)
        .agg(
            Rounds=("District", "size"),
            Districts=("District", "nunique"),
            SiphonRounds=("GenericSiphonApplied", "sum"),
            MeanSiphonTVD=("GenericSiphonTVD", "mean"),
            MaximumSiphonTVD=("GenericSiphonTVD", "max"),
            MeanEliminatedVoteShare=("EliminatedVoteShare", "mean"),
            TotalSiphonVoteMass=("SiphonVoteMass", "sum"),
        )
        .sort_values(["ONLevel", "EvidenceBacked", "Rounds"], ascending=[True, True, False])
    )
    summary.to_csv(SUMMARY, index=False)
    print(f"Wrote {len(rows)} ON-related rounds; {int(rows.MissingExactEvidence.sum())} lack exact evidence")


if __name__ == "__main__":
    main()
