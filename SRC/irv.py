from SRC.constants import PARTIES
from SRC.preference_engine import (
    diagnose_preference_weights,
)


def preference_source_category(basis: str) -> str:
    """Map detailed engine bases to four user-facing evidence classes."""
    if basis == "federal ON evidence trial":
        return "Exact federal evidence"
    if basis in {"full AEC row", "partial AEC row", "posterior scenario"}:
        return "Victorian preference evidence"
    if basis == "ON special prior":
        return "Special prior"
    return "Generic matrix or fallback"


def district_key(name: str) -> str:
    return str(name).strip().upper()


def initialise_votes(district_votes: dict[str, float]) -> dict[str, float]:
    return {
        party: float(district_votes.get(party, 0) or 0)
        for party in PARTIES
    }


def parcel_origin_retention(params: dict) -> float:
    """Configured share of transferred parcels retaining origin behaviour."""
    value = params.get("scalar_params", {}).get(
        "PARCEL_ORIGIN_RETENTION", 1.0
    )
    return max(0.0, min(1.0, float(value if value is not None else 1.0)))


def initialise_parcels(district_votes: dict[str, float]) -> dict:
    """Track every current holder's vote by its primary-party origin."""
    votes = initialise_votes(district_votes)
    return {
        holder: {
            origin: votes[holder] if holder == origin else 0.0
            for origin in PARTIES
        }
        for holder in PARTIES
    }


def parcel_totals(parcels: dict) -> dict[str, float]:
    return {
        holder: sum(float(value) for value in parcels[holder].values())
        for holder in PARTIES
    }


def distribute_parcel_holder(
    parcels,
    holder,
    alive_after,
    matrix,
    seat_type,
    params,
    posterior,
    ideology,
):
    """Distribute one holder while preserving each parcel's primary origin.

    Special ON scenario priors remain locked holder-level rules.  All other
    parcels blend the current holder's flow with the primary origin's flow.
    """
    holder_diagnostics = diagnose_preference_weights(
        eliminated_party=holder,
        alive_parties=alive_after,
        matrix=matrix,
        geography_class=seat_type,
        params=params,
        posterior=posterior,
        ideology=ideology,
    )
    holder_flows = holder_diagnostics["final_flows"]
    retention = parcel_origin_retention(params)
    outgoing = parcels[holder].copy()
    outgoing_total = sum(outgoing.values())
    parcels[holder] = {origin: 0.0 for origin in PARTIES}
    transferred = {party: 0.0 for party in alive_after}
    origin_rows = []

    for origin, amount in outgoing.items():
        if amount <= 0:
            continue

        origin_basis = holder_diagnostics["basis"]
        flows = holder_flows
        if (
            retention > 0
            and origin != holder
            and holder_diagnostics["basis"] != "ON special prior"
        ):
            origin_diagnostics = diagnose_preference_weights(
                eliminated_party=origin,
                alive_parties=alive_after,
                matrix=matrix,
                geography_class=seat_type,
                params=params,
                posterior=posterior,
                ideology=ideology,
            )
            origin_basis = origin_diagnostics["basis"]
            origin_flows = origin_diagnostics["final_flows"]
            flows = {
                party: (
                    (1.0 - retention) * holder_flows.get(party, 0.0)
                    + retention * origin_flows.get(party, 0.0)
                )
                for party in alive_after
            }
            total = sum(flows.values())
            flows = {
                party: value / total
                for party, value in flows.items()
            }

        for recipient, share in flows.items():
            movement = amount * share
            parcels[recipient][origin] += movement
            transferred[recipient] += movement

        origin_rows.append({
            "origin": origin,
            "votes": amount,
            "basis": origin_basis,
            **{party: flows.get(party, 0.0) for party in alive_after},
        })

    effective_flows = {
        party: transferred[party] / outgoing_total if outgoing_total > 0 else 0.0
        for party in alive_after
    }
    return holder_diagnostics, effective_flows, origin_rows


def run_irv_for_district(
    district_votes: dict[str, float],
    matrix: dict,
    seat_type: str,
    params: dict,
    posterior: dict,
    ideology: dict,
) -> dict:

    parcels = initialise_parcels(district_votes)
    votes = parcel_totals(parcels)

    alive = [
        party for party in PARTIES
        if votes.get(party, 0) > 0
    ]

    elimination_order = []

    while len(alive) > 2:

        eliminated = min(alive, key=lambda party: votes[party])
        elimination_order.append(eliminated)

        alive = [
            party for party in alive
            if party != eliminated
        ]

        distribute_parcel_holder(
            parcels=parcels,
            holder=eliminated,
            alive_after=alive,
            matrix=matrix,
            seat_type=seat_type,
            params=params,
            posterior=posterior,
            ideology=ideology,
        )
        votes = parcel_totals(parcels)

    final_two = sorted(
        alive,
        key=lambda party: votes[party],
        reverse=True,
    )

    winner = final_two[0]
    runner_up = final_two[1]

    final_total = votes[winner] + votes[runner_up]

    winner_pct = votes[winner] / final_total if final_total else 0
    runner_up_pct = votes[runner_up] / final_total if final_total else 0

    return {
        "winner": winner,
        "runner_up": runner_up,
        "winner_pct": winner_pct,
        "runner_up_pct": runner_up_pct,
        "margin": winner_pct - 0.5,
        "matchup": f"{winner}-{runner_up}",
        "elimination_order": ">".join(elimination_order),
        "final_votes": votes,
    }


def run_forced_2pp_for_district(
    district_votes: dict[str, float],
    matrix: dict,
    seat_type: str,
    params: dict,
    posterior: dict,
    ideology: dict,
    party_a: str = "ALP",
    party_b: str = "LNP",
) -> dict:

    parcels = initialise_parcels(district_votes)
    votes = parcel_totals(parcels)

    alive = [
        party for party in PARTIES
        if votes.get(party, 0) > 0
    ]

    for forced_party in [party_a, party_b]:
        if forced_party not in alive:
            alive.append(forced_party)
            votes[forced_party] = 0.0

    elimination_order = []

    while len(alive) > 2:

        removable = [
            party for party in alive
            if party not in [party_a, party_b]
        ]

        if not removable:
            break

        eliminated = min(removable, key=lambda party: votes[party])
        elimination_order.append(eliminated)

        alive = [
            party for party in alive
            if party != eliminated
        ]

        distribute_parcel_holder(
            parcels=parcels,
            holder=eliminated,
            alive_after=alive,
            matrix=matrix,
            seat_type=seat_type,
            params=params,
            posterior=posterior,
            ideology=ideology,
        )
        votes = parcel_totals(parcels)

    total = votes[party_a] + votes[party_b]

    party_a_pct = votes[party_a] / total if total else 0
    party_b_pct = votes[party_b] / total if total else 0

    return {
        f"{party_a}_2pp": party_a_pct,
        f"{party_b}_2pp": party_b_pct,
        "forced_2pp_elimination_order": ">".join(elimination_order),
    }


def trace_irv_for_district(
    district_votes: dict[str, float],
    matrix: dict,
    seat_type: str,
    params: dict,
    posterior: dict,
    ideology: dict,
) -> list[dict]:

    parcels = initialise_parcels(district_votes)
    votes = parcel_totals(parcels)

    alive = [
        party for party in PARTIES
        if votes.get(party, 0) > 0
    ]

    trace_rows = []

    trace_rows.append({
        "round": "Primary",
        "eliminated": "",
        **{party: votes[party] for party in PARTIES},
        **{f"{party}_flow": None for party in PARTIES},
    })

    round_no = 1

    while len(alive) > 2:

        eliminated = min(alive, key=lambda party: votes[party])
        eliminated_votes = votes[eliminated]

        alive_after = [
            party for party in alive
            if party != eliminated
        ]

        diagnostics, flows, origin_rows = distribute_parcel_holder(
            parcels=parcels,
            holder=eliminated,
            alive_after=alive_after,
            matrix=matrix,
            seat_type=seat_type,
            params=params,
            posterior=posterior,
            ideology=ideology,
        )
        final_stage = diagnostics["stages"][-1]
        votes = parcel_totals(parcels)

        trace_rows.append({
            "round": f"Round {round_no}",
            "eliminated": eliminated,
            "source": preference_source_category(diagnostics["basis"]),
            "basis": diagnostics["basis"],
            "evidence_seats": final_stage.get("evidence_seats"),
            "reliability": final_stage.get("posterior_reliability"),
            "parcel_origins": len(origin_rows),
            "origin_retention": parcel_origin_retention(params),
            **{party: votes[party] for party in PARTIES},
            **{
                f"{party}_flow": flows.get(party, None)
                if party in alive_after else None
                for party in PARTIES
            },
        })

        alive = alive_after
        round_no += 1

    return trace_rows


def trace_preference_diagnostics_for_district(
    district_votes: dict[str, float],
    matrix: dict,
    seat_type: str,
    params: dict,
    posterior: dict,
    ideology: dict,
) -> list[dict]:

    parcels = initialise_parcels(district_votes)
    votes = parcel_totals(parcels)

    alive = [
        party for party in PARTIES
        if votes.get(party, 0) > 0
    ]

    diagnostic_rows = []
    round_no = 1

    while len(alive) > 2:

        eliminated = min(alive, key=lambda party: votes[party])
        eliminated_votes = votes[eliminated]

        alive_after = [
            party for party in alive
            if party != eliminated
        ]

        diagnostics, effective_flows, origin_rows = distribute_parcel_holder(
            parcels=parcels,
            holder=eliminated,
            alive_after=alive_after,
            matrix=matrix,
            seat_type=seat_type,
            params=params,
            posterior=posterior,
            ideology=ideology,
        )

        for stage_no, stage in enumerate(diagnostics["stages"], start=1):
            diagnostic_rows.append({
                "round": f"Round {round_no}",
                "stage_no": stage_no,
                "eliminated": eliminated,
                "eliminated_vote": eliminated_votes,
                "alive": ">".join(alive_after),
                "source": preference_source_category(diagnostics["basis"]),
                **stage,
            })
        diagnostic_rows.append({
            "round": f"Round {round_no}",
            "stage_no": len(diagnostics["stages"]) + 1,
            "eliminated": eliminated,
            "eliminated_vote": eliminated_votes,
            "alive": ">".join(alive_after),
            "source": "Parcel-aware aggregate",
            "stage": "parcel-origin aggregate",
            "note": (
                "Effective flow after preserving primary-origin parcels; "
                "ON special priors remain locked at holder level."
            ),
            "basis": diagnostics["basis"],
            "origin_retention": parcel_origin_retention(params),
            "parcel_origins": len(origin_rows),
            **{
                party: effective_flows.get(party)
                if party in alive_after else None
                for party in PARTIES
            },
        })
        votes = parcel_totals(parcels)

        alive = alive_after
        round_no += 1

    return diagnostic_rows


def run_irv_all(
    primary_votes_df,
    matrices,
    params,
    posterior,
    ideology,
):
    results = []

    for district, group in primary_votes_df.groupby("district"):

        first_row = group.iloc[0]
        key = district_key(district)

        if key not in matrices:
            raise ValueError(
                f"No preference matrix found for district: {district}"
            )

        matrix = matrices[key]["matrix"]

        district_votes = {
            row["party"]: row["primary_vote"]
            for _, row in group.iterrows()
        }

        result = run_irv_for_district(
            district_votes=district_votes,
            matrix=matrix,
            seat_type=first_row["seat_type"],
            params=params,
            posterior=posterior,
            ideology=ideology,
        )

        forced_alp_lnp_2pp = run_forced_2pp_for_district(
            district_votes=district_votes,
            matrix=matrix,
            seat_type=first_row["seat_type"],
            params=params,
            posterior=posterior,
            ideology=ideology,
            party_a="ALP",
            party_b="LNP",
        )

        forced_alp_on_2cp = run_forced_2pp_for_district(
            district_votes=district_votes,
            matrix=matrix,
            seat_type=first_row["seat_type"],
            params=params,
            posterior=posterior,
            ideology=ideology,
            party_a="ALP",
            party_b="ON",
        )

        results.append({
            "district": district,
            "region": first_row["region"],
            "held_by": first_row["held_by"],

            "winner": result["winner"],
            "runner_up": result["runner_up"],
            "winner_pct": result["winner_pct"],
            "runner_up_pct": result["runner_up_pct"],
            "margin": result["margin"],
            "matchup": result["matchup"],
            "elimination_order": result["elimination_order"],

            "ALP_2PP": forced_alp_lnp_2pp["ALP_2pp"],
            "LNP_2PP": forced_alp_lnp_2pp["LNP_2pp"],
            "forced_2pp_elimination_order": forced_alp_lnp_2pp[
                "forced_2pp_elimination_order"
            ],

            "ALP_ON_2CP": forced_alp_on_2cp["ALP_2pp"],
            "ON_ALP_2CP": forced_alp_on_2cp["ON_2pp"],
            "forced_alp_on_2cp_elimination_order": forced_alp_on_2cp[
                "forced_2pp_elimination_order"
            ],
        })

    return results
