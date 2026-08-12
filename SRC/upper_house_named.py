"""Named-party statewide and regional Legislative Council primary estimates."""

from __future__ import annotations

from collections import defaultdict
from typing import Mapping

import numpy as np
import pandas as pd


def derive_named_statewide_targets(
    party_inputs: pd.DataFrame,
    lower_house_targets: Mapping[str, float],
) -> dict[str, float]:
    """Link configured parties to lower-house targets and scale direct parties to residual.

    Multiple ballot groups linked to the same lower-house family (metropolitan LIB
    and regional joint LNP, for example) share that family target in proportion to
    their configured statewide baselines.
    """
    frame = party_inputs.copy()
    frame = frame[frame["Enabled"].astype(str).str.upper().isin({"TRUE", "1", "YES"})]
    frame["StatewidePrimaryPct"] = pd.to_numeric(frame["StatewidePrimaryPct"], errors="coerce").fillna(0)
    modes = frame["VoteInputMode"].astype(str).str.upper()
    linked = frame[modes.eq("LOWER_HOUSE_LINKED")].copy()
    direct = frame[~modes.eq("LOWER_HOUSE_LINKED")].copy()

    targets: dict[str, float] = {}
    for lower_key, group in linked.groupby("LowerHousePartyKey"):
        family_target = float(lower_house_targets.get(str(lower_key), 0) or 0)
        baseline_total = group["StatewidePrimaryPct"].sum()
        for _, row in group.iterrows():
            share = row["StatewidePrimaryPct"] / baseline_total if baseline_total > 0 else 1 / len(group)
            targets[str(row["PartyKey"])] = family_target * share

    linked_total = sum(targets.values())
    if linked_total > 100 + 1e-9:
        raise ValueError("linked statewide upper-house targets exceed 100%")
    residual = max(0.0, 100.0 - linked_total)
    direct_total = direct["StatewidePrimaryPct"].sum()
    for _, row in direct.iterrows():
        share = row["StatewidePrimaryPct"] / direct_total if direct_total > 0 else 0
        targets[str(row["PartyKey"])] = residual * share
    return targets


def derive_named_region_targets(
    statewide_targets: Mapping[str, float],
    region_pvi: pd.DataFrame,
    candidate_inputs: pd.DataFrame | None = None,
    tolerance: float = 1e-10,
    max_iterations: int = 10_000,
) -> pd.DataFrame:
    """Rake shrunk regional leans while preserving statewide targets exactly."""
    pvi = region_pvi.copy()
    enabled = pvi["Enabled"].astype(str).str.upper().isin({"TRUE", "1", "YES"})
    pvi = pvi[enabled].copy()
    numeric = ["Votes2022", "RawRegionalLean", "PVIWeight"]
    for column in numeric:
        pvi[column] = pd.to_numeric(pvi[column], errors="coerce").fillna(0)

    regions = sorted(pvi["Region"].unique())
    parties = [party for party, target in statewide_targets.items() if float(target) > 0]
    if not regions or not parties:
        return pd.DataFrame(columns=["Region", "PartyKey", "UpperPrimaryPct"])

    region_votes = pvi.groupby("Region")["Votes2022"].sum().reindex(regions).astype(float)
    region_weights = (region_votes / region_votes.sum()).to_numpy()

    eligible = {(str(row.Region), str(row.PartyKey)) for row in pvi.itertuples()}
    if candidate_inputs is not None and not candidate_inputs.empty:
        candidates = candidate_inputs.copy()
        active = candidates["Enabled"].astype(str).str.upper().isin({"TRUE", "1", "YES"})
        candidate_pairs = {(str(row.Region), str(row.GroupKey)) for row in candidates[active].itertuples()}
        eligible &= candidate_pairs

    lookup = pvi.set_index(["Region", "PartyKey"])
    matrix = np.zeros((len(regions), len(parties)), dtype=float)
    for i, region in enumerate(regions):
        for j, party in enumerate(parties):
            if (region, party) not in eligible:
                continue
            row = lookup.loc[(region, party)]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            lean = max(float(row["RawRegionalLean"]), 1e-9)
            weight = min(1.0, max(0.0, float(row["PVIWeight"])))
            matrix[i, j] = float(statewide_targets[party]) * (lean ** weight)

    target_vector = np.array([float(statewide_targets[party]) for party in parties])
    target_vector = target_vector / target_vector.sum() * 100
    for _ in range(max_iterations):
        row_sums = matrix.sum(axis=1)
        if np.any(row_sums <= 0):
            raise ValueError("at least one region has no enabled named-party vote")
        matrix = matrix / row_sums[:, None] * 100
        current = (matrix * region_weights[:, None]).sum(axis=0)
        if np.any((current <= 0) & (target_vector > 0)):
            missing = [parties[j] for j in range(len(parties)) if current[j] <= 0 < target_vector[j]]
            raise ValueError(f"positive statewide targets have no eligible region: {missing}")
        matrix *= np.divide(target_vector, current, out=np.ones_like(current), where=current > 0)
        row_error = np.max(np.abs(matrix.sum(axis=1) - 100))
        col_error = np.max(np.abs((matrix * region_weights[:, None]).sum(axis=0) - target_vector))
        if max(row_error, col_error) < tolerance:
            break
    else:
        raise RuntimeError("regional named-party raking did not converge")

    rows = []
    for i, region in enumerate(regions):
        for j, party in enumerate(parties):
            if matrix[i, j] <= 0:
                continue
            rows.append({
                "Region": region,
                "PartyKey": party,
                "UpperPrimaryPct": matrix[i, j],
                "StatewideTargetPct": target_vector[j],
                "RegionWeight": region_weights[i],
            })
    return pd.DataFrame(rows)


def weighted_statewide_from_regions(region_targets: pd.DataFrame) -> dict[str, float]:
    values: defaultdict[str, float] = defaultdict(float)
    for row in region_targets.itertuples():
        values[str(row.PartyKey)] += float(row.UpperPrimaryPct) * float(row.RegionWeight)
    return dict(values)
