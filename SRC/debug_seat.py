from SRC.loaders import load_seat_helper
from SRC.transform import build_primary_vote_table
from SRC.matrix_loader import load_synth_pref_matrices
from SRC.params_loader import load_params
from SRC.posterior_loader import load_posterior_scenarios
from SRC.ideology_loader import load_ideology_prior
from SRC.preference_engine import get_preference_weights
from SRC.constants import PARTIES


SEAT_TO_DEBUG = "Morwell"


def pct(x):
    return round(float(x or 0) * 100, 2)


def district_key(name):
    return str(name).strip().upper()


def print_param_debug(params):
    print()
    print("PARAM DEBUG")
    print("PARAM KEYS:", params.keys())

    print()
    print("DIRECT PARAM CHECK")
    specials = params.get("on_special_scenario_priors", {})

    keys_to_check = [
        "LNP+ON|ALP|Provincial",
        "LNP+ON|ALP|PROVINCIAL",
        "LNP+ON|ALP|Regional",
        "LNP+ON|ALP|REGIONAL",
        "ALP+ON|LNP|Provincial",
        "ALP+ON|LNP|PROVINCIAL",
    ]

    for key in keys_to_check:
        print(key, "=>", specials.get(key))

    print()
    print("ON SPECIAL PRIOR KEYS SAMPLE:")
    for key in list(specials.keys())[:30]:
        print(key)

    print()
    print("=" * 60)


def main():
    seat_helper = load_seat_helper()
    primary_votes = build_primary_vote_table(seat_helper)
    matrices = load_synth_pref_matrices()
    params = load_params()
    posterior = load_posterior_scenarios()
    ideology = load_ideology_prior()

    print_param_debug(params)

    district_votes = primary_votes[
        primary_votes["district"] == SEAT_TO_DEBUG
    ].copy()

    if district_votes.empty:
        raise ValueError(f"No district found: {SEAT_TO_DEBUG}")

    seat_info = district_votes.iloc[0]

    district = seat_info["district"]
    region = seat_info["region"]
    seat_type = seat_info["seat_type"]
    held_by = seat_info["held_by"]

    matrix_key = district_key(district)

    if matrix_key not in matrices:
        raise ValueError(f"No matrix found for {district} using key {matrix_key}")

    matrix = matrices[matrix_key]["matrix"]

    print()
    print(f"DEBUGGING: {district}")
    print(f"Region: {region}")
    print(f"Seat type: {seat_type}")
    print(f"Held by: {held_by}")

    votes = {
        row["party"]: float(row["primary_vote"])
        for _, row in district_votes.iterrows()
    }

    for party in PARTIES:
        votes.setdefault(party, 0)

    alive = [
        party for party in PARTIES
        if votes[party] > 0
    ]

    print()
    print("INITIAL PRIMARY VOTES")
    for party in PARTIES:
        print(party, pct(votes[party]))

    round_num = 1

    while len(alive) > 2:
        print()
        print("=" * 50)
        print(f"ROUND {round_num}")

        eliminated = min(alive, key=lambda p: votes[p])

        print("Alive before:", alive)
        print("Eliminated:", eliminated, pct(votes[eliminated]))

        alive_after = [
            p for p in alive
            if p != eliminated
        ]

        flows = get_preference_weights(
            eliminated_party=eliminated,
            alive_parties=alive_after,
            matrix=matrix,
            geography_class=seat_type,
            params=params,
            posterior=posterior,
            ideology=ideology
        )

        print()
        print("Redistribution weights:")
        for party in alive_after:
            print(party, pct(flows.get(party, 0)))

        if "ON" in alive_after:
            raw_key = (
                f'{"+".join(sorted(alive_after))}'
                f'|{eliminated}'
                f'|{seat_type}'
            )

            upper_key = (
                f'{"+".join(sorted(alive_after))}'
                f'|{eliminated}'
                f'|{str(seat_type).upper()}'
            )

            special = params.get("on_special_scenario_priors", {})

            print()
            print("ON SPECIAL DEBUG")
            print("Raw key:", raw_key)
            print("Raw prior:", special.get(raw_key))
            print("Upper key:", upper_key)
            print("Upper prior:", special.get(upper_key))

        transfer_votes = votes[eliminated]
        votes[eliminated] = 0

        for party in alive_after:
            votes[party] += transfer_votes * flows.get(party, 0)

        alive = alive_after

        print()
        print("Votes after redistribution:")
        for party in PARTIES:
            print(party, pct(votes[party]))

        round_num += 1

    print()
    print("=" * 50)

    final_two = sorted(
        alive,
        key=lambda p: votes[p],
        reverse=True
    )

    winner = final_two[0]
    runner_up = final_two[1]

    total = votes[winner] + votes[runner_up]

    print("FINAL TWO:", final_two)
    print("Winner:", winner, pct(votes[winner] / total))
    print("Runner-up:", runner_up, pct(votes[runner_up] / total))
    print("Margin:", round((votes[winner] / total - 0.5) * 100, 2))


if __name__ == "__main__":
    main()