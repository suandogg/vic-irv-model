"""Run the conservative Victorian-federal ON evidence trial.

The script writes diagnostics only. It does not change app.py, PARAMS.csv,
SCENARIO_STATS.csv, or any Google Sheet input.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from SRC.constants import PARTIES
from SRC.federal_on_evidence_loader import (
    add_conservative_trial_evidence,
    conservative_reliability,
    load_federal_on_evidence,
)
from SRC.ideology_loader import load_ideology_prior
from SRC.irv import run_irv_all, trace_preference_diagnostics_for_district
from SRC.legacy_primary_loader import load_legacy_primary_inputs
from SRC.legacy_primary_model import build_corrected_primary_table
from SRC.matrix_loader import load_synth_pref_matrices
from SRC.params_loader import load_params
from SRC.posterior_loader import load_posterior_scenarios


BASELINE = {"ALP": 36.66, "LNP": 34.48, "GRN": 11.50, "ON": 0.28, "IND": 5.55, "OTH": 11.53}
ON_LEVELS = [10.0, 20.0, 24.4]
REPORT_DIR = ROOT / "reports"


def targets_for_on(on_level: float) -> dict[str, float]:
    non_on_total = sum(BASELINE[p] for p in PARTIES if p != "ON")
    return {
        party: (
            on_level if party == "ON"
            else BASELINE[party] * (100.0 - on_level) / non_on_total
        )
        for party in PARTIES
    }


def primary_long(table: pd.DataFrame) -> pd.DataFrame:
    return table.melt(
        id_vars=["district", "region", "seat_type", "held_by"],
        value_vars=PARTIES,
        var_name="party",
        value_name="primary_vote",
    )


def run(remove_on_siphon: bool = False):
    inputs = load_legacy_primary_inputs()
    matrices = load_synth_pref_matrices()
    params = load_params()
    posterior = load_posterior_scenarios()
    ideology = load_ideology_prior()
    evidence = load_federal_on_evidence()
    trial_posterior = add_conservative_trial_evidence(
        posterior, evidence, remove_on_siphon=remove_on_siphon
    )
    on_alpha = float(params["scalar_params"].get("ON alpha", 0.6))

    comparisons = []
    changed = []
    used = []
    for on_level in ON_LEVELS:
        wide = build_corrected_primary_table(
            inputs, targets_for_on(on_level), on_alpha=on_alpha
        )
        long = primary_long(wide)
        current = pd.DataFrame(run_irv_all(long, matrices, params, posterior, ideology))
        trial = pd.DataFrame(run_irv_all(long, matrices, params, trial_posterior, ideology))
        merged = current.merge(trial, on="district", suffixes=("_current", "_trial"))
        merged["ONLevel"] = on_level
        merged["WinnerChanged"] = merged["winner_current"] != merged["winner_trial"]
        merged["PairChanged"] = merged["matchup_current"] != merged["matchup_trial"]
        merged["WinnerPctChange"] = merged["winner_pct_trial"] - merged["winner_pct_current"]
        comparisons.append(merged)
        changed.append(merged[merged["WinnerChanged"] | merged["PairChanged"]].copy())

        wide_lookup = wide.assign(
            district_key=wide["district"].astype(str).str.strip().str.upper()
        ).set_index("district_key")
        for district, matrix_obj in matrices.items():
            row = wide_lookup.loc[str(district).strip().upper()]
            votes = {party: float(row[party]) for party in PARTIES}
            diagnostics = trace_preference_diagnostics_for_district(
                votes, matrix_obj["matrix"], row["seat_type"], params,
                trial_posterior, ideology,
            )
            for stage in diagnostics:
                if stage.get("stage") == "federal ON evidence trial":
                    used.append({
                        "ONLevel": on_level,
                        "District": district,
                        "Round": stage["round"],
                        "Eliminated": stage["eliminated"],
                        "AliveSet": "+".join(sorted(stage["alive"].split(">"))),
                        "Reliability": stage.get("posterior_reliability"),
                        "EvidenceSeats": stage.get("evidence_seats"),
                    })

    reliability = pd.DataFrame([
        {
            "Scenario": key,
            "Seats": scenario["seats"],
            "ScenarioTotal": scenario["scenario_total"],
            "Reliability": conservative_reliability(scenario),
            "Included": conservative_reliability(scenario) > 0,
        }
        for key, scenario in evidence.items()
    ]).sort_values("Reliability", ascending=False)
    return pd.concat(comparisons, ignore_index=True), pd.concat(changed, ignore_index=True), pd.DataFrame(used), reliability


def write_trial(remove_on_siphon: bool, suffix: str):
    all_rows, changed, used, reliability = run(remove_on_siphon=remove_on_siphon)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    all_rows.to_csv(REPORT_DIR / f"federal_on_shrinkage_{suffix}_all_seats.csv", index=False)
    changed.to_csv(REPORT_DIR / f"federal_on_shrinkage_{suffix}_changed_seats.csv", index=False)
    used.to_csv(REPORT_DIR / f"federal_on_shrinkage_{suffix}_rounds_used.csv", index=False)
    reliability.to_csv(REPORT_DIR / f"federal_on_shrinkage_{suffix}_reliability.csv", index=False)
    print(f"\n{suffix}:")
    for level, group in all_rows.groupby("ONLevel"):
        print(
            f"ON {level:g}%: winner changes={int(group.WinnerChanged.sum())}, "
            f"pair changes={int(group.PairChanged.sum())}, "
            f"max |winner share change|={group.WinnerPctChange.abs().max():.3%}"
        )
    print(f"Experimental evidence used in {len(used)} actual elimination rounds")
    return all_rows


def main() -> None:
    retained = write_trial(False, "siphon_retained")
    removed = write_trial(True, "siphon_replaced")
    comparison = retained[[
        "ONLevel", "district", "winner_trial", "runner_up_trial", "winner_pct_trial"
    ]].merge(
        removed[[
            "ONLevel", "district", "winner_trial", "runner_up_trial", "winner_pct_trial"
        ]],
        on=["ONLevel", "district"],
        suffixes=("_siphon_retained", "_siphon_replaced"),
    )
    comparison["WinnerChangedBetweenTrials"] = (
        comparison["winner_trial_siphon_retained"]
        != comparison["winner_trial_siphon_replaced"]
    )
    comparison["PairChangedBetweenTrials"] = (
        comparison["runner_up_trial_siphon_retained"]
        != comparison["runner_up_trial_siphon_replaced"]
    )
    comparison["WinnerPctDifference"] = (
        comparison["winner_pct_trial_siphon_replaced"]
        - comparison["winner_pct_trial_siphon_retained"]
    )
    comparison.to_csv(
        REPORT_DIR / "federal_on_shrinkage_siphon_comparison.csv", index=False
    )


if __name__ == "__main__":
    main()
