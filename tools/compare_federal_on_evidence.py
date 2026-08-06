"""Compare pooled federal ON evidence with current Victorian preference rules.

This is diagnostic only: it does not replace any production preference input.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from SRC.federal_on_evidence_loader import load_federal_on_evidence
from SRC.ideology_loader import load_ideology_prior
from SRC.matrix_loader import load_synth_pref_matrices
from SRC.params_loader import load_params
from SRC.posterior_loader import load_posterior_scenarios
from SRC.preference_engine import diagnose_preference_weights


REPORT_DIR = ROOT / "reports"
FLOW_REPORT = REPORT_DIR / "federal_on_evidence_vs_current_flows.csv"
SOURCE_REPORT = REPORT_DIR / "federal_on_distinctive_source_seats.csv"


def compare() -> tuple[pd.DataFrame, pd.DataFrame]:
    evidence = load_federal_on_evidence()
    matrices = load_synth_pref_matrices()
    params = load_params()
    posterior = load_posterior_scenarios()
    ideology = load_ideology_prior()
    rows = []

    for scenario_key, empirical in evidence.items():
        eliminated, alive_key = scenario_key.split("|", 1)
        alive = alive_key.split("+")
        empirical_shares = empirical["shares"]
        for district, matrix_obj in matrices.items():
            diagnostic = diagnose_preference_weights(
                eliminated_party=eliminated,
                alive_parties=alive,
                matrix=matrix_obj["matrix"],
                geography_class=matrix_obj["seat_type"],
                params=params,
                posterior=posterior,
                ideology=ideology,
            )
            current = diagnostic["final_flows"]
            deltas = {
                party: empirical_shares.get(party, 0.0) - current.get(party, 0.0)
                for party in alive
            }
            rows.append({
                "District": district,
                "SeatType": matrix_obj["seat_type"],
                "Eliminated": eliminated,
                "AliveSet": alive_key,
                "CurrentBasis": diagnostic["basis"],
                "FederalSeats": empirical["seats"],
                "FederalScenarioTotal": empirical["scenario_total"],
                "TotalVariationDistance": 0.5 * sum(abs(v) for v in deltas.values()),
                **{f"Current_{p}": current.get(p, 0.0) for p in alive},
                **{f"Federal_{p}": empirical_shares.get(p, 0.0) for p in alive},
                **{f"Delta_{p}": deltas[p] for p in alive},
            })

    flow_report = pd.DataFrame(rows).sort_values(
        ["TotalVariationDistance", "District"], ascending=[False, True]
    )

    seat_path = ROOT / "data" / "development" / "FEDERAL_VIC_ON_SEAT_FLOWS.csv"
    seat = pd.read_csv(seat_path)
    pooled = pd.read_csv(
        ROOT / "data" / "development" / "FEDERAL_VIC_ON_SCENARIOS.csv"
    )
    pooled_lookup = pooled.set_index(
        ["Eliminated", "AliveSet", "Recipient"]
    )["EqualSeatShare"].to_dict()
    seat["PooledShare"] = seat.apply(
        lambda row: pooled_lookup[(row["Eliminated"], row["AliveSet"], row["Recipient"])],
        axis=1,
    )
    seat["AbsoluteDeviation"] = (seat["Share"] - seat["PooledShare"]).abs()
    source_report = (
        seat.groupby(["Seat", "Eliminated", "AliveSet"], as_index=False)
        .agg(
            TotalVariationFromPool=("AbsoluteDeviation", lambda values: 0.5 * values.sum()),
            ScenarioTotal=("ScenarioTotal", "first"),
            Method=("Method", "first"),
        )
        .sort_values("TotalVariationFromPool", ascending=False)
    )
    return flow_report, source_report


def main() -> None:
    flow_report, source_report = compare()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    flow_report.to_csv(FLOW_REPORT, index=False)
    source_report.to_csv(SOURCE_REPORT, index=False)
    print(f"Wrote {len(flow_report)} Victorian scenario comparisons to {FLOW_REPORT}")
    print(f"Wrote {len(source_report)} federal source-seat diagnostics to {SOURCE_REPORT}")


if __name__ == "__main__":
    main()
