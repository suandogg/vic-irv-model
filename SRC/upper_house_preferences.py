"""Evidence-shrunk post-GVT party rankings and synthetic ballot parcels."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import exp
import random
from typing import Mapping, Sequence

import pandas as pd

from SRC.upper_house_stv import BallotParcel, expand_atl_ranking


LEFT = {"FAR_LEFT", "GREEN_LEFT", "PROGRESSIVE", "CENTRE_LEFT"}
RIGHT = {"CENTRE_RIGHT", "SOCIAL_CONSERVATIVE", "LIBERTARIAN_RIGHT", "POPULIST_RIGHT"}
EVIDENCE_PROXY = {"LNP": "LIB"}


@dataclass(frozen=True)
class PreferenceModel:
    probabilities: Mapping[str, Mapping[str, float]]
    diagnostics: pd.DataFrame


def _enabled(frame: pd.DataFrame) -> pd.DataFrame:
    if "Enabled" not in frame.columns:
        return frame.copy()
    return frame[frame["Enabled"].astype(str).str.upper().isin({"TRUE", "1", "YES"})].copy()


def _prior_weight(source: pd.Series, destination: pd.Series) -> float:
    distance = abs(float(source["IdeologyPosition"]) - float(destination["IdeologyPosition"]))
    weight = exp(-distance / 0.45)
    source_family = str(source["IdeologyFamily"])
    destination_family = str(destination["IdeologyFamily"])
    if source_family == destination_family:
        weight *= 2.5
    elif (source_family in LEFT and destination_family in LEFT) or (
        source_family in RIGHT and destination_family in RIGHT
    ):
        weight *= 1.6
    if destination_family in {"ISSUE", "ALTERNATIVE"}:
        weight *= 0.7
    return max(weight * float(destination.get("PriorConcentration", 1) or 1), 1e-9)


def build_preference_model(
    party_classes: pd.DataFrame,
    evidence: pd.DataFrame,
    prior_strength: float = 1000,
    evidence_cap: float = 10_000,
) -> PreferenceModel:
    classes = _enabled(party_classes).set_index("PartyKey")
    observed = _enabled(evidence)
    for column in ["BallotsObserved", "FlowPct"]:
        observed[column] = pd.to_numeric(observed[column], errors="coerce").fillna(0)
    parties = list(classes.index)
    probabilities: dict[str, dict[str, float]] = {}
    diagnostics = []

    for source in parties:
        prior = {
            destination: _prior_weight(classes.loc[source], classes.loc[destination])
            for destination in parties
            if destination != source
        }
        prior_total = sum(prior.values())
        prior = {key: value / prior_total for key, value in prior.items()}

        evidence_key = EVIDENCE_PROXY.get(source, source)
        exact = observed[observed["SourcePartyKey"].eq(evidence_key)]
        if exact.empty and str(classes.loc[source, "IdeologyFamily"]) == "POPULIST_RIGHT":
            exact = observed[observed["SourcePartyKey"].eq("RIGHT_POPULIST")]
            evidence_source = "POOLED_POPULIST_RIGHT"
        else:
            if not exact.empty and evidence_key != source:
                evidence_source = f"PROXY_2025_VIC_SENATE_{evidence_key}"
            else:
                evidence_source = "EXACT_2025_VIC_SENATE" if not exact.empty else "IDEOLOGY_PRIOR_ONLY"

        counts: defaultdict[str, float] = defaultdict(float)
        for row in exact.itertuples():
            destination = str(row.DestinationPartyKey)
            if destination == "RIGHT_POPULIST":
                destinations = [
                    party for party in parties
                    if party != source and classes.loc[party, "IdeologyFamily"] == "POPULIST_RIGHT"
                ]
                denominator = sum(prior[party] for party in destinations)
                for party in destinations:
                    counts[party] += float(row.BallotsObserved) * prior[party] / denominator
            elif destination in prior:
                counts[destination] += float(row.BallotsObserved)

        raw_evidence = sum(counts.values())
        scale = min(1.0, evidence_cap / raw_evidence) if raw_evidence else 0.0
        scores = {
            destination: prior_strength * prior[destination] + counts[destination] * scale
            for destination in prior
        }
        total = sum(scores.values())
        probabilities[source] = {destination: score / total for destination, score in scores.items()}
        diagnostics.append({
            "SourcePartyKey": source,
            "EvidenceSource": evidence_source,
            "RawEvidenceBallots": raw_evidence,
            "EffectiveEvidenceBallots": raw_evidence * scale,
            "PriorEquivalentBallots": prior_strength,
            "TopDestination": max(probabilities[source], key=probabilities[source].get),
            "TopDestinationPct": max(probabilities[source].values()) * 100,
        })
    return PreferenceModel(probabilities, pd.DataFrame(diagnostics))


def _weighted_choice(rng: random.Random, weights: Mapping[str, float]) -> str:
    keys = list(weights)
    values = [max(0.0, weights[key]) for key in keys]
    return rng.choices(keys, weights=values, k=1)[0]


def _party_behaviour(behaviour: pd.DataFrame, party: str) -> dict[int, float]:
    enabled = _enabled(behaviour)
    row = enabled[enabled["ScopeKey"].eq(party)]
    if row.empty:
        numeric = enabled[["ATL1OnlyPct", "ATL2To4Pct", "ATL5Pct", "ATL6PlusPct", "BTLPct"]].apply(
            pd.to_numeric, errors="coerce"
        )
        values = numeric.mean()
    else:
        values = row.iloc[0]
    # The 2–4 bucket is represented by 3; 6+ by 7. BTL is provisionally
    # represented by five distinct groups until candidate evidence is available.
    return {
        1: float(values["ATL1OnlyPct"]),
        3: float(values["ATL2To4Pct"]),
        5: float(values["ATL5Pct"]) + float(values["BTLPct"]),
        7: float(values["ATL6PlusPct"]),
    }


def generate_ballot_parcels(
    region_party_votes: Mapping[str, int],
    candidates_by_group: Mapping[str, Sequence[str]],
    preference_model: PreferenceModel,
    behaviour: pd.DataFrame,
    archetypes_per_party: int = 1000,
    seed: int = 2026,
) -> tuple[list[BallotParcel], pd.DataFrame]:
    """Generate reproducible ballot archetypes without renormalising exhaustion."""
    parcels: list[BallotParcel] = []
    diagnostics = []
    active_groups = [group for group, candidates in candidates_by_group.items() if candidates]
    for source_index, source in enumerate(active_groups):
        votes = int(region_party_votes.get(source, 0) or 0)
        if votes <= 0:
            continue
        rng = random.Random(seed + source_index * 1009)
        sample_count = min(archetypes_per_party, votes)
        base, remainder = divmod(votes, sample_count)
        depths = _party_behaviour(behaviour, source)
        depth_keys = list(depths)
        exhausted_at_source = 0
        for sample in range(sample_count):
            papers = base + (1 if sample < remainder else 0)
            depth = rng.choices(depth_keys, weights=[depths[key] for key in depth_keys], k=1)[0]
            group_ranking = [source]
            available = set(active_groups) - {source}
            while available and len(group_ranking) < depth:
                weights = {
                    party: preference_model.probabilities.get(group_ranking[-1], {}).get(party, 0)
                    for party in available
                }
                if sum(weights.values()) <= 0:
                    break
                destination = _weighted_choice(rng, weights)
                group_ranking.append(destination)
                available.remove(destination)
            if len(group_ranking) == 1:
                exhausted_at_source += papers
            ranking = expand_atl_ranking(group_ranking, candidates_by_group)
            parcels.append(BallotParcel(ranking, papers))
        diagnostics.append({
            "SourcePartyKey": source,
            "Votes": votes,
            "Archetypes": sample_count,
            "ImmediateExhaustionVotes": exhausted_at_source,
            "ImmediateExhaustionPct": exhausted_at_source / votes * 100,
        })
    return parcels, pd.DataFrame(diagnostics)
