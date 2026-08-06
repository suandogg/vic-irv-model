"""Build development-only ON preference evidence from the federal model.

Only Victorian federal divisions are pooled.  The source is the federal
model's canonical, candidate-level, proportional-origin pass-through output.
This script deliberately does not alter SCENARIO_STATS or production inputs.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path(
    "/Users/callumrees/Desktop/federal_irv_model/data/raw/"
    "CATEGORY_PREF_FLOWS_LONG.csv"
)
DEFAULT_SEAT_OUTPUT = ROOT / "data" / "development" / "FEDERAL_VIC_ON_SEAT_FLOWS.csv"
DEFAULT_POOL_OUTPUT = ROOT / "data" / "development" / "FEDERAL_VIC_ON_SCENARIOS.csv"


def _contains_on(row: pd.Series) -> bool:
    alive = {part.strip().upper() for part in str(row["AliveSet"]).split("+")}
    return str(row["Eliminated"]).strip().upper() == "ON" or "ON" in alive


def build_evidence(source: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    flows = pd.read_csv(source)
    required = {
        "Seat", "State", "Eliminated", "AliveSet", "Recipient", "Votes",
        "ScenarioTotal", "Share", "Method", "VoteBasis", "Source",
    }
    missing = sorted(required.difference(flows.columns))
    if missing:
        raise ValueError(f"Federal category evidence missing columns: {missing}")

    seat = flows[flows["State"].astype(str).str.upper().eq("VIC")].copy()
    seat = seat[seat.apply(_contains_on, axis=1)].copy()
    if seat.empty:
        raise ValueError("No ON-related Victorian federal preference evidence found")

    seat["EvidenceSourceModel"] = "FEDERAL_2025_VIC"
    seat["GeographicUse"] = "STATEWIDE_POOL_ONLY"
    seat["DevelopmentOnly"] = True

    pooled_rows: list[dict] = []
    for (eliminated, alive), group in seat.groupby(["Eliminated", "AliveSet"]):
        alive_parties = str(alive).split("+")
        by_seat = group.pivot_table(
            index="Seat", columns="Recipient", values="Share", fill_value=0.0
        ).reindex(columns=alive_parties, fill_value=0.0)
        scenario_totals = group.groupby("Seat")["ScenarioTotal"].first()
        total_evidence = float(scenario_totals.sum())
        votes = group.groupby("Recipient")["Votes"].sum()

        for recipient in alive_parties:
            observations = by_seat[recipient].astype(float)
            pooled_rows.append({
                "Eliminated": eliminated,
                "AliveSet": alive,
                "Recipient": recipient,
                "EqualSeatShare": float(observations.mean()),
                "VoteWeightedShare": (
                    float(votes.get(recipient, 0.0)) / total_evidence
                    if total_evidence else 0.0
                ),
                "Seats": int(len(by_seat)),
                "Votes": float(votes.get(recipient, 0.0)),
                "ScenarioTotal": total_evidence,
                "BetweenSeatVariance": float(observations.var(ddof=1)) if len(observations) > 1 else 0.0,
                "BetweenSeatSD": float(observations.std(ddof=1)) if len(observations) > 1 else 0.0,
                "MinimumSeatShare": float(observations.min()),
                "MaximumSeatShare": float(observations.max()),
                "PoolingRecommendation": "EQUAL_SEAT_WITH_SHRINKAGE",
                "EvidenceSourceModel": "FEDERAL_2025_VIC",
                "GeographicUse": "STATEWIDE_POOL_ONLY",
                "DevelopmentOnly": True,
            })

    pooled = pd.DataFrame(pooled_rows).sort_values(
        ["Eliminated", "AliveSet", "Recipient"]
    )
    seat = seat.sort_values(["Seat", "Eliminated", "AliveSet", "Recipient"])
    return seat, pooled


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--seat-output", type=Path, default=DEFAULT_SEAT_OUTPUT)
    parser.add_argument("--pool-output", type=Path, default=DEFAULT_POOL_OUTPUT)
    args = parser.parse_args()

    seat, pooled = build_evidence(args.source)
    args.seat_output.parent.mkdir(parents=True, exist_ok=True)
    args.pool_output.parent.mkdir(parents=True, exist_ok=True)
    seat.to_csv(args.seat_output, index=False)
    pooled.to_csv(args.pool_output, index=False)
    print(f"Wrote {len(seat)} seat-flow rows to {args.seat_output}")
    print(f"Wrote {len(pooled)} pooled rows to {args.pool_output}")


if __name__ == "__main__":
    main()
