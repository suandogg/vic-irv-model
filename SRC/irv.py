from SRC.constants import PARTIES
from SRC.preference_engine import (
    diagnose_preference_weights,
    get_preference_weights,
)


def district_key(name: str) -> str:
    return str(name).strip().upper()


def initialise_votes(district_votes: dict[str, float]) -> dict[str, float]:
    return {
        party: float(district_votes.get(party, 0) or 0)
        for party in PARTIES
    }


def run_irv_for_district(
    district_votes: dict[str, float],
    matrix: dict,
    seat_type: str,
    params: dict,
    posterior: dict,
    ideology: dict,
) -> dict:

    votes = initialise_votes(district_votes)

    alive = [
        party for party in PARTIES
        if votes.get(party, 0) > 0
    ]

    elimination_order = []

    while len(alive) > 2:

        eliminated = min(alive, key=lambda party: votes[party])
        eliminated_votes = votes[eliminated]

        elimination_order.append(eliminated)

        alive = [
            party for party in alive
            if party != eliminated
        ]

        flows = get_preference_weights(
            eliminated_party=eliminated,
            alive_parties=alive,
            matrix=matrix,
            geography_class=seat_type,
            params=params,
            posterior=posterior,
            ideology=ideology,
        )

        votes[eliminated] = 0

        for party, share in flows.items():
            votes[party] += eliminated_votes * share

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

    votes = initialise_votes(district_votes)

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
        eliminated_votes = votes[eliminated]

        elimination_order.append(eliminated)

        alive = [
            party for party in alive
            if party != eliminated
        ]

        flows = get_preference_weights(
            eliminated_party=eliminated,
            alive_parties=alive,
            matrix=matrix,
            geography_class=seat_type,
            params=params,
            posterior=posterior,
            ideology=ideology,
        )

        votes[eliminated] = 0

        for party, share in flows.items():
            votes[party] += eliminated_votes * share

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

    votes = initialise_votes(district_votes)

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

        flows = get_preference_weights(
            eliminated_party=eliminated,
            alive_parties=alive_after,
            matrix=matrix,
            geography_class=seat_type,
            params=params,
            posterior=posterior,
            ideology=ideology,
        )

        votes[eliminated] = 0

        for party in alive_after:
            votes[party] += eliminated_votes * flows.get(party, 0)

        trace_rows.append({
            "round": f"Round {round_no}",
            "eliminated": eliminated,
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

    votes = initialise_votes(district_votes)

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

        diagnostics = diagnose_preference_weights(
            eliminated_party=eliminated,
            alive_parties=alive_after,
            matrix=matrix,
            geography_class=seat_type,
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
                **stage,
            })

        votes[eliminated] = 0

        for party, share in diagnostics["final_flows"].items():
            votes[party] += eliminated_votes * share

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
