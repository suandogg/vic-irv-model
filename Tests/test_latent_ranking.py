from SRC.latent_ranking import (
    count_latent_irv,
    enumerate_ranked_ballots,
    fit_voter_type_mixture,
)


def test_ranking_probabilities_sum_to_one():
    utilities = {"LNP": 1.0, "GRN": 0.5, "ON": 0.0, "IND": -0.5, "OTH": -1.0}
    cohorts = enumerate_ranked_ballots("ALP", utilities)
    assert len(cohorts) == 120
    assert abs(sum(row["probability"] for row in cohorts) - 1.0) < 1e-12


def test_coherent_ballots_are_conserved_and_deterministic():
    ballots = [
        {"origin": "ALP", "ranking": ("ALP", "GRN", "LNP", "ON", "IND", "OTH"), "votes": 0.4},
        {"origin": "LNP", "ranking": ("LNP", "ON", "ALP", "GRN", "IND", "OTH"), "votes": 0.35},
        {"origin": "GRN", "ranking": ("GRN", "ALP", "LNP", "ON", "IND", "OTH"), "votes": 0.25},
    ]
    first = count_latent_irv(ballots)
    second = count_latent_irv(ballots)
    assert first == second
    assert abs(sum(first["final_votes"].values()) - 1.0) < 1e-12
    assert first["winner"] == "ALP"


def test_voter_type_weights_are_valid_and_improve_pairwise_fit():
    observations = [
        {"party_a": "ALP", "party_b": "LNP", "observed_party_a": 0.70, "weight": 2.0},
        {"party_a": "ALP", "party_b": "GRN", "observed_party_a": 0.40, "weight": 2.0},
        {"party_a": "ALP", "party_b": "ON", "observed_party_a": 0.75, "weight": 2.0},
        {"party_a": "ALP", "party_b": "OTH", "observed_party_a": 0.65, "weight": 2.0},
        {"party_a": "LNP", "party_b": "GRN", "observed_party_a": 0.65, "weight": 2.0},
        {"party_a": "LNP", "party_b": "ON", "observed_party_a": 0.55, "weight": 2.0},
        {"party_a": "LNP", "party_b": "OTH", "observed_party_a": 0.60, "weight": 2.0},
        {"party_a": "GRN", "party_b": "ON", "observed_party_a": 0.60, "weight": 2.0},
        {"party_a": "GRN", "party_b": "OTH", "observed_party_a": 0.55, "weight": 2.0},
        {"party_a": "ON", "party_b": "OTH", "observed_party_a": 0.60, "weight": 2.0},
    ]
    base_fit = {
        "origin": "IND",
        "utilities": {"ALP": 0.4, "LNP": 0.2, "GRN": 0.0, "ON": -0.1, "OTH": -0.2},
        "observations": observations,
    }
    fitted = fit_voter_type_mixture(base_fit)
    assert abs(sum(fitted["weights"].values()) - 1.0) < 1e-12
    assert all(value >= 0 for value in fitted["weights"].values())
    assert fitted["pairwise_rmse"] < 0.20
