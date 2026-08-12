"""Candidate-level Victorian Legislative Council proportional count.

The default implements Electoral Act 2002 (Vic) s 114A as in force on
1 July 2026: integer Droop quota, inclusive-Gregory surplus transfers,
whole-vote truncation by destination, and exclusion parcels transferred in
descending transfer-value order.  Ballot generation is intentionally outside
this module so statutory mechanics can be tested independently of assumptions.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, replace
from fractions import Fraction
from math import floor
import random
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class BallotParcel:
    ranking: tuple[str, ...]
    papers: int
    transfer_value: Fraction = Fraction(1, 1)

    def __post_init__(self) -> None:
        if self.papers < 0:
            raise ValueError("papers must not be negative")
        if self.transfer_value < 0:
            raise ValueError("transfer value must not be negative")


@dataclass(frozen=True)
class CountResult:
    quota: int
    formal_votes: int
    elected: tuple[str, ...]
    excluded: tuple[str, ...]
    final_tallies: Mapping[str, int]
    exhausted_votes: int
    trace: tuple[dict, ...]


def expand_atl_ranking(
    group_ranking: Sequence[str],
    candidates_by_group: Mapping[str, Sequence[str]],
) -> tuple[str, ...]:
    """Expand ATL groups to candidates in the listed order within each group."""
    ranking: list[str] = []
    for group in group_ranking:
        ranking.extend(candidates_by_group.get(group, ()))
    return tuple(dict.fromkeys(ranking))


def _next_preference(ranking: Sequence[str], continuing: set[str]) -> str | None:
    return next((candidate for candidate in ranking if candidate in continuing), None)


def _quota(formal_votes: int, vacancies: int) -> int:
    return formal_votes // (vacancies + 1) + 1


def inclusive_gregory_transfer_value(surplus: int, ballot_papers: int) -> Fraction:
    """Return the s 114A surplus transfer value without decimal rounding."""
    if surplus < 0:
        raise ValueError("surplus must not be negative")
    if ballot_papers <= 0:
        raise ValueError("ballot_papers must be positive")
    return Fraction(surplus, ballot_papers)


def count_victorian_stv(
    candidates: Sequence[str],
    ballots: Iterable[BallotParcel],
    vacancies: int = 5,
    tie_seed: int = 2026,
) -> CountResult:
    """Count explicit candidate rankings under the current Victorian rules.

    Fractions are used for transfer values, but every destination increment is
    truncated to a whole vote as required by s 114A.  A fixed seed provides a
    reproducible modelling substitute where the Act requires drawing by lot.
    """
    candidate_order = tuple(dict.fromkeys(candidates))
    if len(candidate_order) < vacancies:
        raise ValueError("fewer candidates than vacancies")
    valid = set(candidate_order)
    ballot_list = [
        BallotParcel(tuple(c for c in ballot.ranking if c in valid), ballot.papers, ballot.transfer_value)
        for ballot in ballots
        if ballot.papers > 0 and any(c in valid for c in ballot.ranking)
    ]
    formal_votes = sum(ballot.papers for ballot in ballot_list)
    if formal_votes <= 0:
        raise ValueError("no formal votes")
    quota = _quota(formal_votes, vacancies)
    rng = random.Random(tie_seed)

    continuing = set(candidate_order)
    elected: list[str] = []
    excluded: list[str] = []
    parcels: dict[str, list[BallotParcel]] = {candidate: [] for candidate in candidate_order}
    tallies = {candidate: 0 for candidate in candidate_order}
    histories = {candidate: [0] for candidate in candidate_order}
    trace: list[dict] = []
    exhausted = 0

    for ballot in ballot_list:
        destination = _next_preference(ballot.ranking, continuing)
        if destination is None:
            exhausted += ballot.papers
            continue
        parcels[destination].append(replace(ballot, transfer_value=Fraction(1, 1)))
        tallies[destination] += ballot.papers

    def snapshot(action: str, candidate: str | None = None, **extra) -> None:
        trace.append({
            "count": len(trace) + 1,
            "action": action,
            "candidate": candidate or "",
            "quota": quota,
            "exhausted": exhausted,
            **{name: tallies[name] for name in candidate_order},
            **extra,
        })
        for name in candidate_order:
            histories[name].append(tallies[name])

    def tied_by_history(names: Sequence[str], choose_highest: bool) -> str:
        remaining = list(names)
        max_history = max(len(histories[name]) for name in remaining)
        for offset in range(1, max_history + 1):
            values = {name: histories[name][-offset] if offset <= len(histories[name]) else 0 for name in remaining}
            target = max(values.values()) if choose_highest else min(values.values())
            remaining = [name for name in remaining if values[name] == target]
            if len(remaining) == 1:
                return remaining[0]
        return rng.choice(sorted(remaining))

    surplus_queue: deque[str] = deque()

    def declare_newly_elected(names: Sequence[str]) -> None:
        eligible = [name for name in names if name in continuing and tallies[name] >= quota]
        eligible.sort(key=lambda name: (-tallies[name], candidate_order.index(name)))
        for name in eligible:
            continuing.remove(name)
            elected.append(name)
            surplus_queue.append(name)
            snapshot("ELECT", name, surplus=max(0, tallies[name] - quota))

    def transfer_bucket(bucket: Sequence[BallotParcel], value: Fraction, action: str, source: str) -> None:
        nonlocal exhausted
        by_destination: defaultdict[str | None, list[BallotParcel]] = defaultdict(list)
        for parcel in bucket:
            destination = _next_preference(parcel.ranking, continuing)
            by_destination[destination].append(parcel)
        for destination, destination_parcels in by_destination.items():
            paper_count = sum(parcel.papers for parcel in destination_parcels)
            increment = floor(paper_count * value)
            if destination is None:
                exhausted += increment
                continue
            if increment:
                tallies[destination] += increment
            parcels[destination].extend(
                replace(parcel, transfer_value=value) for parcel in destination_parcels
            )
        snapshot(action, source, transfer_value=float(value))

    snapshot("FIRST_PREFERENCES")
    declare_newly_elected(candidate_order)

    while len(elected) < vacancies:
        if len(continuing) <= vacancies - len(elected):
            for name in sorted(continuing, key=lambda n: (-tallies[n], candidate_order.index(n))):
                continuing.remove(name)
                elected.append(name)
                snapshot("ELECT_REMAINING", name)
            break

        if surplus_queue:
            # Earlier-created surplus takes priority; within a simultaneous batch,
            # declare_newly_elected queued candidates from largest tally downward.
            source = surplus_queue.popleft()
            surplus = tallies[source] - quota
            if surplus <= 0:
                continue
            source_parcels = parcels[source]
            papers = sum(parcel.papers for parcel in source_parcels)
            if papers <= 0:
                continue
            transfer_value = inclusive_gregory_transfer_value(surplus, papers)
            transfer_bucket(source_parcels, transfer_value, "SURPLUS", source)
            tallies[source] = quota
            declare_newly_elected(candidate_order)
            continue

        lowest = min(tallies[name] for name in continuing)
        tied = [name for name in continuing if tallies[name] == lowest]
        source = tied[0] if len(tied) == 1 else tied_by_history(tied, choose_highest=False)
        continuing.remove(source)
        excluded.append(source)
        source_parcels = parcels[source]
        tallies[source] = 0
        snapshot("EXCLUDE", source)

        by_value: defaultdict[Fraction, list[BallotParcel]] = defaultdict(list)
        for parcel in source_parcels:
            by_value[parcel.transfer_value].append(parcel)
        for value in sorted(by_value, reverse=True):
            transfer_bucket(by_value[value], value, "EXCLUSION_TRANSFER", source)
            declare_newly_elected(candidate_order)

    return CountResult(
        quota=quota,
        formal_votes=formal_votes,
        elected=tuple(elected[:vacancies]),
        excluded=tuple(excluded),
        final_tallies=dict(tallies),
        exhausted_votes=exhausted,
        trace=tuple(trace),
    )
