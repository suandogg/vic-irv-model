from SRC.loaders import load_seat_helper
from SRC.transform import build_primary_vote_table
from SRC.matrix_loader import load_synth_pref_matrices
from SRC.params_loader import load_params
from SRC.posterior_loader import load_posterior_scenarios
from SRC.ideology_loader import load_ideology_prior
from SRC.preference_engine import get_preference_weights
from SRC.constants import PARTIES


SEAT_TO_TRACE = "Williamstown"


def pct(x):
    return round(float(x or 0) * 100, 2)


def main():
    seat_helper = load_seat_helper()
    primary_votes = build_primary_vote_table(seat_helper)
    matrices = load_synth_pref_matrices()
    params = load_params()
    posterior = load_posterior_scenarios()
    ideology = load_ideology_prior()

    group = primary_votes[primary_votes["district"] == SEAT_TO_TRACE].copy()
    first = group.iloc[0]

    seat_type = first["seat_type"]
    matrix = matrices[SEAT_TO_TRACE.upper()]["matrix"]

    votes = {row["party"]: float(row["primary_vote"]) for _, row in group.iterrows()}
    alive = [p for p in PARTIES if votes.get(p, 0) > 0]

    print()
    print("TRACE SEAT:", SEAT_TO_TRACE)
    print("Seat type:", seat_type)

    round_no = 1

    while len(alive) > 2:
        eliminated = min(alive, key=lambda p: votes[p])
        alive_after = [p for p in alive if p != eliminated]

        print()
        print("=" * 70)
        print("ROUND", round_no)
        print("Eliminated:", eliminated)
        print("Alive after:", "+".join(alive_after))

        print()
        print("Current votes:")
        for p in PARTIES:
            print(p, pct(votes.get(p, 0)))

        print()
        print("Raw matrix row:")
        raw = matrix.get(eliminated, {})
        for p in PARTIES:
            print(p, pct(raw.get(p, 0)))

        post_key = f"{eliminated}|{'+'.join(sorted(alive_after))}"
        print()
        print("Posterior key:", post_key)
        print("Posterior row:", posterior.get(post_key))

        special_key = f"{'+'.join(sorted(alive_after))}|{eliminated}|{seat_type}"
        print()
        print("ON special key:", special_key)
        print("ON special row:", params.get("on_special_scenario_priors", {}).get(special_key))

        print()
        print("Final Python weights:")
        weights = get_preference_weights(
            eliminated_party=eliminated,
            alive_parties=alive_after,
            matrix=matrix,
            geography_class=seat_type,
            params=params,
            posterior=posterior,
            ideology=ideology,
        )

        for p in alive_after:
            print(p, pct(weights.get(p, 0)))

        transfer = votes[eliminated]
        votes[eliminated] = 0

        for p in alive_after:
            votes[p] += transfer * weights.get(p, 0)

        alive = alive_after
        round_no += 1


if __name__ == "__main__":
    main()