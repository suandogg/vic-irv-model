"""End-to-end named-party Victorian Legislative Council forecast."""

from __future__ import annotations

from collections import defaultdict
from typing import Mapping

import pandas as pd

from SRC.upper_house_named import derive_named_region_targets, derive_named_statewide_targets
from SRC.upper_house_preferences import build_preference_model, generate_ballot_parcels
from SRC.upper_house_stv import count_victorian_stv


def _enabled(frame: pd.DataFrame) -> pd.Series:
    return frame["Enabled"].astype(str).str.upper().isin({"TRUE", "1", "YES"})


def _params(frame: pd.DataFrame) -> dict[str, object]:
    enabled = frame[_enabled(frame)] if "Enabled" in frame else frame
    return dict(zip(enabled["Parameter"], enabled["Value"]))


def run_upper_house_forecast(
    inputs: Mapping[str, pd.DataFrame],
    lower_house_targets: Mapping[str, float],
) -> dict[str, pd.DataFrame]:
    party_inputs = inputs["party_inputs"].copy()
    pvi = inputs["region_pvi"].copy()
    candidates = inputs["candidates"].copy()
    historical = inputs["historical"].copy()
    params = _params(inputs["params"])

    # Party-level PVI controls are the user-facing defaults; a region-party row
    # can still override them by changing PVIWeight in UPPER_REGION_PVI_NAMED.
    party_weights = pd.to_numeric(
        party_inputs.set_index("PartyKey")["RegionalPVIWeight"], errors="coerce"
    ).to_dict()
    pvi["PVIWeight"] = pvi.apply(
        lambda row: float(row["PVIWeight"])
        if pd.notna(row["PVIWeight"])
        else float(party_weights.get(row["PartyKey"], params.get("PVI_SHRINKAGE_DEFAULT", 0.75))),
        axis=1,
    )
    statewide = derive_named_statewide_targets(party_inputs, lower_house_targets)
    region_targets = derive_named_region_targets(statewide, pvi, candidates)
    preference_model = build_preference_model(
        inputs["classes"],
        inputs["evidence"],
        prior_strength=float(params.get("PREFERENCE_EVIDENCE_PRIOR_STRENGTH", 1000)),
        evidence_cap=float(params.get("PREFERENCE_EVIDENCE_MAX_BALLOTS", 10_000)),
    )

    result_rows = []
    trace_rows = []
    ballot_rows = []
    active = candidates[_enabled(candidates)].copy()
    formal_by_region = historical.groupby("Region")["FirstPreferenceVotes"].sum().astype(int).to_dict()
    for region, targets in region_targets.groupby("Region"):
        roster = active[active["Region"].eq(region)].sort_values(["GroupKey", "BallotOrder"])
        groups = {
            key: group["CandidateID"].tolist()
            for key, group in roster.groupby("GroupKey", sort=False)
        }
        formal = formal_by_region[region]
        raw_votes = {
            row.PartyKey: float(row.UpperPrimaryPct) / 100 * formal
            for row in targets.itertuples()
        }
        votes = {party: int(value) for party, value in raw_votes.items()}
        remainder = formal - sum(votes.values())
        for party, _ in sorted(raw_votes.items(), key=lambda item: item[1] - int(item[1]), reverse=True)[:remainder]:
            votes[party] += 1
        parcels, ballot_diagnostics = generate_ballot_parcels(
            votes,
            groups,
            preference_model,
            inputs["behaviour"],
            archetypes_per_party=int(float(params.get("BALLOT_ARCHETYPES_PER_PARTY", 1000))),
            seed=int(float(params.get("COUNT_TIE_SEED", 2026))),
        )
        result = count_victorian_stv(
            roster["CandidateID"].tolist(),
            parcels,
            vacancies=int(float(params.get("SEATS_PER_REGION", 5))),
            tie_seed=int(float(params.get("COUNT_TIE_SEED", 2026))),
        )
        lookup = roster.set_index("CandidateID")
        final_candidates = [
            candidate for candidate in roster["CandidateID"]
            if candidate not in result.elected and candidate not in result.excluded
        ]
        last_loser_tally = max((result.final_tallies[candidate] for candidate in final_candidates), default=0)
        for order, candidate_id in enumerate(result.elected, 1):
            row = lookup.loc[candidate_id]
            elected_tally = result.final_tallies[candidate_id]
            margin_votes = elected_tally - last_loser_tally if order == 5 else elected_tally - result.quota
            reliability = "High"
            if order == 5 and abs(margin_votes) < result.formal_votes * 0.01:
                reliability = "Low"
            elif order == 5 and abs(margin_votes) < result.formal_votes * 0.025:
                reliability = "Moderate"
            result_rows.append({
                "Region": region,
                "ElectedOrder": order,
                "Candidate": row["CandidateName"],
                "GroupKey": row["GroupKey"],
                "PartyKey": row["PartyKey"],
                "Quota": result.quota,
                "FinalTally": elected_tally,
                "FinalTallyQuotas": elected_tally / result.quota,
                "FinalSeatMarginVotes": margin_votes if order == 5 else None,
                "Reliability": reliability,
                "ExhaustedPct": result.exhausted_votes / result.formal_votes * 100,
            })
        trace_rows.extend({"Region": region, **row} for row in result.trace)
        ballot_diagnostics.insert(0, "Region", region)
        ballot_rows.extend(ballot_diagnostics.to_dict("records"))

    statewide_rows = []
    seats: defaultdict[str, int] = defaultdict(int)
    family = party_inputs.set_index("PartyKey")["PartyFamily"].to_dict()
    for row in result_rows:
        seats[str(family.get(row["PartyKey"], row["PartyKey"]))] += 1
    for party, target in sorted(statewide.items(), key=lambda item: -item[1]):
        statewide_rows.append({
            "PartyKey": party,
            "PartyFamily": family.get(party, party),
            "StatewidePrimaryPct": target,
            "Seats": seats.get(family.get(party, party), 0),
        })
    return {
        "statewide": pd.DataFrame(statewide_rows),
        "regions": region_targets,
        "results": pd.DataFrame(result_rows),
        "trace": pd.DataFrame(trace_rows),
        "ballots": pd.DataFrame(ballot_rows),
        "preference_diagnostics": preference_model.diagnostics,
    }
